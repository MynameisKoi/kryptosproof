import type { Audit } from "./types";

const API_BASE = "/api/backend";

export async function listAudits(): Promise<Audit[]> {
  const res = await fetch(`${API_BASE}/api/audits`);
  if (!res.ok) throw new Error(`listAudits failed: ${res.status}`);
  return res.json();
}

export async function getAudit(id: string): Promise<Audit> {
  const res = await fetch(`${API_BASE}/api/audits/${id}`);
  if (!res.ok) throw new Error(`getAudit failed: ${res.status}`);
  return res.json();
}

export async function startAudit(params: {
  targetUrl: string;
  vulnerabilityTypes: string[];
  severityThreshold: string;
}): Promise<Audit> {
  const res = await fetch(`${API_BASE}/api/audits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`startAudit failed: ${res.status}`);
  return res.json();
}
