#!/bin/bash

# List programs that need DockerHub organizations to be found
# Usage: ./scripts/todo.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../dockerhub-orgs-data"

# Find all lines where the second column is exactly '?' (tab-separated).
# Uses a literal tab + '?' + end-of-line to avoid false matches from '?' in program URLs.
grep -Prn $'\t\?$' "$DATA_DIR"/*.tsv

