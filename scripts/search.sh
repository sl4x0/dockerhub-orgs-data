#!/bin/bash

# Search for a DockerHub organization across all bug bounty programs
# Usage: ./scripts/search.sh QUERY

if [ -z "$1" ]; then
    echo "Usage: $0 QUERY"
    echo "Example: $0 github"
    exit 1
fi

QUERY="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../dockerhub-orgs-data"

echo "Searching for: $QUERY"
echo ""

# -F: fixed string (not regex) prevents injection via special chars in QUERY
grep -iF "$QUERY" "$DATA_DIR"/*.tsv | while IFS=: read -r file line; do
    platform=$(basename "$file" .tsv)
    echo "[$platform] $line"
done
