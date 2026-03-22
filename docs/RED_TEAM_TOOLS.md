# Red Team — Tools & Toolset Reference

This document lists every tool exposed to the red-team agents, what each one does, and when to use it. Implementation lives in `ai/agents/red_team/attack_script.py`, `ai/agents/red_team/execution.py`, and `tools/`.

---

## Master table — all tools

| # | Tool name (Attack Script Agent) | Tool name (Execution Agent) | What it does |
|---|--------------------------------|-----------------------------|--------------|
| 1 | `probe_target_endpoints` | `probe` | Sends HTTP GETs to a built-in list of common paths on the target and returns status codes, lengths, and header hints so you can see which routes exist. |
| 2 | `check_security_headers` | `security_headers` | Fetches the target once and extracts security-related response headers (e.g. CSP, HSTS, X-Frame-Options) to assess baseline hardening. |
| 3 | `detect_target_technologies` | `detect_tech` | Inspects response headers and a short body sample for fingerprints (cookies, framework strings) to guess stack (PHP, Django, etc.). |
| 4 | `extract_forms` | `forms` | Parses HTML forms for a given path; returns actions, methods, input names, and whether a CSRF-like token might be present. |
| 5 | `nuclei_scan` | `nuclei` | Runs the Nuclei CLI against the target URL and returns template findings (JSON); optional template tags and severity filter. |
| 6 | `ffuf_fuzz_directories` | `ffuf` | Runs FFUF to fuzz one path segment against a wordlist (default `wordlists/common.txt`) to discover hidden paths or files. |
| 7 | `sqlmap_scan` | `sqlmap` | Runs sqlmap against a **full URL that includes at least one HTTP parameter** (e.g. `?id=1`) for automated SQL injection testing. |
| 8 | `pat_search_payload_files` | `pat_search` | Searches the local PayloadsAllTheThings tree (`PAYLOADS_ROOT`) for `.txt` files whose paths match a keyword. |
| 9 | `pat_read_payload_lines` | `pat_read` | Reads up to `max_lines` non-empty, non-comment lines from a file under `PAYLOADS_ROOT` (path from search). |
| 10 | `zap_status` | `zap_status_check` | Calls ZAP’s JSON API to verify the proxy is reachable at `ZAP_PROXY_URL`. |
| 11 | `zap_spider_scan` | `zap_spider` | Drives ZAP to spider the target URL, then returns passive scan alerts for that scope. |
| 12 | `zap_aggressive_active_scan` | `zap_active` | Starts ZAP’s **active** scan against the target (aggressive; use only on authorized systems). |
| 13 | — | `run_all_recon` | **Execution only:** runs probe, headers, tech, forms, Nuclei, FFUF, ZAP ping, and optionally ZAP spider in one chained call; returns one aggregated dict. |
| 14 | — | `create_attack_sandbox` | **Execution only:** creates a Docker container on the sandbox network and returns its ID for running the attack script. |
| 15 | — | `run_attack_script` | **Execution only:** installs `httpx`, writes the attack `script` to the container, runs it, returns stdout/stderr/exit code and crash heuristics. |
| 16 | — | `teardown_sandbox` | **Execution only:** stops and removes the sandbox container by ID. |
| 17 | — | `execute_attack` | **Execution only:** runs the full deterministic pipeline (create → run script → destroy) and returns a structured `ExecutionResult` (preferred over manual 14–16). |

**Legend:** Rows 1–12 are the same behavior in both agents where two names appear; Attack Script uses the left name, Execution’s `FunctionToolset` uses the right name. Rows 13–17 exist only on the **Execution Agent**.

---

## How the pieces fit together

| Piece | Role |
|--------|------|
| **Attack Script Agent** | Uses **flat tools** (no `FunctionToolset`) to gather recon and scanner output, then produces an **`AttackScriptResult`** (including a Python `script` that runs in Docker with `httpx`). |
| **Execution Agent** | Uses a **`FunctionToolset`** with the same recon/scanner logic under **shorter names**, plus **sandbox tools** and **`execute_attack`**. Intended for flows where an LLM orchestrates recon + execution after a script already exists. |
| **Main audit pipeline** (`orchestrator`) | Calls **`attack_script_agent`** → validation → **`run_attack_execution`** (deterministic). It does **not** call **`execution_agent.run`** by default. |

---

## Order of activation (what runs when)

### 1. Default red-team path (`run_audit` → orchestrator → `run_red_team`)

This is what **`main.py`** drives. **Tool call order is not hard-coded** for recon/scanners; only the **pipeline stages** are fixed.

| Stage | What runs | Order / notes |
|-------|-----------|----------------|
| A | **Orchestrator** LLM | Chooses when to call `run_red_team` / `run_blue_team` and with what arguments (e.g. `vulnerability_focus`). **Order of focuses is model-defined.** |
| B | **`run_red_team` tool** (per focus) | **Fixed sequence:** (1) **`attack_script_agent.run`** → (2) **`validate_attack_script_result`** → (3) **`run_attack_execution`**. |
| C | **Attack Script Agent** (inside B.1) | The model may call **zero or more** tools (`probe_target_endpoints`, `nuclei_scan`, …) in **any order** and **any number of times**. There is **no** enforced order in code. |
| D | **`run_attack_execution`** (inside B.3) | **Fixed sequence** (see below). **Does not** call the Attack Script or Execution tool APIs — only Docker + script run. |

### 2. Fixed sequence inside `run_attack_execution` (sandbox)

Used by the default pipeline and by the **`execute_attack`** tool. **No LLM.**

| Step | Action |
|------|--------|
| 1 | `create_sandbox` — start container on `SANDBOX_NETWORK` |
| 2 | `pip install httpx` (inside container) |
| 3 | Write `/tmp/script.py` via Docker `put_archive` (tar) |
| 4 | `python /tmp/script.py` (subject to `SANDBOX_TIMEOUT`) |
| 5 | `destroy_sandbox` — stop and remove container |
| 6 | Build **`ExecutionResult`** from stdout/stderr (e.g. `[VULN]` lines, indicators) |

### 3. Fixed sequence inside `run_all_recon` (Execution Agent toolset only)

When the **`run_all_recon`** tool is invoked, the code runs **this order** (each awaits the previous):

1. `probe` (`probe_endpoints`)
2. `security_headers` (`get_security_headers`)
3. `technologies` (`detect_technologies`)
4. `forms` (`get_forms` on `target/` )
5. `nuclei` (`run_nuclei_scan`)
6. `ffuf` (`run_ffuf_directory_fuzz`)
7. `zap` (`zap_ping`)
8. **If** ZAP reports `available`: `zap_spider` (`zap_spider_and_alerts`)

**Not** run in this batch: `sqlmap`, PAT search/read, ZAP active (by design).

### 4. Manual sandbox path (Execution Agent only)

If the model does **not** use **`execute_attack`**, the intended order is:

1. `create_attack_sandbox`
2. `run_attack_script`
3. `teardown_sandbox`

### 5. `execution_agent.run` (optional, not default audit)

If you call **`execution_agent.run`** yourself, **tool order is LLM-defined** among the toolset + sandbox tools — same idea as Attack Script Agent: **no** fixed order except when the model chooses **`run_all_recon`** (then §3 applies) or **`execute_attack`** (then §2 applies).

---

## Recon & HTTP (httpx-based)

These tools hit the **target URL** from agent deps (`target_url`). They are safe for broad discovery before writing exploit logic.

| Tool (Attack Script Agent) | Tool (Execution `FunctionToolset`) | What it does | Use case |
|----------------------------|-------------------------------------|--------------|----------|
| `probe_target_endpoints` | `probe` | GETs a fixed list of common paths (`/`, `/login`, `/admin`, …) and returns status, length, headers. | Map what exists on the host; prioritize pages to test. |
| `check_security_headers` | `security_headers` | Reads security-related headers (CSP, HSTS, X-Frame-Options, …). | Spot missing hardening; note for XSS/clickjacking narrative. |
| `detect_target_technologies` | `detect_tech` | Heuristics from headers + body snippet (cookies, framework strings). | Choose payloads (PHP vs Java, etc.) and template wording. |
| `extract_forms` | `forms` | Parses HTML forms on `target_url + path` (default `/`): action, method, input names, CSRF hints. | Find injection points, CSRF, login flows; build `httpx` requests in the generated script. |

**Prerequisites:** Target must be reachable from the process running the agent (host or container). No extra binaries.

---

## External scanners (must be on `PATH` or in your Docker image)

| Tool (Attack Script) | Tool (Execution) | What it does | Use case |
|----------------------|------------------|----------------|----------|
| `nuclei_scan` | `nuclei` | Runs [Nuclei](https://github.com/projectdiscovery/nuclei) against the base URL; JSON findings. Optional `tags` / `severity`. | Broad template-based issues (misconfigs, known CVE-style checks). |
| `ffuf_fuzz_directories` | `ffuf` | [FFUF](https://github.com/ffuf/ffuf) path fuzzing on `{base}/FUZZ` using `wordlists/common.txt` or a custom path. | Discover hidden paths (`/admin`, `/api`, …). |
| `sqlmap_scan` | `sqlmap` | [sqlmap](https://github.com/sqlmapproject/sqlmap) on a **full URL that already has a query parameter** (e.g. `...?id=1`). | Deep SQLi testing when a parameter is known. |

**If the binary is missing:** the tool returns `available: false` (or similar). Fall back to **httpx** in the generated script.

**Use case nuance:** Prefer **recon + forms** first to find parameters, then pass a concrete URL into **`sqlmap_scan`** / **`sqlmap`**.

---

## PayloadsAllTheThings (local files)

| Tool (Attack Script) | Tool (Execution) | What it does | Use case |
|----------------------|------------------|--------------|----------|
| `pat_search_payload_files` | `pat_search` | Search under **`PAYLOADS_ROOT`** (default `third_party/PayloadsAllTheThings`) for `.txt` paths matching a **keyword**. | Find wordlists/snippets for SQLi/XSS/RCE when the repo is cloned. |
| `pat_read_payload_lines` | `pat_read` | Read up to `max_lines` non-comment lines from a **relative path** under `PAYLOADS_ROOT`. | Feed concrete strings into the generated script or report. |

**Prerequisites:** Clone [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings) into `PAYLOADS_ROOT` (or set `PAYLOADS_ROOT` in config). **Do not** commit the full clone if it is huge; `.gitignore` may exclude it.

---

## OWASP ZAP (JSON API)

| Tool (Attack Script) | Tool (Execution) | What it does | Use case |
|----------------------|------------------|--------------|----------|
| `zap_status` | `zap_status_check` | Ping ZAP’s REST API (`ZAP_PROXY_URL`). | Confirm ZAP is up before heavier scans. |
| `zap_spider_scan` | `zap_spider` | Spider the target, then fetch **passive** alerts. | Map surface + low-noise findings. |
| `zap_aggressive_active_scan` | `zap_active` | Start **active** scan (can be destructive). | Only on **authorized** targets (e.g. local DVWA). |

**Prerequisites:** ZAP daemon reachable at `ZAP_PROXY_URL`; ZAP must reach the target (same Docker network as the app when using compose).

---

## Batch recon (Execution toolset only)

| Tool | What it does | Use case |
|------|----------------|----------|
| `run_all_recon` | Runs **in order:** probe → security headers → technologies → forms (`/`) → Nuclei → FFUF → ZAP ping; if ZAP is available, runs **ZAP spider** as well. | One-shot landscape before manual tool calls or before running the sandbox. |

**Does not include:** `sqlmap`, PAT search/read, or ZAP **active** scan (to avoid long or dangerous runs by default).

---

## Sandbox & execution (Execution Agent only)

These operate on **`ExecutionDeps.attack_script.script`** in an isolated **Docker** container.

| Tool | What it does | Use case |
|------|----------------|----------|
| `create_attack_sandbox` | Starts a container (`SANDBOX_IMAGE` on `SANDBOX_NETWORK`); returns container ID. | Manual step when you want control between create / run / teardown. |
| `run_attack_script` | Installs `httpx`, writes `script.py` via tar, runs `python /tmp/script.py`; returns stdout/stderr/exit_code. | Run the generated script after `create_attack_sandbox`. |
| `teardown_sandbox` | Stops and removes the container. | Cleanup after `run_attack_script`. |
| **`execute_attack`** | **Same** as the full pipeline: create → run → destroy → build **`ExecutionResult`** (deterministic). | **Preferred** end-to-end execution; avoids LLM mis-formatting the final result. |

**Prerequisites:** Docker available to the process; target hostname must resolve from **inside** the sandbox (e.g. `http://dvwa:80` on the compose network).

---

## Quick reference: name mapping (Attack Script ↔ Execution toolset)

| Attack Script Agent | Execution `FunctionToolset` |
|---------------------|----------------------------|
| `probe_target_endpoints` | `probe` |
| `check_security_headers` | `security_headers` |
| `detect_target_technologies` | `detect_tech` |
| `extract_forms` | `forms` |
| `nuclei_scan` | `nuclei` |
| `ffuf_fuzz_directories` | `ffuf` |
| `sqlmap_scan` | `sqlmap` |
| `pat_search_payload_files` | `pat_search` |
| `pat_read_payload_lines` | `pat_read` |
| `zap_status` | `zap_status_check` |
| `zap_spider_scan` | `zap_spider` |
| `zap_aggressive_active_scan` | `zap_active` |

*(Same underlying functions; different exposed names.)*

---

## Configuration (env / `config.py`)

| Concern | Typical settings |
|---------|------------------|
| Target | `target_url` |
| Sandbox | `sandbox_image`, `sandbox_network`, `sandbox_timeout` |
| Payloads | `PAYLOADS_ROOT` |
| ZAP | `ZAP_PROXY_URL`, `ZAP_API_KEY` |
| Scanner timeouts | `RED_TEAM_NUCLEI_TIMEOUT`, `RED_TEAM_FFUF_TIMEOUT`, `RED_TEAM_SQLMAP_TIMEOUT` |
| Attack script limits | `attack_script_min_chars`, `max_attack_script_bytes`, `attack_output_retries` |
| Execution log size | `max_execution_output_chars` |

---

## Local verification (no Docker / no LLM)

Run the **mock red-team execution** test — it patches the sandbox and checks `run_attack_execution` → `ExecutionResult` parsing:

```bash
uv run pytest tests/test_red_team_mock.py -v
```

---

## Safety

Use **sqlmap**, **Nuclei**, **FFUF**, **ZAP active**, and generated exploit scripts only against **systems you are allowed to test**. This project assumes lab targets (e.g. DVWA) or explicit authorization.
