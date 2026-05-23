import type {
  WorkflowBlockStatus,
  WorkflowBlockKind,
  WorkflowStage,
  WorkflowStep,
} from "./workflow";

export type ApiChartType = "bar" | "line" | "pie";

export type ApiChartPayload = {
  id: string;
  title: string;
  type: ApiChartType;
  categories: string[];
  series: Array<{
    name: string;
    data: number[];
  }>;
  unit?: string;
  description?: string;
};

export type ApiArtifactType = "ppt" | "todo" | "report" | "file" | "html_report";

export type ApiArtifact = {
  id: string;
  type: ApiArtifactType;
  title: string;
  size?: string;
  createdAt?: string;
  url?: string;
  preview?: string[];
};

export type ApiSessionItemBase = {
  id: string;
  createdAt?: string;
};

export type ApiUserMessageItem = ApiSessionItemBase & {
  kind: "user_message";
  text: string;
};

export type ApiAssistantMessageItem = ApiSessionItemBase & {
  kind: "assistant_message";
  text: string;
};

export type ApiClarificationItem = ApiSessionItemBase & {
  kind: "clarification";
  blockKind: Extract<WorkflowBlockKind, "clarification">;
  title: string;
  subtitle?: string;
  status: WorkflowBlockStatus;
  questionId: string;
  prompt: string;
  options?: string[];
  answer?: string;
};

export type ApiProgressItem = ApiSessionItemBase & {
  kind: "progress";
  blockKind: Extract<WorkflowBlockKind, "execution">;
  title: string;
  subtitle?: string;
  status: WorkflowBlockStatus;
  steps: WorkflowStep[];
};

export type ApiReviewItem = ApiSessionItemBase & {
  kind: "review";
  blockKind: Extract<WorkflowBlockKind, "review">;
  title: string;
  subtitle?: string;
  status: WorkflowBlockStatus;
  steps: WorkflowStep[];
};

export type ApiChartItem = ApiSessionItemBase & {
  kind: "chart";
  title: string;
  description?: string;
  chart: ApiChartPayload;
};

export type ApiArtifactItem = ApiSessionItemBase & {
  kind: "artifact";
  title: string;
  artifacts: ApiArtifact[];
};

export type ApiErrorItem = ApiSessionItemBase & {
  kind: "error";
  title: string;
  message: string;
};

export type ApiSessionItem =
  | ApiUserMessageItem
  | ApiAssistantMessageItem
  | ApiClarificationItem
  | ApiProgressItem
  | ApiReviewItem
  | ApiChartItem
  | ApiArtifactItem
  | ApiErrorItem;

export type ApiChatSession = {
  sessionId: string;
  stage: WorkflowStage;
  items: ApiSessionItem[];
};

export type ReplyClarificationInput = {
  questionId: string;
  answer: string;
};

// ── SSE Stream Event Payloads ───────────────────────────────────────────

export type ApiStreamEventThinking = {
  text: string;
  source: string;
};

export type ApiClarificationQuestion = {
  id: string;
  question: string;
  type: string;
  options: string[];
  required: boolean;
  source: string;
};

export type ApiStreamEventClarification = {
  status: "needs_clarification";
  conversation_id: string;
  text: string;
  clarification_questions: ApiClarificationQuestion[];
};

export type ApiChartData = {
  type: string;
  data: Record<string, any>[];
};

export type ApiThinkingStep = {
  text: string;
  source?: string;
  chart?: ApiChartData;
};

export type ApiAttachment = {
  id: string;
  type: string;
  title: string;
  size?: string;
  preview?: string[];
  url?: string;
};

export type ApiStreamEventResult = {
  status: string;
  conversation_id: string;
  text: string;
  thinking: ApiThinkingStep[];
  charts: ApiChartData[];
  attachments: ApiAttachment[];
  raw?: any;
};

export type ApiStreamEventError = {
  text: string;
};

export type ApiStreamEvent =
  | { type: "thinking"; data: ApiStreamEventThinking }
  | { type: "clarification"; data: ApiStreamEventClarification }
  | { type: "result"; data: ApiStreamEventResult }
  | { type: "error"; data: ApiStreamEventError }
  | { type: "done"; data: {} };

