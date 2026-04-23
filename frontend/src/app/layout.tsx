import type { Metadata } from "next";
import { ChatProvider } from "@/context/ChatContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "steuerpilot-ai",
  description: "KI-gestützter Steuerberater-Assistent für maximale Steuerersparnis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="h-full antialiased">
      <body className="h-full bg-surface text-foreground">
        <ChatProvider>{children}</ChatProvider>
      </body>
    </html>
  );
}
