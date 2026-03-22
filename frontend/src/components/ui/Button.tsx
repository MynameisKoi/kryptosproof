import { cn } from "@/lib/utils";
import { type ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "danger" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-medium rounded transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-bg-primary disabled:opacity-40 disabled:cursor-not-allowed",
        {
          "bg-blue-600 hover:bg-blue-500 text-white focus:ring-blue-500": variant === "primary",
          "bg-red-600 hover:bg-red-500 text-white focus:ring-red-500": variant === "danger",
          "text-fg-muted hover:text-fg-base hover:bg-bg-elevated": variant === "ghost",
          "border border-border text-fg-muted hover:text-fg-base hover:border-border-glow bg-transparent": variant === "outline",
        },
        {
          "text-xs px-3 py-1.5": size === "sm",
          "text-sm px-4 py-2": size === "md",
          "text-base px-6 py-3": size === "lg",
        },
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
