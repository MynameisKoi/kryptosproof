"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Plus,
  Play,
  Shield,
  Terminal,
  Clock,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Globe,
  History,
  AlertTriangle,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AuditStatusBadge, SeverityBadge } from "@/components/ui/Badge";
import { listAudits } from "@/lib/api";
import { formatDate, formatDuration, cn } from "@/lib/utils";
import type { Audit, AuditPhase, VulnerabilityFinding } from "@/lib/types";

export default function DashboardPage() {
  const [audits, setAudits] = useState<Audit[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await listAudits();
        if (!cancelled) setAudits(data);
      } catch { /* backend not running yet */ }
    };
    load();
    const id = setInterval(load, 3000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const liveAudit = audits.find((a) => a.status === "running") ?? null;
  const recentTargets = [...new Set(
    audits
      .filter((a) => a.status !== "running")
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .map((a) => a.targetUrl)
  )].slice(0, 4);

  if (liveAudit) return <LiveAuditView audit={liveAudit} />;
  return <NoAuditView recentTargets={recentTargets} audits={audits} />;
}

/* ─── Live audit view ─────────────────────────────────────── */
function LiveAuditView({ audit }: { audit: Audit }) {
  const runningPhase = audit.phases.find((p) => p.status === "running");
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(audit.createdAt).getTime();
    const tick = () => setElapsed(Date.now() - start);
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [audit.createdAt]);

  return (
    <div className="min-h-full">
      <PageHeader
        title="Live Audit"
        subtitle={`Targeting ${audit.targetUrl}`}
        actions={
          <Link href="/history">
            <Button variant="ghost" size="sm">
              <History size={13} /> History
            </Button>
          </Link>
        }
      />

      <div className="px-6 py-6 max-w-4xl space-y-5">
        {/* Target + elapsed */}
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-blue-500/25 bg-blue-500/5">
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="text-sm font-mono text-fg-base">{audit.targetUrl}</span>
          </div>
          <AuditStatusBadge status="running" />
          <span className="text-xs text-fg-subtle flex items-center gap-1">
            <Clock size={11} /> {formatDuration(elapsed)}
          </span>
        </div>

        {/* Phase tracker */}
        <Card>
          <CardHeader>
            <span className="text-sm font-medium text-fg-base">Phases</span>
            <span className="text-xs text-fg-subtle">
              {audit.phases.filter((p) => p.status === "completed").length} / {audit.phases.length} done
            </span>
          </CardHeader>
          <CardBody className="space-y-2">
            {/* Step connector */}
            <div className="flex items-center mb-3">
              {audit.phases.map((phase, i) => (
                <div key={phase.id} className="flex-1 flex items-center">
                  <StepDot phase={phase} index={i} />
                  {i < audit.phases.length - 1 && (
                    <div className={cn("flex-1 h-px mx-1", phase.status === "completed" ? "bg-emerald-500/50" : "bg-border")} />
                  )}
                </div>
              ))}
            </div>

            {audit.phases.map((phase) => (
              <PhaseRow key={phase.id} phase={phase} defaultOpen={phase.status === "running"} />
            ))}
          </CardBody>
        </Card>

        {/* Vulnerabilities discovered */}
        <Card>
          <CardHeader>
            <span className="text-sm font-medium text-fg-base flex items-center gap-2">
              <AlertTriangle size={13} className="text-yellow-400" />
              Findings
            </span>
            <span className="text-xs text-fg-subtle">{audit.vulnerabilities.length} confirmed</span>
          </CardHeader>
          {audit.vulnerabilities.length === 0 ? (
            <CardBody>
              <p className="text-xs text-fg-subtle text-center py-4">No findings yet — attack execution in progress</p>
            </CardBody>
          ) : (
            <div className="divide-y divide-border">
              {audit.vulnerabilities.map((v) => (
                <VulnRow key={v.id} vuln={v} />
              ))}
            </div>
          )}
        </Card>

        {runningPhase && (
          <p className="text-[10px] text-fg-faint text-center">
            KryptoSproof · Claude Opus 4.6 · {runningPhase.name}
          </p>
        )}
      </div>
    </div>
  );
}

/* ─── No audit running view ───────────────────────────────── */
function NoAuditView({ recentTargets, audits }: { recentTargets: string[]; audits: Audit[] }) {
  return (
    <div className="min-h-full flex flex-col">
      <PageHeader
        title="Dashboard"
        subtitle="No audit running"
        actions={
          <Link href="/history">
            <Button variant="ghost" size="sm">
              <History size={13} /> History
            </Button>
          </Link>
        }
      />

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        {/* CTA */}
        <div className="w-full max-w-sm text-center space-y-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500/20 to-blue-600/20 border border-border flex items-center justify-center mx-auto">
            <Shield size={28} className="text-fg-subtle" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-fg-base">Ready to audit</h2>
            <p className="text-sm text-fg-subtle mt-1">
              Start a new security audit to begin the red team / blue team cycle.
            </p>
          </div>
          <Link href="/audit/new" className="block">
            <Button size="lg" variant="danger" className="w-full">
              <Play size={15} />
              Start New Audit
            </Button>
          </Link>
        </div>

        {/* Recent targets */}
        {recentTargets.length > 0 && (
          <div className="w-full max-w-sm mt-10">
            <p className="text-xs text-fg-subtle uppercase tracking-widest mb-3 text-center">
              Recent targets
            </p>
            <div className="space-y-2">
              {recentTargets.map((url) => {
                const lastAudit = audits
                  .filter((a) => a.targetUrl === url)
                  .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0];
                return (
                  <Link key={url} href={`/audit/${lastAudit.id}`}>
                    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border hover:border-border-glow bg-bg-surface hover:bg-bg-elevated transition-all group">
                      <Globe size={13} className="text-fg-subtle flex-shrink-0" />
                      <span className="text-xs font-mono text-fg-muted truncate flex-1">{url}</span>
                      <span className="text-[10px] text-fg-faint">
                        {formatDate(lastAudit.createdAt)}
                      </span>
                      <Plus size={11} className="text-fg-faint group-hover:text-fg-subtle transition-colors" />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Shared sub-components ───────────────────────────────── */
function StepDot({ phase, index }: { phase: AuditPhase; index: number }) {
  const isRed = phase.team === "red_team";
  const cls = {
    pending: "bg-bg-elevated border-border text-fg-faint",
    running: "bg-blue-500/20 border-blue-500/60 text-blue-300 animate-pulse",
    completed: isRed
      ? "bg-red-500/15 border-red-500/40 text-red-300"
      : "bg-blue-500/15 border-blue-500/40 text-blue-300",
    failed: "bg-red-500/20 border-red-500/50 text-red-400",
    skipped: "bg-bg-elevated border-border text-fg-faint",
  }[phase.status];

  return (
    <div className={cn("w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold flex-shrink-0", cls)}>
      {phase.status === "completed" ? "✓" : phase.status === "failed" ? "✗" : index + 1}
    </div>
  );
}

function PhaseRow({ phase, defaultOpen }: { phase: AuditPhase; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const isRed = phase.team === "red_team";
  const teamColor = isRed
    ? { border: "border-red-500/20", label: "text-red-400", bg: "bg-red-500/5" }
    : { border: "border-blue-500/20", label: "text-blue-400", bg: "bg-blue-500/5" };

  const statusIcon = {
    pending: <Clock size={13} className="text-fg-faint" />,
    running: <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />,
    completed: <CheckCircle size={13} className="text-emerald-400" />,
    failed: <XCircle size={13} className="text-red-400" />,
    skipped: <Clock size={13} className="text-fg-faint" />,
  }[phase.status];

  const inactive = phase.status === "pending" || phase.status === "skipped";

  return (
    <div className={cn("rounded-lg border overflow-hidden transition-all", inactive ? "border-border opacity-50" : teamColor.border)}>
      <button
        onClick={() => phase.output && setOpen(!open)}
        className={cn(
          "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
          phase.output ? "cursor-pointer hover:bg-bg-elevated" : "cursor-default",
          !inactive ? teamColor.bg : ""
        )}
      >
        {statusIcon}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-fg-base">{phase.name}</span>
            <span className={cn("text-[9px] uppercase font-bold tracking-widest", teamColor.label)}>
              {isRed ? "Red Team" : "Blue Team"}
            </span>
          </div>
          {phase.summary && <p className="text-[10px] text-fg-subtle mt-0.5">{phase.summary}</p>}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {phase.durationMs && <span className="text-[10px] text-fg-faint">{formatDuration(phase.durationMs)}</span>}
          {phase.output && (open ? <ChevronDown size={13} className="text-fg-subtle" /> : <ChevronRight size={13} className="text-fg-subtle" />)}
        </div>
      </button>

      {open && phase.output && (
        <div className="border-t border-border bg-bg-primary">
          <div className="flex items-center gap-2 px-4 py-2 border-b border-border/50">
            <Terminal size={10} className="text-fg-faint" />
            <span className="text-[10px] text-fg-faint uppercase tracking-wider">Output</span>
          </div>
          <pre className="terminal-text text-[11px] text-fg-muted px-4 py-3 max-h-60 overflow-y-auto leading-relaxed">
            {phase.output}
            {phase.status === "running" && <span className="cursor" />}
          </pre>
        </div>
      )}
    </div>
  );
}

function VulnRow({ vuln }: { vuln: VulnerabilityFinding }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <XCircle size={13} className="text-red-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-fg-base">{vuln.type}</span>
          <SeverityBadge severity={vuln.severity} />
        </div>
        {vuln.endpoint && (
          <span className="text-[10px] text-fg-faint font-mono">{vuln.endpoint}</span>
        )}
      </div>
    </div>
  );
}
