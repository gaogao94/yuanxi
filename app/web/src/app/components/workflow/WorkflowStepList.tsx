import { Database, Loader2 } from "lucide-react";

import type { WorkflowStep } from "../../types/workflow";

import { WorkflowStatusTag } from "./WorkflowStatusTag";

type WorkflowStepListProps = {
  steps: WorkflowStep[];
};

export function WorkflowStepList({ steps }: WorkflowStepListProps) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={step.id} className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-600">
                {index + 1}
              </div>
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                  {step.status === "running" ? <Loader2 className="h-4 w-4 animate-spin text-[#1a73e8]" /> : null}
                  {step.title}
                </div>
                {step.detail ? <p className="mt-1 text-sm leading-relaxed text-gray-600">{step.detail}</p> : null}
                {step.source ? (
                  <div className="mt-2 inline-flex items-center gap-1 rounded-md border border-blue-100 bg-[#e8f0fe] px-2 py-1 text-xs font-medium text-[#1a73e8]">
                    <Database className="h-3 w-3" />
                    {step.source}
                  </div>
                ) : null}
              </div>
            </div>
            <WorkflowStatusTag status={step.status} />
          </div>
        </div>
      ))}
    </div>
  );
}
