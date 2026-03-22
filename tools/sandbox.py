"""
Docker sandbox manager — isolated containers for attack script execution.
Scripts are copied with tar (put_archive) to avoid shell escaping limits.
"""
import asyncio
import io
import tarfile
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


_CRASH_SUBSTRINGS = (
    "error",
    "exception",
    "traceback",
    "crash",
    "failed",
    "segfault",
    "segmentation fault",
)


def _client() -> docker.DockerClient:
    return docker.from_env()


def _crash_from_streams(exit_code: int, stderr: str) -> bool:
    if exit_code != 0:
        return True
    low = stderr.lower()
    return any(s in low for s in _CRASH_SUBSTRINGS)


def _put_script_archive(container_id: str, script: str) -> None:
    """Write /tmp/script.py inside the container via docker put_archive (no shell quoting)."""
    client = _client()
    container = client.containers.get(container_id)
    data = script.encode("utf-8")
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        info = tarfile.TarInfo(name="script.py")
        info.size = len(data)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(data))
    stream.seek(0)
    ok = container.put_archive("/tmp", stream.read())
    if not ok:
        raise RuntimeError("put_archive failed to write /tmp/script.py")


async def create_sandbox(image: str = "python:3.11-slim", network: str = "kryptosproof_sandbox") -> str:
    """Create and start a sandbox container, return container ID."""
    loop = asyncio.get_running_loop()

    def _create():
        client = _client()
        container = client.containers.run(
            image,
            command="sleep 300",
            detach=True,
            network=network,
            remove=False,
            mem_limit="256m",
            nano_cpus=500_000_000,
        )
        return container.id

    return await loop.run_in_executor(None, _create)


async def run_script_string(container_id: str, script: str, timeout: int = 30) -> SandboxResult:
    """Install httpx, write script to /tmp/script.py via tar, run python /tmp/script.py."""
    loop = asyncio.get_running_loop()

    def _run():
        client = _client()
        container = client.containers.get(container_id)

        container.exec_run(["pip", "install", "httpx", "--quiet"], demux=False)

        _put_script_archive(container_id, script)

        result = container.exec_run(
            ["python", "/tmp/script.py"],
            demux=True,
            timeout=timeout,
        )

        exit_code = result.exit_code if result.exit_code is not None else -1
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace")

        crash_detected = _crash_from_streams(exit_code, stderr)

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
    loop = asyncio.get_running_loop()

    def _destroy():
        client = _client()
        try:
            container = client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True)
        except DockerException:
            pass

    await loop.run_in_executor(None, _destroy)
