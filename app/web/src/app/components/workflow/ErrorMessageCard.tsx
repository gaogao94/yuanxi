import type { ErrorChatMessage } from "../../types/chat";

export function ErrorMessageCard({ message }: { message: ErrorChatMessage }) {
  return (
    <div className="rounded-[20px] border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700 shadow-sm">
      <div className="font-medium">{message.title}</div>
      <p className="mt-2 leading-relaxed">{message.message}</p>
    </div>
  );
}
