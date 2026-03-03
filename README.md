# dockerhub-orgs-data

[![Update Programs](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/update.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/update.yml)
[![Validate Data](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/validate.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/validate.yml)
[![Auto-Discover](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/auto-discover.yml/badge.svg)](https://github.com/sl4x0/dockerhub-orgs-data/actions/workflows/auto-discover.yml)

> **🐳 The Definitive Mapping of Bug Bounty Programs to DockerHub Organizations**

A comprehensive, fully-automated database connecting **1,882+ bug bounty programs** to their DockerHub organizations with **81.8% coverage**. Built for security researchers conducting container security analysis and supply chain research.

> **⚠️ RESPONSIBLE DISCLOSURE**: This repository uses automated discovery and data aggregation. While we strive for accuracy, **always manually verify DockerHub organizations and ensure you're operating within the authorized scope** of the bug bounty program before conducting any security research.

---

## 📊 Current Statistics

| Metric                             | Count       |
| ---------------------------------- | ----------- |
| **Total Bug Bounty Programs**      | 3,330       |
| **Mapped DockerHub Organizations** | 98         |
| **Coverage**                       | 2.9%       |
| **TODO (Needs Research)**          | 3,232       |
| **Data Sources**                   | 8 platforms |

_Last automated update: 2026-03-03 UTC_

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

| Workflow             | Schedule        | Purpose                                                          |
| -------------------- | --------------- | ---------------------------------------------------------------- |
| **Update Programs**  | Daily 02:00 UTC | Fetches latest bug bounty programs from all platforms            |
| **Auto-Discover**    | Daily 05:00 UTC | Discovers DockerHub usernames using intelligent pattern matching |
| **Generate Reports** | Daily 06:00 UTC | Produces statistics and detailed analysis reports                |
| **Validate Data**    | On every push   | Ensures data integrity and format compliance                     |

### 🧠 Intelligent Discovery Algorithm

The auto-discovery system uses a **low false-positive** strategy:

1. **Domain-Aware Extraction** - Detects whether a URL belongs to a known bug bounty platform (uses the URL path) or a company website (extracts the second-level domain)
2. **Exact Match** - Tests the program identifier as-is
3. **Separator Normalization** - Tests with hyphens removed, underscores removed, and both removed
4. **API Verification** - Validates each candidate with a HEAD request to DockerHub's official API

> Split-name parts (e.g., `corp` from `example-corp`) and suffix appends (`hq`, `inc`, `io`) are intentionally **not tested** to keep the false-positive rate near zero.

**Coverage**: ~28% overall across all 8 platforms (diodb entries are company websites, harder to match automatically)

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

| File                             | Platform               | Programs |
| -------------------------------- | ---------------------- | -------- |
| `hackerone.tsv`                  | HackerOne (bounty)     | ~234     |
| `hackerone.external_program.tsv` | HackerOne (VDPs)       | ~221     |
| `chaos.tsv`                      | ProjectDiscovery Chaos | ~798     |
| `diodb.tsv`                      | disclose.io (diodb)    | ~1,609   |
| `bugcrowd.tsv`                   | Bugcrowd               | ~211     |
| `intigriti.tsv`                  | Intigriti              | ~134     |
| `yeswehack.external_program.tsv` | YesWeHack              | ~90      |
| `federacy.tsv`                   | Federacy               | ~35      |

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
