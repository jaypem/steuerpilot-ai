import type { Message } from "@/types/chat";

const RISK_LABELS: Record<string, string> = {
  low: "Unstreitig",
  medium: "Grauzone",
  high: "Strittig",
};

// ─── Markdown ─────────────────────────────────────────────────────────────────

function buildMarkdown(messages: Message[], taxYear: number): string {
  const date = new Date().toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  const lines: string[] = [
    `# steuerpilot-ai — Steuerberatung ${taxYear}`,
    `_Exportiert am ${date}_`,
    "",
    "---",
    "",
  ];

  for (const msg of messages) {
    if (msg.isStreaming) continue;

    if (msg.role === "user") {
      lines.push(`**Du:** ${msg.content}`, "", "---", "");
      continue;
    }

    lines.push(`**steuerpilot:** ${msg.content}`, "");

    if (msg.sources?.length) {
      lines.push(
        "**Quellen:**",
        ...msg.sources.map(
          (s) =>
            `- ${[s.paragraph, s.section, s.law].filter(Boolean).join(" ")}${s.text ? ` — ${s.text.slice(0, 120)}…` : ""}`,
        ),
        "",
      );
    }

    if (msg.riskBadge) {
      const level = RISK_LABELS[msg.riskBadge.level] ?? msg.riskBadge.level;
      lines.push(
        `**Rechtssicherheit:** ${level} — ${msg.riskBadge.explanation}`,
        "",
      );
    }

    if (msg.savingAmount) {
      lines.push(`**Geschätzte Steuerersparnis:** ~${msg.savingAmount} €`, "");
    }

    lines.push("---", "");
  }

  lines.push(
    "_Hinweis: Diese Ausgabe ersetzt keine Steuerberatung im Sinne des StBerG._",
  );

  return lines.join("\n");
}

export function exportMarkdown(messages: Message[], taxYear: number): void {
  const content = buildMarkdown(messages, taxYear);
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `steuerpilot-${taxYear}-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── PDF (via Browser-Print) ──────────────────────────────────────────────────

function buildPrintHTML(messages: Message[], taxYear: number): string {
  const date = new Date().toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  const rows = messages
    .filter((m) => !m.isStreaming)
    .map((msg) => {
      if (msg.role === "user") {
        return `<div class="msg user"><span class="label">Du</span><p>${escHtml(msg.content)}</p></div>`;
      }

      let html = `<div class="msg assistant"><span class="label">steuerpilot</span><p>${escHtml(msg.content)}</p>`;

      if (msg.sources?.length) {
        const items = msg.sources
          .map((s) => {
            const ref = [s.paragraph, s.section, s.law].filter(Boolean).join(" ");
            return `<li>${escHtml(ref)}</li>`;
          })
          .join("");
        html += `<div class="meta"><strong>Quellen:</strong><ul>${items}</ul></div>`;
      }

      if (msg.riskBadge) {
        const level = RISK_LABELS[msg.riskBadge.level] ?? msg.riskBadge.level;
        html += `<div class="meta"><strong>Rechtssicherheit:</strong> ${escHtml(level)} — ${escHtml(msg.riskBadge.explanation)}</div>`;
      }

      if (msg.savingAmount) {
        html += `<div class="meta saving"><strong>Geschätzte Steuerersparnis:</strong> ~${msg.savingAmount} €</div>`;
      }

      html += "</div>";
      return html;
    })
    .join("");

  return `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>steuerpilot-ai — ${taxYear}</title>
<style>
  body { font-family: system-ui, sans-serif; font-size: 13px; color: #111; max-width: 780px; margin: 0 auto; padding: 32px; }
  h1 { font-size: 18px; margin-bottom: 4px; }
  .subtitle { color: #666; font-size: 12px; margin-bottom: 24px; }
  .msg { margin-bottom: 20px; padding: 12px 16px; border-radius: 6px; }
  .msg.user { background: #f5f5f5; }
  .msg.assistant { border: 1px solid #e5e5e5; }
  .label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: #888; display: block; margin-bottom: 6px; }
  .msg.user .label { color: #555; }
  p { margin: 0 0 8px; white-space: pre-wrap; }
  .meta { font-size: 12px; color: #555; margin-top: 8px; }
  .meta ul { margin: 4px 0 0 16px; padding: 0; }
  .saving { color: #166534; font-weight: 500; }
  .disclaimer { margin-top: 32px; font-size: 11px; color: #999; border-top: 1px solid #e5e5e5; padding-top: 12px; }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
<h1>steuerpilot-ai — Steuerberatung ${taxYear}</h1>
<p class="subtitle">Exportiert am ${date}</p>
${rows}
<p class="disclaimer">Hinweis: Diese Ausgabe ersetzt keine Steuerberatung im Sinne des StBerG.</p>
<script>window.onload = () => { window.print(); }<\/script>
</body>
</html>`;
}

function escHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function exportPDF(messages: Message[], taxYear: number): void {
  const html = buildPrintHTML(messages, taxYear);
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank");
  if (win) {
    win.addEventListener("afterprint", () => URL.revokeObjectURL(url));
  } else {
    URL.revokeObjectURL(url);
  }
}
