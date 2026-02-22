#!/usr/bin/env python3
"""
Auto-discover DockerHub usernames for programs marked with '?'

Discovery engine — Gemini AI
------------------------------
Uses Gemini's world-knowledge to identify a company's official DockerHub
org name(s) from its bug bounty URL.  Gemini is far more accurate than any
heuristic — especially for diodb company-website entries where the URL
gives little domain signal.

Rate-limit behaviour
---------------------
When all API keys are temporarily throttled the code SLEEPS until the
earliest key unblocks.  No program is ever skipped due to a per-minute
rate limit.  Keys are only permanently dropped on daily exhaustion
("limit: 0"), in which case the program stays '?' for today and will be
retried on the next daily run.

Requires GEMINI_API_KEYS env var (comma-separated list of API keys).
"""

import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Gemini AI discovery module (same package)
try:
    import gemini_discover
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False


# Domains and path segments to strip when extracting the program identifier.
# Add any new platform domains here.
SKIP_PARTS = {
    'hackerone.com', 'bugcrowd.com', 'app.intigriti.com', 'intigriti.com',
    'yeswehack.com', 'federacy.com', 'hackenproof.com', 'bugbase.io',
    'bugrap.com', 'hatsfinance.io', 'whitehub.io', 'chaos.projectdiscovery.io',
    'programs', 'program', 'engagements', 'www', 'company', 'app', 'bounty', 'security',
}

# Known bug bounty PLATFORM domains — for these we extract the program ID from the URL PATH.
# Everything else is treated as a company website and the SLD (second-level domain) is used.
PLATFORM_DOMAINS: frozenset = frozenset({
    'hackerone.com', 'bugcrowd.com', 'vdp.bugcrowd.com',
    'app.intigriti.com', 'intigriti.com',
    'yeswehack.com', 'federacy.com', 'hackenproof.com', 'bugbase.io',
    'bugrap.com', 'hatsfinance.io', 'whitehub.io',
    'chaos.projectdiscovery.io', 'huntr.dev', 'bugbountyjp.com',
})

# Path segments that carry no program-identity information on platform URLs.
SKIP_PATH_PARTS: frozenset = frozenset({
    'programs', 'program', 'engagements', 'company', 'app', 'bounty',
    'security', 'vulnerability-disclosure', 'responsible-disclosure',
    'policy', 'legal', 'bug-bounty', 'bugbounty', 'security-policy', 'vdp',
    'www', 'api', 'submit',
})

HEADERS = {
    'User-Agent': 'dockerhub-orgs-data/2.0 (https://github.com/sl4x0/dockerhub-orgs-data)'
}


def check_dockerhub_user(username: str) -> Optional[bool]:
    """Check if a DockerHub user/org exists.

    Returns:
        True  — user exists (HTTP 200)
        False — user does not exist (HTTP 404)
        None  — transient error (timeout, rate-limit, 5xx, network) — do NOT treat as not-found
    """
    try:
        url = f"https://hub.docker.com/v2/users/{username}"
        req = urllib.request.Request(url, method='HEAD', headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        # 429 (rate-limited), 5xx, or other HTTP errors → transient, skip
        return None
    except Exception:
        # Network timeout, DNS failure, etc. → transient, skip
        return None


def _is_platform_url(hostname: str) -> bool:
    """Return True if hostname belongs to a known bug bounty platform."""
    return hostname in PLATFORM_DOMAINS or any(
        hostname == p or hostname.endswith('.' + p) for p in PLATFORM_DOMAINS
    )


def _extract_sld(hostname: str) -> str:
    """Extract the second-level domain label from a hostname.

    Examples:
        'www.acme.com'       -> 'acme'
        'api.example.co.uk'  -> 'example'
        'google.com'         -> 'google'
        'security.corp.io'   -> 'corp'
    """
    parts = hostname.split('.')
    if len(parts) < 2:
        return parts[0] if parts else ''

    # Heuristic for 2-level TLDs (co.uk, com.br, etc.):
    # If the second-to-last label is short AND not a well-known org-level TLD,
    # skip it as part of the TLD.
    known_single_tlds = {'com', 'org', 'net', 'gov', 'edu', 'mil', 'int',
                         'io', 'ai', 'dev', 'app', 'cloud', 'tech', 'security'}
    penultimate = parts[-2] if len(parts) >= 2 else ''
    tld_levels = 1
    if len(parts) >= 3 and len(penultimate) <= 3 and penultimate not in known_single_tlds:
        tld_levels = 2  # treat as 2-level TLD (e.g. co.uk)

    sld_idx = -(tld_levels + 1)
    if abs(sld_idx) > len(parts):
        sld_idx = -len(parts)
    return parts[sld_idx]


def extract_company_name(url: str) -> str:
    """Extract the primary company/program identifier from a program URL.

    For known bug bounty platform URLs the identifier comes from the URL PATH
    (e.g. https://hackerone.com/acme  ->  'acme').

    For company website URLs (common in diodb) the identifier is the
    second-level domain of the hostname
    (e.g. https://www.acme.com/security/policy  ->  'acme').
    """
    clean_url = url.lower().replace('https://', '').replace('http://', '')
    parts = clean_url.split('/')
    hostname = parts[0] if parts else ''

    if _is_platform_url(hostname):
        # Platform URL — use meaningful path segments
        for part in parts[1:]:
            if part and part not in SKIP_PATH_PARTS:
                clean = re.sub(r'[^a-z0-9\-_]', '', part)
                if len(clean) >= 2:
                    return clean
    else:
        # Company website — extract SLD from the hostname
        sld = _extract_sld(hostname)
        clean = re.sub(r'[^a-z0-9\-_]', '', sld)
        if len(clean) >= 2:
            return clean

    return ''


def discover_dockerhub_for_program(program_url: str) -> str:
    """Discover DockerHub username for a program using Gemini AI.

    Blocks/sleeps when API keys are throttled — no program is skipped due
    to a per-minute rate limit.  Returns '?' only when Gemini definitively
    has no answer or all keys are daily-dead.

    Returns:
        Full hub.docker.com/u/<username> URL, or '?' if not found.
    """
    print(f"\n  Searching: {program_url}")
    company_name = extract_company_name(program_url)
    print(f"  Identifier: {company_name or '(company website)'}")

    if not _GEMINI_AVAILABLE:
        print("  [ERROR] gemini_discover module not found — cannot discover")
        return '?'

    if not gemini_discover.has_live_keys():
        print("  [SKIP] All Gemini keys are daily-dead — leaving as '?'")
        return '?'

    try:
        url, status = gemini_discover.discover_dockerhub(
            program_url,
            verify_fn=check_dockerhub_user,
            company_hint=company_name,
        )
        if url is not None:
            return url
        if status == 'daily_dead':
            print("  All keys daily-dead — retry tomorrow")
            return '?'
        elif status == 'max_wait':
            print("  Max wait time exceeded — leaving as '?' to retry")
            return '?'
        elif status == 'not_found':
            print("  Gemini: no confident candidates — trying direct identifier check")
        else:
            print(f"  Gemini: status={status} — trying direct identifier check")
    except Exception as e:
        print(f"  Gemini exception: {str(e)[:120]} — trying direct identifier check")

    # ------------------------------------------------------------------ #
    # Direct identifier check: if Gemini gave up / returned [], try the   #
    # extracted company name verbatim on DockerHub.  Catches cases like   #
    # 'comcast-mbb' → Gemini unsure → direct check 'comcast' → FOUND.    #
    # ------------------------------------------------------------------ #
    if company_name and len(company_name) >= 2:
        print(f"    [Direct] Checking '{company_name}' on DockerHub …", end=' ', flush=True)
        result = check_dockerhub_user(company_name)
        if result is True:
            url = f"https://hub.docker.com/u/{company_name}"
            print(f"CONFIRMED")
            return url
        elif result is False:
            print("not found")
        else:
            print("error (skipping)")

    return '?'


def load_programs_to_discover(data_dir: Path, max_count: int) -> List[Tuple[Path, str]]:
    """Load programs that need DockerHub discovery (status == '?')"""
    programs: List[Tuple[Path, str]] = []

    tsv_files = sorted(data_dir.glob("*.tsv"))

    if not tsv_files:
        print(f"  No TSV files found in {data_dir}")
        return programs

    for tsv_file in tsv_files:
        try:
            with open(tsv_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # Only match lines where the second column is exactly '?'
                    parts = line.split('\t')
                    if len(parts) == 2 and parts[1] == '?':
                        programs.append((tsv_file, parts[0]))

                        if len(programs) >= max_count:
                            return programs
        except Exception as e:
            print(f"  Error reading {tsv_file.name}: {str(e)[:80]}")
            continue

    return programs


def update_tsv_files(discoveries: Dict[str, Dict[str, str]]):
    """Update TSV files with newly discovered DockerHub URLs"""
    for filepath_str, updates in discoveries.items():
        filepath = Path(filepath_str)

        lines: List[str] = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    program_url = parts[0]
                    lines.append(f"{program_url}\t{updates.get(program_url, parts[1])}")
                else:
                    lines.append(line)

        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            for line in sorted(lines):
                f.write(line + '\n')


def main():
    max_count = 50
    if len(sys.argv) > 1:
        try:
            max_count = int(sys.argv[1])
            if max_count <= 0:
                raise ValueError("must be positive")
        except ValueError as e:
            print(f"  Invalid max_count '{sys.argv[1]}': {e}. Using default: {max_count}")

    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return 1

    # ------------------------------------------------------------------ #
    # Load Gemini keys (GitHub Actions passes GEMINI_API_KEYS secret)      #
    # ------------------------------------------------------------------ #
    if not _GEMINI_AVAILABLE:
        print("ERROR: gemini_discover module not found in actions/. Cannot run.")
        return 1

    raw_keys = os.environ.get("GEMINI_API_KEYS", "") or os.environ.get("GEMINI_API_KEY", "")
    keys = [k.strip() for k in re.split(r"[,\n]+", raw_keys) if k.strip()]
    if not keys:
        print("ERROR: GEMINI_API_KEYS environment variable not set.")
        print("       Set it to a comma-separated list of Gemini API keys.")
        return 1

    gemini_discover.set_keys(keys)
    print(f"Gemini AI ready: {len(keys)} key(s) loaded")

    print("=" * 70)
    print(f"AUTO-DISCOVERING DOCKERHUB USERNAMES (max: {max_count})")
    print("=" * 70)
    print("Strategy: Gemini AI (world-knowledge based, waits on rate limits)")
    print("=" * 70)

    try:
        programs = load_programs_to_discover(data_dir, max_count)
    except Exception as e:
        print(f"Error loading programs: {e}")
        return 1

    if not programs:
        print("\nNo programs need discovery!")
        return 0

    print(f"\nFound {len(programs)} programs to search\n")

    discoveries: Dict[str, Dict[str, str]] = {}
    found_count = 0
    start_time = time.time()

    for idx, (tsv_file, program_url) in enumerate(programs, 1):
        print(f"\n[{idx}/{len(programs)}] " + "-" * 50)

        try:
            dockerhub_url = discover_dockerhub_for_program(program_url)

            if dockerhub_url != '?':
                file_key = str(tsv_file)
                if file_key not in discoveries:
                    discoveries[file_key] = {}
                discoveries[file_key][program_url] = dockerhub_url
                found_count += 1
                print(f"  SUCCESS: {dockerhub_url}")
        except Exception as e:
            print(f"  Error processing {program_url}: {str(e)[:100]}")
            continue

    elapsed = time.time() - start_time

    if discoveries:
        print(f"\n{'=' * 70}")
        print(f"Updating TSV files with {found_count} discoveries...")
        try:
            update_tsv_files(discoveries)
            print("Files updated successfully")
        except Exception as e:
            print(f"Error updating files: {e}")
            return 1

    # Write discovery log
    try:
        summary_file = Path(__file__).parent.parent / 'discovery_log.txt'
        total = len(programs)
        rate = round(found_count * 100 / total, 1) if total else 0
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"**Searched**: {total} programs\n")
            f.write(f"**Found**: {found_count} DockerHub organizations\n")
            f.write(f"**Success Rate**: {rate}%\n")
            f.write(f"**Elapsed Time**: {int(elapsed)} seconds\n")
            f.write(f"**Engine**: Gemini AI\n")

            if found_count > 0:
                f.write("\n### Discoveries\n\n")
                for file_path, updates in discoveries.items():
                    platform = Path(file_path).stem
                    for program, dockerhub in updates.items():
                        f.write(f"- **{platform}**: {program} -> {dockerhub}\n")

        print(f"Summary written to: {summary_file}")
    except Exception as e:
        print(f"  Could not write summary: {e}")

    print(f"\n{'=' * 70}")
    total = len(programs)
    rate = round(found_count * 100 / total, 1) if total else 0
    print(f"DISCOVERY COMPLETE!")
    print(f"Found: {found_count}/{total} ({rate}%) via Gemini AI")
    print(f"Time: {int(elapsed)} seconds")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
