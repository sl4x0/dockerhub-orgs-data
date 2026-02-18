#!/bin/bash

# Check if a DockerHub username exists
# Usage: ./scripts/check-dockerhub-user.sh USERNAME

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 USERNAME" >&2
    exit 1
fi

USERNAME="$1"

# Validate username format (DockerHub allows: lowercase letters, numbers, hyphens, underscores, 4-30 chars)
if ! [[ "$USERNAME" =~ ^[a-z0-9_-]{2,30}$ ]]; then
    echo "Error: Invalid DockerHub username format. Must be 2-30 chars: lowercase letters, numbers, hyphens, underscores only." >&2
    exit 1
fi

# Sanitize username for URL (prevent command injection)
USERNAME_SAFE=$(printf '%s' "$USERNAME" | sed 's/[^a-z0-9_-]//g')
URL="https://hub.docker.com/v2/users/${USERNAME_SAFE}"

echo "Checking DockerHub user: $USERNAME_SAFE"

# Use curl to check if the user exists with timeout and user agent
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed." >&2
    exit 3
fi

STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    --user-agent "dockerhub-orgs-data/1.0" \
    --retry 2 \
    --retry-delay 1 \
    "$URL")

if [ "$STATUS_CODE" -eq 200 ]; then
    echo "✓ User exists: https://hub.docker.com/u/${USERNAME_SAFE}"
    exit 0
elif [ "$STATUS_CODE" -eq 404 ]; then
    echo "✗ User not found"
    exit 1
elif [ "$STATUS_CODE" -eq 000 ]; then
    echo "✗ Connection failed (timeout or network error)" >&2
    exit 3
else
    echo "? Unable to determine (HTTP $STATUS_CODE)" >&2
    exit 2
fi

