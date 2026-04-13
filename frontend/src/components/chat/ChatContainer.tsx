"use client";

import { useChatContext } from "@/context/ChatContext";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";

export default function ChatContainer() {
  const { messages, isLoading, submitMessage } = useChatContext();

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />
      </div>
      <ChatInput onSubmit={submitMessage} isLoading={isLoading} />
    </div>
  );
}
