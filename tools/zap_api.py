"""
OWASP ZAP — JSON API over HTTP (ZAP must be running, e.g. docker run -p 8080:8080 zaproxy/zap-stable).
Uses httpx only; no zapv2 package required.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from config import settings
from tools.tool_logs import merge_tool_logs, with_logs


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
    base = settings.zap_proxy_url
    try:
        async with httpx.AsyncClient() as client:
            data = await _get(client, "/JSON/core/view/version/")
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return with_logs(
            {"available": False, "error": str(e), "zap": None},
            f"zap_ping: cannot connect to {base}: {e}",
        )
    if "_error" in data:
        return with_logs(
            {"available": False, "error": data.get("_error"), "zap": data},
            merge_tool_logs(f"zap_ping GET {base}", str(data.get("_error")), str(data.get("body", ""))[:1500]),
        )
    ver = data.get("version")
    return with_logs(
        {"available": bool(ver), "version": ver, "zap": data},
        merge_tool_logs(f"zap_ping: ZAP reachable at {base}", f"version={ver!r}"),
    )


async def zap_spider_and_alerts(target_url: str) -> dict[str, Any]:
    """
    Run ZAP spider against target_url, then fetch alerts for that URL (passive findings).
    Requires ZAP to reach the target (same Docker network if both in compose).
    """
    ping = await zap_ping()
    if not ping.get("available"):
        return with_logs(
            {
                "tool": "zap",
                "available": False,
                "error": ping.get("error") or "ZAP API not reachable — start ZAP on ZAP_PROXY_URL",
                "alerts": [],
            },
            ping.get("logs", ""),
            "zap_spider_and_alerts: ZAP not available",
        )

    try:
        async with httpx.AsyncClient() as client:
            base = settings.zap_proxy_url.rstrip("/")
            p = {**_params(), "url": target_url}
            r = await client.get(f"{base}/JSON/spider/action/scan/", params=p, timeout=60.0)
            if r.status_code != 200:
                return with_logs(
                    {
                        "tool": "zap",
                        "available": True,
                        "error": f"spider start failed: HTTP {r.status_code}",
                        "alerts": [],
                    },
                    f"spider scan HTTP {r.status_code}",
                )
            start = r.json()
            scan_id = start.get("scan") or start.get("scanId")
            if scan_id is None:
                return with_logs(
                    {
                        "tool": "zap",
                        "available": True,
                        "error": f"unexpected spider response: {start}",
                        "alerts": [],
                    },
                    f"unexpected spider response: {start!r}",
                )

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
            return with_logs(
                {
                    "tool": "zap",
                    "available": True,
                    "target_url": target_url,
                    "spider_start": start,
                    "alerts": alerts[:200],
                    "alerts_truncated": len(alerts) > 200,
                },
                merge_tool_logs(
                    f"zap spider+alerts target={target_url}",
                    f"scan_id={scan_id!r}",
                    f"alerts count: {len(alerts)} (returning up to 200)",
                ),
            )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return with_logs(
            {"tool": "zap", "available": False, "error": str(e), "alerts": []},
            f"zap_spider_and_alerts request error: {e}",
        )


async def zap_active_scan(target_url: str) -> dict[str, Any]:
    """
    Launch ZAP active scan (aggressive). Use only on authorized targets.
    """
    ping = await zap_ping()
    if not ping.get("available"):
        return with_logs(
            {"tool": "zap", "available": False, "error": ping.get("error"), "status": None},
            ping.get("logs", ""),
            "zap_active_scan: ZAP not available",
        )

    try:
        async with httpx.AsyncClient() as client:
            base = settings.zap_proxy_url.rstrip("/")
            r = await client.get(
                f"{base}/JSON/ascan/action/scan/",
                params={**_params(), "url": target_url},
                timeout=60.0,
            )
            if r.status_code != 200:
                return with_logs(
                    {
                        "tool": "zap",
                        "available": True,
                        "error": f"active scan start failed: HTTP {r.status_code}",
                        "status": None,
                    },
                    f"active scan HTTP {r.status_code}",
                )
            body = r.json()
            return with_logs(
                {"tool": "zap", "available": True, "target_url": target_url, "active_scan": body},
                merge_tool_logs(f"zap_active_scan target={target_url}", f"response keys: {list(body) if isinstance(body, dict) else type(body)}"),
            )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return with_logs(
            {"tool": "zap", "available": False, "error": str(e), "status": None},
            f"zap_active_scan: {e}",
        )
