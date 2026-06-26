import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Data Factory",
  description: "Generate synthetic datasets with AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface-900 text-gray-100 antialiased">
        <div className="flex min-h-screen flex-col">
          <header className="border-b border-surface-600 bg-surface-800/80 backdrop-blur-sm sticky top-0 z-50">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="flex h-16 items-center gap-4">
                <a href="/" className="flex items-center gap-3 group">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500/20 border border-brand-500/30 group-hover:bg-brand-500/30 transition-colors">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-400">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                      <path d="M2 17l10 5 10-5"/>
                      <path d="M2 12l10 5 10-5"/>
                    </svg>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-100 group-hover:text-brand-400 transition-colors">AI Data Factory</span>
                    <span className="ml-2 text-xs text-surface-400 font-mono">v0.1</span>
                  </div>
                </a>
                <div className="flex-1" />
                <nav className="flex items-center gap-1">
                  <a href="/" className="rounded-lg px-3 py-1.5 text-sm text-surface-400 hover:text-gray-100 hover:bg-surface-700 transition-colors">
                    Projects
                  </a>
                </nav>
              </div>
            </div>
          </header>
          <main className="flex-1">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
