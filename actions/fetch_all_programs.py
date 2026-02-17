#!/usr/bin/env python3
"""
Comprehensive fetch script for ALL bug bounty platforms
Pulls data from: HackerOne, Bugcrowd, Intigriti, YesWeHack, Federacy, Chaos, diodb
"""

import json
import urllib.request
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import time


# Data source URLs
BOUNTY_TARGETS_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data"
CHAOS_URL = "https://raw.githubusercontent.com/projectdiscovery/public-bugbounty-programs/main"
DIODB_URL = "https://raw.githubusercontent.com/disclose/diodb/master"

DATA_SOURCES = {
    "hackerone.external_program": f"{BOUNTY_TARGETS_URL}/hackerone_data.json",
    "hackerone": f"{BOUNTY_TARGETS_URL}/hackerone_data.json",
    "bugcrowd": f"{BOUNTY_TARGETS_URL}/bugcrowd_data.json",
    "intigriti": f"{BOUNTY_TARGETS_URL}/intigriti_data.json",
    "yeswehack": f"{BOUNTY_TARGETS_URL}/yeswehack_data.json",
    "federacy": f"{BOUNTY_TARGETS_URL}/federacy_data.json",
    "chaos": f"{CHAOS_URL}/chaos-bugbounty-list.json",
    "diodb": f"{DIODB_URL}/program-list.json",
}


def fetch_json(url: str) -> dict:
    """Fetch JSON data from URL"""
    try:
        print(f"Fetching: {url}")
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return {}


def extract_programs_hackerone(data: dict) -> List[Tuple[str, str]]:
    """Extract programs from HackerOne data"""
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        handle = program.get('handle')
        if not handle:
            continue

        url = f"https://hackerone.com/{handle}"
        programs.append((url, '?'))

    return programs


def extract_programs_bugcrowd(data: dict) -> List[Tuple[str, str]]:
    """Extract programs from Bugcrowd data"""
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        code = program.get('code')
        if not code:
            continue

        url = f"https://bugcrowd.com/{code}"
        programs.append((url, '?'))

    return programs


def extract_programs_intigriti(data: dict) -> List[Tuple[str, str]]:
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


def extract_programs_yeswehack(data: dict) -> List[Tuple[str, str]]:
    """Extract programs from YesWeHack data"""
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        slug = program.get('slug')
        if not slug:
            continue

        url = f"https://yeswehack.com/programs/{slug}"
        programs.append((url, '?'))

    return programs


def extract_programs_federacy(data: dict) -> List[Tuple[str, str]]:
    """Extract programs from Federacy data"""
    programs = []

    for program in data:
        if not isinstance(program, dict):
            continue

        identifier = program.get('handle') or program.get('name')
        if identifier:
            url = f"https://federacy.com/{identifier}"
            programs.append((url, '?'))

    return programs


def extract_programs_chaos(data: dict) -> List[Tuple[str, str]]:
    """Extract programs from Chaos (ProjectDiscovery) data"""
    programs = []

    if isinstance(data, dict):
        data = data.get('programs', [])

    for program in data:
        if not isinstance(program, dict):
            continue

        name = program.get('name')
        url = program.get('url')

        if url and 'http' in url:
            programs.append((url, '?'))
        elif name:
            # Use program name as identifier
            url = f"https://chaos.projectdiscovery.io/programs/{name.replace(' ', '-')}"
            programs.append((url, '?'))

    return programs


def extract_programs_diodb(data: dict) -> List[Tuple[str, str]]:
    """Extract programs from diodb data"""
    programs = []

    if isinstance(data, dict):
        data = data.get('programs', [])

    for program in data:
        if not isinstance(program, dict):
            continue

        # Try to get program URL
        program_url = program.get('program_url') or program.get('url')

        if program_url:
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
    """Update TSV file with program data"""
    existing = load_existing_data(filepath)

    # Merge with new data (preserve existing mappings)
    for program_url, status in programs:
        if program_url not in existing:
            existing[program_url] = status

    # Write back to file (sorted)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        for url in sorted(existing.keys()):
            f.write(f"{url}\t{existing[url]}\n")

    print(f"✓ Updated {filepath.name}: {len(existing)} programs")


def main():
    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"

    print("=" * 70)
    print("Fetching bug bounty programs from ALL sources")
    print("=" * 70)
    print()

    # HackerOne External Programs
    print("Processing HackerOne (External Programs)...")
    h1_data = fetch_json(DATA_SOURCES["hackerone.external_program"])
    if h1_data:
        programs = extract_programs_hackerone(h1_data)
        update_tsv_file(data_dir / "hackerone.external_program.tsv", programs)

    # HackerOne Main
    print("\nProcessing HackerOne (Main List)...")
    h1_main = fetch_json(DATA_SOURCES["hackerone"])
    if h1_main:
        programs = extract_programs_hackerone(h1_main)
        update_tsv_file(data_dir / "hackerone.tsv", programs)

    # Bugcrowd
    print("\nProcessing Bugcrowd...")
    bc_data = fetch_json(DATA_SOURCES["bugcrowd"])
    if bc_data:
        programs = extract_programs_bugcrowd(bc_data)
        update_tsv_file(data_dir / "bugcrowd.tsv", programs)

    # Intigriti
    print("\nProcessing Intigriti...")
    ig_data = fetch_json(DATA_SOURCES["intigriti"])
    if ig_data:
        programs = extract_programs_intigriti(ig_data)
        update_tsv_file(data_dir / "intigriti.tsv", programs)

    # YesWeHack
    print("\nProcessing YesWeHack...")
    ywh_data = fetch_json(DATA_SOURCES["yeswehack"])
    if ywh_data:
        programs = extract_programs_yeswehack(ywh_data)
        update_tsv_file(data_dir / "yeswehack.tsv", programs)

    # Federacy
    print("\nProcessing Federacy...")
    fed_data = fetch_json(DATA_SOURCES["federacy"])
    if fed_data:
        programs = extract_programs_federacy(fed_data)
        update_tsv_file(data_dir / "federacy.tsv", programs)

    # Chaos (ProjectDiscovery)
    print("\nProcessing Chaos (ProjectDiscovery)...")
    chaos_data = fetch_json(DATA_SOURCES["chaos"])
    if chaos_data:
        programs = extract_programs_chaos(chaos_data)
        update_tsv_file(data_dir / "chaos.tsv", programs)

    # diodb (disclose.io)
    print("\nProcessing diodb (disclose.io)...")
    diodb_data = fetch_json(DATA_SOURCES["diodb"])
    if diodb_data:
        programs = extract_programs_diodb(diodb_data)
        update_tsv_file(data_dir / "diodb.tsv", programs)

    print()
    print("=" * 70)
    print("✅ Update complete!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
