import type { WorkflowBlockMessage } from "../../types/chat";

import { CollapsibleWorkflowBlock } from "./CollapsibleWorkflowBlock";
import { WorkflowStepList } from "./WorkflowStepList";

export function ReviewBlock({ message }: { message: WorkflowBlockMessage }) {
  return (
    <CollapsibleWorkflowBlock
      title={message.title}
      subtitle={message.subtitle}
      status={message.status}
      defaultOpen={false}
    >
      <WorkflowStepList steps={message.steps} />
    </CollapsibleWorkflowBlock>
  );
}
