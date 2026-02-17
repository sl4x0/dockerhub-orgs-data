#!/bin/bash

# List all DockerHub organization/username from TSV files
# Usage: ./scripts/all-dockerhub-orgs.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../dockerhub-orgs-data"

# Find all DockerHub URLs in TSV files and extract usernames
find "$DATA_DIR" -name "*.tsv" -type f -exec cat {} \; | \
    grep -E "https://hub\.docker\.com/u/" | \
    sed 's/.*https:\/\/hub\.docker\.com\/u\///' | \
    sed 's/[[:space:]].*$//' | \
    sort -u

