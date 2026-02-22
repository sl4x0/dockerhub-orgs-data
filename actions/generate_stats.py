#!/usr/bin/env python3
"""
Generate statistics and reports for dockerhub-orgs-data.
Also updates the README.md statistics table so it always reflects live data.
"""

import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict


def extract_username_from_url(dockerhub_url: str) -> str:
    """Safely extract DockerHub username from a hub.docker.com/u/<name> URL."""
    try:
        parsed = urllib.parse.urlparse(dockerhub_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        # Expected path structure: /u/username
        if len(path_parts) >= 2 and path_parts[0] == 'u':
            return path_parts[1]
    except Exception:
        pass
    return ""


def parse_tsv_files(data_dir):
    """Parse all TSV files and extract statistics"""
    stats = {
        'total': 0,
        'mapped': 0,
        'todo': 0,
        'not_found': 0,
        'by_platform': defaultdict(lambda: {'total': 0, 'mapped': 0})
    }

    dockerhub_orgs = set()

    for tsv_file in Path(data_dir).glob("*.tsv"):
        platform = tsv_file.stem

        with open(tsv_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '\t' not in line:
                    continue

                parts = line.split('\t', 1)
                if len(parts) != 2:
                    continue

                col2 = parts[1]

                stats['total'] += 1
                stats['by_platform'][platform]['total'] += 1

                # Only inspect column 2 for DockerHub URLs — avoids false matches
                # in column 1 (the bug bounty program URL).
                if 'hub.docker.com/u/' in col2:
                    stats['mapped'] += 1
                    stats['by_platform'][platform]['mapped'] += 1

                    username = extract_username_from_url(col2)
                    if username:
                        dockerhub_orgs.add(username)

                elif col2 == '?':
                    stats['todo'] += 1
                elif col2 == '-':
                    stats['not_found'] += 1

    return stats, sorted(dockerhub_orgs)


def generate_report(stats, orgs):
    """Generate markdown report"""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    lines = [
        "# DockerHub Organizations Statistics",
        "",
        f"Last updated: {today} (UTC)",
        "",
        "## Overview",
        "",
        f"- **Total Programs**: {stats['total']}",
        f"- **Mapped Organizations**: {stats['mapped']}",
        f"- **TODO**: {stats['todo']}",
        f"- **Not Found**: {stats['not_found']}",
    ]

    if stats['total'] > 0 and stats['mapped'] > 0:
        coverage = round(stats['mapped'] * 100 / stats['total'], 1)
        lines.append(f"- **Coverage**: {coverage}%")

    lines.extend([
        "",
        "## By Platform",
        ""
    ])

    for platform, data in sorted(stats['by_platform'].items()):
        lines.extend([
            f"### {platform}",
            f"- Total: {data['total']}",
            f"- Mapped: {data['mapped']}",
            ""
        ])

    lines.extend([
        "## All DockerHub Organizations",
        ""
    ])

    for org in orgs:
        lines.append(f"- [{org}](https://hub.docker.com/u/{org})")

    lines.extend([
        "",
        "## Contributing",
        "",
        "Help us improve coverage! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on how to add missing DockerHub organizations.",
        "",
        "Run `./scripts/todo.sh` to see which programs need research.",
    ])

    return "\n".join(lines)


def update_readme_stats(stats: dict, readme_path: Path) -> bool:
    """Update the statistics table and last-updated line in README.md.

    The function uses regex substitution so the surrounding markdown prose is
    never touched.  Returns True if the README was modified, False otherwise.
    """
    if not readme_path.exists():
        print(f"  README not found at {readme_path} — skipping README update")
        return False

    content = readme_path.read_text(encoding='utf-8')
    original = content

    total = stats['total']
    mapped = stats['mapped']
    todo = stats['todo']
    coverage = f"{round(mapped * 100 / total, 1)}%" if total > 0 else "0%"
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Helper: format a number with thousands commas exactly like the table uses.
    def fmt(n: int) -> str:
        return f"{n:,}"

    # Update each stat row independently so column padding changes don't matter.
    replacements = [
        # Total programs row
        (
            r'(\|\s*\*\*Total Bug Bounty Programs\*\*\s*\|\s*)[\d,]+(\s*\|)',
            rf'\g<1>{fmt(total)}\2'
        ),
        # Mapped orgs row
        (
            r'(\|\s*\*\*Mapped DockerHub Organizations\*\*\s*\|\s*)[\d,]+(\s*\|)',
            rf'\g<1>{fmt(mapped)}\2'
        ),
        # Coverage row
        (
            r'(\|\s*\*\*Coverage\*\*\s*\|\s*)[\d.]+%(\s*\|)',
            rf'\g<1>{coverage}\2'
        ),
        # TODO row
        (
            r'(\|\s*\*\*TODO \(Needs Research\)\*\*\s*\|\s*)[\d,]+(\s*\|)',
            rf'\g<1>{fmt(todo)}\2'
        ),
        # Last-updated line — update the date while keeping the rest of the line.
        (
            r'_Last automated update:.*?_',
            f'_Last automated update: {today} UTC_'
        ),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    if content == original:
        print("  README stats unchanged — no update needed")
        return False

    readme_path.write_text(content, encoding='utf-8')
    print(f"  README.md stats updated: {fmt(total)} programs, {fmt(mapped)} mapped ({coverage}), {fmt(todo)} TODO")
    return True


def main():
    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"
    output_file = Path(__file__).parent.parent / "docs" / "STATISTICS.md"
    readme_file = Path(__file__).parent.parent / "README.md"

    print("Generating statistics report...")

    stats, orgs = parse_tsv_files(data_dir)
    report = generate_report(stats, orgs)

    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(report, encoding='utf-8')

    print(f"✅ Report generated: {output_file}")
    print(f"   Total: {stats['total']}, Mapped: {stats['mapped']}, TODO: {stats['todo']}")

    # Keep README statistics table in sync with live data.
    print("Updating README.md statistics...")
    update_readme_stats(stats, readme_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
