#!/usr/bin/env python3
"""
Auto-discover DockerHub usernames for programs marked with '?'
Uses smart variations and direct API verification
"""

import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


def check_dockerhub_user(username: str) -> bool:
    """Check if DockerHub user exists"""
    try:
        url = f"https://hub.docker.com/v2/users/{username}"
        req = urllib.request.Request(
            url,
            method='HEAD',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        return False


def extract_company_name(url: str) -> str:
    """Extract company/program name from URL"""
    # Remove protocol and common domains
    clean_url = url.lower().replace('https://', '').replace('http://', '')

    # Extract path parts
    parts = clean_url.split('/')

    for part in parts:
        if part and part not in ['hackerone.com', 'bugcrowd.com', 'app.intigriti.com',
                                   'yeswehack.com', 'federacy.com', 'hackenproof.com',
                                   'programs', 'www', 'program', 'company']:
            # Clean and return the identifier
            clean = re.sub(r'[^a-z0-9-_]', '', part)
            if len(clean) >= 2:
                return clean

    return ""


def extract_potential_usernames(url: str) -> List[str]:
    """Extract potential DockerHub usernames from program URL with smart variations"""
    variations = []

    # Extract the program identifier from URL
    parts = url.lower().replace('https://', '').replace('http://', '').split('/')

    for part in parts:
        if part and part not in ['hackerone.com', 'bugcrowd.com', 'app.intigriti.com',
                                   'yeswehack.com', 'federacy.com', 'hackenproof.com',
                                   'programs', 'www', 'program', 'company']:
            # Clean up the identifier
            clean = re.sub(r'[^a-z0-9-_]', '', part)
            if len(clean) >= 2:
                # Priority variations (most likely to work)
                variations.append(clean)  # Exact match
                variations.append(clean.replace('-', ''))  # No hyphens
                variations.append(clean.replace('_', ''))  # No underscores
                variations.append(clean.replace('-', '').replace('_', ''))  # No separators

                # Company/org name variations
                if '-' in clean:
                    variations.append(clean.split('-')[0])  # First part
                    variations.append(clean.split('-')[-1])  # Last part
                if '_' in clean:
                    variations.append(clean.split('_')[0])
                    variations.append(clean.split('_')[-1])

                # Common suffixes (less priority)
                variations.append(f"{clean}hq")
                variations.append(f"{clean}inc")
                variations.append(f"{clean}io")
                variations.append(f"{clean}team")

    # Remove duplicates while preserving order (prioritizing earlier ones)
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen and len(v) >= 2 and v.replace('-', '').replace('_', '').isalnum():
            seen.add(v)
            unique_variations.append(v)

    return unique_variations[:15]  # Return top 15 variations


def discover_dockerhub_for_program(program_url: str) -> str:
    """Try to discover DockerHub username for a program using smart variations"""
    print(f"\n🔍 Searching for: {program_url}")

    company_name = extract_company_name(program_url)
    print(f"  📌 Company name: {company_name}")

    # Get smart variations
    print(f"  🔧 Testing variations...")
    variations = extract_potential_usernames(program_url)

    for idx, variant in enumerate(variations[:20], 1):  # Test top 20 variations
        print(f"    [{idx}/20] {variant}...", end=' ')

        if check_dockerhub_user(variant):
            print("✅ FOUND!")
            time.sleep(0.5)
            return f"https://hub.docker.com/u/{variant}"
        else:
            print("❌")
            time.sleep(0.3)

    print("  ❌ No DockerHub organization found")
    return '?'


def load_programs_to_discover(data_dir: Path, max_count: int) -> List[Tuple[Path, str]]:
    """Load programs that need DockerHub discovery"""
    programs = []

    tsv_files = sorted(data_dir.glob("*.tsv"))

    if not tsv_files:
        print(f"⚠️  No TSV files found in {data_dir}")
        return programs

    for tsv_file in tsv_files:
        try:
            with open(tsv_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # Check if line ends with '?' (needs discovery)
                    if '\t?' in line or line.endswith('\t?'):
                        parts = line.split('\t')
                        if len(parts) == 2 and parts[1] == '?':
                            programs.append((tsv_file, parts[0]))

                            if len(programs) >= max_count:
                                return programs
        except Exception as e:
            print(f"⚠️  Error reading {tsv_file.name}: {str(e)[:50]}")
            continue

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
            print(f"⚠️  Invalid max_count argument, using default: {max_count}")

    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"

    if not data_dir.exists():
        print(f"❌ Error: Data directory not found: {data_dir}")
        return 1

    print("=" * 80)
    print(f"🐳 AUTO-DISCOVERING DOCKERHUB USERNAMES (max: {max_count})")
    print("=" * 80)
    print(f"📊 Strategy: Google Dorks → Smart Variations → Direct Testing")
    print("=" * 80)

    # Load programs that need discovery
    try:
        programs = load_programs_to_discover(data_dir, max_count)
    except Exception as e:
        print(f"❌ Error loading programs: {e}")
        return 1

    if not programs:
        print("\n✅ No programs need discovery!")
        return 0

    print(f"\n📋 Found {len(programs)} programs to search\n")

    # Track discoveries by file
    discoveries = {}
    found_count = 0

    start_time = time.time()

    for idx, (tsv_file, program_url) in enumerate(programs, 1):
        print(f"\n[{idx}/{len(programs)}] " + "=" * 60)

        try:
            dockerhub_url = discover_dockerhub_for_program(program_url)

            if dockerhub_url != '?':
                if str(tsv_file) not in discoveries:
                    discoveries[str(tsv_file)] = {}
                discoveries[str(tsv_file)][program_url] = dockerhub_url
                found_count += 1
                print(f"  ✅ SUCCESS: {dockerhub_url}")
        except Exception as e:
            print(f"  ❌ Error processing {program_url}: {str(e)[:100]}")
            continue

    elapsed = time.time() - start_time

    # Update files
    if discoveries:
        print(f"\n{'=' * 80}")
        print(f"💾 Updating TSV files with {found_count} discoveries...")
        try:
            update_tsv_files(discoveries)
            print("✅ Files updated successfully")
        except Exception as e:
            print(f"❌ Error updating files: {e}")
            return 1

    # Write summary
    try:
        summary_file = Path(__file__).parent.parent / 'discovery_log.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"**Searched**: {len(programs)} programs\n")
            f.write(f"**Found**: {found_count} DockerHub organizations\n")
            f.write(f"**Success Rate**: {found_count * 100 // len(programs) if programs else 0}%\n")
            f.write(f"**Elapsed Time**: {int(elapsed)} seconds\n")

            if found_count > 0:
                f.write("\n### Discoveries\n\n")
                for file_path, updates in discoveries.items():
                    platform = Path(file_path).stem
                    for program, dockerhub in updates.items():
                        f.write(f"- **{platform}**: {program} → {dockerhub}\n")

        print(f"📄 Summary written to: {summary_file}")
    except Exception as e:
        print(f"⚠️  Could not write summary: {e}")

    print(f"\n{'=' * 80}")
    print(f"🎉 DISCOVERY COMPLETE!")
    print(f"✅ Found: {found_count}/{len(programs)} ({found_count * 100 // len(programs) if programs else 0}%)")
    print(f"⏱️  Time: {int(elapsed)} seconds")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
