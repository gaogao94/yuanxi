/**
 * yuanxi Chat API 客户端
 *
 * 封装与后端 /api/chat 的通信逻辑。
 */

// ── 类型定义 ──────────────────────────────────────────────

export interface ClarificationQuestion {
  id: string;
  question: string;
  type: "single_select" | "free_text";
  options: string[];
  required: boolean;
  source: string;
}

export interface ChartData {
  type: "bar" | "line" | "pie";
  data: Array<{ name: string; value?: number; rate?: number; ideal?: number }>;
}

export interface ThinkingStep {
  text: string;
  source?: string;
  chart?: ChartData;
}

export interface Attachment {
  id: string;
  type: "ppt" | "todo" | "html_report";
  title: string;
  size: string;
  preview: string[];
  url?: string;
}

export interface ChatResponse {
  status: "needs_clarification" | "completed" | "error";
  conversation_id: string;
  text: string;
  clarification_questions: ClarificationQuestion[];
  thinking: ThinkingStep[];
  charts: ChartData[];
  attachments: Attachment[];
}

export interface ChatRequest {
  question: string;
  conversation_id?: string;
}

// ── API 调用 ──────────────────────────────────────────────

const API_BASE = "/api";

export async function sendChatMessage(
  question: string,
  conversationId?: string
): Promise<ChatResponse> {
  const body: ChatRequest = { question };
  if (conversationId) {
    body.conversation_id = conversationId;
  }

  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errorDetail = await res.text();
    throw new Error(`API error ${res.status}: ${errorDetail}`);
  }

  return res.json();
}

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}
