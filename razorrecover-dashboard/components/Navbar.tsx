"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-rule bg-paper sticky top-0 z-30">
      <div className="mx-auto max-w-6xl px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 group">
            <span className="w-2.5 h-2.5 rounded-full bg-recovered group-hover:scale-110 transition-transform" />
            <span className="font-serif font-semibold text-lg text-ink tracking-tight">
              RazorRecover
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            <Link
              href="/"
              className={`px-3 py-1.5 text-[13px] font-medium rounded transition-colors ${
                pathname === "/"
                  ? "bg-ink text-paper font-semibold"
                  : "text-ink-muted hover:text-ink hover:bg-rule/40"
              }`}
            >
              📊 Executive Ledger
            </Link>
            <Link
              href="/simulator"
              className={`px-3 py-1.5 text-[13px] font-medium rounded transition-colors flex items-center gap-1.5 ${
                pathname === "/simulator"
                  ? "bg-accent text-paper font-semibold shadow-sm"
                  : "text-accent hover:bg-accent-soft/70"
              }`}
            >
              <span className="inline-block animate-pulse text-[11px]">⚡</span>
              <span>Live Recovery Simulator</span>
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3 text-[12px] text-ink-muted font-mono">
          <div className="flex items-center gap-1.5 bg-paper px-2.5 py-1 rounded border border-rule">
            <span className="w-1.5 h-1.5 rounded-full bg-recovered animate-ping" />
            <span className="text-[11px] text-ink">Engine: Online</span>
          </div>
        </div>
      </div>
    </header>
  );
}
