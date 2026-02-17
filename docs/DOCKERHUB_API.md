# DockerHub API Guide

This guide covers how to interact with the DockerHub API for security research.

## API Endpoints

### Get User/Organization Info

```bash
curl -s "https://hub.docker.com/v2/users/USERNAME" | jq
```

Response:

```json
{
  "id": "abc123",
  "username": "example",
  "full_name": "Example Organization",
  "location": "San Francisco, CA",
  "company": "Example Inc",
  "profile_url": "https://hub.docker.com/u/example",
  "date_joined": "2020-01-01T00:00:00.000000Z",
  "type": "Organization"
}
```

### List Repositories

```bash
curl -s "https://hub.docker.com/v2/repositories/USERNAME/?page_size=100" | jq -r '.results[].name'
```

### Get Repository Details

```bash
curl -s "https://hub.docker.com/v2/repositories/USERNAME/REPO" | jq
```

### Get Repository Tags

```bash
curl -s "https://hub.docker.com/v2/repositories/USERNAME/REPO/tags/?page_size=100" | jq -r '.results[].name'
```

## Rate Limiting

DockerHub API has rate limits:

- **Unauthenticated**: 100 requests per 6 hours
- **Authenticated**: Higher limits

To avoid rate limiting:

1. Add delays between requests (use `sleep`)
2. Authenticate with a DockerHub account
3. Cache results when possible

## Authentication

```bash
# Get authentication token
TOKEN=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"USERNAME","password":"PASSWORD"}' \
  https://hub.docker.com/v2/users/login/ | jq -r '.token')

# Use token in requests
curl -s -H "Authorization: JWT $TOKEN" \
  "https://hub.docker.com/v2/repositories/USERNAME/"
```

## Useful Queries

### Find all public images for an organization

```bash
curl -s "https://hub.docker.com/v2/repositories/USERNAME/?page_size=100" | \
  jq -r '.results[] | "\(.name) - \(.description)"'
```

### Check image pull count

```bash
curl -s "https://hub.docker.com/v2/repositories/USERNAME/REPO" | \
  jq '.pull_count'
```

### Get latest tag

```bash
curl -s "https://hub.docker.com/v2/repositories/USERNAME/REPO/tags/?page_size=1" | \
  jq -r '.results[0].name'
```

## Security Research Tips

### 1. Enumerate all images

```bash
#!/bin/bash
ORG="example"
PAGE=1

while true; do
  response=$(curl -s "https://hub.docker.com/v2/repositories/${ORG}/?page=${PAGE}&page_size=100")

  echo "$response" | jq -r '.results[].name'

  next=$(echo "$response" | jq -r '.next')
  if [ "$next" == "null" ]; then
    break
  fi

  PAGE=$((PAGE + 1))
  sleep 1
done
```

### 2. Check for leaked secrets

```bash
# Pull and scan image
docker pull org/image:latest
trufflehog docker --image org/image:latest
```

### 3. Analyze image layers

```bash
docker history org/image:latest
dive org/image:latest
```

### 4. Extract Dockerfile

```bash
# Using docker-explorer
docker pull org/image:latest
docker save org/image:latest -o image.tar
tar -xf image.tar
# Look for layer.tar files and extract
```

## Python Example

```python
import requests
import time

def get_dockerhub_repos(username):
    """Get all repositories for a DockerHub user/org"""
    repos = []
    page = 1

    while True:
        url = f"https://hub.docker.com/v2/repositories/{username}/"
        params = {"page": page, "page_size": 100}

        response = requests.get(url, params=params)

        if response.status_code != 200:
            break

        data = response.json()
        repos.extend(data.get("results", []))

        if not data.get("next"):
            break

        page += 1
        time.sleep(1)  # Rate limiting

    return repos

# Usage
repos = get_dockerhub_repos("docker")
for repo in repos:
    print(f"{repo['name']} - {repo.get('description', 'No description')}")
```

## References

- [DockerHub API Documentation](https://docs.docker.com/docker-hub/api/latest/)
- [DockerHub Registry HTTP API](https://docs.docker.com/registry/spec/api/)
