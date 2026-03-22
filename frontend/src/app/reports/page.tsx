import Link from "next/link";
import {
  FileText,
  Globe,
  ArrowRight,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  Bug,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { AuditStatusBadge, OverallStatusBadge } from "@/components/ui/Badge";
import { mockAudits } from "@/lib/mock-data";
import { formatDate, patchRate } from "@/lib/utils";

export default function ReportsPage() {
  const completed = mockAudits.filter((a) => a.status === "completed");
  const running = mockAudits.filter((a) => a.status === "running");

  return (
    <div className="min-h-full">
      <PageHeader
        title="Audit Reports"
        subtitle={`${completed.length} completed · ${running.length} running`}
        actions={
          <Link href="/audit/new">
            <button className="flex items-center gap-2 px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors">
              <Bug size={12} />
              New Audit
            </button>
          </Link>
        }
      />

      <div className="px-6 py-6 max-w-5xl space-y-6">
        {running.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              <h2 className="text-xs text-fg-subtle uppercase tracking-widest font-semibold">Active Audits</h2>
            </div>
            <div className="space-y-2">
              {running.map((audit) => <AuditRow key={audit.id} audit={audit} />)}
            </div>
          </section>
        )}

        <section>
          <div className="flex items-center gap-2 mb-3">
            <Shield size={12} className="text-fg-faint" />
            <h2 className="text-xs text-fg-subtle uppercase tracking-widest font-semibold">Completed Audits</h2>
          </div>
          {completed.length === 0 ? (
            <Card>
              <div className="text-center py-12 text-fg-subtle">
                <FileText size={24} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm">No completed audits yet</p>
                <Link href="/audit/new">
                  <button className="mt-3 text-xs text-blue-400 hover:text-blue-300 transition-colors">
                    Start your first audit →
                  </button>
                </Link>
              </div>
            </Card>
          ) : (
            <div className="space-y-2">
              {completed.map((audit) => <AuditRow key={audit.id} audit={audit} />)}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function AuditRow({ audit }: { audit: (typeof mockAudits)[0] }) {
  const phasesDone = audit.phases.filter((p) => p.status === "completed").length;
  const currentPhase = audit.phases.find((p) => p.status === "running");
  const critCount = audit.vulnerabilities.filter((v) => v.severity === "critical" && !v.patched).length;
  const highCount = audit.vulnerabilities.filter((v) => v.severity === "high" && !v.patched).length;

  return (
    <Link href={`/audit/${audit.id}`}>
      <div className="group flex items-start gap-4 bg-bg-surface border border-border hover:border-border-glow rounded-lg px-4 py-3.5 transition-all hover:bg-bg-elevated">
        <div className="w-9 h-9 rounded-lg bg-bg-elevated border border-border flex items-center justify-center flex-shrink-0">
          <Globe size={15} className="text-fg-subtle" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-fg-base font-mono">{audit.targetUrl}</span>
              <AuditStatusBadge status={audit.status} />
              {audit.overallStatus && <OverallStatusBadge status={audit.overallStatus} />}
            </div>
            <span className="text-[10px] text-fg-subtle flex items-center gap-1 flex-shrink-0">
              <Clock size={9} /> {formatDate(audit.createdAt)}
            </span>
          </div>

          <div className="flex items-center gap-4 mt-2 flex-wrap">
            <div className="flex items-center gap-1.5">
              {audit.phases.map((p) => (
                <div
                  key={p.id}
                  className={`w-5 h-1 rounded-full ${
                    p.status === "completed"
                      ? p.team === "red_team" ? "bg-red-500/70" : "bg-blue-500/70"
                      : p.status === "running"
                      ? "bg-blue-400 animate-pulse"
                      : p.status === "failed"
                      ? "bg-red-400/40"
                      : "bg-border"
                  }`}
                />
              ))}
              <span className="text-[10px] text-fg-faint ml-1">
                {currentPhase ? currentPhase.name : `${phasesDone}/4 phases`}
              </span>
            </div>

            {audit.totalVulnerabilities > 0 && (
              <div className="flex items-center gap-2 text-[10px]">
                {critCount > 0 && (
                  <span className="flex items-center gap-1 text-red-400">
                    <XCircle size={9} /> {critCount} critical
                  </span>
                )}
                {highCount > 0 && (
                  <span className="flex items-center gap-1 text-orange-400">
                    <XCircle size={9} /> {highCount} high
                  </span>
                )}
                {audit.patchedCount > 0 && (
                  <span className="flex items-center gap-1 text-emerald-400">
                    <CheckCircle size={9} /> {audit.patchedCount} patched
                  </span>
                )}
                <span className="text-fg-faint">{patchRate(audit.totalVulnerabilities, audit.patchedCount)}% patched</span>
              </div>
            )}
          </div>
        </div>

        <ArrowRight size={14} className="text-fg-faint group-hover:text-fg-subtle transition-colors flex-shrink-0 mt-2" />
      </div>
    </Link>
  );
}
