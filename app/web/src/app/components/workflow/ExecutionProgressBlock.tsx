import type { WorkflowBlockMessage } from "../../types/chat";

import { CollapsibleWorkflowBlock } from "./CollapsibleWorkflowBlock";
import { WorkflowStepList } from "./WorkflowStepList";

export function ExecutionProgressBlock({ message }: { message: WorkflowBlockMessage }) {
  return (
    <CollapsibleWorkflowBlock
      title={message.title}
      subtitle={message.subtitle}
      status={message.status}
      defaultOpen={message.status === "running"}
    >
      <WorkflowStepList steps={message.steps} />
    </CollapsibleWorkflowBlock>
  );
}
