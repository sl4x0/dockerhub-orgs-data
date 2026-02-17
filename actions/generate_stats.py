#!/usr/bin/env python3
"""
Generate statistics and reports for dockerhub-orgs-data
"""

import sys
from pathlib import Path
from collections import defaultdict


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
                if not line:
                    continue

                stats['total'] += 1
                stats['by_platform'][platform]['total'] += 1

                if 'hub.docker.com/u/' in line:
                    stats['mapped'] += 1
                    stats['by_platform'][platform]['mapped'] += 1

                    # Extract org name
                    parts = line.split('hub.docker.com/u/')
                    if len(parts) > 1:
                        username = parts[1].split()[0].strip('/')
                        dockerhub_orgs.add(username)

                elif line.endswith('\t?'):
                    stats['todo'] += 1
                elif line.endswith('\t-'):
                    stats['not_found'] += 1

    return stats, sorted(dockerhub_orgs)


def generate_report(stats, orgs):
    """Generate markdown report"""
    lines = [
        "# DockerHub Organizations Statistics",
        "",
        f"Last updated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Overview",
        "",
        f"- **Total Programs**: {stats['total']}",
        f"- **Mapped Organizations**: {stats['mapped']}",
        f"- **TODO**: {stats['todo']}",
        f"- **Not Found**: {stats['not_found']}",
    ]

    if stats['mapped'] > 0:
        coverage = (stats['mapped'] * 100) // stats['total']
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
