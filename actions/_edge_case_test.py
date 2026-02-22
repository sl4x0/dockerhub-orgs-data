#!/usr/bin/env python3
"""Edge case tests for gemini_discover — run before any release."""
import sys, re, json, os
sys.path.insert(0, 'actions')
import gemini_discover

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
errors = 0

def check(name, got, expected):
    global errors
    if got == expected:
        print(f"  {PASS}  {name}")
    else:
        print(f"  {FAIL}  {name} — expected {expected!r}, got {got!r}")
        errors += 1

print("=" * 60)
print("gemini_discover edge-case tests")
print("=" * 60)

# ------------------------------------------------------------------
# Helper: mirrors production grounded-response extraction
# ------------------------------------------------------------------
def extract_last_json_str_array(text):
    """Last string-only JSON array in text (rejects integer citation arrays)."""
    result = []
    for m in re.finditer(r'(\[[^\[\]]*\])', text):
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                result = parsed
        except json.JSONDecodeError:
            pass
    if not result:
        m2 = re.search(r'(\[[\s\S]*?\])', text)
        if m2:
            try:
                parsed2 = json.loads(m2.group(1))
                if isinstance(parsed2, list) and all(isinstance(x, str) for x in parsed2):
                    result = parsed2
            except json.JSONDecodeError:
                pass
    return result


# ------------------------------------------------------------------
# 1. Regex: citation markers [1][2] before final JSON array
# ------------------------------------------------------------------
check("1 last-array wins over [1] citations",
      extract_last_json_str_array('Shopify on DockerHub [1][2].\n["shopify"]'),
      ["shopify"])

# ------------------------------------------------------------------
# 2. Regex: multi-candidate array at end
# ------------------------------------------------------------------
check("2 multi-candidate array extracted",
      extract_last_json_str_array('Sources [1][2].\n["google", "googlecloudplatform"]'),
      ["google", "googlecloudplatform"])

# ------------------------------------------------------------------
# 3. Regex: citations only — integer arrays rejected, result = []
# ------------------------------------------------------------------
check("3 citations-only response -> []",
      extract_last_json_str_array("See [1] and [2] for more information about this company."),
      [])

# ------------------------------------------------------------------
# 4. Regex: plain [] (AI confident no org exists)
# ------------------------------------------------------------------
check("4 plain [] response parsed correctly",
      extract_last_json_str_array("I searched and found no DockerHub org.\n[]"),
      [])

# ------------------------------------------------------------------
# 4b. Integer-only array rejected
# ------------------------------------------------------------------
check("4b integer-only array rejected",
      extract_last_json_str_array("[1, 2, 3]"),
      [])

# ------------------------------------------------------------------
# 5. Module: set_keys / key pool
# ------------------------------------------------------------------
gemini_discover.set_keys(["key_a", "key_b", "key_c"])
check("set_keys populates pool", len(gemini_discover._keys), 3)
check("all keys start alive", all(not gemini_discover._key_daily_dead.get(k) for k in gemini_discover._keys), True)

# ------------------------------------------------------------------
# 6. _kill_key marks dead; has_live_keys still True
# ------------------------------------------------------------------
gemini_discover._kill_key("key_a")
check("_kill_key marks key dead", gemini_discover._key_daily_dead.get("key_a"), True)
check("has_live_keys True with 1 live remaining", gemini_discover.has_live_keys(), True)

# ------------------------------------------------------------------
# 7. Kill all keys → has_live_keys False
# ------------------------------------------------------------------
gemini_discover._kill_key("key_b")
gemini_discover._kill_key("key_c")
check("All dead → has_live_keys False", gemini_discover.has_live_keys(), False)

# ------------------------------------------------------------------
# 8. _wait_for_any_key returns False immediately when all dead
# ------------------------------------------------------------------
ok, spent = gemini_discover._wait_for_any_key(0.0)
check("_wait_for_any_key all-dead returns (False, 0)", (ok, spent), (False, 0.0))

# ------------------------------------------------------------------
# 9. _wait_for_any_key returns False when max wait already spent
# ------------------------------------------------------------------
import time
gemini_discover.set_keys(["key_x"])
# Park key_x for 120s
gemini_discover._park_key("key_x", 120)
# Simulate already having spent MAX_TOTAL_WAIT_SECONDS
ok2, spent2 = gemini_discover._wait_for_any_key(float(gemini_discover.MAX_TOTAL_WAIT_SECONDS))
check("_wait_for_any_key respects MAX_TOTAL_WAIT cap", ok2, False)

# ------------------------------------------------------------------
# 10. _parse_429: daily exhaustion detection
# ------------------------------------------------------------------
body_daily = '{"error": {"message": "Quota exceeded: limit: 0 for model"}}'
is_daily, delay = gemini_discover._parse_429(body_daily)
check("_parse_429 detects 'limit: 0' as daily exhaustion", is_daily, True)

# ------------------------------------------------------------------
# 11. _parse_429: per-minute throttle with retryDelay
# ------------------------------------------------------------------
body_minute = '{"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "57s"}]}}'
is_daily2, delay2 = gemini_discover._parse_429(body_minute)
check("_parse_429 detects per-minute throttle (not daily)", is_daily2, False)
check("_parse_429 extracts retryDelay=57", delay2, 57)

# ------------------------------------------------------------------
# 12. _parse_429: malformed body handled gracefully
# ------------------------------------------------------------------
is_daily3, delay3 = gemini_discover._parse_429("not valid json {{{{")
check("_parse_429 handles malformed JSON gracefully", is_daily3, False)

# ------------------------------------------------------------------
# 13. discover_dockerhub returns no_keys when pool is empty
# ------------------------------------------------------------------
gemini_discover.set_keys([])
# Temporarily unset env var so _load_keys_from_env() doesn't repopulate
_saved_env = os.environ.pop("GEMINI_API_KEYS", None)
_saved_env2 = os.environ.pop("GEMINI_API_KEY", None)
_, status = gemini_discover.discover_dockerhub("https://hackerone.com/test")
if _saved_env:  os.environ["GEMINI_API_KEYS"] = _saved_env
if _saved_env2: os.environ["GEMINI_API_KEY"]  = _saved_env2
check("discover_dockerhub with empty keys → 'no_keys'", status, "no_keys")

# ------------------------------------------------------------------
# 14. extract_company_name edge cases (auto_discover)
# ------------------------------------------------------------------
sys.path.insert(0, '.')
os.chdir('d:/Automation Bug Bounty/dockerhub-orgs-data')
sys.path.insert(0, 'actions')
from auto_discover import extract_company_name

check("Platform slug: comcast-mbb → 'comcast-mbb'",   extract_company_name("https://bugcrowd.com/engagements/comcast-mbb"),   "comcast-mbb")
check("Platform slug: shopify → 'shopify'",             extract_company_name("https://hackerone.com/shopify"),                  "shopify")
check("Company URL: www.acme.com/security → 'acme'",   extract_company_name("https://www.acme.com/security"),                  "acme")
check("Company URL: security.corp.co.uk → 'corp'",     extract_company_name("https://security.corp.co.uk/vdp"),                "corp")
check("Empty path → ''",                                extract_company_name("https://hackerone.com/"),                         "")

# ------------------------------------------------------------------
print()
print("=" * 60)
if errors == 0:
    print(f"ALL {PASS} — {14} tests passed")
else:
    print(f"{errors} test(s) FAILED")
print("=" * 60)
sys.exit(errors)
