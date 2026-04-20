import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/types/chat";
import SourceChip from "./SourceChip";
import RiskBadge from "./RiskBadge";

interface AssistantMessageProps {
  message: Message;
}

// ─── Markdown component overrides ────────────────────────────────────────────

const mdComponents: React.ComponentProps<typeof Markdown>["components"] = {
  p: ({ node: _node, ...props }) => (
    <p
      className="mb-2 text-sm leading-relaxed text-foreground last:mb-0"
      {...props}
    />
  ),
  strong: ({ node: _node, ...props }) => (
    <strong className="font-semibold text-foreground" {...props} />
  ),
  em: ({ node: _node, ...props }) => <em className="italic" {...props} />,
  ul: ({ node: _node, ...props }) => (
    <ul
      className="mb-2 ml-4 list-disc space-y-0.5 text-sm leading-relaxed text-foreground last:mb-0"
      {...props}
    />
  ),
  ol: ({ node: _node, ...props }) => (
    <ol
      className="mb-2 ml-4 list-decimal space-y-0.5 text-sm leading-relaxed text-foreground last:mb-0"
      {...props}
    />
  ),
  li: ({ node: _node, ...props }) => (
    <li className="text-sm leading-relaxed" {...props} />
  ),
  pre: ({ node: _node, ...props }) => (
    <pre
      className="my-2 overflow-x-auto rounded border border-border bg-surface p-3 text-xs"
      {...props}
    />
  ),
  code: ({ node: _node, ...props }) => (
    <code
      className="rounded bg-surface px-1 py-0.5 font-mono text-xs text-foreground"
      {...props}
    />
  ),
  blockquote: ({ node: _node, ...props }) => (
    <blockquote
      className="my-2 border-l-2 border-border pl-3 text-sm italic text-muted"
      {...props}
    />
  ),
  h1: ({ node: _node, ...props }) => (
    <h1 className="mb-1 text-base font-semibold text-foreground" {...props} />
  ),
  h2: ({ node: _node, ...props }) => (
    <h2 className="mb-1 text-sm font-semibold text-foreground" {...props} />
  ),
  h3: ({ node: _node, ...props }) => (
    <h3 className="mb-1 text-sm font-medium text-foreground" {...props} />
  ),
  a: ({ node: _node, ...props }) => (
    <a
      className="text-accent underline hover:text-accent-hover"
      target="_blank"
      rel="noopener noreferrer"
      {...props}
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
            <span className="flex items-center gap-1.5 py-0.5">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted" />
            </span>
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
