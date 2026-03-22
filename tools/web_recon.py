"""
Basic web reconnaissance tools used by the attack script agent.
All async entrypoints return a dict with a `logs` field (human-readable run summary / errors).
"""
import httpx
from typing import Any

from tools.tool_logs import merge_tool_logs

COMMON_ENDPOINTS = [
    "/",
    "/login",
    "/admin",
    "/api",
    "/api/v1",
    "/upload",
    "/search",
    "/user",
    "/profile",
    "/register",
    "/logout",
    "/dashboard",
    "/config",
    "/debug",
]


async def probe_endpoints(base_url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Probe common web endpoints; returns `endpoints` plus `logs`."""
    results: list[dict[str, Any]] = []
    lines: list[str] = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for path in COMMON_ENDPOINTS:
            url = base_url.rstrip("/") + path
            try:
                resp = await client.get(url)
                results.append(
                    {
                        "url": url,
                        "status": resp.status_code,
                        "content_type": resp.headers.get("content-type", ""),
                        "server": resp.headers.get("server", ""),
                        "length": len(resp.content),
                        "reachable": True,
                    }
                )
                lines.append(f"{url} -> HTTP {resp.status_code} len={len(resp.content)}")
            except (httpx.RequestError, httpx.TimeoutException) as e:
                results.append({"url": url, "reachable": False, "error": str(e)})
                lines.append(f"{url} -> unreachable ({e})")
    reachable = sum(1 for r in results if r.get("reachable"))
    header = f"probe_endpoints: {len(results)} paths, {reachable} reachable"
    return {
        "endpoints": results,
        "logs": merge_tool_logs(header, *lines),
    }


async def get_security_headers(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Return security-relevant response headers plus `logs`."""
    security_header_names = [
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "strict-transport-security",
        "x-xss-protection",
        "referrer-policy",
        "permissions-policy",
    ]
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            headers_flat = {h: resp.headers.get(h) for h in security_header_names}
            detail = [f"{h}={headers_flat[h]!r}" for h in security_header_names]
            return {
                **headers_flat,
                "logs": merge_tool_logs(f"GET {url} -> HTTP {resp.status_code}", *detail),
            }
        except (httpx.RequestError, httpx.TimeoutException) as e:
            empty = {h: None for h in security_header_names}
            return {
                **empty,
                "logs": merge_tool_logs(f"GET {url} failed: {e}"),
            }


async def detect_technologies(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Detect server technology from headers and response body; includes `logs`."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            body = resp.text[:5000]
            headers = dict(resp.headers)

            tech: dict[str, Any] = {
                "server": headers.get("server"),
                "powered_by": headers.get("x-powered-by"),
                "framework_hints": [],
                "cookies": [c for c in resp.cookies.keys()],
            }

            checks = {
                "Django": ["csrfmiddlewaretoken", "django"],
                "Laravel": ["laravel_session", "laravel"],
                "Rails": ["_rails_session", "rails"],
                "Flask": ["session", "werkzeug"],
                "WordPress": ["wp-content", "wp-login"],
                "PHP": [".php", "<?php"],
            }
            for fw, signals in checks.items():
                if any(s.lower() in body.lower() or s.lower() in str(headers).lower() for s in signals):
                    tech["framework_hints"].append(fw)

            hints = ", ".join(tech["framework_hints"]) or "(none matched)"
            return {
                **tech,
                "logs": merge_tool_logs(
                    f"detect_technologies GET {url} -> HTTP {resp.status_code}",
                    f"server={tech.get('server')!r} x-powered-by={tech.get('powered_by')!r}",
                    f"framework_hints: {hints}",
                ),
            }
        except (httpx.RequestError, httpx.TimeoutException) as e:
            return {
                "server": None,
                "powered_by": None,
                "framework_hints": [],
                "cookies": [],
                "logs": merge_tool_logs(f"detect_technologies failed for {url}: {e}"),
            }


async def get_forms(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Extract HTML form details; returns `forms` + `logs`."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            body = resp.text
            forms: list[dict[str, Any]] = []
            import re

            for form_match in re.finditer(r"<form[^>]*>(.*?)</form>", body, re.IGNORECASE | re.DOTALL):
                form_html = form_match.group(0)
                action = re.search(r'action=["\']([^"\']*)["\']', form_html)
                method = re.search(r'method=["\']([^"\']*)["\']', form_html)
                inputs = re.findall(r'<input[^>]*name=["\']([^"\']*)["\'][^>]*>', form_html)
                forms.append(
                    {
                        "action": action.group(1) if action else "",
                        "method": (method.group(1) if method else "GET").upper(),
                        "inputs": inputs,
                        "has_csrf_token": any("csrf" in i.lower() or "token" in i.lower() for i in inputs),
                    }
                )
            return {
                "forms": forms,
                "logs": merge_tool_logs(
                    f"get_forms GET {url} -> HTTP {resp.status_code}",
                    f"parsed {len(forms)} form(s)",
                ),
            }
        except (httpx.RequestError, httpx.TimeoutException) as e:
            return {"forms": [], "logs": merge_tool_logs(f"get_forms failed for {url}: {e}")}
