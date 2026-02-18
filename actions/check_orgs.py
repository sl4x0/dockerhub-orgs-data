#!/usr/bin/env python3
"""
Check DockerHub organizations validity.
Uses stdlib urllib only (no third-party dependencies) for consistency with other scripts.
"""

import urllib.request
import urllib.error
import urllib.parse
import sys
import time
from pathlib import Path
from typing import Optional


HEADERS = {
    'User-Agent': 'dockerhub-orgs-data/1.0 (https://github.com/sl4x0/dockerhub-orgs-data)'
}


def check_dockerhub_user(username: str) -> Optional[bool]:
    """Check if a DockerHub user/organization exists.

    Returns:
        True  — exists (HTTP 200)
        False — not found (HTTP 404)
        None  — transient error (rate-limit, 5xx, timeout) — do NOT record as missing
    """
    url = f"https://hub.docker.com/v2/users/{username}"
    try:
        req = urllib.request.Request(url, method='HEAD', headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        # 429 (rate-limit), 5xx → transient, caller should skip/retry
        return None
    except Exception:
        return None


def extract_username_from_url(dockerhub_url: str) -> str:
    """Safely extract DockerHub username from a hub.docker.com/u/<name> URL."""
    try:
        parsed = urllib.parse.urlparse(dockerhub_url)
        # path is like /u/username or /u/username/
        path_parts = [p for p in parsed.path.split('/') if p]
        # Expected: ['u', 'username']
        if len(path_parts) >= 2 and path_parts[0] == 'u':
            return path_parts[1]
    except Exception:
        pass
    return ""


def extract_dockerhub_orgs(data_dir: Path) -> list:
    """Extract all unique DockerHub usernames from TSV files."""
    orgs: set = set()

    for tsv_file in sorted(data_dir.glob("*.tsv")):
        with open(tsv_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '\t' not in line:
                    continue
                parts = line.split('\t', 1)
                if len(parts) != 2:
                    continue
                col2 = parts[1]
                if 'hub.docker.com/u/' in col2:
                    username = extract_username_from_url(col2)
                    if username:
                        orgs.add(username)

    return sorted(orgs)


def main():
    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"

    print("Checking DockerHub organizations...")

    orgs = extract_dockerhub_orgs(data_dir)

    if not orgs:
        print("No DockerHub organizations found.")
        return 0

    print(f"Found {len(orgs)} organizations to verify.\n")

    confirmed = []
    missing = []
    errors = []

    for org in orgs:
        print(f"Checking: {org}...", end=' ', flush=True)

        result = check_dockerhub_user(org)

        if result is True:
            print("OK")
            confirmed.append(org)
        elif result is False:
            print("NOT FOUND")
            missing.append(org)
        else:
            # Transient error — do NOT record as missing
            print("ERROR (skipped)")
            errors.append(org)

        time.sleep(0.5)  # Respectful rate limiting

    print(f"\nResults:")
    print(f"  Confirmed : {len(confirmed)}")
    print(f"  Missing   : {len(missing)}")
    print(f"  Errors    : {len(errors)} (transient — not counted as missing)")

    if missing:
        print(f"\n{len(missing)} organization(s) confirmed missing (HTTP 404):")
        for org in missing:
            print(f"  - {org}")
        return 1

    print(f"\nAll {len(confirmed)} organizations verified!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
