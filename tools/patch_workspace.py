"""
Isolated patch workspace inside a Docker container.

All mutations happen under /workspace in an ephemeral container. The host project
tree and the kryptosproof app directory are never modified by these operations.
Optional one-way mirror (BLUE_TEAM_MIRROR_SOURCE) copies host files into the
workspace for patching without writing back to the source path.
"""
from __future__ import annotations

import asyncio
import io
import os
import subprocess
import tarfile
from pathlib import Path

import docker

from config import settings
from tools.sandbox import create_sandbox, destroy_sandbox


WORKSPACE_ROOT = "/workspace"


def _client():
    return docker.from_env()


def _safe_rel_path(relative_path: str) -> str:
    """Reject path traversal; return normalized path relative to WORKSPACE_ROOT."""
    if not str(relative_path).strip():
        raise ValueError("Path must be non-empty")
    p = Path(relative_path.replace("\\", "/"))
    if p.is_absolute():
        raise ValueError("Path must be relative")
    norm = os.path.normpath(str(p))
    if norm.startswith("..") or "/../" in f"/{norm}/":
        raise ValueError("Path must not escape the workspace")
    return norm.replace("\\", "/")


def _put_file_in_container(container_id: str, path_in_container: str, data: bytes) -> None:
    directory = os.path.dirname(path_in_container) or "/"
    basename = os.path.basename(path_in_container)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        info = tarfile.TarInfo(name=basename)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    stream.seek(0)
    client = _client()
    container = client.containers.get(container_id)
    container.put_archive(directory, stream)


async def create_patch_workspace() -> str:
    """Create a container with an empty /workspace tree (host filesystem untouched)."""
    loop = asyncio.get_event_loop()
    container_id = await create_sandbox(settings.sandbox_image, settings.sandbox_network)

    def _init_workspace():
        client = _client()
        container = client.containers.get(container_id)
        container.exec_run(["mkdir", "-p", WORKSPACE_ROOT])

    await loop.run_in_executor(None, _init_workspace)
    return container_id


async def destroy_patch_workspace(container_id: str) -> None:
    await destroy_sandbox(container_id)


async def write_workspace_file(container_id: str, relative_path: str, content: str) -> str:
    """Write a UTF-8 text file under /workspace only."""
    safe = _safe_rel_path(relative_path)
    full = f"{WORKSPACE_ROOT}/{safe}".replace("//", "/")
    data = content.encode("utf-8")

    def _write():
        parent = os.path.dirname(full)
        client = _client()
        container = client.containers.get(container_id)
        container.exec_run(["mkdir", "-p", parent])
        _put_file_in_container(container_id, full, data)

    await asyncio.get_event_loop().run_in_executor(None, _write)
    return full


async def read_workspace_file(container_id: str, relative_path: str) -> str:
    safe = _safe_rel_path(relative_path)
    full = f"{WORKSPACE_ROOT}/{safe}".replace("//", "/")

    def _read():
        client = _client()
        container = client.containers.get(container_id)
        result = container.exec_run(["cat", full], demux=True)
        out = (result.output[0] or b"").decode("utf-8", errors="replace")
        err = (result.output[1] or b"").decode("utf-8", errors="replace")
        exit_code = result.exit_code or 0
        if exit_code != 0:
            raise RuntimeError(f"read_workspace_file failed: {err}")
        return out

    return await asyncio.get_event_loop().run_in_executor(None, _read)


async def list_workspace_dir(container_id: str, relative_path: str = "") -> str:
    safe = _safe_rel_path(relative_path) if relative_path.strip() else ""
    full = f"{WORKSPACE_ROOT}/{safe}".rstrip("/") if safe else WORKSPACE_ROOT

    def _ls():
        client = _client()
        container = client.containers.get(container_id)
        result = container.exec_run(["ls", "-la", full], demux=True)
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace")
        if (result.exit_code or 0) != 0:
            return f"(error) {stderr}"
        return stdout

    return await asyncio.get_event_loop().run_in_executor(None, _ls)


async def run_workspace_command(container_id: str, command: str) -> dict:
    """Run a shell command with cwd=/workspace (does not touch host paths)."""
    shell = ["bash", "-lc", command]

    def _run():
        client = _client()
        container = client.containers.get(container_id)
        result = container.exec_run(shell, workdir=WORKSPACE_ROOT, demux=True)
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace")
        return {
            "exit_code": result.exit_code or 0,
            "stdout": stdout,
            "stderr": stderr,
        }

    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def apply_fix_script_in_workspace(
    container_id: str,
    fix_script: str,
    target_url: str,
) -> dict:
    """
    Execute the generated fix script inside the workspace container.
    Script runs with cwd=/workspace; TARGET_URL is set in the environment.
    """
    script = fix_script.strip()
    first_line = script.split("\n", 1)[0].strip() if script else ""
    is_shell = bool(first_line.startswith("#!") and "python" not in first_line.lower())

    def _apply():
        client = _client()
        container = client.containers.get(container_id)
        container.exec_run(["mkdir", "-p", "/tmp"])
        remote_path = "/tmp/kryptosproof_apply_fix.sh" if is_shell else "/tmp/kryptosproof_apply_fix.py"
        _put_file_in_container(container_id, remote_path, script.encode("utf-8"))
        if is_shell:
            container.exec_run(["chmod", "+x", remote_path])
            cmd = [remote_path]
        else:
            cmd = ["python", remote_path]
        env = {"TARGET_URL": target_url, "WORKSPACE": WORKSPACE_ROOT}
        result = container.exec_run(
            cmd,
            workdir=WORKSPACE_ROOT,
            environment=env,
            demux=True,
        )
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace")
        return {
            "exit_code": result.exit_code or 0,
            "stdout": stdout,
            "stderr": stderr,
        }

    return await asyncio.get_event_loop().run_in_executor(None, _apply)


async def mirror_host_path_to_workspace(container_id: str, host_path: str, dest_relative: str = "") -> dict:
    """
    One-way copy from host into /workspace (read from host; never writes back).
    Only runs when host_path is under the configured blue_team_mirror_source root.
    """
    allowed = settings.blue_team_mirror_source
    if not allowed:
        return {"ok": False, "error": "BLUE_TEAM_MIRROR_SOURCE is not configured"}

    abs_host = Path(host_path).resolve()
    abs_allowed = Path(allowed).resolve()
    if not abs_host.is_relative_to(abs_allowed):
        return {"ok": False, "error": "host_path must be under BLUE_TEAM_MIRROR_SOURCE"}

    dest = dest_relative.strip().replace("\\", "/")
    if dest:
        _safe_rel_path(dest)
    container_dest = f"{WORKSPACE_ROOT}/{dest}".replace("//", "/") if dest else WORKSPACE_ROOT

    def _cp():
        client = _client()
        container = client.containers.get(container_id)
        container.exec_run(["mkdir", "-p", container_dest])
        try:
            subprocess.run(
                ["docker", "cp", str(abs_host), f"{container_id}:{container_dest}"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            return {"ok": False, "error": e.stderr or str(e)}
        return {"ok": True, "host_path": str(abs_host), "workspace_dest": container_dest}

    return await asyncio.get_event_loop().run_in_executor(None, _cp)


async def mirror_workspace_subpath(container_id: str, subpath: str = "") -> dict:
    """
    One-way copy from BLUE_TEAM_MIRROR_SOURCE (optional) into /workspace/mirror/...
    Only paths under the configured mirror root are allowed; host source is never modified.
    """
    if not settings.blue_team_mirror_source:
        return {"ok": False, "error": "BLUE_TEAM_MIRROR_SOURCE is not configured"}

    base = Path(settings.blue_team_mirror_source).resolve()
    if subpath.strip():
        rel = _safe_rel_path(subpath)
        src = (base / rel).resolve()
    else:
        rel = ""
        src = base.resolve()
    if not src.is_relative_to(base):
        return {"ok": False, "error": "subpath must stay under BLUE_TEAM_MIRROR_SOURCE"}

    dest = f"mirror/{rel}" if rel else "mirror"
    return await mirror_host_path_to_workspace(container_id, str(src), dest)
