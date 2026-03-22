import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "var(--bg-primary)",
          secondary: "var(--bg-secondary)",
          surface: "var(--bg-surface)",
          elevated: "var(--bg-elevated)",
        },
        border: {
          DEFAULT: "var(--border)",
          muted: "var(--border-muted)",
          glow: "var(--border-glow)",
        },
        fg: {
          base: "var(--fg-base)",
          muted: "var(--fg-muted)",
          subtle: "var(--fg-subtle)",
          faint: "var(--fg-faint)",
        },
        red: {
          team: "#ef4444",
          glow: "rgba(239,68,68,0.15)",
        },
        blue: {
          team: "#3b82f6",
          glow: "rgba(59,130,246,0.15)",
        },
        severity: {
          critical: "#dc2626",
          high: "#ea580c",
          medium: "#ca8a04",
          low: "#16a34a",
        },
        status: {
          success: "#10b981",
          warning: "#f59e0b",
          danger: "#ef4444",
          info: "#3b82f6",
          pending: "#6b7280",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Cascadia Code", "monospace"],
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(30,30,58,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(30,30,58,0.4) 1px, transparent 1px)",
        "red-glow": "radial-gradient(circle, rgba(239,68,68,0.08) 0%, transparent 70%)",
        "blue-glow": "radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)",
      },
      backgroundSize: {
        grid: "32px 32px",
      },
      animation: {
        pulse: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scan-line": "scan 3s linear infinite",
        blink: "blink 1s step-end infinite",
        "fade-in": "fadeIn 0.3s ease-in",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { transform: "translateY(8px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
      },
      boxShadow: {
        "red-glow": "0 0 20px rgba(239,68,68,0.2)",
        "blue-glow": "0 0 20px rgba(59,130,246,0.2)",
        "green-glow": "0 0 20px rgba(16,185,129,0.2)",
        panel: "0 0 0 1px rgba(30,30,58,0.8), 0 4px 20px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [],
};

export default config;
