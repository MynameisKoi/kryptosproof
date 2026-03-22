"""
KryptoSproof — Automated Web Security Audit Platform
Entry point: runs the full orchestrated red team → blue team cycle.
"""
import asyncio
import sys
import json

from config import settings
from ai.agents.orchestrator import run_audit


async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else settings.target_url
    print(f"[*] KryptoSproof starting audit against: {target}\n")

    report = await run_audit(target)

    print("\n" + "=" * 60)
    print(report.report_markdown)
    print("=" * 60)
    print(f"\nStatus : {report.overall_status.upper()}")
    print(f"Found  : {report.total_vulnerabilities} vulnerabilities")
    print(f"Patched: {report.patched_count}")

    # Write JSON report to logs/
    import os
    os.makedirs("logs", exist_ok=True)
    out_path = "logs/report.json"
    with open(out_path, "w") as f:
        json.dump(report.model_dump(), f, indent=2)
    print(f"\n[*] Full report saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
