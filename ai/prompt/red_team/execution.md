# Red Team — Execution (deterministic)

Attack scripts are **not** interpreted by an LLM. The platform runs them in Docker and builds `ExecutionResult` from real telemetry.

## Pipeline (`run_attack_execution`)

1. **Create** a container on `SANDBOX_NETWORK` using `SANDBOX_IMAGE` (default `python:3.11-slim`).
2. **Install** `httpx` in the container.
3. **Write** `/tmp/script.py` via Docker `put_archive` (tar — no shell quoting limits).
4. **Run** `python /tmp/script.py` with `SANDBOX_TIMEOUT`.
5. **Destroy** the container.
6. **Build** `ExecutionResult`:
   - **`vulnerabilities_confirmed`**: lines containing `[VULN]`; if none, substring matches against `expected_indicators` from the attack result.
   - **`status`**: `exploited` (findings, clean stderr), `partial` (findings + crash noise), `failed` (clean run, no findings), `error` (crash / non‑zero exit, no confirmed findings).
   - **`crash_detected`**: non‑zero exit or stderr containing error/traceback/segfault patterns.
   - **`error_logs`**: trimmed stderr for blue team.

## Script contract

Attack scripts should print `[VULN] ...` when a check succeeds (see Attack Script Agent prompt).
