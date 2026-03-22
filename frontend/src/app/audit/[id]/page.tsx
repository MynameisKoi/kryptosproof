"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Terminal,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SeverityBadge, AuditStatusBadge, OverallStatusBadge } from "@/components/ui/Badge";
import { mockAudits } from "@/lib/mock-data";
import { formatDate, formatDuration, patchRate, cn } from "@/lib/utils";
import type { AuditPhase, VulnerabilityFinding } from "@/lib/types";

export default function AuditDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const audit = mockAudits.find((a) => a.id === id) ?? mockAudits[0];

  return (
    <div className="min-h-full">
      <PageHeader
        title={audit.targetUrl}
        subtitle={`Audit ${audit.id} · Started ${formatDate(audit.createdAt)}`}
        actions={
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft size={13} /> Dashboard
            </Button>
          </Link>
        }
      />

      <div className="px-6 py-6 max-w-5xl space-y-6">
        {/* Status bar */}
        <div className="flex flex-wrap items-center gap-3">
          <AuditStatusBadge status={audit.status} />
          {audit.overallStatus && <OverallStatusBadge status={audit.overallStatus} />}
          <span className="text-xs text-fg-subtle flex items-center gap-1">
            <Clock size={10} /> {formatDate(audit.createdAt)}
          </span>
          {audit.totalVulnerabilities > 0 && (
            <span className="text-xs text-fg-subtle">
              {audit.totalVulnerabilities} vulns · {patchRate(audit.totalVulnerabilities, audit.patchedCount)}% patched
            </span>
          )}
        </div>

        {/* Phase tracker */}
        <PhaseTracker phases={audit.phases} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader>
              <span className="text-sm font-medium text-fg-base flex items-center gap-2">
                <AlertTriangle size={13} className="text-yellow-400" />
                Vulnerabilities
              </span>
              <span className="text-xs text-fg-subtle">
                {audit.vulnerabilities.filter((v) => v.patched).length} / {audit.vulnerabilities.length} patched
              </span>
            </CardHeader>
            {audit.vulnerabilities.length === 0 ? (
              <CardBody>
                <div className="text-center py-8 text-fg-subtle text-sm">
                  No vulnerabilities discovered yet
                </div>
              </CardBody>
            ) : (
              <div className="divide-y divide-border">
                {audit.vulnerabilities.map((v) => (
                  <VulnRow key={v.id} vuln={v} />
                ))}
              </div>
            )}
          </Card>

          {audit.reportMarkdown && (
            <Card className="lg:col-span-2">
              <CardHeader>
                <span className="text-sm font-medium text-fg-base">Security Report</span>
                <CopyButton text={audit.reportMarkdown} />
              </CardHeader>
              <CardBody className="bg-bg-primary">
                <pre className="text-xs text-fg-muted terminal-text whitespace-pre-wrap">
                  {audit.reportMarkdown}
                </pre>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function PhaseTracker({ phases }: { phases: AuditPhase[] }) {
  return (
    <Card>
      <CardHeader>
        <span className="text-sm font-medium text-fg-base">Audit Phases</span>
        <span className="text-xs text-fg-subtle">
          {phases.filter((p) => p.status === "completed").length}/{phases.length} complete
        </span>
      </CardHeader>
      <CardBody className="space-y-3">
        {/* Step dots */}
        <div className="flex items-center gap-0 mb-4">
          {phases.map((phase, i) => (
            <div key={phase.id} className="flex-1 flex items-center">
              <PhaseStep phase={phase} index={i} />
              {i < phases.length - 1 && (
                <div className={cn("flex-1 h-px mx-1", phase.status === "completed" ? "bg-emerald-500/50" : "bg-border")} />
              )}
            </div>
          ))}
        </div>
        {phases.map((phase) => (
          <PhaseCard key={phase.id} phase={phase} />
        ))}
      </CardBody>
    </Card>
  );
}

function PhaseStep({ phase, index }: { phase: AuditPhase; index: number }) {
  const isRedTeam = phase.team === "red_team";
  const stepColors = {
    pending: "bg-bg-elevated border-border text-fg-faint",
    running: "bg-blue-500/20 border-blue-500/60 text-blue-300 animate-pulse",
    completed: isRedTeam
      ? "bg-red-500/15 border-red-500/40 text-red-300"
      : "bg-blue-500/15 border-blue-500/40 text-blue-300",
    failed: "bg-red-500/20 border-red-500/50 text-red-400",
    skipped: "bg-bg-elevated border-border text-fg-faint",
  };
  return (
    <div className={cn("w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold flex-shrink-0", stepColors[phase.status])}>
      {phase.status === "completed" ? "✓" : phase.status === "failed" ? "✗" : index + 1}
    </div>
  );
}

function PhaseCard({ phase }: { phase: AuditPhase }) {
  const [expanded, setExpanded] = useState(phase.status === "running");
  const isRedTeam = phase.team === "red_team";

  const teamColor = isRedTeam
    ? { border: "border-red-500/20", label: "text-red-400", bg: "bg-red-500/5" }
    : { border: "border-blue-500/20", label: "text-blue-400", bg: "bg-blue-500/5" };

  const statusIcon = {
    pending: <Clock size={13} className="text-fg-faint" />,
    running: <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />,
    completed: <CheckCircle size={13} className="text-emerald-400" />,
    failed: <XCircle size={13} className="text-red-400" />,
    skipped: <Clock size={13} className="text-fg-faint" />,
  }[phase.status];

  return (
    <div className={cn(
      "rounded-lg border overflow-hidden transition-all",
      phase.status === "pending" || phase.status === "skipped" ? "border-border opacity-50" : teamColor.border
    )}>
      <button
        onClick={() => phase.output && setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
          phase.output ? "hover:bg-bg-elevated cursor-pointer" : "cursor-default",
          phase.status !== "pending" && phase.status !== "skipped" ? teamColor.bg : ""
        )}
      >
        {statusIcon}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-fg-base">{phase.name}</span>
            <span className={cn("text-[9px] uppercase font-bold tracking-widest", teamColor.label)}>
              {isRedTeam ? "Red Team" : "Blue Team"}
            </span>
          </div>
          {phase.summary && <p className="text-[10px] text-fg-subtle mt-0.5">{phase.summary}</p>}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {phase.durationMs && <span className="text-[10px] text-fg-faint">{formatDuration(phase.durationMs)}</span>}
          {phase.output && (expanded ? <ChevronDown size={13} className="text-fg-subtle" /> : <ChevronRight size={13} className="text-fg-subtle" />)}
        </div>
      </button>

      {expanded && phase.output && (
        <div className="border-t border-border bg-bg-primary">
          <div className="flex items-center gap-2 px-4 py-2 border-b border-border/50">
            <Terminal size={10} className="text-fg-faint" />
            <span className="text-[10px] text-fg-faint uppercase tracking-wider">Output</span>
          </div>
          <pre className="terminal-text text-[11px] text-fg-muted px-4 py-3 max-h-64 overflow-y-auto leading-relaxed">
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
    <div className="flex items-start gap-4 px-4 py-3">
      <div className="mt-0.5">
        {vuln.patched ? <CheckCircle size={14} className="text-emerald-400" /> : <XCircle size={14} className="text-red-400" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-fg-base font-medium">{vuln.type}</span>
          <SeverityBadge severity={vuln.severity} />
          {vuln.patched ? (
            <span className="text-[10px] text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Patched</span>
          ) : (
            <span className="text-[10px] text-red-400 bg-red-400/10 border border-red-400/20 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Unpatched</span>
          )}
        </div>
        <p className="text-xs text-fg-subtle mt-1">{vuln.description}</p>
        <div className="flex items-center gap-3 mt-1">
          {vuln.endpoint && (
            <span className="text-[10px] text-fg-faint font-mono flex items-center gap-1">
              <ExternalLink size={9} /> {vuln.endpoint}
            </span>
          )}
          {vuln.cve && <span className="text-[10px] text-fg-faint">{vuln.cve}</span>}
        </div>
      </div>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} className="text-xs text-fg-subtle hover:text-fg-muted flex items-center gap-1 transition-colors">
      {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
