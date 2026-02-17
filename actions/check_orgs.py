#!/usr/bin/env python3
"""
Check DockerHub organizations validity
"""

import requests
import sys
import time
from pathlib import Path


def check_dockerhub_user(username):
    """Check if a DockerHub user/organization exists"""
    url = f"https://hub.docker.com/v2/users/{username}"

    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return None


def extract_dockerhub_orgs(data_dir):
    """Extract all DockerHub organizations from TSV files"""
    orgs = set()

    for tsv_file in Path(data_dir).glob("*.tsv"):
        with open(tsv_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if 'hub.docker.com/u/' in line:
                    # Extract username from URL
                    parts = line.split('hub.docker.com/u/')
                    if len(parts) > 1:
                        username = parts[1].split()[0].strip('/')
                        orgs.add(username)

    return sorted(orgs)


def main():
    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"

    print("Checking DockerHub organizations...")

    orgs = extract_dockerhub_orgs(data_dir)

    if not orgs:
        print("No DockerHub organizations found.")
        return 0

    errors = []

    for org in orgs:
        print(f"Checking: {org}...", end=' ')

        exists = check_dockerhub_user(org)

        if exists is True:
            print("✓")
        elif exists is False:
            print("✗ NOT FOUND")
            errors.append(org)
        else:
            print("? ERROR")

        # Be nice to the API
        time.sleep(1)

    if errors:
        print(f"\n❌ {len(errors)} organization(s) not found:")
        for org in errors:
            print(f"  - {org}")
        return 1

    print(f"\n✅ All {len(orgs)} organizations verified!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
