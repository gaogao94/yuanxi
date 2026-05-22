import type { UserChatMessage } from "../../types/chat";

export function UserMessageBubble({ message }: { message: UserChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-[24px] rounded-tr-sm border border-[#e8f0fe] bg-[#f4f7fc] p-5 text-[15px] leading-relaxed text-gray-800 shadow-sm whitespace-pre-wrap">
        {message.text}
      </div>
    </div>
  );
}
