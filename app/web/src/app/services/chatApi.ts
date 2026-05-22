import type {
  ApiArtifact,
  ApiChartPayload,
  ApiChatSession,
  ApiSessionItem,
  ReplyClarificationInput,
} from "../types/api";
import type { WorkflowStage, WorkflowStep } from "../types/workflow";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? "";

type MockSessionState = {
  sessionId: string;
  question: string;
  clinicName: string;
  wantsReport: boolean;
  clarificationQuestionId: string;
  clarificationPrompt: string;
  clarificationOptions: string[];
  selectedFocus?: string;
};

const mockSessions = new Map<string, MockSessionState>();

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function createStep(id: string, title: string, status: WorkflowStep["status"], detail?: string): WorkflowStep {
  return { id, title, status, detail };
}

function createChart(id: string, title: string, type: ApiChartPayload["type"], categories: string[], series: ApiChartPayload["series"], description?: string): ApiChartPayload {
  return { id, title, type, categories, series, description };
}

function inferClinicName(question: string): string {
  if (question.includes("仙乐斯")) return "仙乐斯店";
  if (question.includes("大宁")) return "大宁店";
  if (question.includes("徐汇")) return "徐汇店";
  return "全部门诊";
}

function buildClarificationOptions(question: string): string[] {
  if (question.includes("续卡") || question.includes("复诊")) {
    return ["深挖服务体验与候诊时长", "深挖价格与项目转化问题", "全面综合分析并输出行动方案"];
  }

  if (question.includes("报告") || question.includes("PPT")) {
    return ["重点看经营概览和核心指标", "重点看问题归因和优化建议", "先给完整结论再附带报告"];
  }

  return ["先补齐业务口径再分析", "直接进入完整分析流程", "聚焦异常指标与行动建议"];
}

function buildClarificationPrompt(question: string, clinicName: string): string {
  return `我已识别到问题范围与门店：${clinicName}。为了让最终结果更可执行，您更希望我优先从哪个方向深入分析“${question}”？`;
}

function buildExecutionItems(state: MockSessionState): ApiSessionItem[] {
  const clinicName = state.clinicName;
  const focus = state.selectedFocus ?? "全面综合分析并输出行动方案";

  const executionSteps: WorkflowStep[] = [
    createStep("graph", "图谱校验业务范围", "completed", `已确认 ${clinicName} 的指标口径与关系边界。`),
    createStep("fetch", "拉取经营与就诊数据", "completed", `已提取 ${clinicName} 最近 30 天的核心业务数据。`),
    createStep("analyze", "生成趋势与归因分析", "completed", `围绕“${focus}”完成趋势、拆解和归因。`),
    createStep("visualize", "生成图表与报告资产", "completed", "已生成图表与可预览的报告附件。"),
  ];

  const reviewSteps: WorkflowStep[] = [
    createStep("scope", "审核分析范围", "completed", "分析范围、时间口径和门店范围均已确认。"),
    createStep("result", "审核结论与建议", "completed", "结论与建议已对齐当前问题。"),
  ];

  const barChart = createChart(
    `${state.sessionId}-bar`,
    `${clinicName} 关键指标周对比`,
    "bar",
    ["第 1 周", "第 2 周", "第 3 周", "第 4 周"],
    [
      { name: "转化率", data: [84, 81, 69, 73] },
      { name: "目标线", data: [90, 90, 90, 90] },
    ],
    "用于展示近 4 周关键指标与目标线的差异。",
  );

  const lineChart = createChart(
    `${state.sessionId}-line`,
    `${clinicName} 改进动作后的趋势预估`,
    "line",
    ["现状", "1 周", "2 周", "1 个月"],
    [{ name: "流失率", data: [12, 9, 6, 4] }],
    "用于展示执行优化动作后的趋势预估。",
  );

  const artifacts: ApiArtifact[] = [
    {
      id: `${state.sessionId}-report`,
      type: "report",
      title: `${clinicName} 经营分析报告.html`,
      size: "在线报告",
      createdAt: "刚刚",
      preview: [
        `报告摘要：${clinicName} 当前主要问题集中在「${focus}」。`,
        "建议优先处理高影响、低成本的动作，并持续跟踪近 4 周指标变化。",
      ],
    },
    state.wantsReport
      ? {
          id: `${state.sessionId}-ppt`,
          type: "ppt",
          title: `${clinicName} 深度分析汇报.pptx`,
          size: "3.2 MB",
          createdAt: "刚刚",
          preview: [
            `幻灯片 1：${clinicName} 现状综述`,
            `幻灯片 2：围绕「${focus}」的归因与策略。`,
          ],
        }
      : {
          id: `${state.sessionId}-todo`,
          type: "todo",
          title: `${clinicName} 执行待办 SOP`,
          size: "4 项待办",
          createdAt: "刚刚",
          preview: [
            "[ ] 每周复盘异常指标并跟踪责任人",
            "[ ] 优化候诊与分诊提醒流程",
            "[ ] 针对高客单项目补充分期与话术支持",
            "[ ] 2 周后复查执行效果并更新报告",
          ],
        },
  ];

  return [
    {
      id: `${state.sessionId}-assistant-summary`,
      kind: "assistant_message",
      text: `已收到您的偏好：「${focus}」。我已完成 ${clinicName} 的多 Agent 分析流程，下面是本次执行过程、关键图表和输出资产。`,
    },
    {
      id: `${state.sessionId}-execution`,
      kind: "progress",
      blockKind: "execution",
      title: "执行进度",
      subtitle: "图谱查询、取数、分析和可视化已完成",
      status: "completed",
      steps: executionSteps,
    },
    {
      id: `${state.sessionId}-bar-chart`,
      kind: "chart",
      title: barChart.title,
      description: barChart.description,
      chart: barChart,
    },
    {
      id: `${state.sessionId}-line-chart`,
      kind: "chart",
      title: lineChart.title,
      description: lineChart.description,
      chart: lineChart,
    },
    {
      id: `${state.sessionId}-review`,
      kind: "review",
      blockKind: "review",
      title: "审核结果",
      subtitle: "Agent1 已完成结果审核",
      status: "completed",
      steps: reviewSteps,
    },
    {
      id: `${state.sessionId}-final`,
      kind: "assistant_message",
      text: `${clinicName} 当前最值得优先处理的是「${focus}」。从近 30 天数据看，指标下滑主要发生在第 3 周后半段；如果按建议动作落地，预计 1 个月内可以把高风险流失率从 12% 压低到 4%-6%。`,
    },
    {
      id: `${state.sessionId}-artifacts`,
      kind: "artifact",
      title: "已生成的附件",
      artifacts,
    },
  ];
}

function buildClarificationSession(question: string): ApiChatSession {
  const sessionId = `mock-${Date.now()}`;
  const clinicName = inferClinicName(question);
  const clarificationQuestionId = `${sessionId}-clarification`;
  const wantsReport = question.includes("报告") || question.includes("PPT");
  const clarificationOptions = buildClarificationOptions(question);

  const state: MockSessionState = {
    sessionId,
    question,
    clinicName,
    wantsReport,
    clarificationQuestionId,
    clarificationPrompt: buildClarificationPrompt(question, clinicName),
    clarificationOptions,
  };

  mockSessions.set(sessionId, state);

  return {
    sessionId,
    stage: "clarifying",
    items: [
      {
        id: `${sessionId}-user`,
        kind: "user_message",
        text: question,
      },
      {
        id: `${sessionId}-assistant-intro`,
        kind: "assistant_message",
        text: `收到，我会按完整主流程分析 ${clinicName} 的这次问题。开始执行前，我先确认一下您的关注重点。`,
      },
      {
        id: `${sessionId}-clarification-item`,
        kind: "clarification",
        blockKind: "clarification",
        title: "澄清问题",
        subtitle: "请先确认本轮分析的优先方向",
        status: "running",
        questionId: clarificationQuestionId,
        prompt: state.clarificationPrompt,
        options: clarificationOptions,
      },
    ],
  };
}

function buildCompletedSession(state: MockSessionState): ApiChatSession {
  return {
    sessionId: state.sessionId,
    stage: "completed",
    items: [
      {
        id: `${state.sessionId}-user`,
        kind: "user_message",
        text: state.question,
      },
      {
        id: `${state.sessionId}-clarification-completed`,
        kind: "clarification",
        blockKind: "clarification",
        title: "澄清问题",
        subtitle: "已确认本轮分析优先方向",
        status: "completed",
        questionId: state.clarificationQuestionId,
        prompt: state.clarificationPrompt,
        options: state.clarificationOptions,
        answer: state.selectedFocus,
      },
      ...buildExecutionItems(state),
    ],
  };
}

async function createMockChatSession(question: string): Promise<ApiChatSession> {
  return buildClarificationSession(question);
}

async function replyMockClarification(sessionId: string, input: ReplyClarificationInput): Promise<ApiChatSession> {
  const state = mockSessions.get(sessionId);
  if (!state || state.clarificationQuestionId !== input.questionId) {
    throw new Error("Session not found");
  }

  state.selectedFocus = input.answer;
  mockSessions.set(sessionId, state);
  return buildCompletedSession(state);
}

async function getMockChatSession(sessionId: string): Promise<ApiChatSession> {
  const state = mockSessions.get(sessionId);
  if (!state) {
    throw new Error("Session not found");
  }

  if (state.selectedFocus) {
    return buildCompletedSession(state);
  }

  return {
    sessionId: state.sessionId,
    stage: "clarifying",
    items: [
      {
        id: `${state.sessionId}-user`,
        kind: "user_message",
        text: state.question,
      },
      {
        id: `${state.sessionId}-clarification-item`,
        kind: "clarification",
        blockKind: "clarification",
        title: "澄清问题",
        subtitle: "等待用户补充方向",
        status: "running",
        questionId: state.clarificationQuestionId,
        prompt: state.clarificationPrompt,
        options: state.clarificationOptions,
      },
    ],
  };
}

export async function createChatSession(question: string): Promise<ApiChatSession> {
  if (!API_BASE_URL) {
    return createMockChatSession(question);
  }

  try {
    return await requestJson<ApiChatSession>("/api/chat/session", {
      method: "POST",
      body: JSON.stringify({ question }),
    });
  } catch (error) {
    console.warn("Falling back to mock chat session", error);
    return createMockChatSession(question);
  }
}

export async function replyClarification(sessionId: string, input: ReplyClarificationInput): Promise<ApiChatSession> {
  if (!API_BASE_URL) {
    return replyMockClarification(sessionId, input);
  }

  try {
    return await requestJson<ApiChatSession>(`/api/chat/session/${sessionId}/reply`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  } catch (error) {
    console.warn("Falling back to mock clarification flow", error);
    return replyMockClarification(sessionId, input);
  }
}

export async function getChatSession(sessionId: string): Promise<ApiChatSession> {
  if (!API_BASE_URL) {
    return getMockChatSession(sessionId);
  }

  try {
    return await requestJson<ApiChatSession>(`/api/chat/session/${sessionId}`);
  } catch (error) {
    console.warn("Falling back to mock session snapshot", error);
    return getMockChatSession(sessionId);
  }
}
