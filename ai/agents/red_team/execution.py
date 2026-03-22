"""
Red Team — Execution agent with full attack-script tool set + sandbox tools.
Tools run recon/exploit scanners one-by-one; sandbox tools execute the generated script.
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.toolsets import FunctionToolset

from config import settings
from schemas import AttackScriptResult, ExecutionResult
from tools.execution_pipeline import run_attack_execution
from tools.payloads_pat import read_payload_lines, search_payload_files
from tools.red_team import run_ffuf_directory_fuzz, run_nuclei_scan, run_sqlmap_probe
from tools.sandbox import create_sandbox, destroy_sandbox, run_script_string
from tools.tool_logs import merge_tool_logs, with_logs
from tools.web_recon import probe_endpoints, get_security_headers, detect_technologies, get_forms
from tools.zap_api import zap_active_scan, zap_ping, zap_spider_and_alerts

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "red_team" / "execution.md").read_text()


@dataclass
class ExecutionDeps:
    attack_script: AttackScriptResult
    target_url: str


def _attack_script_toolset() -> FunctionToolset[ExecutionDeps]:
    """Toolset that runs each attack-script tool one by one (recon + scanners)."""

    async def probe(ctx: RunContext[ExecutionDeps]) -> dict:
        """Probe common endpoints; includes `endpoints` and `logs`."""
        return await probe_endpoints(ctx.deps.target_url)

    async def security_headers(ctx: RunContext[ExecutionDeps]) -> dict:
        """Return security headers plus `logs`."""
        return await get_security_headers(ctx.deps.target_url)

    async def detect_tech(ctx: RunContext[ExecutionDeps]) -> dict:
        """Detect technologies; includes `logs`."""
        return await detect_technologies(ctx.deps.target_url)

    async def forms(ctx: RunContext[ExecutionDeps], path: str = "/") -> dict:
        """Extract HTML forms; includes `forms` and `logs`."""
        url = ctx.deps.target_url.rstrip("/") + path
        return await get_forms(url)

    async def nuclei(
        ctx: RunContext[ExecutionDeps],
        tags: str | None = None,
        severity: str | None = None,
    ) -> dict:
        """Run Nuclei template scan against the target URL. Optional tags and severity filter."""
        return await run_nuclei_scan(ctx.deps.target_url, tags=tags, severity=severity)

    async def ffuf(ctx: RunContext[ExecutionDeps], wordlist_path: str | None = None) -> dict:
        """FFUF directory fuzzing from the default or custom wordlist."""
        return await run_ffuf_directory_fuzz(ctx.deps.target_url, wordlist_path=wordlist_path)

    async def sqlmap(ctx: RunContext[ExecutionDeps], url_with_param: str) -> dict:
        """Run sqlmap against a URL that includes a query parameter to test."""
        return await run_sqlmap_probe(url_with_param)

    async def pat_search(ctx: RunContext[ExecutionDeps], keyword: str) -> dict:
        """Search PayloadsAllTheThings tree for .txt paths matching keyword."""
        return search_payload_files(keyword)

    async def pat_read(
        ctx: RunContext[ExecutionDeps], relative_path: str, max_lines: int = 40
    ) -> dict:
        """Read sanitized payload lines from a file under PAYLOADS_ROOT."""
        return read_payload_lines(relative_path, max_lines=max_lines)

    async def zap_status_check(ctx: RunContext[ExecutionDeps]) -> dict:
        """Check whether OWASP ZAP JSON API is reachable."""
        return await zap_ping()

    async def zap_spider(ctx: RunContext[ExecutionDeps]) -> dict:
        """Run ZAP spider against the target, then return passive alerts."""
        return await zap_spider_and_alerts(ctx.deps.target_url)

    async def zap_active(ctx: RunContext[ExecutionDeps]) -> dict:
        """Start ZAP active scan — destructive; only for authorized targets."""
        return await zap_active_scan(ctx.deps.target_url)

    async def run_all_recon(ctx: RunContext[ExecutionDeps]) -> dict:
        """Run probe, headers, tech, forms, nuclei, ffuf, and zap sequentially. Includes per-step `logs` plus combined `logs`."""
        target = ctx.deps.target_url
        out: dict = {}
        out["probe"] = await probe_endpoints(target)
        out["security_headers"] = await get_security_headers(target)
        out["technologies"] = await detect_technologies(target)
        out["forms"] = await get_forms(target.rstrip("/") + "/")
        out["nuclei"] = await run_nuclei_scan(target)
        out["ffuf"] = await run_ffuf_directory_fuzz(target)
        out["zap"] = await zap_ping()
        if out["zap"].get("available"):
            out["zap_spider"] = await zap_spider_and_alerts(target)
        parts: list[str] = []
        for key in ("probe", "security_headers", "technologies", "forms", "nuclei", "ffuf", "zap", "zap_spider"):
            block = out.get(key)
            if isinstance(block, dict) and block.get("logs"):
                parts.append(f"--- {key} ---\n{block['logs']}")
        out["logs"] = merge_tool_logs(
            f"run_all_recon target={target}",
            *parts,
        )
        return out

    return FunctionToolset[ExecutionDeps](
        tools=[
            probe,
            security_headers,
            detect_tech,
            forms,
            nuclei,
            ffuf,
            sqlmap,
            pat_search,
            pat_read,
            zap_status_check,
            zap_spider,
            zap_active,
            run_all_recon,
        ],
    )


execution_agent = Agent(
    model=settings.model,
    deps_type=ExecutionDeps,
    output_type=ExecutionResult,
    system_prompt=_PROMPT,
    toolsets=[_attack_script_toolset()],
)


@execution_agent.tool
async def create_attack_sandbox(ctx: RunContext[ExecutionDeps]) -> dict:
    """Spin up an isolated Docker container on the sandbox network. Returns `container_id` and `logs`."""
    cid = await create_sandbox(
        image=settings.sandbox_image,
        network=settings.sandbox_network,
    )
    return {
        "container_id": cid,
        "logs": merge_tool_logs(f"create_attack_sandbox: started container_id={cid!r}"),
    }


@execution_agent.tool
async def run_attack_script(ctx: RunContext[ExecutionDeps], container_id: str) -> dict:
    """Execute the attack script inside the sandbox container. Returns stdout, stderr, exit_code, and combined `logs`."""
    result = await run_script_string(
        container_id=container_id,
        script=ctx.deps.attack_script.script,
        timeout=settings.sandbox_timeout,
    )
    cap = 12_000
    return with_logs(
        {
            "container_id": result.container_id,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "crash_detected": result.crash_detected,
        },
        merge_tool_logs(
            f"run_attack_script container_id={result.container_id!r} exit_code={result.exit_code}",
            f"crash_detected={result.crash_detected}",
            "stdout:\n" + (result.stdout[:cap] if result.stdout else ""),
            "stderr:\n" + (result.stderr[:cap] if result.stderr else ""),
        ),
    )


@execution_agent.tool
async def teardown_sandbox(ctx: RunContext[ExecutionDeps], container_id: str) -> dict:
    """Stop and remove the sandbox container after execution. Returns `message` and `logs`."""
    await destroy_sandbox(container_id)
    msg = f"Container {container_id} destroyed."
    return {
        "message": msg,
        "logs": merge_tool_logs(f"teardown_sandbox: {msg}"),
    }


@execution_agent.tool
async def execute_attack(ctx: RunContext[ExecutionDeps]) -> ExecutionResult:
    """
    Run the full deterministic pipeline: create sandbox → run attack script → destroy.
    Returns structured ExecutionResult. Prefer this over manual create/run/teardown.
    """
    return await run_attack_execution(ctx.deps.attack_script, ctx.deps.target_url)


__all__ = [
    "run_attack_execution",
    "ExecutionDeps",
    "execution_agent",
]
