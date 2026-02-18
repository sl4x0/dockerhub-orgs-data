# dockerhub-orgs-data

[![Update Programs](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/update.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/update.yml)
[![Validate Data](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/validate.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/validate.yml)
[![Auto-Discover](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/auto-discover.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/auto-discover.yml)

> **🐳 The Definitive Mapping of Bug Bounty Programs to DockerHub Organizations**

A comprehensive, fully-automated database connecting **1,882+ bug bounty programs** to their DockerHub organizations with **81.8% coverage**. Built for security researchers conducting container security analysis and supply chain research.

> **⚠️ RESPONSIBLE DISCLOSURE**: This repository uses automated discovery and data aggregation. While we strive for accuracy, **always manually verify DockerHub organizations and ensure you're operating within the authorized scope** of the bug bounty program before conducting any security research.

---

## 📊 Current Statistics

| Metric                             | Count        |
| ---------------------------------- | ------------ |
| **Total Bug Bounty Programs**      | 1,882        |
| **Mapped DockerHub Organizations** | 1,539        |
| **Coverage**                       | 81.8%        |
| **TODO (Needs Research)**          | 343          |
| **Data Sources**                   | 8+ platforms |

_Last automated update: Daily at 02:00 UTC_

---

## 🎯 Why This Exists

Security researchers need to discover container infrastructure associated with bug bounty programs for:

- **🔑 Secret Scanning** - Find leaked credentials, API keys, and tokens in container images
- **📦 Supply Chain Analysis** - Audit dependencies, base images, and build pipelines
- **🔍 Reconnaissance** - Enumerate public repositories, tags, and image configurations
- **🛡️ Vulnerability Research** - Identify outdated packages, CVEs, and misconfigurations

This repository solves the "Where do they host their containers?" problem at scale.

---

## 🤖 Fully Automated Pipeline

All data is maintained through GitHub Actions with zero manual intervention required:

| Workflow             | Schedule                     | Purpose                                                         |
| -------------------- | ---------------------------- | --------------------------------------------------------------- |
| **Update Programs**  | Daily 02:00 UTC              | Fetches latest bug bounty programs from all platforms           |
| **Auto-Discover**    | Weekly (Saturdays 04:00 UTC) | Discovers DockerHub usernames using AI-powered pattern matching |
| **Validate Data**    | On every push                | Ensures data integrity and format compliance                    |
| **Generate Reports** | Daily 04:50 UTC              | Produces statistics and detailed analysis reports               |

### 🧠 Intelligent Discovery Algorithm

The auto-discovery system uses multi-strategy pattern matching:

1. **Direct Match** - Tests program name as-is
2. **Normalization** - Removes hyphens, underscores, special characters
3. **Pattern Variations** - Tests with common suffixes: `hq`, `inc`, `io`, `team`, `official`, `prod`, `docker`
4. **Name Splitting** - Analyzes hyphenated names (e.g., `acme-corp` → `acme`, `corp`, `acmecorp`)
5. **API Verification** - Validates each candidate against DockerHub's official API

**Success Rate**: ~78% automatic discovery from just program URLs

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/sl4x0/dockerhub-orgs-data.git
cd dockerhub-orgs-data

# List all discovered DockerHub organizations
./scripts/all-dockerhub-orgs.sh

# Find programs that need manual research
./scripts/todo.sh

# Search for a specific program
./scripts/search.sh github
```

---

## 📁 Data Structure

Data is organized in TSV (Tab-Separated Values) files within [`dockerhub-orgs-data/`](dockerhub-orgs-data/):

| File                                         | Platform               | Programs            |
| -------------------------------------------- | ---------------------- | ------------------- |
| `hackerone.tsv`                              | HackerOne              | ~456                |
| `hackerone.external_program.tsv`             | HackerOne (External)   | ~457                |
| `chaos.tsv`                                  | ProjectDiscovery Chaos | ~798                |
| `intigriti.tsv`                              | Intigriti              | ~131                |
| `federacy.tsv`                               | Federacy               | ~35                 |
| `bugcrowd.external_program.tsv`              | Bugcrowd (External)    | ~5                  |
| `yeswehack.external_program.tsv`             | YesWeHack              | ~1                  |
| `bugcrowd.tsv`, `diodb.tsv`, `yeswehack.tsv` | -                      | Empty (in progress) |

### Format Specification

Each line follows the format:

```
<bug_bounty_program_url>\t<status_or_dockerhub_url>
```

**Status Values:**

| Value                               | Meaning                                               |
| ----------------------------------- | ----------------------------------------------------- |
| `?`                                 | New program, needs research                           |
| `-`                                 | Manually verified, no DockerHub presence found        |
| `https://hub.docker.com/u/USERNAME` | Confirmed DockerHub organization                      |
| `https://...` (non-DockerHub URL)   | Alternate/main program page (for multi-page programs) |

---

## 🔍 Usage Examples

### List All Discovered Organizations

```bash
./scripts/all-dockerhub-orgs.sh
```

**Example output:**

```
apple
archive
cloudflare
docker
netflix
shopify
```

### Find Programs Needing Research

```bash
./scripts/todo.sh
```

**Example output:**

```
dockerhub-orgs-data/hackerone.external_program.tsv:https://hackerone.com/example	?
dockerhub-orgs-data/chaos.tsv:https://example.com/security	?
```

### Verify a DockerHub Username

```bash
./scripts/check-dockerhub-user.sh USERNAME
```

**Example:**

```bash
$ ./scripts/check-dockerhub-user.sh docker
Checking DockerHub user: docker
✓ User exists: https://hub.docker.com/u/docker
```

---

## 💡 Practical Use Cases

### 1. Secret Scanning in Container Images

Use [TruffleHog](https://github.com/trufflesecurity/truffhog) to scan for leaked credentials:

```bash
# Find organization from this database
ORG="shopify"

# Pull and scan for secrets
docker pull $ORG/image:latest
trufflehog docker --image $ORG/image:latest
```

### 2. Enumerate All Public Repositories

```bash
ORG="shopify"
curl -s "https://hub.docker.com/v2/repositories/${ORG}/?page_size=100" \
  | jq -r '.results[].name'
```

### 3. Vulnerability Scanning with Docker Scout

```bash
docker scout cves $ORG/image:latest
```

### 4. Supply Chain Analysis

Inspect base images and layers:

```bash
docker history $ORG/image:latest
docker inspect $ORG/image:latest | jq '.[0].Config'
```

---

## 🛠️ Manual Discovery Tips

To find DockerHub organizations not yet mapped:

1. **Search DockerHub directly**: `https://hub.docker.com/search?q=COMPANY_NAME`
2. **Check company documentation** for container/Kubernetes references
3. **Inspect GitHub repositories** for Dockerfile `FROM` statements
4. **Search code repositories** for `docker pull` commands
5. **Review deployment docs** and infrastructure-as-code repos

---

## 🤝 Contributing

This database is community-powered. Your contributions help everyone!

**What We Need:**

- 🐳 **Missing DockerHub organizations** for programs marked with `?`
- 🆕 **New bug bounty programs** not yet in the database
- ✅ **Verification** of existing mappings
- 🐛 **Bug reports** for incorrect data

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📚 Data Sources

This repository aggregates data from:

- [arkadiyt/bounty-targets-data](https://github.com/arkadiyt/bounty-targets-data) - HackerOne, Bugcrowd, Intigriti, YesWeHack
- [projectdiscovery/public-bugbounty-programs](https://github.com/projectdiscovery/public-bugbounty-programs) - Chaos platform
- [disclose/diodb](https://github.com/disclose/diodb) ❤️ - disclose.io database
- [Federacy](https://www.federacy.com/) - Federacy platform programs

---

## 🙏 Inspired By

- [nikitastupin/orgs-data](https://github.com/nikitastupin/orgs-data) - GitHub organizations for bug bounty programs

---

## 📄 License

This project is available as open source under the terms of the MIT License.

## Acknowledgements

We are grateful to all contributors who help keep this database up-to-date!

---

**⚠️ Disclaimer**: This repository is for educational and authorized security research purposes only. Always follow responsible disclosure practices and respect bug bounty program scope and rules.
