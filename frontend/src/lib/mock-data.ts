import type { Audit } from "./types";

const sampleOutput = `GET /vulnerabilities/sqli/ 200
[VULN] SQL syntax error near...
[OK] probe complete`;

const sampleReport = `## Security audit summary

**Target:** http://dvwa:80  
**Status:** Partially patched

### Findings
- SQL Injection (high) — endpoint /login

### Recommendations
1. Use parameterized queries.
`;

export const mockAudits: Audit[] = [
  {
    id: "audit-live-001",
    targetUrl: "http://dvwa:80",
    status: "running",
    createdAt: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
    totalVulnerabilities: 2,
    patchedCount: 0,
    overallStatus: undefined,
    phases: [
      {
        id: "p1",
        name: "Recon & attack script",
        team: "red_team",
        status: "completed",
        summary: "Generated httpx-based exploit script",
        durationMs: 120_000,
        output: sampleOutput,
      },
      {
        id: "p2",
        name: "Sandbox execution",
        team: "red_team",
        status: "completed",
        summary: "Confirmed SQLi",
        durationMs: 45_000,
        output: "[VULN] reflected in response body",
      },
      {
        id: "p3",
        name: "Fix generation",
        team: "blue_team",
        status: "running",
        summary: "Drafting patches…",
        output: "Applying fix_script agent…\n",
      },
      {
        id: "p4",
        name: "Verification",
        team: "blue_team",
        status: "pending",
      },
    ],
    vulnerabilities: [
      {
        id: "v1",
        type: "SQL Injection",
        severity: "high",
        endpoint: "/login.php",
        patched: false,
      },
    ],
  },
  {
    id: "audit-001",
    targetUrl: "http://localhost:8080",
    status: "completed",
    createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    totalVulnerabilities: 3,
    patchedCount: 2,
    overallStatus: "partially_patched",
    phases: [
      {
        id: "a1",
        name: "Recon & attack script",
        team: "red_team",
        status: "completed",
        durationMs: 90_000,
        output: sampleOutput,
      },
      {
        id: "a2",
        name: "Sandbox execution",
        team: "red_team",
        status: "completed",
        durationMs: 30_000,
      },
      {
        id: "a3",
        name: "Fix generation",
        team: "blue_team",
        status: "completed",
        durationMs: 60_000,
      },
      {
        id: "a4",
        name: "Verification",
        team: "blue_team",
        status: "completed",
        durationMs: 20_000,
        output: "Retest passed for XSS; SQLi still open in edge case.",
      },
    ],
    vulnerabilities: [
      {
        id: "v2",
        type: "XSS",
        severity: "medium",
        endpoint: "/search?q=",
        patched: true,
      },
      {
        id: "v3",
        type: "SQL Injection",
        severity: "high",
        endpoint: "/id=1",
        patched: true,
      },
      {
        id: "v4",
        type: "CSRF",
        severity: "low",
        endpoint: "/admin/change",
        patched: false,
      },
    ],
    reportMarkdown: sampleReport,
  },
  {
    id: "audit-002",
    targetUrl: "http://dvwa:80",
    status: "completed",
    createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
    totalVulnerabilities: 0,
    patchedCount: 0,
    overallStatus: "secure",
    phases: [
      {
        id: "b1",
        name: "Recon & attack script",
        team: "red_team",
        status: "completed",
        durationMs: 40_000,
      },
      {
        id: "b2",
        name: "Sandbox execution",
        team: "red_team",
        status: "completed",
        durationMs: 15_000,
      },
      {
        id: "b3",
        name: "Fix generation",
        team: "blue_team",
        status: "skipped",
      },
      {
        id: "b4",
        name: "Verification",
        team: "blue_team",
        status: "skipped",
      },
    ],
    vulnerabilities: [],
    reportMarkdown: "## No issues found\n\nTarget responded safely to probes.",
  },
];
