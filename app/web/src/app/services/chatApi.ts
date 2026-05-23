import type { ApiStreamEvent } from "../types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? "";

/**
 * Sends a message to the backend via SSE stream and yields events.
 * 
 * @param question The user's input (question or clarification answer)
 * @param conversationId The session ID for multi-turn conversations (optional)
 */
export async function* sendMessageStream(
  question: string,
  conversationId?: string
): AsyncGenerator<ApiStreamEvent, void, unknown> {
  const url = `${API_BASE_URL}/api/chat/stream`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("ReadableStream not yet supported in this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let newlineIndex;
      while ((newlineIndex = buffer.indexOf("\n\n")) >= 0) {
        const chunk = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 2);

        const lines = chunk.split("\n");
        let event = "message";
        let data = "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            event = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            data = line.slice(5).trim();
          }
        }

        if (event === "done") {
          yield { type: "done", data: {} } as ApiStreamEvent;
        } else if (data) {
          try {
            const parsed = JSON.parse(data);
            yield { type: event, data: parsed } as ApiStreamEvent;
          } catch (e) {
            console.error("Error parsing SSE data:", data, e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

