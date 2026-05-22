import type { ApiArtifact } from "../../types/api";
import type { ChatMessage } from "../../types/chat";

import { ChartMessageCard } from "../charts/ChartMessageCard";
import { ClarificationBlock } from "../workflow/ClarificationBlock";
import { ErrorMessageCard } from "../workflow/ErrorMessageCard";
import { ExecutionProgressBlock } from "../workflow/ExecutionProgressBlock";
import { ReviewBlock } from "../workflow/ReviewBlock";
import { ArtifactMessageCard } from "../workflow/ArtifactMessageCard";
import { AssistantMessageBubble } from "./AssistantMessageBubble";
import { UserMessageBubble } from "./UserMessageBubble";

type ChatMessageListProps = {
  messages: ChatMessage[];
  onClarificationAnswer?: (questionId: string, answer: string) => void;
  onOpenArtifact?: (artifact: ApiArtifact) => void;
};

export function ChatMessageList({
  messages,
  onClarificationAnswer,
  onOpenArtifact,
}: ChatMessageListProps) {
  return (
    <div className="space-y-8 pb-60 max-w-4xl mx-auto w-full px-4">
      {messages.map((message) => {
        switch (message.type) {
          case "user":
            return <UserMessageBubble key={message.id} message={message} />;
          case "assistant_text":
            return <AssistantMessageBubble key={message.id} message={message} />;
          case "workflow_block":
            return (
              <div key={message.id} className="flex gap-4 max-w-3xl">
                <div className="w-10 shrink-0" />
                <div className="flex-1">
                  {message.blockKind === "clarification" ? (
                    <ClarificationBlock message={message} onAnswer={onClarificationAnswer} />
                  ) : message.blockKind === "execution" ? (
                    <ExecutionProgressBlock message={message} />
                  ) : (
                    <ReviewBlock message={message} />
                  )}
                </div>
              </div>
            );
          case "chart":
            return (
              <div key={message.id} className="flex gap-4 max-w-3xl">
                <div className="w-10 shrink-0" />
                <div className="flex-1">
                  <ChartMessageCard message={message} />
                </div>
              </div>
            );
          case "artifact":
            return (
              <div key={message.id} className="flex gap-4 max-w-3xl">
                <div className="w-10 shrink-0" />
                <div className="flex-1">
                  <ArtifactMessageCard message={message} onOpenArtifact={onOpenArtifact} />
                </div>
              </div>
            );
          case "error":
            return (
              <div key={message.id} className="flex gap-4 max-w-3xl">
                <div className="w-10 shrink-0" />
                <div className="flex-1">
                  <ErrorMessageCard message={message} />
                </div>
              </div>
            );
        }
      })}
    </div>
  );
}
