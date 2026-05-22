import { Badge } from "../ui/badge";

import type { WorkflowBlockStatus, WorkflowStepStatus } from "../../types/workflow";

type WorkflowStatusTagProps = {
  status: WorkflowBlockStatus | WorkflowStepStatus;
};

const STATUS_LABEL: Record<WorkflowBlockStatus | WorkflowStepStatus, string> = {
  pending: "待执行",
  running: "进行中",
  completed: "已完成",
  failed: "失败",
};

export function WorkflowStatusTag({ status }: WorkflowStatusTagProps) {
  const variant = status === "failed" ? "destructive" : status === "completed" ? "secondary" : "outline";

  return <Badge variant={variant}>{STATUS_LABEL[status]}</Badge>;
}
