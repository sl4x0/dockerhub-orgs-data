#!/bin/bash

# List programs that need DockerHub organizations to be found
# Usage: ./scripts/todo.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../dockerhub-orgs-data"

# Find all lines with '?' indicating missing DockerHub organizations
grep -rn "?" "$DATA_DIR"/*.tsv | grep -E "\.tsv:.*\?"

