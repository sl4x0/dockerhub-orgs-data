#!/bin/bash

# Check if a DockerHub username exists
# Usage: ./scripts/check-dockerhub-user.sh USERNAME

if [ -z "$1" ]; then
    echo "Usage: $0 USERNAME"
    exit 1
fi

USERNAME="$1"
URL="https://hub.docker.com/v2/users/${USERNAME}"

echo "Checking DockerHub user: $USERNAME"

# Use curl to check if the user exists
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$STATUS_CODE" -eq 200 ]; then
    echo "✓ User exists: https://hub.docker.com/u/${USERNAME}"
    exit 0
elif [ "$STATUS_CODE" -eq 404 ]; then
    echo "✗ User not found"
    exit 1
else
    echo "? Unable to determine (HTTP $STATUS_CODE)"
    exit 2
fi

