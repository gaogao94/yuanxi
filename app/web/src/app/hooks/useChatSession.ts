import { useCallback, useMemo, useRef, useState } from "react";

import { sendMessageStream } from "../services/chatApi";
import type { ChatMessage, WorkflowBlockMessage, ChartChatMessage, ArtifactChatMessage, AssistantTextMessage } from "../types/chat";
import type { WorkflowStage, WorkflowStep } from "../types/workflow";
import type { ApiChartData } from "../types/api";
import { buildChartOption } from "../mappers/chartToEcharts";

function mapChartDataToPayload(chartData: ApiChartData, index: number) {
  if (!chartData.data || chartData.data.length === 0) {
    return { id: `chart-${index}`, title: "图表", type: chartData.type as "bar" | "line" | "pie", categories: [], series: [] };
  }
  
  const firstRow = chartData.data[0];
  const keys = Object.keys(firstRow);
  const categoryKey = keys.find(k => typeof firstRow[k] === "string") || keys[0];
  const valueKeys = keys.filter(k => k !== categoryKey);
  
  const categories = chartData.data.map(row => String(row[categoryKey]));
  const series = valueKeys.map(k => ({
    name: k === "value" ? "数值" : k,
    data: chartData.data.map(row => Number(row[k]) || 0),
  }));

  return {
    id: `chart-${index}`,
    title: "数据图表",
    type: chartData.type as "bar" | "line" | "pie",
    categories,
    series,
  };
}

export function useChatSession() {
  const sessionIdRef = useRef<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stage, setStage] = useState<WorkflowStage>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeClarificationId, setActiveClarificationId] = useState<string | null>(null);

  const processStream = useCallback(async (question: string) => {
    setIsSubmitting(true);
    setStage("executing");

    // Add user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      type: "user",
      text: question,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => {
      const updatedPrev = prev.map((msg) => {
        if (msg.type === "workflow_block" && msg.blockKind === "clarification" && msg.status === "running") {
          return { ...msg, status: "completed" };
        }
        return msg;
      });
      return [...updatedPrev, userMsg];
    });
    setActiveClarificationId(null);

    try {
      const stream = sendMessageStream(question, sessionIdRef.current ?? undefined);
      let execBlockId = `exec-${Date.now()}`;
      
      for await (const event of stream) {
        if (event.type === "thinking") {
          const thinkingData = event.data;
          setMessages((prev) => {
            const lastMsg = prev[prev.length - 1];
            const newStep: WorkflowStep = {
              id: `step-${Date.now()}-${Math.random()}`,
              title: thinkingData.text,
              status: "running",
              source: thinkingData.source,
            };

            if (lastMsg?.type === "workflow_block" && lastMsg.blockKind === "execution" && lastMsg.status === "running") {
              const updatedSteps = lastMsg.steps.map(step => ({ ...step, status: "completed" as const }));
              return [...prev.slice(0, -1), { ...lastMsg, steps: [...updatedSteps, newStep] }];
            } else {
              const newBlock: WorkflowBlockMessage = {
                id: execBlockId,
                type: "workflow_block",
                blockKind: "execution",
                status: "running",
                title: "执行中",
                steps: [newStep],
                createdAt: new Date().toISOString(),
              };
              return [...prev, newBlock];
            }
          });
        } else if (event.type === "clarification") {
          const clarificationData = event.data;
          if (clarificationData.conversation_id) {
            sessionIdRef.current = clarificationData.conversation_id;
          }
          setStage("clarifying");
          
          setMessages((prev) => {
            let newMsgs = [...prev];
            // Complete any running execution blocks
            const lastMsg = newMsgs[newMsgs.length - 1];
            if (lastMsg?.type === "workflow_block" && lastMsg.blockKind === "execution" && lastMsg.status === "running") {
              const updatedSteps = lastMsg.steps.map(step => ({ ...step, status: "completed" as const }));
              newMsgs[newMsgs.length - 1] = { ...lastMsg, status: "completed", steps: updatedSteps };
            }

            if (clarificationData.text) {
              newMsgs.push({
                id: `assistant-${Date.now()}`,
                type: "assistant_text",
                text: clarificationData.text,
                createdAt: new Date().toISOString(),
              });
            }

            const clarificationBlocks = (clarificationData.clarification_questions || []).map((q) => ({
              id: `clarification-${q.id}`,
              type: "workflow_block" as const,
              blockKind: "clarification" as const,
              status: "running" as const,
              title: "需要澄清",
              prompt: q.question,
              questionId: q.id,
              options: q.options,
              steps: [],
              createdAt: new Date().toISOString(),
            }));

            if (clarificationBlocks.length > 0) {
              setActiveClarificationId(clarificationBlocks[0].questionId || null);
            }

            return [...newMsgs, ...clarificationBlocks];
          });
        } else if (event.type === "result") {
          const resultData = event.data;
          if (resultData.conversation_id) {
            sessionIdRef.current = resultData.conversation_id;
          }
          setStage("completed");

          setMessages((prev) => {
            let newMsgs = [...prev];
            const lastMsg = newMsgs[newMsgs.length - 1];
            if (lastMsg?.type === "workflow_block" && lastMsg.blockKind === "execution" && lastMsg.status === "running") {
              const updatedSteps = lastMsg.steps.map(step => ({ ...step, status: "completed" as const }));
              newMsgs[newMsgs.length - 1] = { ...lastMsg, status: "completed", steps: updatedSteps };
            }

            if (resultData.text) {
              newMsgs.push({
                id: `assistant-result-${Date.now()}`,
                type: "assistant_text",
                text: resultData.text,
                createdAt: new Date().toISOString(),
              });
            }

            if (resultData.charts && resultData.charts.length > 0) {
              const chartMsgs = resultData.charts.map((chart, index) => {
                const payload = mapChartDataToPayload(chart, index);
                return {
                  id: `chart-${Date.now()}-${index}`,
                  type: "chart" as const,
                  title: payload.title,
                  option: buildChartOption(payload),
                  createdAt: new Date().toISOString(),
                };
              });
              newMsgs.push(...chartMsgs);
            }

            if (resultData.attachments && resultData.attachments.length > 0) {
              newMsgs.push({
                id: `artifact-${Date.now()}`,
                type: "artifact",
                title: "相关附件",
                artifacts: resultData.attachments as any[],
                createdAt: new Date().toISOString(),
              });
            }

            return newMsgs;
          });
        } else if (event.type === "error") {
          const errorData = event.data;
          setStage("failed");
          setMessages((prev) => {
            let newMsgs = [...prev];
            const lastMsg = newMsgs[newMsgs.length - 1];
            if (lastMsg?.type === "workflow_block" && lastMsg.blockKind === "execution" && lastMsg.status === "running") {
              const updatedSteps = lastMsg.steps.map((step, idx) => 
                idx === lastMsg.steps.length - 1 ? { ...step, status: "failed" as const } : { ...step, status: "completed" as const }
              );
              newMsgs[newMsgs.length - 1] = { ...lastMsg, status: "failed", steps: updatedSteps };
            }
            newMsgs.push({
              id: `error-${Date.now()}`,
              type: "error",
              title: "请求失败",
              message: errorData.text || "未知错误",
              createdAt: new Date().toISOString(),
            });
            return newMsgs;
          });
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "请求失败";
      setStage("failed");
      setMessages((prev) => {
        let newMsgs = [...prev];
        const lastMsg = newMsgs[newMsgs.length - 1];
        if (lastMsg?.type === "workflow_block" && lastMsg.blockKind === "execution" && lastMsg.status === "running") {
          const updatedSteps = lastMsg.steps.map((step, idx) => 
            idx === lastMsg.steps.length - 1 ? { ...step, status: "failed" as const } : { ...step, status: "completed" as const }
          );
          newMsgs[newMsgs.length - 1] = { ...lastMsg, status: "failed", steps: updatedSteps };
        }
        newMsgs.push({
          id: `local-error-${Date.now()}`,
          type: "error",
          title: "请求异常",
          message,
          createdAt: new Date().toISOString(),
        });
        return newMsgs;
      });
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const submitQuestion = useCallback(
    (question: string) => {
      return processStream(question);
    },
    [processStream]
  );

  const answerClarification = useCallback(
    (questionId: string, answer: string) => {
      setMessages((prev) => {
        return prev.map((msg) => {
          if (msg.type === "workflow_block" && msg.blockKind === "clarification" && msg.questionId === questionId) {
            return { ...msg, status: "completed", answer };
          }
          return msg;
        });
      });
      return processStream(answer);
    },
    [processStream]
  );

  const refreshSession = useCallback(async () => {
    // Optionally implemented if needed, left empty for now
  }, []);

  return useMemo(
    () => ({
      messages,
      stage,
      isSubmitting,
      activeClarificationId,
      submitQuestion,
      answerClarification,
      refreshSession,
    }),
    [messages, stage, isSubmitting, activeClarificationId, submitQuestion, answerClarification, refreshSession]
  );
}
