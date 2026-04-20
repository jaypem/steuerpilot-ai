"use client";

import { useChatContext } from "@/context/ChatContext";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import ExportButton from "./ExportButton";

export default function ChatContainer() {
  const { messages, isLoading, submitMessage, taxYear } = useChatContext();

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-end px-4 py-1 border-b border-border">
        <ExportButton messages={messages} taxYear={taxYear} />
      </div>
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />
      </div>
      <ChatInput onSubmit={submitMessage} isLoading={isLoading} />
    </div>
  );
}
