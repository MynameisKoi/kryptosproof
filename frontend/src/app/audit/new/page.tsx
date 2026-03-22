"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Globe,
  Shield,
  Zap,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Play,
  Lock,
  Code,
  Bug,
  Server,
  Link as LinkIcon,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { startAudit } from "@/lib/api";
import type { VulnType, Severity } from "@/lib/types";

const VULN_TYPES: { type: VulnType; icon: React.ElementType; description: string; color: string }[] = [
  { type: "SQL Injection", icon: Bug, description: "Parameterized query bypass, UNION attacks, blind SQLi", color: "text-red-400" },
  { type: "XSS", icon: Code, description: "Reflected, stored, DOM-based cross-site scripting", color: "text-orange-400" },
  { type: "Command Injection", icon: Server, description: "OS command execution via unsanitized input", color: "text-red-500" },
  { type: "Path Traversal", icon: LinkIcon, description: "Directory traversal to read arbitrary files", color: "text-yellow-500" },
  { type: "Broken Authentication", icon: Lock, description: "Default creds, session fixation, token leakage", color: "text-red-400" },
  { type: "CSRF", icon: RefreshCw, description: "Cross-Site Request Forgery on state-changing endpoints", color: "text-orange-400" },
  { type: "SSRF", icon: Globe, description: "Server-Side Request Forgery to internal networks", color: "text-yellow-500" },
  { type: "Security Misconfiguration", icon: AlertTriangle, description: "Exposed headers, debug endpoints, verbose errors", color: "text-yellow-500" },
];

const PRESETS = [
  { label: "DVWA (Default)", url: "http://dvwa:80" },
  { label: "Juice Shop", url: "http://juice-shop.local:3000" },
  { label: "WebGoat", url: "http://webgoat.local:8080" },
];

export default function NewAuditPage() {
  const router = useRouter();
  const [targetUrl, setTargetUrl] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<VulnType[]>([...VULN_TYPES.map((v) => v.type)]);
  const [severity, setSeverity] = useState<Severity>("low");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [urlError, setUrlError] = useState("");

  const toggleType = (type: VulnType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const validate = () => {
    if (!targetUrl.trim()) { setUrlError("Target URL is required"); return false; }
    try { new URL(targetUrl); } catch { setUrlError("Enter a valid URL (e.g. http://target:80)"); return false; }
    setUrlError("");
    return true;
  };

  const handleLaunch = async () => {
    if (!validate()) return;
    setLaunching(true);
    try {
      const audit = await startAudit({
        targetUrl,
        vulnerabilityTypes: selectedTypes,
        severityThreshold: severity,
      });
      router.push(`/audit/${audit.id}`);
    } catch {
      setLaunching(false);
    }
  };

  return (
    <div className="min-h-full">
      <PageHeader title="New Security Audit" subtitle="Configure target and attack parameters" />

      <div className="px-6 py-6 max-w-3xl space-y-6">
        {/* Target URL */}
        <Card>
          <CardHeader>
            <span className="text-sm font-medium text-fg-base flex items-center gap-2">
              <Globe size={14} className="text-blue-400" />
              Target
            </span>
          </CardHeader>
          <CardBody className="space-y-4">
            <div>
              <label className="text-xs text-fg-subtle uppercase tracking-wider block mb-2">
                Target URL
              </label>
              <input
                type="text"
                placeholder="http://target-app:80"
                value={targetUrl}
                onChange={(e) => { setTargetUrl(e.target.value); setUrlError(""); }}
                className={cn(
                  "w-full bg-bg-elevated border rounded px-3 py-2.5 text-sm text-fg-base font-mono placeholder-fg-faint focus:outline-none focus:ring-1 transition-all",
                  urlError
                    ? "border-red-500/50 focus:ring-red-500/30"
                    : "border-border focus:ring-blue-500/30 focus:border-blue-500/40"
                )}
              />
              {urlError && <p className="text-xs text-red-400 mt-1">{urlError}</p>}
            </div>
            <div>
              <label className="text-xs text-fg-faint block mb-2">Quick presets</label>
              <div className="flex flex-wrap gap-2">
                {PRESETS.map((p) => (
                  <button
                    key={p.url}
                    onClick={() => { setTargetUrl(p.url); setUrlError(""); }}
                    className={cn(
                      "px-2.5 py-1 rounded border text-xs font-mono transition-all",
                      targetUrl === p.url
                        ? "border-blue-500/40 bg-blue-500/10 text-blue-300"
                        : "border-border text-fg-subtle hover:text-fg-muted hover:border-border-glow bg-bg-elevated"
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Vulnerability types */}
        <Card>
          <CardHeader>
            <span className="text-sm font-medium text-fg-base flex items-center gap-2">
              <Shield size={14} className="text-red-400" />
              Vulnerability Types
            </span>
            <div className="flex gap-2 text-xs">
              <button onClick={() => setSelectedTypes(VULN_TYPES.map((v) => v.type))} className="text-blue-400 hover:text-blue-300 transition-colors">All</button>
              <span className="text-fg-faint">·</span>
              <button onClick={() => setSelectedTypes([])} className="text-fg-subtle hover:text-fg-muted transition-colors">None</button>
            </div>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {VULN_TYPES.map(({ type, icon: Icon, description, color }) => {
                const selected = selectedTypes.includes(type);
                return (
                  <button
                    key={type}
                    onClick={() => toggleType(type)}
                    className={cn(
                      "flex items-start gap-3 px-3 py-2.5 rounded border text-left transition-all",
                      selected
                        ? "border-blue-500/30 bg-blue-500/[0.07] text-fg-base"
                        : "border-border bg-bg-elevated text-fg-subtle hover:text-fg-muted hover:border-border-glow"
                    )}
                  >
                    <div className={cn("mt-0.5 flex-shrink-0", selected ? color : "text-fg-faint")}>
                      <Icon size={13} />
                    </div>
                    <div>
                      <div className="text-xs font-medium">{type}</div>
                      <div className="text-[10px] text-fg-faint mt-0.5">{description}</div>
                    </div>
                    <div className={cn(
                      "ml-auto w-4 h-4 rounded-sm border flex-shrink-0 mt-0.5 transition-all flex items-center justify-center",
                      selected ? "bg-blue-500 border-blue-500" : "border-fg-faint"
                    )}>
                      {selected && <span className="text-white text-[9px] font-bold">✓</span>}
                    </div>
                  </button>
                );
              })}
            </div>
          </CardBody>
        </Card>

        {/* Advanced */}
        <Card>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full px-4 py-3 flex items-center justify-between text-sm text-fg-muted hover:text-fg-base transition-colors"
          >
            <span className="flex items-center gap-2">
              <Zap size={13} className="text-yellow-400" />
              Advanced Options
            </span>
            {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showAdvanced && (
            <div className="border-t border-border px-4 pb-4 pt-3 space-y-4 animate-fade-in">
              <div>
                <label className="text-xs text-fg-subtle uppercase tracking-wider block mb-2">
                  Minimum Severity to Report
                </label>
                <div className="flex gap-2">
                  {(["critical", "high", "medium", "low"] as Severity[]).map((s) => {
                    const colors = {
                      critical: "border-red-500/40 bg-red-500/10 text-red-300",
                      high: "border-orange-500/40 bg-orange-500/10 text-orange-300",
                      medium: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",
                      low: "border-green-500/40 bg-green-500/10 text-green-300",
                    };
                    return (
                      <button
                        key={s}
                        onClick={() => setSeverity(s)}
                        className={cn(
                          "px-3 py-1.5 rounded border text-xs font-semibold uppercase tracking-wider transition-all",
                          severity === s ? colors[s] : "border-border text-fg-faint hover:text-fg-subtle bg-bg-elevated"
                        )}
                      >
                        {s}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* Launch */}
        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-fg-subtle">
            {selectedTypes.length} type{selectedTypes.length !== 1 ? "s" : ""} selected · min severity: {severity}
          </div>
          <Button onClick={handleLaunch} disabled={launching || selectedTypes.length === 0} size="md" variant="danger" className="min-w-36">
            {launching ? (
              <><div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />Launching...</>
            ) : (
              <><Play size={13} />Launch Audit</>
            )}
          </Button>
        </div>

        {/* Warning */}
        <div className="flex gap-3 px-3 py-2.5 rounded border border-yellow-500/20 bg-yellow-500/5 text-xs text-yellow-600 dark:text-yellow-400/80">
          <AlertTriangle size={13} className="text-yellow-500 flex-shrink-0 mt-0.5" />
          <span>
            Only audit systems you own or have explicit written permission to test.
            Attack scripts execute in a sandboxed Docker container but target the specified URL.
          </span>
        </div>
      </div>
    </div>
  );
}
