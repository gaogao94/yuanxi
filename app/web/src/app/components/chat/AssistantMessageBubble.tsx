import { Sparkles } from "lucide-react";

import type { AssistantTextMessage } from "../../types/chat";

export function AssistantMessageBubble({ message }: { message: AssistantTextMessage }) {
  return (
    <div className="flex gap-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-gradient-to-br from-[#1a73e8] to-[#4285f4] shadow-md shadow-blue-500/20">
        <Sparkles className="h-5 w-5 text-white" />
      </div>
      <div className="pt-1 text-[15px] leading-relaxed text-gray-800 whitespace-pre-wrap">{message.text}</div>
    </div>
  );
}
