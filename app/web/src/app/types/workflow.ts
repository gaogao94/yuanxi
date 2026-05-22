export type WorkflowStage =
  | "idle"
  | "clarifying"
  | "ready_to_execute"
  | "executing"
  | "reviewing"
  | "completed"
  | "blocked"
  | "failed";

export type WorkflowStepStatus = "pending" | "running" | "completed" | "failed";

export type WorkflowBlockKind = "clarification" | "execution" | "review";

export type WorkflowBlockStatus = "running" | "completed" | "failed";

export type WorkflowStep = {
  id: string;
  title: string;
  status: WorkflowStepStatus;
  detail?: string;
  source?: string;
};
