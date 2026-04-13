import type { RiskLevel } from "@/types/chat";

const config: Record<
  RiskLevel,
  { label: string; bgClass: string; textClass: string; dotClass: string }
> = {
  low: {
    label: "Unstreitig",
    bgClass: "bg-risk-low-subtle",
    textClass: "text-risk-low",
    dotClass: "bg-risk-low",
  },
  medium: {
    label: "Grauzone",
    bgClass: "bg-risk-medium-subtle",
    textClass: "text-risk-medium",
    dotClass: "bg-risk-medium",
  },
  high: {
    label: "Strittig",
    bgClass: "bg-risk-high-subtle",
    textClass: "text-risk-high",
    dotClass: "bg-risk-high",
  },
};

interface RiskBadgeProps {
  level: RiskLevel;
  label?: string;
  explanation?: string;
}

export default function RiskBadge({ level, label, explanation }: RiskBadgeProps) {
  const c = config[level];
  const displayLabel = label ?? c.label;

  return (
    <div className="group relative inline-block">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${c.bgClass} ${c.textClass}`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${c.dotClass}`} aria-hidden />
        {displayLabel}
      </span>

      {explanation && (
        <div
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-0 z-10 mb-1.5 hidden w-56 rounded-lg border border-border bg-surface-raised p-2.5 shadow-md group-hover:block"
        >
          <p className="text-xs leading-relaxed text-foreground">{explanation}</p>
        </div>
      )}
    </div>
  );
}
