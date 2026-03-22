"""
Docker sandbox manager — isolated containers for attack script execution.
Falls back to direct subprocess execution when Docker is unavailable (e.g. Cloud Run).
"""
import asyncio
import io
import os
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass

try:
    import docker
    from docker.errors import DockerException

    def _docker_available() -> bool:
        try:
            docker.from_env().ping()
            return True
        except Exception:
            return False
except ImportError:
    _docker_available = lambda: False  # noqa: E731

    class DockerException(Exception):  # type: ignore[no-redef]
        pass

_DOCKER_OK: bool | None = None

def _use_docker() -> bool:
    global _DOCKER_OK
    if _DOCKER_OK is None:
        _DOCKER_OK = _docker_available()
        if not _DOCKER_OK:
            print("[sandbox] Docker unavailable — using direct subprocess execution")
    return _DOCKER_OK


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


def _client() -> "docker.DockerClient":
    return docker.from_env()


def _crash_from_streams(exit_code: int, stderr: str) -> bool:
    if exit_code != 0:
        return True
    low = stderr.lower()
    return any(s in low for s in _CRASH_SUBSTRINGS)


def _put_script_archive(container_id: str, script: str) -> None:
    """Write /tmp/script.py inside the container via docker put_archive."""
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


# ── Subprocess fallback (no Docker) ──────────────────────────────────────

_FALLBACK_ID = "subprocess-fallback"


async def _subprocess_run_script(script: str, timeout: int = 30) -> SandboxResult:
    """Run a script directly via subprocess (used when Docker is unavailable)."""
    loop = asyncio.get_running_loop()

    def _run():
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script)
            script_path = f.name
        try:
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                timeout=timeout,
                text=True,
            )
            return SandboxResult(
                container_id=_FALLBACK_ID,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                crash_detected=_crash_from_streams(result.returncode, result.stderr),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                container_id=_FALLBACK_ID,
                exit_code=124,
                stdout="",
                stderr=f"Script timed out after {timeout}s",
                crash_detected=True,
            )
        finally:
            os.unlink(script_path)

    return await loop.run_in_executor(None, _run)


# ── Public API ────────────────────────────────────────────────────────────

async def create_sandbox(image: str = "python:3.11-slim", network: str = "kryptosproof_sandbox") -> str:
    if not _use_docker():
        return _FALLBACK_ID

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
    if container_id == _FALLBACK_ID:
        return await _subprocess_run_script(script, timeout)

    loop = asyncio.get_running_loop()

    def _run():
        client = _client()
        container = client.containers.get(container_id)

        pip_result = container.exec_run(["pip", "install", "httpx", "--quiet"], demux=False)
        if pip_result.exit_code != 0:
            raise RuntimeError(
                f"httpx installation failed (exit={pip_result.exit_code}): "
                + (pip_result.output or b"").decode("utf-8", errors="replace")[:500]
            )

        _put_script_archive(container_id, script)

        result = container.exec_run(
            ["timeout", str(timeout), "python", "/tmp/script.py"],
            demux=True,
        )

        exit_code = result.exit_code if result.exit_code is not None else -1
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace")

        return SandboxResult(
            container_id=container_id,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            crash_detected=_crash_from_streams(exit_code, stderr),
        )

    return await loop.run_in_executor(None, _run)


async def destroy_sandbox(container_id: str) -> None:
    if container_id == _FALLBACK_ID:
        return

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
