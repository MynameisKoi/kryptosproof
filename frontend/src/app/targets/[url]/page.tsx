import Link from "next/link";
import {
  ArrowLeft,
  Globe,
  Clock,
  CheckCircle,
  XCircle,
  Bug,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AuditStatusBadge, OverallStatusBadge } from "@/components/ui/Badge";
import { mockAudits } from "@/lib/mock-data";
import { formatDate, patchRate } from "@/lib/utils";

export default async function TargetHistoryPage({
  params,
}: {
  params: Promise<{ url: string }>;
}) {
  const { url } = await params;
  const targetUrl = decodeURIComponent(url);
  const audits = mockAudits
    .filter((a) => a.targetUrl === targetUrl)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  const allVulns = audits.flatMap((a) => a.vulnerabilities);
  const totalVulns = allVulns.length;
  const totalPatched = allVulns.filter((v) => v.patched).length;
  const critical = allVulns.filter((v) => v.severity === "critical" && !v.patched).length;

  return (
    <div className="min-h-full">
      <PageHeader
        title={targetUrl}
        subtitle={`${audits.length} audit${audits.length !== 1 ? "s" : ""} · ${totalVulns} vulns found · ${totalPatched} patched`}
        actions={
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft size={13} /> Dashboard
            </Button>
          </Link>
        }
      />

      <div className="px-6 py-6 max-w-4xl space-y-6">
        {/* Summary bar */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Total Audits", value: audits.length, color: "text-blue-400" },
            { label: "Vulnerabilities", value: totalVulns, color: "text-red-400" },
            { label: "Unpatched Critical", value: critical, color: critical > 0 ? "text-red-500" : "text-emerald-400" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-bg-surface border border-border rounded-lg px-4 py-3">
              <div className="text-xs text-fg-subtle uppercase tracking-wider">{label}</div>
              <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
            </div>
          ))}
        </div>

        {/* Audit history list */}
        <Card>
          <CardHeader>
            <span className="text-sm font-medium text-fg-base flex items-center gap-2">
              <Globe size={13} className="text-fg-subtle" />
              Audit History
            </span>
            <Link href="/audit/new">
              <button className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors">
                <Bug size={11} /> Re-audit
              </button>
            </Link>
          </CardHeader>

          {audits.length === 0 ? (
            <CardBody>
              <p className="text-sm text-fg-subtle text-center py-8">No audits found for this target.</p>
            </CardBody>
          ) : (
            <div className="divide-y divide-border">
              {audits.map((audit, i) => {
                const rate = patchRate(audit.totalVulnerabilities, audit.patchedCount);
                const unpatchedCrit = audit.vulnerabilities.filter((v) => v.severity === "critical" && !v.patched).length;
                const unpatchedHigh = audit.vulnerabilities.filter((v) => v.severity === "high" && !v.patched).length;

                return (
                  <Link key={audit.id} href={`/audit/${audit.id}`}>
                    <div className="group flex items-start gap-4 px-4 py-3.5 hover:bg-bg-elevated transition-colors">
                      {/* Audit number */}
                      <div className="w-8 h-8 rounded-lg bg-bg-elevated border border-border flex items-center justify-center flex-shrink-0 text-xs text-fg-subtle font-mono">
                        #{audits.length - i}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm text-fg-base font-medium">
                            Audit {audit.id}
                          </span>
                          <AuditStatusBadge status={audit.status} />
                          {audit.overallStatus && <OverallStatusBadge status={audit.overallStatus} />}
                        </div>

                        <div className="flex items-center gap-4 mt-1.5 text-[10px] flex-wrap">
                          <span className="text-fg-subtle flex items-center gap-1">
                            <Clock size={9} /> {formatDate(audit.createdAt)}
                          </span>

                          {/* Phase dots */}
                          <div className="flex items-center gap-1">
                            {audit.phases.map((p) => (
                              <div
                                key={p.id}
                                title={p.name}
                                className={`w-4 h-1 rounded-full ${
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
                          </div>

                          {unpatchedCrit > 0 && (
                            <span className="flex items-center gap-1 text-red-400">
                              <XCircle size={9} /> {unpatchedCrit} critical
                            </span>
                          )}
                          {unpatchedHigh > 0 && (
                            <span className="flex items-center gap-1 text-orange-400">
                              <XCircle size={9} /> {unpatchedHigh} high
                            </span>
                          )}
                          {audit.patchedCount > 0 && (
                            <span className="flex items-center gap-1 text-emerald-400">
                              <CheckCircle size={9} /> {audit.patchedCount} patched
                            </span>
                          )}
                          {audit.totalVulnerabilities > 0 && (
                            <span className="text-fg-faint ml-auto">{rate}% patch rate</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
