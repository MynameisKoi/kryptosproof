"""
OWASP ZAP — JSON API over HTTP (ZAP must be running, e.g. docker run -p 8080:8080 zaproxy/zap-stable).
Uses httpx only; no zapv2 package required.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from config import settings


def _params() -> dict[str, str]:
    k = settings.zap_api_key
    return {"apikey": k} if k else {}


async def _get(client: httpx.AsyncClient, path: str, **extra: str) -> dict[str, Any]:
    base = settings.zap_proxy_url.rstrip("/")
    p = {**_params(), **extra}
    r = await client.get(f"{base}{path}", params=p, timeout=settings.zap_http_timeout)
    if r.status_code != 200:
        return {"_error": f"HTTP {r.status_code}", "body": r.text[:2000]}
    try:
        return r.json()
    except Exception:
        return {"_error": "invalid JSON", "text": r.text[:2000]}


async def zap_ping() -> dict[str, Any]:
    """Return ZAP version if the API is reachable."""
    try:
        async with httpx.AsyncClient() as client:
            data = await _get(client, "/JSON/core/view/version/")
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return {"available": False, "error": str(e), "zap": None}
    if "_error" in data:
        return {"available": False, "error": data.get("_error"), "zap": data}
    ver = data.get("version")
    return {"available": bool(ver), "version": ver, "zap": data}


async def zap_spider_and_alerts(target_url: str) -> dict[str, Any]:
    """
    Run ZAP spider against target_url, then fetch alerts for that URL (passive findings).
    Requires ZAP to reach the target (same Docker network if both in compose).
    """
    ping = await zap_ping()
    if not ping.get("available"):
        return {
            "tool": "zap",
            "available": False,
            "error": ping.get("error") or "ZAP API not reachable — start ZAP on ZAP_PROXY_URL",
            "alerts": [],
        }

    try:
        async with httpx.AsyncClient() as client:
            base = settings.zap_proxy_url.rstrip("/")
            p = {**_params(), "url": target_url}
            r = await client.get(f"{base}/JSON/spider/action/scan/", params=p, timeout=60.0)
            if r.status_code != 200:
                return {
                    "tool": "zap",
                    "available": True,
                    "error": f"spider start failed: HTTP {r.status_code}",
                    "alerts": [],
                }
            start = r.json()
            scan_id = start.get("scan") or start.get("scanId")
            if scan_id is None:
                return {"tool": "zap", "available": True, "error": f"unexpected spider response: {start}", "alerts": []}

            loop = asyncio.get_running_loop()
            deadline = loop.time() + settings.zap_spider_max_wait
            while loop.time() < deadline:
                st = await _get(client, "/JSON/spider/view/status/", scanId=str(scan_id))
                pct = await _get(client, "/JSON/spider/view/percentage/", scanId=str(scan_id))
                progress = pct.get("percentage")
                if progress == "100" or st.get("status") in ("100", 100):
                    break
                await asyncio.sleep(2.0)

            alerts_raw = await client.get(
                f"{base}/JSON/core/view/alerts/",
                params={**_params(), "baseurl": target_url, "start": "0", "count": "200"},
                timeout=60.0,
            )
            alerts: list[dict[str, Any]] = []
            if alerts_raw.status_code == 200:
                try:
                    aj = alerts_raw.json()
                    alerts = aj.get("alerts", []) if isinstance(aj, dict) else []
                except Exception:
                    pass
            return {
                "tool": "zap",
                "available": True,
                "target_url": target_url,
                "spider_start": start,
                "alerts": alerts[:200],
                "alerts_truncated": len(alerts) > 200,
            }
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return {"tool": "zap", "available": False, "error": str(e), "alerts": []}


async def zap_active_scan(target_url: str) -> dict[str, Any]:
    """
    Launch ZAP active scan (aggressive). Use only on authorized targets.
    """
    ping = await zap_ping()
    if not ping.get("available"):
        return {"tool": "zap", "available": False, "error": ping.get("error"), "status": None}

    try:
        async with httpx.AsyncClient() as client:
            base = settings.zap_proxy_url.rstrip("/")
            r = await client.get(
                f"{base}/JSON/ascan/action/scan/",
                params={**_params(), "url": target_url},
                timeout=60.0,
            )
            if r.status_code != 200:
                return {
                    "tool": "zap",
                    "available": True,
                    "error": f"active scan start failed: HTTP {r.status_code}",
                    "status": None,
                }
            return {"tool": "zap", "available": True, "target_url": target_url, "active_scan": r.json()}
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return {"tool": "zap", "available": False, "error": str(e), "status": None}
