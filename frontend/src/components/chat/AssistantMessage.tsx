import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/types/chat";
import SourceChip from "./SourceChip";
import RiskBadge from "./RiskBadge";

interface AssistantMessageProps {
  message: Message;
}

// ─── Markdown component overrides ────────────────────────────────────────────

function withoutNode<T extends { node?: unknown }>(props: T): Omit<T, "node"> {
  const { node, ...rest } = props;
  void node;
  return rest;
}

const mdComponents: React.ComponentProps<typeof Markdown>["components"] = {
  p: (props) => (
    <p
      className="mb-2 text-sm leading-relaxed text-foreground last:mb-0"
      {...withoutNode(props)}
    />
  ),
  strong: (props) => (
    <strong className="font-semibold text-foreground" {...withoutNode(props)} />
  ),
  em: (props) => <em className="italic" {...withoutNode(props)} />,
  ul: (props) => (
    <ul
      className="mb-2 ml-4 list-disc space-y-0.5 text-sm leading-relaxed text-foreground last:mb-0"
      {...withoutNode(props)}
    />
  ),
  ol: (props) => (
    <ol
      className="mb-2 ml-4 list-decimal space-y-0.5 text-sm leading-relaxed text-foreground last:mb-0"
      {...withoutNode(props)}
    />
  ),
  li: (props) => (
    <li className="text-sm leading-relaxed" {...withoutNode(props)} />
  ),
  pre: (props) => (
    <pre
      className="my-2 overflow-x-auto rounded border border-border bg-surface p-3 text-xs"
      {...withoutNode(props)}
    />
  ),
  code: (props) => (
    <code
      className="rounded bg-surface px-1 py-0.5 font-mono text-xs text-foreground"
      {...withoutNode(props)}
    />
  ),
  blockquote: (props) => (
    <blockquote
      className="my-2 border-l-2 border-border pl-3 text-sm italic text-muted"
      {...withoutNode(props)}
    />
  ),
  h1: (props) => (
    <h1 className="mb-1 text-base font-semibold text-foreground" {...withoutNode(props)} />
  ),
  h2: (props) => (
    <h2 className="mb-1 text-sm font-semibold text-foreground" {...withoutNode(props)} />
  ),
  h3: (props) => (
    <h3 className="mb-1 text-sm font-medium text-foreground" {...withoutNode(props)} />
  ),
  a: (props) => (
    <a
      className="text-accent underline hover:text-accent-hover"
      target="_blank"
      rel="noopener noreferrer"
      {...withoutNode(props)}
    />
  ),
};

// ─── Component ───────────────────────────────────────────────────────────────

export default function AssistantMessage({ message }: AssistantMessageProps) {
  const isWaiting = message.isStreaming && message.content === "";
  const displayContent = message.isStreaming
    ? message.content + " ▌"
    : message.content;

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        {/* Bubble */}
        <div className="rounded-2xl rounded-tl-sm border border-border bg-surface-raised px-4 py-3 shadow-sm">
          {isWaiting ? (
            <div className="space-y-1.5 py-0.5">
              {/* Abgeschlossene Schritte mit Dauer */}
              {message.statusSteps && message.statusSteps.length > 0 && (
                <div className="space-y-1">
                  {message.statusSteps.map((step, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-muted">
                      <span className="text-accent">✓</span>
                      <span>{step.label}</span>
                      <span className="ml-auto tabular-nums opacity-60">
                        {(step.durationMs / 1000).toFixed(1)}s
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {/* Aktuell laufender Schritt */}
              <span className="flex items-center gap-2 text-xs text-muted">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted" />
                </span>
                {message.statusLabel && (
                  <span className="animate-pulse">{message.statusLabel}</span>
                )}
              </span>
            </div>
          ) : (
            <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>
              {displayContent}
            </Markdown>
          )}
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
