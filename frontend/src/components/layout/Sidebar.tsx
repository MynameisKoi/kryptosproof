"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shield,
  LayoutDashboard,
  Plus,
  History,
  Activity,
  Terminal,
  ChevronRight,
  Sun,
  Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/theme";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/audit/new", label: "New Audit", icon: Plus },
  { href: "/history", label: "History", icon: History },
];

export function Sidebar() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();

  return (
    <aside className="w-56 flex-shrink-0 bg-bg-secondary border-r border-border flex flex-col">
      {/* Logo */}
      <div className="h-14 px-4 flex items-center gap-2.5 border-b border-border">
        <div className="w-7 h-7 rounded bg-gradient-to-br from-red-500 to-blue-600 flex items-center justify-center">
          <Shield size={14} className="text-white" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-wide text-fg-base leading-none">
            Kryptos<span className="text-blue-400">Proof</span>
          </div>
          <div className="text-[9px] text-fg-subtle tracking-widest uppercase">
            Security Audit
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-all group",
                active
                  ? "bg-blue-600/15 text-blue-300 border border-blue-500/20"
                  : "text-fg-muted hover:text-fg-base hover:bg-bg-elevated"
              )}
            >
              <Icon
                size={14}
                className={active ? "text-blue-400" : "text-fg-subtle group-hover:text-fg-muted"}
              />
              <span>{label}</span>
              {active && <ChevronRight size={12} className="ml-auto text-blue-500" />}
            </Link>
          );
        })}
      </nav>

      {/* Status indicator */}
      <div className="px-3 pb-3">
        <div className="rounded border border-border bg-bg-elevated px-3 py-2.5 space-y-2">
          <div className="flex items-center gap-2 text-xs text-fg-muted">
            <Activity size={11} className="text-emerald-400" />
            <span className="text-emerald-400 font-medium">System Online</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-fg-subtle">
            <Terminal size={10} />
            <span>Claude Opus 4.6</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-fg-subtle">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Docker sandbox ready</span>
          </div>
        </div>
      </div>

      {/* Theme toggle */}
      <div className="px-3 pb-4">
        <button
          onClick={toggle}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded border border-border hover:bg-bg-elevated text-fg-subtle hover:text-fg-muted transition-all text-xs"
        >
          {theme === "dark" ? (
            <>
              <Sun size={13} className="text-yellow-400" />
              <span>Light mode</span>
            </>
          ) : (
            <>
              <Moon size={13} className="text-blue-400" />
              <span>Dark mode</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
