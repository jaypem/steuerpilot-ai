"use client";

import type { Message } from "@/types/chat";
import { useMockChat } from "@/hooks/useMockChat";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";

const INITIAL_MESSAGES: Message[] = [
  {
    id: "init-1",
    role: "user",
    content: "Kann ich mein Homeoffice von der Steuer absetzen?",
    timestamp: new Date(),
  },
  {
    id: "init-2",
    role: "assistant",
    content:
      "Ja, Homeoffice-Kosten können Sie steuerlich geltend machen. Seit 2023 gilt die erhöhte Tagespauschale von 6 € pro Tag (max. 1.260 € im Jahr, also 210 Tage).\n\nAlternativ können Sie ein häusliches Arbeitszimmer absetzen, wenn es ausschließlich beruflich genutzt wird — dann sind die tatsächlichen anteiligen Kosten absetzbar, was bei größeren Wohnungen deutlich mehr einbringen kann.\n\nMöchten Sie wissen, ob sich das Arbeitszimmer oder die Tagespauschale für Sie mehr lohnt?",
    sources: [
      {
        law: "EStG",
        paragraph: "§ 4",
        section: "Abs. 5 Nr. 6b",
        text: "Für jeden Kalendertag, an dem der Steuerpflichtige seine betriebliche oder berufliche Tätigkeit ausschließlich in der häuslichen Wohnung ausübt, kann er einen Betrag von 6 Euro abziehen, höchstens 1 260 Euro im Wirtschafts- oder Kalenderjahr.",
      },
    ],
    riskBadge: {
      level: "low",
      label: "Unstreitig",
      explanation:
        "Tagespauschale ist seit 2023 gesetzlich klar geregelt (§ 4 Abs. 5 Nr. 6b EStG). Volle Akzeptanz durch Finanzbehörden.",
    },
    savingAmount: 252,
    timestamp: new Date(),
  },
];

export default function ChatContainer() {
  const { messages, isLoading, submitMessage } = useMockChat({
    initialMessages: INITIAL_MESSAGES,
  });

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />
      </div>
      <ChatInput onSubmit={submitMessage} isLoading={isLoading} />
    </div>
  );
}
