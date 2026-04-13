"use client";

import { useState } from "react";
import Header from "./Header";
import SessionSidebar from "./SessionSidebar";
import SparSidebar from "./SparSidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const [sessionSidebarOpen, setSessionSidebarOpen] = useState(false);
  const [sparSidebarOpen, setSparSidebarOpen] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string>("1");

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Mobile Overlay ─────────────────────────────────────── */}
      {(sessionSidebarOpen || sparSidebarOpen) && (
        <div
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={() => {
            setSessionSidebarOpen(false);
            setSparSidebarOpen(false);
          }}
          aria-hidden
        />
      )}

      {/* ── Session-Sidebar ────────────────────────────────────── */}
      <div
        className={`
          fixed inset-y-0 left-0 z-30 transition-transform duration-200
          lg:relative lg:translate-x-0 lg:z-auto
          ${sessionSidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <SessionSidebar
          activeSessionId={activeSessionId}
          onSelectSession={(id) => {
            setActiveSessionId(id);
            setSessionSidebarOpen(false);
          }}
          onNewSession={() => {
            setActiveSessionId("");
            setSessionSidebarOpen(false);
          }}
        />
      </div>

      {/* ── Hauptbereich ───────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          onToggleSessionSidebar={() =>
            setSessionSidebarOpen((prev) => !prev)
          }
          onToggleSparSidebar={() => setSparSidebarOpen((prev) => !prev)}
        />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>

      {/* ── Spar-Sidebar ───────────────────────────────────────── */}
      <div
        className={`
          fixed inset-y-0 right-0 z-30 transition-transform duration-200
          lg:relative lg:translate-x-0 lg:z-auto
          ${sparSidebarOpen ? "translate-x-0" : "translate-x-full"}
        `}
      >
        <SparSidebar />
      </div>
    </div>
  );
}
