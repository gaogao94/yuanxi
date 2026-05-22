import type { EChartsOption } from "echarts";

import type { ApiArtifact } from "./api";
import type {
  WorkflowBlockKind,
  WorkflowBlockStatus,
  WorkflowStep,
} from "./workflow";

export type UserChatMessage = {
  id: string;
  type: "user";
  text: string;
  createdAt?: string;
};

export type AssistantTextMessage = {
  id: string;
  type: "assistant_text";
  text: string;
  createdAt?: string;
};

export type WorkflowBlockMessage = {
  id: string;
  type: "workflow_block";
  blockKind: WorkflowBlockKind;
  status: WorkflowBlockStatus;
  title: string;
  subtitle?: string;
  steps: WorkflowStep[];
  questionId?: string;
  prompt?: string;
  options?: string[];
  answer?: string;
  createdAt?: string;
};

export type ChartChatMessage = {
  id: string;
  type: "chart";
  title: string;
  description?: string;
  option: EChartsOption;
  createdAt?: string;
};

export type ArtifactChatMessage = {
  id: string;
  type: "artifact";
  title: string;
  artifacts: ApiArtifact[];
  createdAt?: string;
};

export type ErrorChatMessage = {
  id: string;
  type: "error";
  title: string;
  message: string;
  createdAt?: string;
};

export type ChatMessage =
  | UserChatMessage
  | AssistantTextMessage
  | WorkflowBlockMessage
  | ChartChatMessage
  | ArtifactChatMessage
  | ErrorChatMessage;
