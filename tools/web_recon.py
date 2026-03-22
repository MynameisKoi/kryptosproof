"""
Basic web reconnaissance tools used by the attack script agent.
"""
import httpx
from typing import Any


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


async def probe_endpoints(base_url: str, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Probe common web endpoints and return status/headers for each."""
    results = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for path in COMMON_ENDPOINTS:
            url = base_url.rstrip("/") + path
            try:
                resp = await client.get(url)
                results.append({
                    "url": url,
                    "status": resp.status_code,
                    "content_type": resp.headers.get("content-type", ""),
                    "server": resp.headers.get("server", ""),
                    "length": len(resp.content),
                    "reachable": True,
                })
            except (httpx.RequestError, httpx.TimeoutException):
                results.append({"url": url, "reachable": False})
    return results


async def get_security_headers(url: str, timeout: float = 5.0) -> dict[str, str | None]:
    """Return security-relevant response headers."""
    security_headers = [
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
            return {h: resp.headers.get(h) for h in security_headers}
        except (httpx.RequestError, httpx.TimeoutException):
            return {h: None for h in security_headers}


async def detect_technologies(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Detect server technology from headers and response body."""
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

            # Detect common frameworks from body/headers
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

            return tech
        except (httpx.RequestError, httpx.TimeoutException):
            return {}


async def get_forms(url: str, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Extract HTML form details from a page for CSRF/injection analysis."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            # Basic form parsing without extra deps
            body = resp.text
            forms = []
            import re
            for form_match in re.finditer(r"<form[^>]*>(.*?)</form>", body, re.IGNORECASE | re.DOTALL):
                form_html = form_match.group(0)
                action = re.search(r'action=["\']([^"\']*)["\']', form_html)
                method = re.search(r'method=["\']([^"\']*)["\']', form_html)
                inputs = re.findall(r'<input[^>]*name=["\']([^"\']*)["\'][^>]*>', form_html)
                forms.append({
                    "action": action.group(1) if action else "",
                    "method": (method.group(1) if method else "GET").upper(),
                    "inputs": inputs,
                    "has_csrf_token": any(
                        "csrf" in i.lower() or "token" in i.lower() for i in inputs
                    ),
                })
            return forms
        except (httpx.RequestError, httpx.TimeoutException):
            return []
