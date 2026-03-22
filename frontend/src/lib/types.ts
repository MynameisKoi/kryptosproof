/** Shared UI types for the KryptoSproof dashboard (mock + future API). */

export type Team = "red_team" | "blue_team";

export type PhaseStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export type AuditStatus = "pending" | "running" | "completed" | "failed";

export type OverallStatus = "secure" | "vulnerable" | "partially_patched";

export type Severity = "critical" | "high" | "medium" | "low";

export type VulnType =
  | "SQL Injection"
  | "XSS"
  | "Command Injection"
  | "Path Traversal"
  | "Broken Authentication"
  | "CSRF"
  | "SSRF"
  | "Security Misconfiguration";

export interface AuditPhase {
  id: string;
  name: string;
  team: Team;
  status: PhaseStatus;
  summary?: string;
  durationMs?: number;
  output?: string;
}

export interface VulnerabilityFinding {
  id: string;
  type: string;
  severity: Severity;
  confirmed: boolean;
  endpoint?: string;
  patched: boolean;
  description?: string;
  cve?: string;
  logs?: string;
}

export interface FilePatch {
  file_path: string;
  original_snippet: string;
  patched_snippet: string;
  explanation: string;
}

export interface FixResult {
  vulnerabilityType: string;
  overallPatched: boolean;
  rootCause?: string;
  fixDescription?: string;
  fixScript?: string;
  patches?: FilePatch[];
  recommendation?: string;
  references?: string[];
}

export interface Audit {
  id: string;
  targetUrl: string;
  status: AuditStatus;
  createdAt: string; // ISO
  completedAt?: string;
  phases: AuditPhase[];
  vulnerabilities: VulnerabilityFinding[];
  overallStatus?: OverallStatus;
  totalVulnerabilities: number;
  patchedCount: number;
  reportMarkdown?: string;
  fixResults: FixResult[];
}
