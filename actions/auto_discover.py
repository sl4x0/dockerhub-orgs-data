#!/usr/bin/env python3
"""
Auto-discover DockerHub usernames for programs marked with '?'
"""

import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple
import re


def check_dockerhub_user(username: str) -> bool:
    """Check if DockerHub user exists"""
    try:
        url = f"https://hub.docker.com/v2/users/{username}"
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except:
        return False


def extract_potential_usernames(url: str) -> List[str]:
    """Extract potential DockerHub usernames from program URL"""
    variations = []

    # Extract the program identifier from URL
    parts = url.lower().replace('https://', '').replace('http://', '').split('/')

    for part in parts:
        if part and part not in ['hackerone.com', 'bugcrowd.com', 'app.intigriti.com',
                                   'yeswehack.com', 'federacy.com', 'hackenproof.com',
                                   'programs', 'www']:
            # Clean up the identifier
            clean = re.sub(r'[^a-z0-9-_]', '', part)
            if len(clean) >= 2:
                variations.append(clean)

                # Try without hyphens/underscores
                variations.append(clean.replace('-', '').replace('_', ''))

                # Try with common suffixes
                variations.append(f"{clean}-docker")
                variations.append(f"{clean}docker")
                variations.append(f"{clean}-official")

                # Try company/org name variations
                if '-' in clean:
                    variations.append(clean.split('-')[0])
                if '_' in clean:
                    variations.append(clean.split('_')[0])

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen and len(v) >= 2:
            seen.add(v)
            unique_variations.append(v)

    return unique_variations[:10]  # Limit to top 10 variations


def discover_dockerhub_for_program(program_url: str) -> str:
    """Try to discover DockerHub username for a program"""
    print(f"\nSearching for: {program_url}")

    variations = extract_potential_usernames(program_url)

    for variant in variations:
        print(f"  Trying: {variant}...", end=' ')

        if check_dockerhub_user(variant):
            print("✓ FOUND!")
            time.sleep(1)  # Rate limiting
            return f"https://hub.docker.com/u/{variant}"
        else:
            print("✗")
            time.sleep(0.5)  # Rate limiting

    print("  No DockerHub organization found")
    return '?'


def load_programs_to_discover(data_dir: Path, max_count: int) -> List[Tuple[Path, str]]:
    """Load programs that need DockerHub discovery"""
    programs = []

    for tsv_file in sorted(data_dir.glob("*.tsv")):
        with open(tsv_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '\t?' in line or line.endswith('\t?'):
                    parts = line.split('\t')
                    if len(parts) == 2 and parts[1] == '?':
                        programs.append((tsv_file, parts[0]))

                        if len(programs) >= max_count:
                            return programs

    return programs


def update_tsv_files(discoveries: Dict[str, Dict[str, str]]):
    """Update TSV files with discoveries"""
    for filepath_str, updates in discoveries.items():
        filepath = Path(filepath_str)

        # Read existing data
        lines = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        program_url = parts[0]
                        if program_url in updates:
                            lines.append(f"{program_url}\t{updates[program_url]}")
                        else:
                            lines.append(line)
                    else:
                        lines.append(line)

        # Write back
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            for line in sorted(lines):
                f.write(line + '\n')


def main():
    max_count = 50
    if len(sys.argv) > 1:
        try:
            max_count = int(sys.argv[1])
        except ValueError:
            pass

    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"

    print("=" * 70)
    print(f"Auto-discovering DockerHub usernames (max: {max_count})")
    print("=" * 70)

    # Load programs that need discovery
    programs = load_programs_to_discover(data_dir, max_count)

    if not programs:
        print("\nNo programs need discovery!")
        return 0

    print(f"\nFound {len(programs)} programs to search")

    # Track discoveries by file
    discoveries = {}
    found_count = 0

    for tsv_file, program_url in programs:
        dockerhub_url = discover_dockerhub_for_program(program_url)

        if dockerhub_url != '?':
            if str(tsv_file) not in discoveries:
                discoveries[str(tsv_file)] = {}
            discoveries[str(tsv_file)][program_url] = dockerhub_url
            found_count += 1

    # Update files
    if discoveries:
        print(f"\n{'=' * 70}")
        print(f"Updating TSV files with {found_count} discoveries...")
        update_tsv_files(discoveries)
        print("✓ Files updated")

    # Write summary
    with open('discovery_log.txt', 'w', encoding='utf-8') as f:
        f.write(f"**Searched**: {len(programs)} programs\n")
        f.write(f"**Found**: {found_count} DockerHub organizations\n")
        f.write(f"**Success Rate**: {found_count * 100 // len(programs) if programs else 0}%\n")

        if found_count > 0:
            f.write("\n### Discoveries\n\n")
            for file_path, updates in discoveries.items():
                platform = Path(file_path).stem
                for program, dockerhub in updates.items():
                    f.write(f"- **{platform}**: {program} -> {dockerhub}\n")

    print(f"\n{'=' * 70}")
    print(f"✅ Discovery complete! Found {found_count}/{len(programs)}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
