import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { ThemeProvider } from "@/lib/theme";

export const metadata: Metadata = {
  title: "KryptoSproof — Automated Security Audit",
  description: "AI-powered red team / blue team security audit platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      {/* Inline script prevents theme flash on load */}
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('ks-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}`,
          }}
        />
      </head>
      <body className="bg-bg-primary text-fg-base min-h-screen">
        <ThemeProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto bg-bg-primary bg-grid">
              {children}
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
