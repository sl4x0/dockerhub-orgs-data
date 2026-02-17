# dockerhub-orgs-data

[![Update Programs](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/update.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/update.yml)
[![Validate Data](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/validate.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/validate.yml)

> **🐳 Mapping Bug Bounty Programs to DockerHub Organizations**

A comprehensive, fully-automated database mapping 2000+ bug bounty programs to their DockerHub organizations/usernames for security research and container analysis.

## 🎯 Purpose

This repository helps security researchers discover DockerHub organizations associated with bug bounty programs for:

1. **Leaked Secrets** - Scan container images for exposed credentials and API keys
2. **Supply Chain Security** - Analyze dependencies and base images in production containers
3. **Reconnaissance** - Discover public container repositories and image configurations
4. **Container Vulnerabilities** - Find outdated packages and known CVEs in Docker images

## 🤖 Automation

This repository is **fully automated** with GitHub Actions:

- **Daily Updates** (02:00 UTC): Fetches latest bug bounty programs from all platforms
- **Weekly Auto-Discovery** (Saturdays 04:00 UTC): Automatically discovers DockerHub usernames using intelligent pattern matching
- **Continuous Validation**: Validates data format and checks organization status
- **Automatic Reports**: Generates statistics and detailed reports

### 🧠 Intelligent Discovery

The auto-discovery system uses smart variations to find DockerHub organizations:

1. **Exact Matches** - Tests the program name directly
2. **Name Variations** - Removes hyphens, underscores, tries different combinations  
3. **Common Patterns** - Tests with common suffixes (hq, inc, io, team, official)
4. **Split Names** - Tries first/last parts of hyphenated names
5. **Direct Verification** - Validates each candidate against DockerHub API

This approach discovers ~40-60% of DockerHub usernames automatically, with the rest requiring manual research.

### Current Stats

- **Total Programs**: 2066+
- **Mapped DockerHub Organizations**: 16+
- **Platforms**: HackerOne, Bugcrowd, Intigriti, YesWeHack, Federacy, Chaos (ProjectDiscovery), diodb (disclose.io), and more!

## Quick Start

```bash
# Clone the repository
git clone https://github.com/sl4x0/dockerhub-orgs-data.git
cd dockerhub-orgs-data

# List all discovered DockerHub organizations
./scripts/all-dockerhub-orgs.sh

# Find programs that need DockerHub organization mapping
./scripts/todo.sh

# Search for a specific program
./scripts/search.sh github
```

## Contributing

It is challenging to keep a database like this up-to-date. However, when each of us contributes a bit, it becomes much easier and benefits everyone!

We are open to contributions and appreciate your willingness to help! In particular, we are happy when you share missing:

1. **DockerHub organizations/usernames**
2. **Bug Bounty Programs (BBPs) / Vulnerability Disclosure Programs (VDPs)**

See the [contributing guide](CONTRIBUTING.md) for detailed instructions.

## Usage

### Legend

| Second Column Value | Meaning                                                                    |
| ------------------- | -------------------------------------------------------------------------- |
| `?`                 | This is a new program and nobody has looked for DockerHub organization(s)  |
| `-`                 | Someone has looked for DockerHub organization(s) and haven't found one     |
| non-DockerHub URL   | The program has multiple policy pages; this is the "main" policy page      |
| DockerHub user URL  | A DockerHub organization/username (e.g. `https://hub.docker.com/u/docker`) |

### Scripts

#### List all DockerHub organizations

```bash
./scripts/all-dockerhub-orgs.sh
```

**Example output:**

```
apple
archive
check
clay
confido
cyberinfo
docker
netflix
```

#### List programs missing DockerHub organizations

```bash
./scripts/todo.sh
```

**Example output:**

```
/path/to/dockerhub-orgs-data/hackerone.external_program.tsv:https://hackerone.com/shopify	?
/path/to/dockerhub-orgs-data/hackerone.external_program.tsv:https://hackerone.com/slack	?
```

#### Check if a DockerHub user exists

```bash
./scripts/check-dockerhub-user.sh USERNAME
```

## Data Structure

Data is organized in TSV (Tab-Separated Values) files within the `dockerhub-orgs-data/` directory:

- `hackerone.tsv` / `hackerone.external_program.tsv` - HackerOne programs
- `bugcrowd.tsv` / `bugcrowd.external_program.tsv` - Bugcrowd programs
- `intigriti.tsv` / `intigriti.external_program.tsv` - Intigriti programs
- `yeswehack.external_program.tsv` - YesWeHack programs
- `federacy.tsv` - Federacy programs
- `chaos.tsv` - ProjectDiscovery Chaos programs
- `diodb.tsv` - disclose.io database programs
- And more platforms...

Each file follows the format:

```
<bug_bounty_program_url>	<dockerhub_org_url_or_status>
```

## How to Find DockerHub Organizations

1. **Search by company name** on DockerHub: `https://hub.docker.com/search?q=COMPANY_NAME`
2. **Check company documentation** for container image references
3. **Look at their GitHub repositories** for Dockerfile references to DockerHub
4. **Search their websites** for Docker documentation or deployment guides
5. **Check public registries** like Docker Hub explore page

## Use Cases

### 1. Secret Scanning in Docker Images

Pull and scan Docker images from bug bounty programs for leaked credentials:

```bash
docker pull organization/image:latest
trufflehog docker --image organization/image:latest
```

### 2. Supply Chain Analysis

Analyze dependencies and base images:

```bash
docker history organization/image:latest
```

### 3. Vulnerability Research

Look for outdated packages or known vulnerabilities:

```bash
docker scout cves organization/image:latest
```

### 4. Reconnaissance

Enumerate all public repositories for an organization:

```bash
curl -s "https://hub.docker.com/v2/repositories/ORGANIZATION/?page_size=100" | jq -r '.results[].name'
```

## Dependencies

- [arkadiyt/bounty-targets-data](https://github.com/arkadiyt/bounty-targets-data) - Bug bounty targets data
- [disclose/bug-bounty-platforms](https://github.com/disclose/bug-bounty-platforms) - Bug bounty platform list
- [disclose/diodb](https://github.com/disclose/diodb) ❤️ - Full disclosure database
- [projectdiscovery/public-bugbounty-programs](https://github.com/projectdiscovery/public-bugbounty-programs) - Public bug bounty programs

## Inspired By

This repository is inspired by [nikitastupin/orgs-data](https://github.com/nikitastupin/orgs-data) which maps bug bounty programs to GitHub organizations.

## License

This project is available as open source under the terms of the MIT License.

## Acknowledgements

We are grateful to all contributors who help keep this database up-to-date!

---

**⚠️ Disclaimer**: This repository is for educational and authorized security research purposes only. Always follow responsible disclosure practices and respect bug bounty program scope and rules.
