# KryptosProof

> Automated web security audit platform — Hack Hayward 2026

KryptosProof is a multi-agent security framework built on [pydantic-ai](https://ai.pydantic.dev/) that orchestrates a full red team → blue team cycle against web applications. It automatically discovers vulnerabilities, generates exploit scripts, runs them in an isolated Docker sandbox, produces fix patches, verifies fix quality — all driven by an LLM orchestrator with no human intervention.

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │           Orchestrator Agent         │
                        │  (pydantic-ai · drives tool calls)  │
                        └────────────┬────────────────────────┘
                                     │
               ┌─────────────────────┴──────────────────────┐
               │  RED TEAM                                   │  BLUE TEAM
               ▼                                             ▼
   Attack Script Agent                            Fix Script Agent
   · Generates targeted                           · Reads confirmed vulns
     Python exploit script                          and attack logs
   · Uses recon tools                             · Generates a patch +
     (Nuclei, FFUF, sqlmap,                         a runnable fix_script
     ZAP, PayloadsAllTheThings)                   · Runs fix in isolated
                                                    Docker workspace to
   Execution Pipeline                               self-validate
   · Runs script in Docker
     sandbox (no LLM)                            Testing Agent
   · Parses [VULN] markers                       · Static analysis of fix
   · Returns ExecutionResult                       (checks for correct
                                                   defensive patterns)
                                                 · Re-runs original attack
                                                   as an audit log
                                                 · Retry loop (up to 2×)
                                                   if fix quality is weak
```

### Data Flow

```
Target URL
  → Attack Script Agent   →  exploit script + payloads
  → Execution Pipeline    →  confirmed vulnerabilities + stdout/stderr logs
  → Fix Script Agent      →  patches + fix_script (workspace-validated)
  → Testing Agent         →  semantic fix verification + retest log
  → SecurityAuditReport   →  overall_status + markdown report
  → FastAPI + Next.js     →  live phase tracking in the browser
```

### Fix Verification — how it works

Because the audit target (DVWA) is a running Docker container that cannot be patched mid-run, the testing agent uses **static/semantic analysis** as its primary signal rather than live retesting:

1. `analyze_fix_coverage()` — pattern-matches the fix script for correct defensive constructs per vulnerability type (e.g. `parameterized`/`cursor.execute` for SQL injection, `html.escape` for XSS, `shlex.quote` for command injection). A `coverage_score ≥ 50` sets `overall_patched = True`.
2. `rerun_attack()` — re-runs the original exploit as a secondary audit log. Since DVWA is unmodified, `[VULN]` markers are expected and do **not** flip the verdict — the output is stored in the Patch Verification phase log for human review.
3. If verification fails, the orchestrator retries the fix agent (up to 2 attempts) with the test failure context.

---

## Vulnerability Coverage

| Type | Tools Used |
|---|---|
| SQL Injection | sqlmap, custom httpx scripts |
| Cross-Site Scripting (XSS) | Nuclei, custom scripts |
| Command Injection | Custom httpx scripts |
| Path Traversal | FFUF, custom scripts |
| Broken Authentication | Custom scripts |
| CSRF | Custom scripts |
| SSRF | Custom scripts |
| Security Misconfiguration | Nuclei, ZAP, security headers check |

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Docker](https://www.docker.com/) — for the sandbox, DVWA target, and patch workspace
- An LLM API key — Anthropic (`ANTHROPIC_API_KEY`) or Google AI Studio (`GEMINI_API_KEY`)

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
# Edit .env — set your API key and model (see Environment Variables below)

# 4. Start DVWA (the vulnerable target) and create the sandbox network
docker-compose up -d dvwa

# 5. (DVWA only) Complete the initial setup
#    Open http://localhost:8080/setup.php → click "Create / Reset Database"
#    Then go to DVWA Security → set level to "Low"
```

---

## Running

### Backend (FastAPI)

```bash
uv run uvicorn api:app --reload --port 8000
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

The frontend proxies `/api/backend/*` to `http://localhost:8000` via Next.js rewrites.

### CLI (no frontend)

```bash
# Audit the default target (DVWA)
uv run python main.py

# Audit a custom target
uv run python main.py http://your-target.com
```

---

## Project Structure

```
kryptosproof/
├── api.py                     # FastAPI server — audit lifecycle + phase tracking
├── main.py                    # CLI entry point
├── config.py                  # Settings (pydantic-settings + .env)
├── docker-compose.yml         # DVWA target + kryptosproof_sandbox network
│
├── ai/
│   ├── agents/
│   │   ├── orchestrator.py    # Top-level coordinator; runs red→blue loop
│   │   ├── red_team/
│   │   │   ├── attack_script.py   # Generates exploit scripts via LLM
│   │   │   └── execution.py       # (unused directly — execution_pipeline.py handles it)
│   │   └── blue_team/
│   │       ├── fix_script.py      # Generates + workspace-validates patches
│   │       ├── testing.py         # Semantic fix verification + retest
│   │       └── handoff_report.py  # Developer handoff when fix fails
│   └── prompt/                # Markdown system prompts per agent
│       ├── orchestrator.md
│       ├── red_team/
│       └── blue_team/
│
├── schemas/                   # Pydantic models for inter-agent data
│   ├── orchestrator.py        # SecurityAuditReport, VulnerabilityReport
│   ├── red_team.py/           # AttackScriptResult, ExecutionResult
│   └── blue_team.py/          # FixScriptResult, TestResult, BlueTeamHandoffReport
│
├── tools/
│   ├── sandbox.py             # Docker sandbox — create/run/destroy
│   ├── patch_workspace.py     # Isolated Docker workspace for fix validation
│   ├── execution_pipeline.py  # Deterministic red team execution (no LLM)
│   ├── attack_validation.py   # Attack script quality checks
│   ├── web_recon.py           # Endpoint discovery, form extraction, headers
│   ├── red_team.py            # Nuclei, FFUF, sqlmap, ZAP wrappers
│   ├── payloads_pat.py        # PayloadsAllTheThings integration
│   ├── gitleaks.py            # Secret scanning on source repos
│   ├── zap_api.py             # OWASP ZAP JSON API client
│   └── tool_logs.py           # Structured log merging
│
└── frontend/                  # Next.js dashboard
    └── src/app/
        ├── page.tsx           # Dashboard — live audit + history
        ├── audit/new/         # Launch a new audit
        ├── audit/[id]/        # Live audit detail with phase logs
        └── history/           # Past audits
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/audits` | Start a new audit (runs in background) |
| `GET` | `/api/audits` | List all audits (newest first) |
| `GET` | `/api/audits/{id}` | Get audit details + live phase output |
| `POST` | `/api/sandbox/run` | Run an arbitrary Python script in the sandbox |

Audits are stored in memory — they are lost on server restart.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AI_MODEL` | `anthropic:claude-opus-4-6` | pydantic-ai model ID — prefix determines provider (`anthropic:`, `google-gla:`) |
| `ANTHROPIC_API_KEY` | — | Required if using an Anthropic model |
| `GEMINI_API_KEY` | — | Required if using a Gemini model |
| `TARGET_URL` | `http://dvwa:80` | Default audit target (used by docker-compose) |
| `SANDBOX_TIMEOUT` | `30` | Script execution timeout in seconds |
| `SANDBOX_IMAGE` | `python:3.11-slim` | Docker image for the execution sandbox |
| `SANDBOX_NETWORK` | `kryptosproof_sandbox` | Docker network shared with DVWA |
| `SOURCE_REPO_PATH` | — | Path to a local source repo for Gitleaks secret scanning |
| `BLUE_TEAM_MIRROR_SOURCE` | — | Host directory to copy into the patch workspace |
| `ZAP_PROXY_URL` | `http://127.0.0.1:8080` | OWASP ZAP JSON API (optional) |
| `LOGFIRE_TOKEN` | — | Logfire token for pydantic-ai tracing (optional) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## License

MIT
