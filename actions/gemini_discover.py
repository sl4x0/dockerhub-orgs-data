#!/usr/bin/env python3
"""
Gemini-powered DockerHub organization discovery.

Strategy
--------
1. For each program URL, ask Gemini to return confident DockerHub username
   candidates based on its world-knowledge of the company.
2. Verify each candidate with a HEAD request to hub.docker.com/v2/users/.
3. Return the first confirmed username as a full hub.docker.com/u/ URL.

Rate-limit handling (NO fuzzy fallback, NO giving up)
------------------------------------------------------
Keys are rotated round-robin across all models.  When a key hits a
per-minute throttle (429 + retryDelay) it is parked until the delay expires
and the NEXT key is tried immediately.  If ALL keys are parked at the same
time the code SLEEPS until the earliest one unblocks — no program is ever
skipped due to a temporary rate limit.

A key is permanently killed only when it returns a true daily exhaustion
("limit: 0" in the 429 body).  If every key is daily-dead the function
returns None with status='daily_dead' so the caller can leave the program
as '?' and retry on the next daily run.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Models confirmed available on free-tier keys (as of Feb 2026).
# Cheapest/fastest first; only escalate when cheaper model is 404.
# gemini-2.0-flash-lite: 30 RPM / 1500 RPD free — ideal for bulk discovery.
# gemini-2.0-flash: 15 RPM / 1500 RPD free — fallback.
# gemini-1.5-flash: widely available, good free quota.
# gemini-1.5-pro: highest quality, lower quota — last resort.
MODELS: List[str] = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

# Safety cap: if we have been waiting for throttled keys for longer than
# this many seconds total (across all sleeps for one program), give up on
# that program and leave as '?'.  Prevents a single broken key from
# blocking the run for hours.  Set to 0 to wait indefinitely.
MAX_TOTAL_WAIT_SECONDS: int = 600  # 10 minutes per program is plenty

HEADERS = {
    "User-Agent": "dockerhub-orgs-data/2.0 (https://github.com/sl4x0/dockerhub-orgs-data)"
}

# ---------------------------------------------------------------------------
# System prompt — precision-tuned for zero false positives
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an expert security researcher specialising in container-image
reconnaissance for bug bounty programs.  Your ONLY job is to map a bug
bounty program URL to its official DockerHub organisation(s).

You have access to Google Search — USE IT to verify current DockerHub
presence before answering.  Search for things like:
  "<company name> docker hub"
  "hub.docker.com/u/<candidate>"
  "<company name> container registry"
Only include a username if your search CONFIRMS it exists on hub.docker.com.

OUTPUT FORMAT
• Return a valid JSON array of strings — nothing else, no markdown, no prose.
• The VERY LAST line of your response must be the JSON array and nothing else.
• Empty array [] if you cannot confirm any DockerHub org after searching.

CANDIDATE RULES
1. Include ONLY usernames CONFIRMED to exist on hub.docker.com via search.
   Do NOT guess, hallucinate, or invent names you are unsure about.
2. Order by confidence — most likely first.
3. Maximum 8 candidates.
4. DockerHub username constraints: lowercase, 4–30 chars, alphanumeric + hyphens.
5. One company can own multiple orgs — include all known ones.
   Examples: engineering sandboxes, product-specific orgs, legacy orgs.
6. For large tech companies include their well-known sub-orgs:
   • Google  → google, googlecloudplatform, googlesamples, kubernetes, tensorflow
   • AWS     → amazon, amazonlinux, aws-cli
   • MS      → microsoft
   • Meta    → meta, pytorch
7. The URL may be a bug-bounty platform handle OR a company's own domain.
   Use the extracted company identifier as your primary search term.

QUALITY OVER QUANTITY — a short correct list beats a long speculative one.

Example final-line outputs:
  ["shopify"]
  ["gitlab", "gitlab-org"]
  ["google", "googlecloudplatform", "googlesamples", "kubernetes", "tensorflow"]
  []
"""

# ---------------------------------------------------------------------------
# Key pool state (module-level singletons)
# ---------------------------------------------------------------------------
_keys: List[str] = []
_key_index: int = 0
_key_blocked_until: Dict[str, float] = {}   # key -> epoch when usable again
_key_daily_dead:    Dict[str, bool]  = {}   # key -> True = dead for today


def set_keys(keys: List[str]) -> None:
    """Configure the key pool. Call before any discover_*() function."""
    global _keys, _key_index, _key_blocked_until, _key_daily_dead
    clean = [k.strip() for k in keys if k.strip()]
    _keys              = clean
    _key_index         = 0
    _key_blocked_until = {}
    _key_daily_dead    = {k: False for k in clean}


def _load_keys_from_env() -> None:
    raw = (
        os.environ.get("GEMINI_API_KEYS", "")
        or os.environ.get("GEMINI_API_KEY", "")
    )
    if raw:
        set_keys([k.strip() for k in re.split(r"[,\n]+", raw) if k.strip()])


def _live_keys() -> List[str]:
    """Keys that are not daily-dead (may still be temporarily throttled)."""
    return [k for k in _keys if not _key_daily_dead.get(k)]


def _next_usable_key() -> Optional[str]:
    """Return the next non-dead, non-throttled key (round-robin)."""
    if not _keys:
        return None
    now = time.time()
    for _ in range(len(_keys)):
        key = _keys[_key_index % len(_keys)]
        if not _key_daily_dead.get(key) and now >= _key_blocked_until.get(key, 0):
            return key
        _rotate_key()
    return None


def _rotate_key() -> None:
    global _key_index
    _key_index = (_key_index + 1) % max(len(_keys), 1)


def _park_key(key: str, retry_delay_s: int) -> None:
    """Temporarily block a key until its rate-limit window expires."""
    _key_blocked_until[key] = time.time() + retry_delay_s + 2
    _rotate_key()


def _kill_key(key: str) -> None:
    """Mark a key as daily-dead (quota fully exhausted for today)."""
    _key_daily_dead[key] = True
    _rotate_key()


def _wait_for_any_key(spent_waiting: float) -> Tuple[bool, float]:
    """Sleep until the earliest throttled-but-alive key unblocks.

    Returns:
        (can_continue, new_spent_waiting)
        can_continue = False means every key is daily-dead — caller should abort.
    """
    live = _live_keys()
    if not live:
        return False, spent_waiting  # all daily dead

    now   = time.time()
    wakeup = min(_key_blocked_until.get(k, 0) for k in live)
    sleep  = max(wakeup - now + 1, 1)  # at least 1s

    if MAX_TOTAL_WAIT_SECONDS > 0 and spent_waiting + sleep > MAX_TOTAL_WAIT_SECONDS:
        remaining = MAX_TOTAL_WAIT_SECONDS - spent_waiting
        if remaining <= 0:
            print(f"    [Gemini] Max wait time reached ({MAX_TOTAL_WAIT_SECONDS}s) — leaving as '?'")
            return False, MAX_TOTAL_WAIT_SECONDS  # signal caller: cap hit
        sleep = remaining

    print(f"    [Gemini] All keys throttled — sleeping {int(sleep)}s …", flush=True)
    time.sleep(sleep)
    return True, spent_waiting + sleep


# ---------------------------------------------------------------------------
# Gemini API call — wait-and-retry, never gives up on throttled keys
# ---------------------------------------------------------------------------

def _parse_429(body: str) -> Tuple[bool, int]:
    """Return (is_daily_exhausted, retry_delay_seconds)."""
    is_daily = False
    delay    = 65  # default: wait >1 minute to be safe
    try:
        data = json.loads(body)
        msg  = data.get("error", {}).get("message", "")
        # True daily exhaustion always says "limit: 0" in the message
        is_daily = bool(re.search(r"limit:\s*0", msg))
        for detail in data.get("error", {}).get("details", []):
            if detail.get("@type", "").endswith("RetryInfo"):
                rd = detail.get("retryDelay", "65s")
                m  = re.match(r"(\d+)", rd)
                if m:
                    delay = int(m.group(1))
    except Exception:
        pass
    return is_daily, delay


def _call_gemini(prompt_url: str, company_hint: str = "") -> Tuple[Optional[List[str]], str]:
    """Send prompt to Gemini; block/sleep until keys unthrottle.

    Returns:
        (candidates, status)
        candidates  = List[str] on success (may be empty list = AI unsure)
        candidates  = None on permanent failure
        status      = 'ok' | 'daily_dead' | 'max_wait' | 'no_keys' | 'error'
    """
    if not _keys:
        return None, 'no_keys'

    user_text = f"Bug bounty program URL: {prompt_url}"
    if company_hint:
        user_text += f"\nExtracted company identifier: {company_hint}"

    _contents  = [{"role": "user", "parts": [{"text": user_text}]}]
    _sysinstruct = {"parts": [{"text": SYSTEM_PROMPT}]}
    _genconf_base = {"temperature": 0.0, "maxOutputTokens": 1024}

    # Primary payload: Google Search grounding enabled.
    # responseMimeType must NOT be set when tools are active.
    payload_grounded = json.dumps({
        "system_instruction": _sysinstruct,
        "contents": _contents,
        "tools": [{"google_search": {}}],
        "generationConfig": _genconf_base,
    }).encode()

    # Fallback payload: no tools (for models that reject google_search with 400).
    # Use responseMimeType=application/json so the output is clean JSON.
    payload_plain = json.dumps({
        "system_instruction": _sysinstruct,
        "contents": _contents,
        "generationConfig": {**_genconf_base, "responseMimeType": "application/json"},
    }).encode()

    # Track which (key, model) combos have already been tried in plain mode
    tried_plain: set = set()

    tried:          set   = set()          # (key, model) pairs already attempted
    spent_waiting:  float = 0.0

    while True:
        # ——— check if we've tried every combo ———
        live = _live_keys()
        if not live:
            return None, 'daily_dead'

        # Skip dead keys from our tried-combo count
        remaining = sum(
            1 for k in live for m in MODELS if (k, m) not in tried
        )
        if remaining == 0:
            # Every live key + model combo has been tried with 404 (model N/A)
            # That means no model is available on any key
            return None, 'error'

        # ——— get next usable key ———
        key = _next_usable_key()
        if key is None:
            ok, spent_waiting = _wait_for_any_key(spent_waiting)
            if not ok:
                return None, 'max_wait'
            continue  # retry after sleep

        # ——— try all models for this key ———
        rotated = False
        for model in MODELS:
            if (key, model) in tried:
                continue
            tried.add((key, model))

            api_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={key}"
            )
            # Choose grounded payload; fall back to plain if model rejected tools
            use_plain   = (key, model) in tried_plain
            active_payload = payload_plain if use_plain else payload_grounded
            req = urllib.request.Request(
                api_url, data=active_payload, method="POST",
                headers={"Content-Type": "application/json", **HEADERS},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode())
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if use_plain:
                    # Plain mode: response is pure JSON
                    try:
                        result = json.loads(text)
                    except json.JSONDecodeError:
                        result = []
                else:
                    # Grounded mode: extract the LAST valid JSON array from the
                    # response text.  Gemini grounding adds citation markers like
                    # [1], [2] BEFORE the final answer, so we must take the last
                    # parseable [...] block, not the first.
                    # Only accept arrays where ALL elements are strings — citation
                    # markers like [1] are valid JSON but contain integers, not
                    # DockerHub usernames.
                    result = []
                    for m in re.finditer(r'(\[[^\[\]]*\])', text):
                        try:
                            parsed = json.loads(m.group(1))
                            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                                result = parsed   # keep updating — last valid wins
                        except json.JSONDecodeError:
                            pass
                    # Also try full multiline array in case answer spans lines
                    if not result:
                        m2 = re.search(r'(\[[\s\S]*?\])', text)
                        if m2:
                            try:
                                parsed2 = json.loads(m2.group(1))
                                if isinstance(parsed2, list) and all(isinstance(x, str) for x in parsed2):
                                    result = parsed2
                            except json.JSONDecodeError:
                                pass
                candidates = [str(c).strip().lower() for c in result if c] \
                             if isinstance(result, list) else []
                return candidates, 'ok'

            except urllib.error.HTTPError as e:
                body = e.read().decode()
                if e.code == 429:
                    is_daily, delay = _parse_429(body)
                    if is_daily:
                        print(f"    [Gemini] Daily quota dead — key …{key[-6:]}")
                        _kill_key(key)
                    else:
                        print(f"    [Gemini] Throttled {delay}s — parking key …{key[-6:]}")
                        _park_key(key, delay)
                    rotated = True
                    break  # rotate to next key
                elif e.code == 400 and not use_plain:
                    # Model rejected google_search tool — retry without grounding
                    print(f"    [Gemini] {model} no grounding support — retrying plain")
                    tried_plain.add((key, model))
                    tried.discard((key, model))  # allow re-try in plain mode
                    continue
                elif e.code == 404:
                    # Model not available on this project — try next model
                    continue
                elif e.code == 403:
                    print(f"    [Gemini] Auth error (403) — killing key …{key[-6:]}")
                    _kill_key(key)
                    rotated = True
                    break
                else:
                    print(f"    [Gemini] HTTP {e.code} on {model} — trying next model")
                    continue

            except Exception as ex:
                print(f"    [Gemini] {model} exception: {str(ex)[:80]}")
                continue

        if not rotated:
            # All models on this key returned 404 — rotate manually
            _rotate_key()



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_dockerhub(
    program_url: str,
    verify_fn=None,
    company_hint: str = "",
) -> Tuple[Optional[str], str]:
    """Ask Gemini for DockerHub candidates and verify each against the API.

    Blocks/sleeps when keys are temporarily throttled — never skips a program
    due to a per-minute rate limit.  Only returns early when:
      - All keys are daily-dead (can't help today)
      - MAX_TOTAL_WAIT_SECONDS exceeded (safety valve)
      - Gemini responded but confirmed no DockerHub presence

    Args:
        program_url:  Bug bounty program URL.
        verify_fn:    callable(username) -> Optional[bool].
                      True = exists, False = 404, None = transient error.
        company_hint: Clean company name extracted from the URL slug (e.g.
                      'comcast' for 'comcast-mbb').  Included in the prompt
                      so Gemini can resolve ambiguous slugs correctly.

    Returns:
        (url, status)  where url is hub.docker.com/u/<name> or None.
        status: 'found' | 'not_found' | 'daily_dead' | 'max_wait' |
                'no_keys' | 'error'
    """
    if not _keys:
        _load_keys_from_env()
    if not _keys:
        return None, 'no_keys'

    if verify_fn is None:
        verify_fn = _default_verify

    print(f"    [Gemini] Querying AI …")
    candidates, status = _call_gemini(program_url, company_hint)

    if status != 'ok':
        return None, status

    if not candidates:
        print(f"    [Gemini] AI has no confident candidates")
        return None, 'not_found'

    # Sanitize to valid DockerHub username chars
    valid = [re.sub(r"[^a-z0-9\-]", "", c) for c in candidates]
    valid = [c for c in valid if 2 <= len(c) <= 64]
    print(f"    [Gemini] Candidates: {valid}")

    for username in valid:
        result = verify_fn(username)
        if result is True:
            url = f"https://hub.docker.com/u/{username}"
            print(f"    [Gemini] ✅ CONFIRMED: {url}")
            return url, 'found'
        elif result is False:
            print(f"    [Gemini] ✗ {username} — not on DockerHub")
        else:
            print(f"    [Gemini] ? {username} — transient check error, skipping")

    return None, 'not_found'


def has_live_keys() -> bool:
    """True if at least one key is alive (not daily-dead); may still be throttled."""
    if not _keys:
        _load_keys_from_env()
    return any(not _key_daily_dead.get(k) for k in _keys)


def is_available() -> bool:
    """True if at least one key is both alive AND not currently throttled."""
    if not _keys:
        _load_keys_from_env()
    now = time.time()
    return any(
        not _key_daily_dead.get(k) and now >= _key_blocked_until.get(k, 0)
        for k in _keys
    )


def _default_verify(username: str) -> Optional[bool]:
    url = f"https://hub.docker.com/v2/users/{username}"
    req = urllib.request.Request(url, method="HEAD", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return None  # transient
    except Exception:
        return None

