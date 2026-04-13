"use client";

import { useState } from "react";
import type { Message } from "@/types/chat";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";

const DUMMY_MESSAGES: Message[] = [
  {
    id: "1",
    role: "user",
    content: "Kann ich mein Homeoffice von der Steuer absetzen?",
    timestamp: new Date(),
  },
  {
    id: "2",
    role: "assistant",
    content:
      "Ja, Homeoffice-Kosten können Sie steuerlich geltend machen. Seit 2023 gilt die erhöhte Tagespauschale von 6 € pro Tag (max. 1.260 € im Jahr, also 210 Tage).\n\nAlternativ können Sie ein häusliches Arbeitszimmer absetzen, wenn es ausschließlich beruflich genutzt wird — dann sind die tatsächlichen anteiligen Kosten absetzbar, was bei größeren Wohnungen deutlich mehr einbringen kann.\n\nMöchten Sie wissen, ob sich das Arbeitszimmer oder die Tagespauschale für Sie mehr lohnt?",
    sources: [
      {
        law: "EStG",
        paragraph: "§ 4",
        section: "Abs. 5 Nr. 6b",
        text: "Für jeden Kalendertag, an dem der Steuerpflichtige seine betriebliche oder berufliche Tätigkeit ausschließlich in der häuslichen Wohnung ausübt und keine außerhäusliche erste Tätigkeitsstätte aufsucht, kann er für seine gesamte betriebliche und berufliche Betätigung einen Betrag von 6 Euro abziehen.",
      },
      {
        law: "EStG",
        paragraph: "§ 9",
        section: "Abs. 1 Nr. 7",
        text: "Aufwendungen für ein häusliches Arbeitszimmer sowie die Kosten der Ausstattung sind als Werbungskosten abzugsfähig, wenn das Arbeitszimmer den Mittelpunkt der gesamten betrieblichen und beruflichen Betätigung bildet.",
      },
    ],
    riskBadge: {
      level: "low",
      label: "Unstreitig",
      explanation:
        "Tagespauschale ist seit 2023 gesetzlich klar geregelt (§ 4 Abs. 5 Nr. 6b EStG). Volle Akzeptanz durch Finanzbehörden, kein Streitpotenzial.",
    },
    savingAmount: 210,
    timestamp: new Date(),
  },
  {
    id: "3",
    role: "user",
    content: "Ich habe auch einen Laptop für 1.400 € gekauft. Kann ich den komplett absetzen?",
    timestamp: new Date(),
  },
  {
    id: "4",
    role: "assistant",
    content:
      "Ja, und sogar vollständig im Kaufjahr — das ist eine sehr günstige Regelung.\n\nSeit 2021 können Computerhardware und Software sofort und vollständig abgeschrieben werden (0 Jahre Nutzungsdauer). Bei einem Grenzsteuersatz von 30 % würden Sie damit ~420 € Steuern sparen.\n\nHaben Sie noch weitere Arbeitsmittel gekauft? Ein zweiter Monitor, Headset oder Bürostuhl wären ebenfalls absetzbar.",
    sources: [
      {
        law: "EStG",
        paragraph: "§ 9",
        section: "Abs. 1 Nr. 7",
        text: "Bei Wirtschaftsgütern, die ausschließlich oder fast ausschließlich der Berufsausübung dienen, können die Anschaffungs- oder Herstellungskosten als Werbungskosten abgezogen werden.",
      },
    ],
    riskBadge: {
      level: "medium",
      label: "Grauzone",
      explanation:
        "Die Sofortabschreibung für PCs ist seit BMF-Schreiben vom 22.02.2022 möglich, aber das Finanzamt prüft gelegentlich die berufliche Nutzung. Empfehlung: Nutzungsprotokoll führen.",
    },
    savingAmount: 420,
    timestamp: new Date(),
  },
];

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>(DUMMY_MESSAGES);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (text: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Platzhalter bis Mock-Streaming in Phase 4 kommt
    setTimeout(() => {
      const reply: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "Diese Funktion wird in Phase 4 mit echtem Mock-Streaming implementiert. Ihre Frage wurde registriert.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, reply]);
      setIsLoading(false);
    }, 800);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />
      </div>
      <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
}
