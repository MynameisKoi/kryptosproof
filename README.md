# KryptoSproof

> Automated web security audit platform — Hack Hayward 2026

KryptoSproof is a multi-agent security framework built on [pydantic-ai](https://ai.pydantic.dev/) that orchestrates a full red team → blue team cycle against web applications. It automatically discovers vulnerabilities, generates exploit scripts, runs them in an isolated sandbox, produces fix patches, and verifies the patches work — all without human intervention.

---

## Architecture

```
Orchestrator
├── Red Team
│   ├── Attack Script Agent  — generates targeted web exploit scripts
│   └── Execution Agent      — runs scripts in an isolated Docker sandbox
└── Blue Team
    ├── Fix Script Agent     — parses crash logs and generates patches
    └── Testing Agent        — re-runs the attack to verify fixes
```

### Data Flow

```
Target URL
  → Attack Script Agent  →  exploit script + payloads
  → Execution Agent      →  confirmed vulnerabilities + error logs
  → Fix Script Agent     →  patches + fix script
  → Testing Agent        →  verification result
  → SecurityAuditReport  →  markdown report + JSON output
```

---

## Vulnerability Coverage

| Type | Severity |
|---|---|
| SQL Injection | Critical / High |
| Cross-Site Scripting (XSS) | High |
| Command Injection | Critical |
| Path Traversal | High |
| Broken Authentication | Critical |
| CSRF | Medium |
| SSRF | High |
| Security Misconfiguration | Low / Medium |

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Docker](https://www.docker.com/) — for the sandbox and DVWA target
- An [Anthropic API key](https://console.anthropic.com/)

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-org/kryptosproof
cd kryptosproof

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Start the sandbox + DVWA target
docker-compose up -d
```

---

## Usage

```bash
# Audit the default target (DVWA on localhost:8080)
uv run python main.py

# Audit a custom target
uv run python main.py http://your-target.com
```

Reports are saved to `logs/report.json` and printed as markdown to stdout.

---

## Project Structure

```
kryptosproof/
├── main.py                    # Entry point
├── config.py                  # Settings (pydantic-settings + .env)
├── docker-compose.yml         # DVWA target + sandbox network
├── dockerfile
│
├── ai/
│   ├── agents/
│   │   ├── orchestrator.py    # Top-level coordinator agent
│   │   ├── red_team/
│   │   │   ├── attack_script.py
│   │   │   └── execution.py
│   │   └── blue_team/
│   │       ├── fix_script.py
│   │       └── testing.py
│   └── prompt/                # Markdown system prompts per agent
│
├── schemas/                   # Pydantic models for inter-agent data
│   ├── orchestrator.py
│   ├── red_team.py/
│   └── blue_team.py/
│
└── tools/
    ├── sandbox.py             # Docker sandbox management
    └── web_recon.py           # Web reconnaissance utilities
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `TARGET_URL` | `http://dvwa:80` | Target web application URL |
| `MODEL` | `claude-opus-4-6` | Claude model to use |
| `SANDBOX_TIMEOUT` | `30` | Script execution timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## License

MIT
