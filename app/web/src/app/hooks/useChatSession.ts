import { useCallback, useMemo, useRef, useState } from "react";

import { createChatSession, getChatSession, replyClarification } from "../services/chatApi";
import type { ChatMessage } from "../types/chat";
import type { WorkflowStage } from "../types/workflow";
import { mapSessionToMessages } from "../mappers/workflowToMessages";
import type { ApiChatSession } from "../types/api";

function getActiveClarificationId(session: ApiChatSession): string | null {
  for (let index = session.items.length - 1; index >= 0; index -= 1) {
    const item = session.items[index];
    if (item.kind === "clarification" && item.status === "running") {
      return item.questionId;
    }
  }
  return null;
}

export function useChatSession() {
  const sessionIdRef = useRef<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stage, setStage] = useState<WorkflowStage>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeClarificationId, setActiveClarificationId] = useState<string | null>(null);

  const syncSession = useCallback((session: ApiChatSession) => {
    sessionIdRef.current = session.sessionId;
    setStage(session.stage);
    setMessages(mapSessionToMessages(session));
    setActiveClarificationId(getActiveClarificationId(session));
  }, []);

  const submitQuestion = useCallback(async (question: string) => {
    setIsSubmitting(true);
    try {
      const session = await createChatSession(question);
      syncSession(session);
    } catch (error) {
      const message = error instanceof Error ? error.message : "发送问题失败";
      setStage("failed");
      setMessages((current) => [
        ...current,
        {
          id: `local-error-${Date.now()}`,
          type: "error",
          title: "发送失败",
          message,
        },
      ]);
    } finally {
      setIsSubmitting(false);
    }
  }, [syncSession]);

  const answerClarification = useCallback(async (questionId: string, answer: string) => {
    if (!sessionIdRef.current) {
      return;
    }

    setIsSubmitting(true);
    try {
      const session = await replyClarification(sessionIdRef.current, { questionId, answer });
      syncSession(session);
    } catch (error) {
      const message = error instanceof Error ? error.message : "提交澄清失败";
      setStage("failed");
      setMessages((current) => [
        ...current,
        {
          id: `clarification-error-${Date.now()}`,
          type: "error",
          title: "澄清提交失败",
          message,
        },
      ]);
    } finally {
      setIsSubmitting(false);
    }
  }, [syncSession]);

  const refreshSession = useCallback(async () => {
    if (!sessionIdRef.current) {
      return;
    }

    const session = await getChatSession(sessionIdRef.current);
    syncSession(session);
  }, [syncSession]);

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
    [messages, stage, isSubmitting, activeClarificationId, submitQuestion, answerClarification, refreshSession],
  );
}
