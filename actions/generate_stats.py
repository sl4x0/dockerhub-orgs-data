#!/usr/bin/env python3
"""
Generate statistics and reports for dockerhub-orgs-data
"""

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


def main():
    data_dir = Path(__file__).parent.parent / "dockerhub-orgs-data"
    output_file = Path(__file__).parent.parent / "docs" / "STATISTICS.md"

    print("Generating statistics report...")

    stats, orgs = parse_tsv_files(data_dir)
    report = generate_report(stats, orgs)

    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(report, encoding='utf-8')

    print(f"✅ Report generated: {output_file}")
    print(f"   Total: {stats['total']}, Mapped: {stats['mapped']}, TODO: {stats['todo']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
