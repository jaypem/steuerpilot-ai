import type { Message } from "@/types/chat";

interface UserMessageProps {
  message: Message;
}

export default function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-accent px-4 py-2.5">
        <p className="text-sm leading-relaxed text-white whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
    </div>
  );
}
