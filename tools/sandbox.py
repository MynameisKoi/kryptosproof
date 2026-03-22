"""
Docker sandbox manager — spins up isolated containers for attack script execution.
"""
import asyncio
import tempfile
import os
from dataclasses import dataclass

import docker
from docker.errors import DockerException


@dataclass
class SandboxResult:
    container_id: str
    exit_code: int
    stdout: str
    stderr: str
    crash_detected: bool


def _client() -> docker.DockerClient:
    return docker.from_env()


async def create_sandbox(image: str = "python:3.11-slim", network: str = "kryptosproof_sandbox") -> str:
    """Create and start a sandbox container, return container ID."""
    loop = asyncio.get_event_loop()

    def _create():
        client = _client()
        container = client.containers.run(
            image,
            command="sleep 300",  # keep alive while we exec
            detach=True,
            network=network,
            remove=False,
            mem_limit="256m",
            nano_cpus=500_000_000,  # 0.5 CPU
        )
        return container.id

    return await loop.run_in_executor(None, _create)


async def run_script_in_sandbox(container_id: str, script: str, timeout: int = 30) -> SandboxResult:
    """Write a Python script to the container and execute it."""
    loop = asyncio.get_event_loop()

    def _run():
        client = _client()
        container = client.containers.get(container_id)

        # Install httpx inside sandbox
        container.exec_run("pip install httpx --quiet", demux=False)

        # Write script to container via stdin
        script_path = "/tmp/attack_script.py"
        container.exec_run(f"bash -c 'cat > {script_path}'", stdin=True)

        # Use exec_run with a shell heredoc trick
        result = container.exec_run(
            ["python", "-c", script],
            demux=True,
            timeout=timeout,
        )

        exit_code = result.exit_code or 0
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace")

        crash_detected = exit_code != 0 or any(
            keyword in stderr.lower()
            for keyword in ["error", "exception", "traceback", "crash", "failed"]
        )

        return SandboxResult(
            container_id=container_id,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            crash_detected=crash_detected,
        )

    return await loop.run_in_executor(None, _run)


async def run_script_string(container_id: str, script: str, timeout: int = 30) -> SandboxResult:
    """Run a multiline Python script string inside the sandbox container."""
    loop = asyncio.get_event_loop()

    def _run():
        client = _client()
        container = client.containers.get(container_id)

        # Install httpx
        container.exec_run("pip install httpx --quiet")

        # Write script to a temp file in the container using echo/printf
        lines = script.replace("'", "'\\''")
        write_result = container.exec_run(
            ["bash", "-c", f"printf '%s' '{lines}' > /tmp/script.py"],
            demux=True,
        )

        # Execute it
        result = container.exec_run(
            ["python", "/tmp/script.py"],
            demux=True,
            timeout=timeout,
        )

        exit_code = result.exit_code or 0
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace")

        crash_detected = exit_code != 0 or any(
            kw in stderr.lower()
            for kw in ["error", "exception", "traceback", "crash", "failed"]
        )

        return SandboxResult(
            container_id=container_id,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            crash_detected=crash_detected,
        )

    return await loop.run_in_executor(None, _run)


async def destroy_sandbox(container_id: str) -> None:
    """Stop and remove the sandbox container."""
    loop = asyncio.get_event_loop()

    def _destroy():
        client = _client()
        try:
            container = client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True)
        except DockerException:
            pass  # already gone

    await loop.run_in_executor(None, _destroy)
