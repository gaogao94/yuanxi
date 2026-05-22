import type { ApiChatSession, ApiSessionItem } from "../types/api";
import type { ChatMessage } from "../types/chat";

import { buildChartOption } from "./chartToEcharts";

function mapItemToMessage(item: ApiSessionItem): ChatMessage {
  switch (item.kind) {
    case "user_message":
      return {
        id: item.id,
        type: "user",
        text: item.text,
        createdAt: item.createdAt,
      };
    case "assistant_message":
      return {
        id: item.id,
        type: "assistant_text",
        text: item.text,
        createdAt: item.createdAt,
      };
    case "clarification":
    case "progress":
    case "review":
      return {
        id: item.id,
        type: "workflow_block",
        blockKind: item.blockKind,
        status: item.status,
        title: item.title,
        subtitle: item.subtitle,
        steps: item.steps ?? [],
        questionId: item.kind === "clarification" ? item.questionId : undefined,
        prompt: item.kind === "clarification" ? item.prompt : undefined,
        options: item.kind === "clarification" ? item.options : undefined,
        answer: item.kind === "clarification" ? item.answer : undefined,
        createdAt: item.createdAt,
      };
    case "chart":
      return {
        id: item.id,
        type: "chart",
        title: item.title,
        description: item.description,
        option: buildChartOption(item.chart),
        createdAt: item.createdAt,
      };
    case "artifact":
      return {
        id: item.id,
        type: "artifact",
        title: item.title,
        artifacts: item.artifacts,
        createdAt: item.createdAt,
      };
    case "error":
      return {
        id: item.id,
        type: "error",
        title: item.title,
        message: item.message,
        createdAt: item.createdAt,
      };
  }
}

export function mapSessionToMessages(session: ApiChatSession): ChatMessage[] {
  return session.items.map(mapItemToMessage);
}
