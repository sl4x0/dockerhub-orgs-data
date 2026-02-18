#!/usr/bin/env python3
"""
Comprehensive fetch script for ALL bug bounty platforms
Pulls data from: HackerOne, Bugcrowd, Intigriti, YesWeHack, Federacy, Chaos, diodb
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Data source URLs
BOUNTY_TARGETS_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data"
CHAOS_URL = "https://raw.githubusercontent.com/projectdiscovery/public-bugbounty-programs/main"
DIODB_URL = "https://raw.githubusercontent.com/disclose/diodb/master"

DATA_SOURCES = {
    "hackerone": f"{BOUNTY_TARGETS_URL}/hackerone_data.json",
    "bugcrowd": f"{BOUNTY_TARGETS_URL}/bugcrowd_data.json",
    "intigriti": f"{BOUNTY_TARGETS_URL}/intigriti_data.json",
    "yeswehack": f"{BOUNTY_TARGETS_URL}/yeswehack_data.json",
    "federacy": f"{BOUNTY_TARGETS_URL}/federacy_data.json",
    "chaos": f"{CHAOS_URL}/chaos-bugbounty-list.json",
    "diodb": f"{DIODB_URL}/program-list.json",
}

HEADERS = {
    'User-Agent': 'dockerhub-orgs-data/1.0 (https://github.com/sl4x0/dockerhub-orgs-data)'
}


def fetch_json(url: str, retries: int = 3) -> Any:
    """Fetch JSON data from URL with retry + exponential backoff.

    Returns parsed JSON (dict or list) on success, None on permanent failure.
    Distinguishes between network errors (retried) and permanent errors (404/403).
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"Fetching: {url} (attempt {attempt}/{retries})")
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} fetching {url}: {e.reason}")
            if e.code in (403, 404):
                print(f"  Permanent error ({e.code}), skipping retries.")
                return None
            # 429, 5xx -> retry with backoff
        except Exception as e:
            print(f"Error fetching {url} (attempt {attempt}): {e}")

        if attempt < retries:
            wait = 2 ** attempt  # 2s, 4s
            print(f"  Retrying in {wait}s...")
            time.sleep(wait)

    print(f"❌ Failed to fetch {url} after {retries} attempts")
    return None


def extract_programs_hackerone(data: list, bounty_only: bool) -> List[Tuple[str, str]]:
    """Extract programs from HackerOne data.

    Args:
        bounty_only: True  -> paid bug bounty programs (offers_bounties=True)
                     False -> VDPs / disclosure programs (offers_bounties=False)

    HackerOne data is fetched once and split into two TSV files so that
    hackerone.tsv and hackerone.external_program.tsv contain distinct,
    non-overlapping programs rather than identical duplicates.
    """
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        handle = program.get('handle')
        if not handle:
            continue

        # Split on offers_bounties; default True if field is absent.
        offers_bounties = program.get('offers_bounties', True)

        if bounty_only and not offers_bounties:
            continue
        if not bounty_only and offers_bounties:
            continue

        url = f"https://hackerone.com/{handle}"
        programs.append((url, '?'))

    return programs


def extract_programs_bugcrowd(data: list) -> List[Tuple[str, str]]:
    """Extract programs from Bugcrowd data.

    The Bugcrowd JSON has a 'url' field with the full program URL.
    There is NO 'code' field — using 'code' caused bugcrowd.tsv to be empty.
    """
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        # Use the full URL directly — it's already the canonical program URL
        url = program.get('url')
        if url and url.startswith(('http://', 'https://')):
            programs.append((url, '?'))

    return programs


def extract_programs_intigriti(data: list) -> List[Tuple[str, str]]:
    """Extract programs from Intigriti data"""
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        handle = program.get('handle') or program.get('company_handle')
        if not handle:
            continue

        url = f"https://app.intigriti.com/programs/{handle}"
        programs.append((url, '?'))

    return programs


def extract_programs_yeswehack(data: list) -> List[Tuple[str, str]]:
    """Extract programs from YesWeHack data.

    Tries 'slug' first (standard URL identifier), falls back to 'id'.
    """
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        # Try 'slug' (human-readable URL slug), then 'id' as fallback
        slug = program.get('slug') or program.get('id')
        if not slug:
            continue

        url = f"https://yeswehack.com/programs/{slug}"
        programs.append((url, '?'))

    return programs


def extract_programs_federacy(data: list) -> List[Tuple[str, str]]:
    """Extract programs from Federacy data.

    Uses the direct 'url' field if present, otherwise builds from 'handle'.
    """
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        # Prefer a direct program URL if the data provides one
        direct_url = program.get('url')
        if direct_url and direct_url.startswith(('http://', 'https://')):
            programs.append((direct_url, '?'))
            continue

        # Fall back to building the URL from the handle slug
        identifier = program.get('handle')
        if not identifier:
            name = str(program.get('name', ''))
            # Only use name if it is already URL-safe (no encoding needed)
            if name and urllib.parse.quote(name, safe='-_') == name:
                identifier = name

        if identifier:
            url = f"https://federacy.com/{identifier}"
            programs.append((url, '?'))

    return programs


def extract_programs_chaos(data) -> List[Tuple[str, str]]:
    """Extract programs from Chaos (ProjectDiscovery) data"""
    programs = []

    if isinstance(data, dict):
        data = data.get('programs', [])

    for program in data:
        if not isinstance(program, dict):
            continue

        name = program.get('name')
        url = program.get('url')

        if url and url.startswith(('http://', 'https://')):
            programs.append((url, '?'))
        elif name:
            slug = name.replace(' ', '-').lower()
            fallback_url = f"https://chaos.projectdiscovery.io/programs/{slug}"
            programs.append((fallback_url, '?'))

    return programs


def extract_programs_diodb(data) -> List[Tuple[str, str]]:
    """Extract programs from diodb (disclose.io) data.

    The diodb program-list.json is a TOP-LEVEL ARRAY (not a dict with 'programs').
    Each program object uses 'policy_url' as the program page URL.
    The field 'program_url' does NOT exist — using it caused diodb.tsv to be empty.
    """
    programs = []

    # If somehow wrapped in a dict, try to unwrap
    if isinstance(data, dict):
        data = data.get('programs', [])

    for program in data:
        if not isinstance(program, dict):
            continue

        # Primary: policy_url (the bug bounty / disclosure policy page)
        # Fallback: contact_url (alternative program entry point)
        program_url = program.get('policy_url') or program.get('contact_url')

        if program_url and program_url.startswith(('http://', 'https://')):
            programs.append((program_url, '?'))

    return programs


def load_existing_data(filepath: Path) -> Dict[str, str]:
    """Load existing TSV data into a dictionary"""
    existing = {}

    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '\t' in line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        existing[parts[0]] = parts[1]

    return existing


def update_tsv_file(filepath: Path, programs: List[Tuple[str, str]]):
    """Update TSV file — adds new programs, preserves all existing mappings"""
    existing = load_existing_data(filepath)
    new_count = 0

    for program_url, status in programs:
        if program_url not in existing:
            existing[program_url] = status
            new_count += 1

    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        for url in sorted(existing.keys()):
            f.write(f"{url}\t{existing[url]}\n")

    print(f"✓ Updated {filepath.name}: {len(existing)} programs (+{new_count} new)")


def main():
    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"

    print("=" * 70)
    print("Fetching bug bounty programs from ALL sources")
    print("=" * 70)
    print()

    # HackerOne — fetch once, split into two files by program type
    print("Processing HackerOne...")
    h1_data = fetch_json(DATA_SOURCES["hackerone"])
    if h1_data is not None:
        # Bug bounty programs (offers_bounties=True) -> hackerone.tsv
        programs = extract_programs_hackerone(h1_data, bounty_only=True)
        update_tsv_file(data_dir / "hackerone.tsv", programs)

        # VDPs / disclosure programs (offers_bounties=False) -> hackerone.external_program.tsv
        programs = extract_programs_hackerone(h1_data, bounty_only=False)
        update_tsv_file(data_dir / "hackerone.external_program.tsv", programs)
    else:
        print("⚠️  Skipping HackerOne — fetch failed")

    # Bugcrowd
    print("\nProcessing Bugcrowd...")
    bc_data = fetch_json(DATA_SOURCES["bugcrowd"])
    if bc_data is not None:
        programs = extract_programs_bugcrowd(bc_data)
        update_tsv_file(data_dir / "bugcrowd.tsv", programs)
    else:
        print("⚠️  Skipping Bugcrowd — fetch failed")

    # Intigriti
    print("\nProcessing Intigriti...")
    ig_data = fetch_json(DATA_SOURCES["intigriti"])
    if ig_data is not None:
        programs = extract_programs_intigriti(ig_data)
        update_tsv_file(data_dir / "intigriti.tsv", programs)
    else:
        print("⚠️  Skipping Intigriti — fetch failed")

    # YesWeHack — file is yeswehack.external_program.tsv (not yeswehack.tsv)
    print("\nProcessing YesWeHack...")
    ywh_data = fetch_json(DATA_SOURCES["yeswehack"])
    if ywh_data is not None:
        programs = extract_programs_yeswehack(ywh_data)
        update_tsv_file(data_dir / "yeswehack.external_program.tsv", programs)
    else:
        print("⚠️  Skipping YesWeHack — fetch failed")

    # Federacy
    print("\nProcessing Federacy...")
    fed_data = fetch_json(DATA_SOURCES["federacy"])
    if fed_data is not None:
        programs = extract_programs_federacy(fed_data)
        update_tsv_file(data_dir / "federacy.tsv", programs)
    else:
        print("⚠️  Skipping Federacy — fetch failed")

    # Chaos (ProjectDiscovery)
    print("\nProcessing Chaos (ProjectDiscovery)...")
    chaos_data = fetch_json(DATA_SOURCES["chaos"])
    if chaos_data is not None:
        programs = extract_programs_chaos(chaos_data)
        update_tsv_file(data_dir / "chaos.tsv", programs)
    else:
        print("⚠️  Skipping Chaos — fetch failed")

    # diodb (disclose.io)
    print("\nProcessing diodb (disclose.io)...")
    diodb_data = fetch_json(DATA_SOURCES["diodb"])
    if diodb_data is not None:
        programs = extract_programs_diodb(diodb_data)
        update_tsv_file(data_dir / "diodb.tsv", programs)
    else:
        print("⚠️  Skipping diodb — fetch failed")

    print()
    print("=" * 70)
    print("✅ Update complete!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
