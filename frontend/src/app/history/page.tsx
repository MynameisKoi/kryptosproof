"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Globe,
  ArrowRight,
  Clock,
  CheckCircle,
  XCircle,
  Shield,
  Bug,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AuditStatusBadge, OverallStatusBadge } from "@/components/ui/Badge";
import { listAudits } from "@/lib/api";
import { formatDate, patchRate } from "@/lib/utils";
import type { Audit } from "@/lib/types";

export default function HistoryPage() {
  const [sorted, setSorted] = useState<Audit[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await listAudits();
        if (!cancelled) setSorted(data);
      } catch { /* backend not running */ }
    };
    load();
    const id = setInterval(load, 5000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  return (
    <div className="min-h-full">
      <PageHeader
        title="Audit History"
        subtitle={`${sorted.length} audit${sorted.length !== 1 ? "s" : ""} total`}
        actions={
          <Link href="/audit/new">
            <Button size="sm" variant="danger">
              <Bug size={12} />
              New Audit
            </Button>
          </Link>
        }
      />

      <div className="px-6 py-6 max-w-3xl space-y-2">
        {sorted.length === 0 && (
          <Card>
            <div className="text-center py-14 text-fg-subtle">
              <Shield size={24} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No audits yet</p>
              <Link href="/audit/new">
                <button className="mt-3 text-xs text-blue-400 hover:text-blue-300 transition-colors">
                  Run your first audit →
                </button>
              </Link>
            </div>
          </Card>
        )}

        {sorted.map((audit, i) => {
          const rate = patchRate(audit.totalVulnerabilities, audit.patchedCount);
          const critUnpatched = audit.vulnerabilities.filter((v) => v.severity === "critical" && !v.patched).length;
          const highUnpatched = audit.vulnerabilities.filter((v) => v.severity === "high" && !v.patched).length;
          const phaseDone = audit.phases.filter((p) => p.status === "completed").length;
          const currentPhase = audit.phases.find((p) => p.status === "running");

          return (
            <Link key={audit.id} href={`/audit/${audit.id}`}>
              <div className="group flex items-start gap-4 bg-bg-surface border border-border hover:border-border-glow rounded-lg px-4 py-3.5 transition-all hover:bg-bg-elevated">
                {/* Index */}
                <div className="w-8 h-8 rounded-lg bg-bg-elevated border border-border flex items-center justify-center flex-shrink-0 text-xs text-fg-faint font-mono">
                  #{sorted.length - i}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Top row */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <Globe size={12} className="text-fg-faint flex-shrink-0" />
                    <span className="text-sm text-fg-base font-mono truncate">{audit.targetUrl}</span>
                    <AuditStatusBadge status={audit.status} />
                    {audit.overallStatus && <OverallStatusBadge status={audit.overallStatus} />}
                  </div>

                  {/* Bottom row */}
                  <div className="flex items-center gap-4 mt-1.5 flex-wrap">
                    {/* Date */}
                    <span className="text-[10px] text-fg-subtle flex items-center gap-1">
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
                      <span className="text-[10px] text-fg-faint ml-1">
                        {currentPhase ? currentPhase.name : `${phaseDone}/4`}
                      </span>
                    </div>

                    {/* Findings */}
                    {critUnpatched > 0 && (
                      <span className="text-[10px] text-red-400 flex items-center gap-1">
                        <XCircle size={9} /> {critUnpatched} critical
                      </span>
                    )}
                    {highUnpatched > 0 && (
                      <span className="text-[10px] text-orange-400 flex items-center gap-1">
                        <XCircle size={9} /> {highUnpatched} high
                      </span>
                    )}
                    {audit.patchedCount > 0 && (
                      <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                        <CheckCircle size={9} /> {audit.patchedCount} patched
                      </span>
                    )}
                    {audit.totalVulnerabilities > 0 && (
                      <span className="text-[10px] text-fg-faint ml-auto">{rate}%</span>
                    )}
                  </div>
                </div>

                <ArrowRight
                  size={14}
                  className="text-fg-faint group-hover:text-fg-subtle transition-colors flex-shrink-0 mt-1.5"
                />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
