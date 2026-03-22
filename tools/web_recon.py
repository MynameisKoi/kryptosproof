"""
Basic web reconnaissance tools used by the attack script agent.
All async entrypoints return a dict with a `logs` field (human-readable run summary / errors).
"""
import re
import httpx
from typing import Any
from urllib.parse import urljoin

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
    from urllib.parse import urljoin
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            body = resp.text
            forms: list[dict[str, Any]] = []

            for form_match in re.finditer(r"<form[^>]*>(.*?)</form>", body, re.IGNORECASE | re.DOTALL):
                form_html = form_match.group(0)
                action = re.search(r'action=["\']([^"\']*)["\']', form_html)
                method = re.search(r'method=["\']([^"\']*)["\']', form_html)
                inputs = re.findall(r'<input[^>]*name=["\']([^"\']*)["\'][^>]*>', form_html)
                raw_action = action.group(1) if action else ""
                forms.append(
                    {
                        "action": urljoin(url, raw_action) if raw_action else url,
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


_DEFAULT_CREDENTIALS = [
    {"username": "admin", "password": "password"},
    {"username": "admin", "password": "admin"},
    {"username": "admin", "password": ""},
    {"username": "root",  "password": "root"},
    {"username": "user",  "password": "user"},
]


async def authenticate_to_target(
    base_url: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Detect whether the target requires authentication, attempt login with common credentials,
    and return the exact form fields and session cookies needed for the attack script.

    The session cookies returned here are obtained at recon time and are NOT shared with the
    sandbox. The attack script must reproduce the login sequence itself using the returned
    `form_action` and `form_fields` as a template.
    """
    lines: list[str] = []

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            # 1. Hit the base URL — follow redirects to see where we land
            resp = await client.get(base_url)
            lines.append(f"GET {base_url} -> HTTP {resp.status_code} final_url={resp.url}")
            body = resp.text
            final_url = str(resp.url)

            login_signals = ["login", "signin", "sign-in"]
            is_login_page = any(s in final_url.lower() for s in login_signals) or (
                any(s in body.lower() for s in login_signals)
                and re.search(r'<input[^>]+type=["\']password["\']', body, re.IGNORECASE)
            )

            if not is_login_page:
                lines.append("No login wall detected — target appears publicly accessible.")
                return {
                    "requires_auth": False,
                    "verified": True,
                    "session_cookies": {},
                    "logs": merge_tool_logs(*lines),
                }

            # 2. Fetch the login page explicitly
            login_url = final_url if any(s in final_url.lower() for s in login_signals) else urljoin(base_url, "/login.php")
            login_resp = await client.get(login_url)
            login_body = login_resp.text
            lines.append(f"GET {login_url} -> HTTP {login_resp.status_code}")

            # 3. Extract all hidden inputs (CSRF tokens etc.)
            hidden_fields: dict[str, str] = {}
            for m in re.finditer(r'<input[^>]+type=["\']hidden["\'][^>]*>', login_body, re.IGNORECASE):
                name_m  = re.search(r'name=["\']([^"\']+)["\']',  m.group(0))
                value_m = re.search(r'value=["\']([^"\']*)["\']', m.group(0))
                if name_m:
                    hidden_fields[name_m.group(1)] = value_m.group(1) if value_m else ""

            # 4. Resolve form action to absolute URL
            action_m = re.search(r'<form[^>]+action=["\']([^"\']*)["\']', login_body, re.IGNORECASE)
            form_action = urljoin(login_url, action_m.group(1)) if action_m else login_url
            lines.append(f"form_action={form_action}  hidden_fields={list(hidden_fields.keys())}")

            # 5. Try each credential set
            for cred in _DEFAULT_CREDENTIALS:
                # Re-fetch login page to get a fresh CSRF token for each attempt
                fresh_resp  = await client.get(login_url)
                fresh_body  = fresh_resp.text
                fresh_hidden: dict[str, str] = {}
                for m in re.finditer(r'<input[^>]+type=["\']hidden["\'][^>]*>', fresh_body, re.IGNORECASE):
                    name_m  = re.search(r'name=["\']([^"\']+)["\']',  m.group(0))
                    value_m = re.search(r'value=["\']([^"\']*)["\']', m.group(0))
                    if name_m:
                        fresh_hidden[name_m.group(1)] = value_m.group(1) if value_m else ""

                form_data = {
                    **fresh_hidden,
                    "username": cred["username"],
                    "password": cred["password"],
                    "Login":    "Login",
                }

                auth_resp = await client.post(form_action, data=form_data, follow_redirects=True)
                auth_url  = str(auth_resp.url)
                auth_body = auth_resp.text
                lines.append(
                    f"POST {form_action} user={cred['username']} -> "
                    f"HTTP {auth_resp.status_code} url={auth_url}"
                )

                failed_signals = ["incorrect", "invalid", "wrong", "failed", "error"]
                still_on_login = any(s in auth_body.lower() for s in failed_signals)

                if not still_on_login and any(s not in auth_url.lower() for s in login_signals):
                    session_cookies = dict(client.cookies)
                    lines.append(
                        f"✓ Authenticated as {cred['username']}  "
                        f"cookies={list(session_cookies.keys())}"
                    )
                    return {
                        "requires_auth": True,
                        "login_url":     login_url,
                        "form_action":   form_action,
                        "form_fields":   form_data,
                        "authenticated_as": cred["username"],
                        "session_cookies":  session_cookies,
                        "verified": True,
                        "note": (
                            "The attack script MUST reproduce this login at runtime — "
                            "the sandbox does not share this session. "
                            "Use form_action + form_fields (refreshing hidden tokens each run) "
                            "then carry the resulting cookies for all subsequent requests."
                        ),
                        "logs": merge_tool_logs(*lines),
                    }

            lines.append("All credential attempts failed.")
            return {
                "requires_auth": True,
                "login_url":  login_url,
                "form_action": form_action,
                "authenticated_as": None,
                "session_cookies": {},
                "verified": False,
                "logs": merge_tool_logs(*lines),
            }

        except (httpx.RequestError, httpx.TimeoutException) as e:
            return {
                "requires_auth": False,
                "verified": False,
                "session_cookies": {},
                "error": str(e),
                "logs": merge_tool_logs(f"authenticate_to_target failed: {e}"),
            }
