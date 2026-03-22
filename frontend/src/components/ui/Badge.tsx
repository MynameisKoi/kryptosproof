import { cn } from "@/lib/utils";
import type { Severity, AuditStatus, OverallStatus } from "@/lib/types";
import { severityColor, auditStatusColor, overallStatusColor, overallStatusLabel } from "@/lib/utils";

interface BadgeProps {
  className?: string;
  children: React.ReactNode;
}

export function Badge({ className, children }: BadgeProps) {
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border", className)}>
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge className={severityColor(severity)}>{severity}</Badge>;
}

export function AuditStatusBadge({ status }: { status: AuditStatus }) {
  const labels: Record<AuditStatus, string> = {
    pending: "Pending",
    running: "Running",
    completed: "Completed",
    failed: "Failed",
  };
  return (
    <Badge className={auditStatusColor(status)}>
      {status === "running" && (
        <span className="mr-1 w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse inline-block" />
      )}
      {labels[status]}
    </Badge>
  );
}

export function OverallStatusBadge({ status }: { status: OverallStatus }) {
  return (
    <Badge className={overallStatusColor(status)}>
      {overallStatusLabel(status)}
    </Badge>
  );
}
