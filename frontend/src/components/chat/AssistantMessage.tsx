import type { Message } from "@/types/chat";
import SourceChip from "./SourceChip";
import RiskBadge from "./RiskBadge";

interface AssistantMessageProps {
  message: Message;
}

export default function AssistantMessage({ message }: AssistantMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        {/* Bubble */}
        <div className="rounded-2xl rounded-tl-sm border border-border bg-surface-raised px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
            {message.content}
            {message.isStreaming && (
              <span
                className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-foreground align-text-bottom"
                aria-hidden
              />
            )}
          </p>
        </div>

        {/* Metadaten: RiskBadge + Ersparnis */}
        {(message.riskBadge || message.savingAmount) && (
          <div className="flex flex-wrap items-center gap-2 px-1">
            {message.riskBadge && (
              <RiskBadge
                level={message.riskBadge.level}
                label={message.riskBadge.label}
                explanation={message.riskBadge.explanation}
              />
            )}
            {message.savingAmount && (
              <span className="inline-flex items-center gap-1 rounded-full bg-saving-subtle px-2.5 py-0.5 text-xs font-medium text-saving">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
                  <path
                    d="M5 1v8M2 6l3 3 3-3"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                ~{message.savingAmount.toLocaleString("de-DE")} € Ersparnis
              </span>
            )}
          </div>
        )}

        {/* Quellen-Chips */}
        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {message.sources.map((source, i) => (
              <SourceChip key={i} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
