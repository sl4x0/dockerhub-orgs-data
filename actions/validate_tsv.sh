#!/bin/bash

# Validate TSV file format
# Usage: ./actions/validate_tsv.sh FILE

if [ -z "$1" ]; then
    echo "Usage: $0 FILE"
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "Error: File not found: $FILE"
    exit 1
fi

echo "Validating: $FILE"

# Check for tabs
if ! grep -q $'\t' "$FILE"; then
    echo "❌ File doesn't appear to be tab-separated"
    exit 1
fi

# Check for trailing whitespace
if grep -q '[[:space:]]$' "$FILE"; then
    echo "⚠️  Warning: File has trailing whitespace"
fi

# Check for valid URLs
while IFS=$'\t' read -r col1 col2; do
    if [ -z "$col1" ] || [ -z "$col2" ]; then
        echo "⚠️  Warning: Empty column found"
        continue
    fi

    # Check if first column is a valid URL
    if [[ ! "$col1" =~ ^https?:// ]]; then
        echo "⚠️  Warning: First column should be a URL: $col1"
    fi

    # Check if second column is valid (URL, ?, or -)
    if [[ ! "$col2" =~ ^(https?://|\?|-)$ ]]; then
        echo "⚠️  Warning: Second column should be URL, ?, or -: $col2"
    fi
done < "$FILE"

echo "✅ Validation complete"
exit 0
