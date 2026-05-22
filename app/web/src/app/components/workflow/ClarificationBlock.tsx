import type { WorkflowBlockMessage } from "../../types/chat";

import { Button } from "../ui/button";

import { CollapsibleWorkflowBlock } from "./CollapsibleWorkflowBlock";

type ClarificationBlockProps = {
  message: WorkflowBlockMessage;
  onAnswer?: (questionId: string, answer: string) => void;
};

export function ClarificationBlock({ message, onAnswer }: ClarificationBlockProps) {
  return (
    <CollapsibleWorkflowBlock
      title={message.title}
      subtitle={message.subtitle}
      status={message.status}
      defaultOpen={message.status === "running"}
    >
      <div className="space-y-4">
        {message.prompt ? <p className="text-sm leading-relaxed text-gray-700">{message.prompt}</p> : null}
        {message.answer ? (
          <div className="rounded-2xl border border-green-100 bg-green-50 px-4 py-3 text-sm text-green-700">
            已确认方向：{message.answer}
          </div>
        ) : null}
        {message.options?.length && message.questionId && message.status === "running" ? (
          <div className="flex flex-col gap-2">
            {message.options.map((option, index) => (
              <Button
                key={`${message.id}-option-${index}`}
                type="button"
                variant="outline"
                className="justify-between rounded-2xl border-blue-200 bg-white px-4 py-3 text-left text-sm text-[#1a73e8] hover:bg-blue-50"
                onClick={() => onAnswer?.(message.questionId as string, option)}
              >
                <span className="truncate">{option}</span>
              </Button>
            ))}
          </div>
        ) : null}
      </div>
    </CollapsibleWorkflowBlock>
  );
}
