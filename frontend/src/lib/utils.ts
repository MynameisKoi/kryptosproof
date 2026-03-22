import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { AuditStatus, OverallStatus, Severity } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/** Elapsed ms → "2m 15s" / "45s" */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m}m ${r}s` : `${m}m`;
}

/** Percent patched (0–100), integer */
export function patchRate(total: number, patched: number): number {
  if (!total || total <= 0) return 0;
  return Math.round((patched / total) * 100);
}

export function severityColor(severity: Severity): string {
  const m: Record<Severity, string> = {
    critical: "border-red-500/40 bg-red-500/10 text-red-300",
    high: "border-orange-500/40 bg-orange-500/10 text-orange-300",
    medium: "border-yellow-500/40 bg-yellow-500/10 text-yellow-200",
    low: "border-slate-500/40 bg-slate-500/10 text-slate-300",
  };
  return m[severity] ?? m.low;
}

export function auditStatusColor(status: AuditStatus): string {
  const m: Record<AuditStatus, string> = {
    pending: "border-border bg-bg-elevated text-fg-subtle",
    running: "border-blue-500/50 bg-blue-500/10 text-blue-300",
    completed: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
    failed: "border-red-500/40 bg-red-500/10 text-red-300",
  };
  return m[status];
}

export function overallStatusColor(status: OverallStatus): string {
  const m: Record<OverallStatus, string> = {
    secure: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
    vulnerable: "border-red-500/40 bg-red-500/10 text-red-300",
    partially_patched: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  };
  return m[status];
}

export function overallStatusLabel(status: OverallStatus): string {
  const m: Record<OverallStatus, string> = {
    secure: "Secure",
    vulnerable: "Vulnerable",
    partially_patched: "Partially patched",
  };
  return m[status];
}
