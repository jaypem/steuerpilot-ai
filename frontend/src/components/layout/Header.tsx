"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useChatContext } from "@/context/ChatContext";

const TAX_YEARS = [2022, 2023, 2024, 2025];

interface HeaderProps {
  onToggleSessionSidebar: () => void;
  onToggleSparSidebar: () => void;
}

export default function Header({
  onToggleSessionSidebar,
  onToggleSparSidebar,
}: HeaderProps) {
  const pathname = usePathname();
  const { taxYear, setTaxYear } = useChatContext();

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface-raised px-4">
      {/* Mobile: Session-Sidebar-Toggle */}
      <button
        onClick={onToggleSessionSidebar}
        aria-label="Konversations-Verlauf öffnen"
        className="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-border lg:hidden"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
          <rect y="3" width="18" height="1.5" rx="0.75" fill="currentColor" />
          <rect y="8.25" width="18" height="1.5" rx="0.75" fill="currentColor" />
          <rect y="13.5" width="18" height="1.5" rx="0.75" fill="currentColor" />
        </svg>
      </button>

      {/* Logo + Nav */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold tracking-tight text-foreground">
            steuerpilot
          </span>
          <select
            value={taxYear}
            onChange={(e) => setTaxYear(Number(e.target.value))}
            aria-label="Steuerjahr auswählen"
            className="rounded-full bg-accent-subtle px-2 py-0.5 font-mono text-xs font-medium text-accent cursor-pointer border-none outline-none appearance-none"
          >
            {TAX_YEARS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Hauptnavigation">
          <Link
            href="/"
            className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
              pathname === "/"
                ? "bg-border text-foreground"
                : "text-muted hover:bg-border hover:text-foreground"
            }`}
          >
            Chat
          </Link>
          <Link
            href="/scan"
            className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
              pathname === "/scan"
                ? "bg-border text-foreground"
                : "text-muted hover:bg-border hover:text-foreground"
            }`}
          >
            Ausgaben-Scan
          </Link>
          <Link
            href="/idea-transfer"
            className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
              pathname === "/idea-transfer"
                ? "bg-border text-foreground"
                : "text-muted hover:bg-border hover:text-foreground"
            }`}
          >
            Ideen-Transfer
          </Link>
          <Link
            href="/instagram-check"
            className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
              pathname === "/instagram-check"
                ? "bg-border text-foreground"
                : "text-muted hover:bg-border hover:text-foreground"
            }`}
          >
            Instagram-Check
          </Link>
        </nav>
      </div>

      {/* Mobile: Spar-Sidebar-Toggle */}
      <button
        onClick={onToggleSparSidebar}
        aria-label="Sparpotenzial öffnen"
        className="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-border lg:hidden"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
          <path
            d="M9 1.5C4.86 1.5 1.5 4.86 1.5 9S4.86 16.5 9 16.5 16.5 13.14 16.5 9 13.14 1.5 9 1.5Zm.75 11.25H8.25V8.25h1.5v4.5Zm0-6H8.25v-1.5h1.5v1.5Z"
            fill="currentColor"
          />
        </svg>
      </button>
    </header>
  );
}
