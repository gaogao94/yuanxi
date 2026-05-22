import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { cn } from "../ui/utils";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../ui/collapsible";

import { WorkflowStatusTag } from "./WorkflowStatusTag";
import type { WorkflowBlockStatus } from "../../types/workflow";

type CollapsibleWorkflowBlockProps = {
  title: string;
  subtitle?: string;
  status: WorkflowBlockStatus;
  defaultOpen?: boolean;
  children: React.ReactNode;
};

export function CollapsibleWorkflowBlock({
  title,
  subtitle,
  status,
  defaultOpen = status === "running",
  children,
}: CollapsibleWorkflowBlockProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="overflow-hidden rounded-[20px] border border-gray-200 bg-[#f8fafd]">
      <CollapsibleTrigger className="flex w-full items-center justify-between gap-4 p-4 text-left cursor-pointer">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800">{title}</span>
            <WorkflowStatusTag status={status} />
          </div>
          {subtitle ? <p className="mt-1 text-sm text-gray-500">{subtitle}</p> : null}
        </div>
        <ChevronDown className={cn("h-4 w-4 text-gray-400 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t border-gray-100 p-4 pt-3">{children}</CollapsibleContent>
    </Collapsible>
  );
}
