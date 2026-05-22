import type { ChartChatMessage } from "../../types/chat";

import { EChart } from "./EChart";

export function ChartMessageCard({ message }: { message: ChartChatMessage }) {
  return (
    <div className="rounded-[20px] border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3">
        <div className="text-sm font-medium text-gray-800">{message.title}</div>
        {message.description ? <p className="mt-1 text-sm text-gray-500">{message.description}</p> : null}
      </div>
      <EChart option={message.option} style={{ height: 240 }} />
    </div>
  );
}
