"use client";

import { use, useState, useEffect, useRef } from "react";
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
import { getAudit } from "@/lib/api";
import { formatDate, formatDuration, patchRate, cn } from "@/lib/utils";
import type { Audit, AuditPhase, VulnerabilityFinding, FixResult, FilePatch } from "@/lib/types";

export default function AuditDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [audit, setAudit] = useState<Audit | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getAudit(id);
        if (!cancelled) setAudit(data);
      } catch { /* not found yet */ }
    };
    load();
    const interval = setInterval(async () => {
      try {
        const data = await getAudit(id);
        if (!cancelled) {
          setAudit(data);
          if (data.status === "completed" || data.status === "failed") {
            clearInterval(interval);
          }
        }
      } catch { /* ignore */ }
    }, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [id]);

  if (!audit) {
    return (
      <div className="min-h-full flex items-center justify-center">
        <p className="text-sm text-fg-subtle">Loading audit...</p>
      </div>
    );
  }

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

        <div className="space-y-4">
          {/* Vulnerabilities */}
          <Card>
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

          {/* Patch Results */}
          {(audit.fixResults?.length > 0 || audit.status === "completed") && (
            <Card>
              <CardHeader>
                <span className="text-sm font-medium text-fg-base flex items-center gap-2">
                  <CheckCircle size={13} className="text-blue-400" />
                  Patch Results
                </span>
                {audit.fixResults?.length > 0 && (
                  <span className="text-xs text-fg-subtle">
                    {audit.fixResults.filter((r) => r.overallPatched).length} / {audit.fixResults.length} patched
                  </span>
                )}
              </CardHeader>
              {!audit.fixResults?.length ? (
                <CardBody>
                  <div className="text-center py-8 text-fg-subtle text-sm">
                    No patch results yet
                  </div>
                </CardBody>
              ) : (
                <div className="divide-y divide-border">
                  {audit.fixResults.map((r, i) => {
                    const wasConfirmed = audit.vulnerabilities.some(
                      (v) => v.type.toLowerCase() === r.vulnerabilityType.toLowerCase() && v.confirmed
                    );
                    return <FixResultRow key={i} fix={r} wasConfirmed={wasConfirmed} />;
                  })}
                </div>
              )}
            </Card>
          )}

          {/* Security Report */}
          {audit.reportMarkdown && (
            <Card>
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
  const isRunning = phase.status === "running";
  const [expanded, setExpanded] = useState(isRunning);
  const logRef = useRef<HTMLPreElement>(null);
  const isRedTeam = phase.team === "red_team";

  // Auto-open when phase becomes running, keep open after completion
  useEffect(() => {
    if (isRunning) setExpanded(true);
  }, [isRunning]);

  // Auto-scroll to bottom as new lines arrive
  useEffect(() => {
    if (expanded && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [phase.output, expanded]);

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

  const hasOutput = !!phase.output || isRunning;

  return (
    <div className={cn(
      "rounded-lg border overflow-hidden transition-all",
      phase.status === "pending" || phase.status === "skipped" ? "border-border opacity-50" : teamColor.border
    )}>
      <button
        onClick={() => hasOutput && setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
          hasOutput ? "hover:bg-bg-elevated cursor-pointer" : "cursor-default",
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
          {hasOutput && (expanded ? <ChevronDown size={13} className="text-fg-subtle" /> : <ChevronRight size={13} className="text-fg-subtle" />)}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border bg-bg-primary">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border/50">
            <div className="flex items-center gap-2">
              <Terminal size={10} className="text-fg-faint" />
              <span className="text-[10px] text-fg-faint uppercase tracking-wider">Output</span>
            </div>
            {isRunning && (
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                <span className="text-[10px] text-blue-400 uppercase tracking-wider font-semibold">Live</span>
              </div>
            )}
          </div>
          <pre
            ref={logRef}
            className="terminal-text text-[11px] text-fg-muted px-4 py-3 max-h-72 overflow-y-auto leading-relaxed"
          >
            {phase.output || (isRunning ? "Waiting for output…" : "")}
            {isRunning && <span className="inline-block w-2 h-3 bg-blue-400 animate-pulse ml-0.5 align-text-bottom" />}
          </pre>
        </div>
      )}
    </div>
  );
}


function VulnRow({ vuln }: { vuln: VulnerabilityFinding }) {
  const [logsOpen, setLogsOpen] = useState(false);

  return (
    <div className="border-b border-border last:border-0">
      <div className="flex items-start gap-4 px-4 py-3">
        <div className="mt-0.5">
          {vuln.patched
            ? <CheckCircle size={14} className="text-emerald-400" />
            : vuln.confirmed
            ? <XCircle size={14} className="text-red-400" />
            : <CheckCircle size={14} className="text-fg-faint" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn("text-sm font-medium", vuln.confirmed ? "text-fg-base" : "text-fg-subtle")}>{vuln.type}</span>
            {vuln.confirmed && <SeverityBadge severity={vuln.severity} />}
            {vuln.patched ? (
              <span className="text-[10px] text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Patched</span>
            ) : vuln.confirmed ? (
              <span className="text-[10px] text-red-400 bg-red-400/10 border border-red-400/20 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Vulnerable</span>
            ) : (
              <span className="text-[10px] text-fg-faint bg-bg-elevated border border-border px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Passed</span>
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
            {vuln.logs && (
              <button
                onClick={() => setLogsOpen(!logsOpen)}
                className="text-[10px] text-fg-subtle hover:text-fg-muted flex items-center gap-1 transition-colors ml-auto"
              >
                <Terminal size={9} />
                {logsOpen ? "Hide logs" : "Show logs"}
                {logsOpen ? <ChevronDown size={9} /> : <ChevronRight size={9} />}
              </button>
            )}
          </div>
        </div>
      </div>
      {logsOpen && vuln.logs && (
        <div className="border-t border-border bg-bg-primary">
          <pre className="terminal-text text-[11px] text-fg-muted px-4 py-3 max-h-64 overflow-y-auto leading-relaxed">
            {vuln.logs}
          </pre>
        </div>
      )}
    </div>
  );
}

function FixResultRow({ fix, wasConfirmed }: { fix: FixResult; wasConfirmed: boolean }) {
  const [codeOpen, setCodeOpen] = useState(false);
  const hasCode = !!(fix.fixScript || fix.patches?.length);

  const codeContent = [
    fix.patches?.length
      ? fix.patches.map((p: FilePatch) =>
          `# ${p.file_path}\n# ${p.explanation}\n\n# BEFORE:\n${p.original_snippet}\n\n# AFTER:\n${p.patched_snippet}`
        ).join("\n\n" + "─".repeat(60) + "\n\n")
      : "",
    fix.fixScript ? `# Fix Script\n${fix.fixScript}` : "",
  ].filter(Boolean).join("\n\n" + "─".repeat(60) + "\n\n");

  return (
    <div className="last:border-0">
      <div className="flex items-start gap-4 px-4 py-3">
        <div className="mt-0.5">
          {fix.overallPatched
            ? <CheckCircle size={14} className="text-emerald-400" />
            : <XCircle size={14} className="text-red-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-fg-base">{fix.vulnerabilityType}</span>
            {fix.overallPatched ? (
              wasConfirmed
                ? <span className="text-[10px] text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Patched</span>
                : <span className="text-[10px] text-blue-400 bg-blue-400/10 border border-blue-400/20 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Enhancement</span>
            ) : (
              <span className="text-[10px] text-red-400 bg-red-400/10 border border-red-400/20 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">Unpatched</span>
            )}
          </div>

          {fix.rootCause && (
            <p className="text-xs text-fg-subtle mt-1">
              <span className="text-fg-faint">Root cause: </span>{fix.rootCause}
            </p>
          )}
          {fix.fixDescription && (
            <p className="text-xs text-fg-subtle mt-0.5">{fix.fixDescription}</p>
          )}
          {fix.recommendation && !fix.overallPatched && (
            <p className="text-xs text-yellow-400/80 mt-0.5">{fix.recommendation}</p>
          )}

          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            {fix.references?.map((ref, i) => (
              <span key={i} className="text-[10px] text-fg-faint font-mono">{ref}</span>
            ))}
            {hasCode && (
              <button
                onClick={() => setCodeOpen(!codeOpen)}
                className="text-[10px] text-blue-400/80 hover:text-blue-300 flex items-center gap-1 transition-colors ml-auto"
              >
                <Terminal size={9} />
                {codeOpen ? "Hide recommended fix" : "Show recommended fix"}
                {codeOpen ? <ChevronDown size={9} /> : <ChevronRight size={9} />}
              </button>
            )}
          </div>
        </div>
      </div>

      {codeOpen && hasCode && (
        <div className="border-t border-border bg-bg-primary">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border/50">
            <div className="flex items-center gap-2">
              <Terminal size={10} className="text-blue-400/60" />
              <span className="text-[10px] text-blue-400/60 uppercase tracking-wider">Recommended Fix</span>
            </div>
            <CopyButton text={codeContent} />
          </div>
          <pre className="terminal-text text-[11px] text-fg-muted px-4 py-3 max-h-96 overflow-y-auto leading-relaxed">
            {codeContent}
          </pre>
        </div>
      )}
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
