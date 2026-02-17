# Security Research Use Cases

This document outlines various security research use cases for the dockerhub-orgs-data repository.

## 1. Secret Scanning

### Leaked Credentials in Images

Many organizations publish Docker images that may contain:

- API keys
- Database passwords
- Private keys
- OAuth tokens
- Configuration files with secrets

#### Tools

**TruffleHog**

```bash
# Scan a Docker image
trufflehog docker --image organization/app:latest

# Scan with custom regex
trufflehog docker --image organization/app:latest --regex patterns.json
```

**Gitleaks**

```bash
docker save organization/app:latest -o image.tar
gitleaks detect --source image.tar
```

**Trivy**

```bash
trivy image --scanners secret organization/app:latest
```

### Practical Example

```bash
# Get all DockerHub orgs from bug bounty programs
./scripts/all-dockerhub-orgs.sh > orgs.txt

# For each organization, scan their images
while read org; do
  echo "Scanning organization: $org"

  # Get all repositories
  repos=$(curl -s "https://hub.docker.com/v2/repositories/${org}/?page_size=100" | \
    jq -r '.results[].name')

  for repo in $repos; do
    echo "  Scanning: $org/$repo"
    docker pull "$org/$repo:latest" 2>/dev/null
    trufflehog docker --image "$org/$repo:latest" --json >> secrets.json
  done

  sleep 5  # Rate limiting
done < orgs.txt
```

## 2. Supply Chain Security

### Dependency Analysis

Analyze what base images and dependencies organizations use.

```bash
# Check base images
docker history organization/app:latest | grep FROM

# Extract all layers
docker save organization/app:latest -o app.tar
tar -xf app.tar

# Analyze package managers
docker run --rm -it organization/app:latest sh -c "pip list"
docker run --rm -it organization/app:latest sh -c "npm list -g"
```

### Vulnerable Dependencies

```bash
# Scan for vulnerabilities
trivy image organization/app:latest

# Generate SBOM
syft organization/app:latest -o spdx-json > sbom.json
```

## 3. Configuration Security

### Exposed Ports and Services

```bash
# Check exposed ports
docker inspect organization/app:latest | jq '.[].Config.ExposedPorts'

# Check environment variables
docker inspect organization/app:latest | jq '.[].Config.Env'
```

### Hardcoded Credentials

```bash
# Extract filesystem
docker create --name temp organization/app:latest
docker export temp > filesystem.tar
tar -xf filesystem.tar
rm filesystem.tar
docker rm temp

# Search for common config files
grep -r "password" etc/
grep -r "api_key" opt/
```

## 4. Reconnaissance

### Domain Discovery

```bash
# Extract domains from images
docker save organization/app:latest -o app.tar
tar -xf app.tar
grep -rEoh "https?://[a-zA-Z0-9./?=_%:-]+" . | sort -u > domains.txt
```

### Email Addresses

```bash
# Find email addresses
docker history organization/app:latest --no-trunc | \
  grep -Eoh "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
```

### Technology Stack

```bash
# Identify technologies
docker run --rm -it organization/app:latest sh -c "cat /proc/version"
docker run --rm -it organization/app:latest sh -c "env"

# Check for common frameworks
docker run --rm -it organization/app:latest sh -c "ls /app"
docker run --rm -it organization/app:latest sh -c "cat package.json"
docker run --rm -it organization/app:latest sh -c "cat requirements.txt"
```

## 5. Vulnerability Research

### Outdated Packages

```bash
# Check base image version
docker inspect organization/app:latest | jq '.[].Config.Image'

# Compare with latest
docker pull organization/app:latest
docker pull ubuntu:latest  # or relevant base

# Check for known vulnerabilities
grype organization/app:latest
```

### Misconfigurations

```bash
# Check if running as root
docker inspect organization/app:latest | jq '.[].Config.User'

# Check capabilities
docker inspect organization/app:latest | jq '.[].HostConfig.CapAdd'

# Check for privileged mode indicators
docker inspect organization/app:latest | jq '.[].HostConfig.Privileged'
```

## 6. Authentication & Authorization

### API Keys and Tokens

```bash
# Search for common secret patterns
docker save organization/app:latest -o app.tar
tar -xf app.tar

# Look for various secret types
grep -r "AKIA" .  # AWS keys
grep -r "ghp_" .  # GitHub tokens
grep -r "sk_live" .  # Stripe keys
grep -r "xox[baprs]" .  # Slack tokens
```

## 7. OSINT & Metadata

### Build Information

```bash
# Check labels and metadata
docker inspect organization/app:latest | jq '.[].Config.Labels'

# Check maintainer info
docker inspect organization/app:latest | jq '.[].Author'

# Check build args
docker history organization/app:latest --no-trunc
```

### Historical Analysis

```bash
# Get all tags for a repository
curl -s "https://hub.docker.com/v2/repositories/organization/app/tags/?page_size=100" | \
  jq -r '.results[] | "\(.name) - \(.last_updated)"'

# Compare versions
docker pull organization/app:v1.0
docker pull organization/app:v2.0
container-diff diff daemon://organization/app:v1.0 daemon://organization/app:v2.0
```

## 8. Automated Workflows

### Continuous Monitoring

```bash
#!/bin/bash
# monitor.sh - Monitor for new images

ORGS=$(./scripts/all-dockerhub-orgs.sh)

for org in $ORGS; do
  # Get latest images
  images=$(curl -s "https://hub.docker.com/v2/repositories/${org}/?page_size=10" | \
    jq -r '.results[] | "\(.name):\(.last_updated)"')

  echo "$images" | while read image; do
    name=$(echo "$image" | cut -d: -f1)

    # Pull and scan
    docker pull "$org/$name:latest"

    # Run security checks
    trivy image "$org/$name:latest" --severity HIGH,CRITICAL
    trufflehog docker --image "$org/$name:latest"

    # Log results
    echo "Scanned: $org/$name at $(date)" >> scan_log.txt
  done

  sleep 10
done
```

## Best Practices

1. **Always respect scope** - Only scan programs you're participating in
2. **Rate limiting** - Add delays between API calls
3. **Responsible disclosure** - Report findings through proper channels
4. **Document findings** - Keep records of your research
5. **Stay legal** - Follow bug bounty program rules

## Tools Reference

- **TruffleHog**: Secret scanning
- **Gitleaks**: Secret detection
- **Trivy**: Vulnerability scanning
- **Grype**: Vulnerability scanner
- **Syft**: SBOM generation
- **Dive**: Image layer analysis
- **Container-diff**: Compare images
- **Docker Scout**: Supply chain security

## Legal Notice

This repository is for **authorized security research only**. Always:

- Get permission before testing
- Follow bug bounty program rules
- Respect rate limits
- Practice responsible disclosure
- Comply with local laws
