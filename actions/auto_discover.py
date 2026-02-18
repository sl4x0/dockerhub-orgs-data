#!/usr/bin/env python3
"""
Auto-discover DockerHub usernames for programs marked with '?'
Uses direct API verification with conservative, low-false-positive variations.

False positive reduction strategy:
  - Only 4 variations are tested (all derived from the exact program identifier):
      1. Exact match
      2. Hyphens removed
      3. Underscores removed
      4. All separators removed
  - Split-name parts (e.g. "corp" from "example-corp") are NOT tested — too generic.
  - Suffix guesses (hq, inc, io, team) are NOT tested — too speculative.
  - Network errors / rate-limits return None and are skipped, never treated as "not found".
"""

import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


# Domains and path segments to strip when extracting the program identifier.
# Add any new platform domains here.
SKIP_PARTS = {
    'hackerone.com', 'bugcrowd.com', 'app.intigriti.com', 'intigriti.com',
    'yeswehack.com', 'federacy.com', 'hackenproof.com', 'bugbase.io',
    'bugrap.com', 'hatsfinance.io', 'whitehub.io', 'chaos.projectdiscovery.io',
    'programs', 'program', 'engagements', 'www', 'company', 'app', 'bounty', 'security',
}

HEADERS = {
    'User-Agent': 'dockerhub-orgs-data/1.0 (https://github.com/sl4x0/dockerhub-orgs-data)'
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


def extract_company_name(url: str) -> str:
    """Extract the primary company/program identifier from a program URL."""
    clean_url = url.lower().replace('https://', '').replace('http://', '')
    parts = clean_url.split('/')

    for part in parts:
        if part and part not in SKIP_PARTS:
            clean = re.sub(r'[^a-z0-9\-_]', '', part)
            if len(clean) >= 2:
                return clean

    return ""


def extract_potential_usernames(url: str) -> List[str]:
    """Return low-false-positive DockerHub username candidates for a program URL.

    Only produces variations that are direct transformations of the program
    identifier — no split-parts, no suffix guesses.
    """
    clean_url = url.lower().replace('https://', '').replace('http://', '')
    parts = clean_url.split('/')

    variations: List[str] = []

    for part in parts:
        if part and part not in SKIP_PARTS:
            clean = re.sub(r'[^a-z0-9\-_]', '', part)
            if len(clean) >= 2:
                candidates = [
                    clean,                                  # 1. exact
                    clean.replace('-', ''),                 # 2. no hyphens
                    clean.replace('_', ''),                 # 3. no underscores
                    clean.replace('-', '').replace('_', ''), # 4. no separators
                ]
                for c in candidates:
                    if c not in variations and len(c) >= 2 and c.replace('-', '').replace('_', '').isalnum():
                        variations.append(c)
                break  # Only use the first meaningful path segment

    # Deduplicate while preserving order
    seen: set = set()
    unique: List[str] = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique.append(v)

    return unique


def discover_dockerhub_for_program(program_url: str) -> str:
    """Try to discover DockerHub username for a program.

    Returns the full hub.docker.com URL on success, '?' if not found,
    or '?' if all API calls returned transient errors (safe — leaves '?' in place).
    """
    print(f"\n  Searching: {program_url}")

    company_name = extract_company_name(program_url)
    print(f"  Identifier: {company_name}")

    variations = extract_potential_usernames(program_url)
    total = len(variations)

    transient_errors = 0

    for idx, variant in enumerate(variations, 1):
        print(f"    [{idx}/{total}] {variant}...", end=' ', flush=True)

        result = check_dockerhub_user(variant)

        if result is True:
            print("FOUND")
            time.sleep(0.5)
            return f"https://hub.docker.com/u/{variant}"
        elif result is False:
            print("not found")
            time.sleep(0.3)
        else:
            # Transient error (rate-limit / network)
            print("error (skipping)")
            transient_errors += 1
            time.sleep(1.0)

    if transient_errors == total:
        print("  All checks hit errors — leaving as '?' to retry later")
    else:
        print("  No DockerHub organization found")

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

    print("=" * 70)
    print(f"AUTO-DISCOVERING DOCKERHUB USERNAMES (max: {max_count})")
    print("=" * 70)
    print("Strategy: Exact match + separator-removal variants (low false-positive mode)")
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
    print(f"Found: {found_count}/{total} ({rate}%)")
    print(f"Time: {int(elapsed)} seconds")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
