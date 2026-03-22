import { cn } from "@/lib/utils";

interface CardProps {
  className?: string;
  children: React.ReactNode;
  glow?: "red" | "blue" | "green" | "none";
}

export function Card({ className, children, glow = "none" }: CardProps) {
  return (
    <div
      className={cn(
        "bg-bg-surface border border-border rounded-lg overflow-hidden",
        {
          "shadow-red-glow border-red-500/20": glow === "red",
          "shadow-blue-glow border-blue-500/20": glow === "blue",
          "shadow-green-glow border-emerald-500/20": glow === "green",
        },
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("px-4 py-3 border-b border-border flex items-center justify-between", className)}>
      {children}
    </div>
  );
}

export function CardBody({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <div className={cn("p-4", className)}>{children}</div>;
}
