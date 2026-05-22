# Chat 工作流接入实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 `app/web/src/app/pages/Chat.tsx` 从本地 mock 演示页重构为可接完整多 Agent 主流程的单线程聊天工作台，支持可折叠的澄清块、执行进度块、审核块、图表消息和附件消息。

**架构：** 保留当前单页聊天布局，把业务状态和接口调用从 `Chat.tsx` 中抽离到 `types`、`services`、`hooks`、`mappers` 和小型展示组件。页面只负责组装输入框、消息流和预览抽屉，后端返回的工作流数据统一先转换为前端消息模型，再渲染为文本、折叠块、图表和附件卡片。

**技术栈：** React 18、TypeScript、Vite 6、Tailwind CSS、Radix Collapsible、ECharts、现有 `ui/` 组件。

---

## 文件结构

### 创建

- `app/web/src/app/types/api.ts`：前后端会话、事件、图表、附件的接口类型。
- `app/web/src/app/types/chat.ts`：前端聊天消息模型和渲染所需联合类型。
- `app/web/src/app/types/workflow.ts`：工作流阶段状态、步骤状态和辅助枚举。
- `app/web/src/app/services/chatApi.ts`：会话创建、澄清回答、会话查询的 HTTP 封装。
- `app/web/src/app/mappers/chartToEcharts.ts`：把后端图表结构转成 `EChartsOption`。
- `app/web/src/app/mappers/workflowToMessages.ts`：把会话快照和事件流转成聊天消息数组。
- `app/web/src/app/hooks/useChatSession.ts`：管理会话状态、消息流和发送 / 回答逻辑。
- `app/web/src/app/components/chat/ChatComposer.tsx`：输入框和发送按钮。
- `app/web/src/app/components/chat/ChatMessageList.tsx`：聊天流容器和消息类型分发。
- `app/web/src/app/components/chat/UserMessageBubble.tsx`：用户消息气泡。
- `app/web/src/app/components/chat/AssistantMessageBubble.tsx`：普通文本消息气泡。
- `app/web/src/app/components/workflow/CollapsibleWorkflowBlock.tsx`：通用可折叠流程块。
- `app/web/src/app/components/workflow/ClarificationBlock.tsx`：澄清问题块。
- `app/web/src/app/components/workflow/ExecutionProgressBlock.tsx`：执行进度块。
- `app/web/src/app/components/workflow/ReviewBlock.tsx`：审核块。
- `app/web/src/app/components/workflow/WorkflowStepList.tsx`：步骤列表。
- `app/web/src/app/components/workflow/WorkflowStatusTag.tsx`：阶段状态标签。
- `app/web/src/app/components/workflow/ArtifactMessageCard.tsx`：附件 / 报告卡片。
- `app/web/src/app/components/workflow/ErrorMessageCard.tsx`：错误卡片。
- `app/web/src/app/components/charts/ChartMessageCard.tsx`：图表消息卡片。

### 修改

- `app/web/src/app/pages/Chat.tsx`：移除本地 mock 工作流，改为组装真实会话 hook 和消息组件。
- `app/web/src/app/components/charts/EChart.tsx`：如有必要，只补充最小 props 支持；不引入业务逻辑。

### 验证

- `app/web/package.json`：确认仍使用现有 `build` / `dev` 脚本。

## 任务 1：定义工作流与消息类型

**文件：**
- 创建：`app/web/src/app/types/api.ts`
- 创建：`app/web/src/app/types/chat.ts`
- 创建：`app/web/src/app/types/workflow.ts`

- [ ] **步骤 1：定义工作流阶段和步骤状态**

```ts
export type WorkflowStage =
  | "idle"
  | "clarifying"
  | "ready_to_execute"
  | "executing"
  | "reviewing"
  | "completed"
  | "blocked"
  | "failed";

export type WorkflowStepStatus = "pending" | "running" | "completed" | "failed";
```

- [ ] **步骤 2：定义后端接口返回类型**

```ts
export type ApiWorkflowStep = {
  id: string;
  title: string;
  status: WorkflowStepStatus;
  detail?: string;
};

export type ApiChartPayload = {
  id: string;
  type: "bar" | "line";
  title: string;
  categories: string[];
  series: Array<{ name: string; data: number[] }>;
  unit?: string;
};
```

- [ ] **步骤 3：定义前端聊天消息联合类型**

```ts
export type ChatMessage =
  | UserChatMessage
  | AssistantTextMessage
  | WorkflowBlockMessage
  | ChartChatMessage
  | ArtifactChatMessage
  | ErrorChatMessage;
```

- [ ] **步骤 4：运行构建确认类型文件不引入错误**

运行：`npm run build`
预期：PASS，构建仍通过，类型文件没有语法错误。

- [ ] **步骤 5：Commit**

```bash
git add app/web/src/app/types/api.ts app/web/src/app/types/chat.ts app/web/src/app/types/workflow.ts
git commit -m "feat: add chat workflow types"
```

## 任务 2：搭建 API 层和数据映射层

**文件：**
- 创建：`app/web/src/app/services/chatApi.ts`
- 创建：`app/web/src/app/mappers/chartToEcharts.ts`
- 创建：`app/web/src/app/mappers/workflowToMessages.ts`
- 依赖：`app/web/src/app/types/api.ts`
- 依赖：`app/web/src/app/types/chat.ts`

- [ ] **步骤 1：实现 API 客户端最小骨架**

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function createChatSession(question: string) {
  return request<ApiSessionResponse>("/api/chat/session", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
```

- [ ] **步骤 2：实现图表数据到 ECharts 的映射函数**

```ts
export function buildChartOption(chart: ApiChartPayload): EChartsOption {
  if (chart.type === "bar") {
    return buildBarOption(chart);
  }

  return buildLineOption(chart);
}
```

- [ ] **步骤 3：实现会话快照到消息数组的映射**

```ts
export function mapSessionToMessages(session: ApiChatSession): ChatMessage[] {
  return session.items.flatMap((item) => mapSessionItem(item));
}
```

- [ ] **步骤 4：运行构建验证服务层和 mapper 可编译**

运行：`npm run build`
预期：PASS，新增服务层和 mapper 不报错。

- [ ] **步骤 5：Commit**

```bash
git add app/web/src/app/services/chatApi.ts app/web/src/app/mappers/chartToEcharts.ts app/web/src/app/mappers/workflowToMessages.ts
git commit -m "feat: add chat api and workflow mappers"
```

## 任务 3：实现会话 hook

**文件：**
- 创建：`app/web/src/app/hooks/useChatSession.ts`
- 依赖：`app/web/src/app/services/chatApi.ts`
- 依赖：`app/web/src/app/mappers/workflowToMessages.ts`
- 依赖：`app/web/src/app/types/chat.ts`
- 依赖：`app/web/src/app/types/workflow.ts`

- [ ] **步骤 1：定义 hook 的状态结构**

```ts
type UseChatSessionResult = {
  messages: ChatMessage[];
  stage: WorkflowStage;
  isSubmitting: boolean;
  submitQuestion: (question: string) => Promise<void>;
  answerClarification: (questionId: string, answer: string) => Promise<void>;
};
```

- [ ] **步骤 2：实现发送问题逻辑**

```ts
const submitQuestion = useCallback(async (question: string) => {
  setIsSubmitting(true);
  try {
    const session = await createChatSession(question);
    setStage(session.stage);
    setMessages(mapSessionToMessages(session));
  } finally {
    setIsSubmitting(false);
  }
}, []);
```

- [ ] **步骤 3：实现回答澄清逻辑**

```ts
const answerClarification = useCallback(async (questionId: string, answer: string) => {
  if (!sessionIdRef.current) return;
  const session = await replyClarification(sessionIdRef.current, { questionId, answer });
  setStage(session.stage);
  setMessages(mapSessionToMessages(session));
}, []);
```

- [ ] **步骤 4：运行构建验证 hook 类型闭环**

运行：`npm run build`
预期：PASS，`useChatSession` 可被页面消费。

- [ ] **步骤 5：Commit**

```bash
git add app/web/src/app/hooks/useChatSession.ts
git commit -m "feat: add chat session hook"
```

## 任务 4：实现聊天基础组件

**文件：**
- 创建：`app/web/src/app/components/chat/ChatComposer.tsx`
- 创建：`app/web/src/app/components/chat/ChatMessageList.tsx`
- 创建：`app/web/src/app/components/chat/UserMessageBubble.tsx`
- 创建：`app/web/src/app/components/chat/AssistantMessageBubble.tsx`
- 依赖：`app/web/src/app/types/chat.ts`

- [ ] **步骤 1：实现输入组件**

```tsx
export function ChatComposer({ value, onChange, onSubmit, disabled }: ChatComposerProps) {
  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <textarea value={value} onChange={(event) => onChange(event.target.value)} />
      <button type="submit" disabled={disabled}>发送</button>
    </form>
  );
}
```

- [ ] **步骤 2：实现用户和助手气泡组件**

```tsx
export function UserMessageBubble({ message }: { message: UserChatMessage }) {
  return <div className="ml-auto max-w-[80%] rounded-2xl bg-blue-600 px-4 py-3 text-white">{message.text}</div>;
}
```

- [ ] **步骤 3：实现消息列表分发逻辑**

```tsx
export function ChatMessageList({ messages }: ChatMessageListProps) {
  return messages.map((message) => renderMessage(message));
}
```

- [ ] **步骤 4：运行构建验证基础聊天组件**

运行：`npm run build`
预期：PASS，基础消息组件可编译。

- [ ] **步骤 5：Commit**

```bash
git add app/web/src/app/components/chat/ChatComposer.tsx app/web/src/app/components/chat/ChatMessageList.tsx app/web/src/app/components/chat/UserMessageBubble.tsx app/web/src/app/components/chat/AssistantMessageBubble.tsx
git commit -m "feat: add chat presentation components"
```

## 任务 5：实现工作流块、图表卡片和附件卡片

**文件：**
- 创建：`app/web/src/app/components/workflow/CollapsibleWorkflowBlock.tsx`
- 创建：`app/web/src/app/components/workflow/WorkflowStepList.tsx`
- 创建：`app/web/src/app/components/workflow/WorkflowStatusTag.tsx`
- 创建：`app/web/src/app/components/workflow/ClarificationBlock.tsx`
- 创建：`app/web/src/app/components/workflow/ExecutionProgressBlock.tsx`
- 创建：`app/web/src/app/components/workflow/ReviewBlock.tsx`
- 创建：`app/web/src/app/components/workflow/ArtifactMessageCard.tsx`
- 创建：`app/web/src/app/components/workflow/ErrorMessageCard.tsx`
- 创建：`app/web/src/app/components/charts/ChartMessageCard.tsx`
- 依赖：`app/web/src/app/components/ui/collapsible.tsx`
- 依赖：`app/web/src/app/components/charts/EChart.tsx`

- [ ] **步骤 1：实现通用可折叠流程块**

```tsx
export function CollapsibleWorkflowBlock({ title, subtitle, defaultOpen, children }: Props) {
  return (
    <Collapsible defaultOpen={defaultOpen}>
      <CollapsibleTrigger>{title}</CollapsibleTrigger>
      <CollapsibleContent>{children}</CollapsibleContent>
    </Collapsible>
  );
}
```

- [ ] **步骤 2：实现澄清块和执行进度块**

```tsx
export function ExecutionProgressBlock({ message }: { message: WorkflowBlockMessage }) {
  return (
    <CollapsibleWorkflowBlock title={message.title} subtitle={message.subtitle} defaultOpen={message.status === "running"}>
      <WorkflowStepList steps={message.steps} />
    </CollapsibleWorkflowBlock>
  );
}
```

- [ ] **步骤 3：实现图表卡片和附件卡片**

```tsx
export function ChartMessageCard({ message }: { message: ChartChatMessage }) {
  return <EChart option={message.option} className="rounded-2xl border border-gray-200 bg-white" />;
}
```

- [ ] **步骤 4：运行构建验证所有渲染组件**

运行：`npm run build`
预期：PASS，可折叠块、图表卡片、附件卡片均可编译。

- [ ] **步骤 5：Commit**

```bash
git add app/web/src/app/components/workflow/CollapsibleWorkflowBlock.tsx app/web/src/app/components/workflow/WorkflowStepList.tsx app/web/src/app/components/workflow/WorkflowStatusTag.tsx app/web/src/app/components/workflow/ClarificationBlock.tsx app/web/src/app/components/workflow/ExecutionProgressBlock.tsx app/web/src/app/components/workflow/ReviewBlock.tsx app/web/src/app/components/workflow/ArtifactMessageCard.tsx app/web/src/app/components/workflow/ErrorMessageCard.tsx app/web/src/app/components/charts/ChartMessageCard.tsx
git commit -m "feat: add workflow and chart message components"
```

## 任务 6：重构 Chat 页面接入新架构

**文件：**
- 修改：`app/web/src/app/pages/Chat.tsx`
- 依赖：`app/web/src/app/hooks/useChatSession.ts`
- 依赖：`app/web/src/app/components/chat/ChatComposer.tsx`
- 依赖：`app/web/src/app/components/chat/ChatMessageList.tsx`

- [ ] **步骤 1：移除页面内的本地 mock 消息与图表 builder**

```tsx
// 删除 DEFAULT_PROMPTS 之外的 mock 工作流拼接逻辑：
// - buildBarChartOption
// - buildLineChartOption
// - handleSend 中的 setTimeout 模拟分析
```

- [ ] **步骤 2：接入 useChatSession 和新组件**

```tsx
const { messages, stage, isSubmitting, submitQuestion, answerClarification } = useChatSession();

<ChatMessageList messages={messages} onClarificationAnswer={answerClarification} />
<ChatComposer
  value={inputText}
  onChange={setInputText}
  onSubmit={() => submitQuestion(inputText)}
  disabled={isSubmitting || stage === "executing" || stage === "reviewing"}
/>
```

- [ ] **步骤 3：保留并收敛页面级特殊 UI**

```tsx
// 保留：
// - 推荐 prompts
// - 历史记录侧栏
// - PPT 预览抽屉
// 但它们不再驱动主工作流，只做辅助入口和预览。
```

- [ ] **步骤 4：运行构建和诊断检查**

运行：`npm run build`
预期：PASS，`Chat.tsx` 能通过构建。

运行：`GetDiagnostics(file:///Users/wen/Desktop/myfisrt%20project/Ai%20project/yuanxi/app/web/src/app/pages/Chat.tsx)`
预期：无新增错误诊断；如有警告仅限已有过时 API 提示。

- [ ] **步骤 5：Commit**

```bash
git add app/web/src/app/pages/Chat.tsx
git commit -m "feat: refactor chat page for workflow integration"
```

## 任务 7：集成验证

**文件：**
- 验证：`app/web/package.json`
- 验证：`app/web/src/app/pages/Chat.tsx`
- 验证：`app/web/src/app/components/`
- 验证：`app/web/src/app/hooks/`

- [ ] **步骤 1：执行完整构建验证**

运行：`npm run build`
预期：PASS，前端可完整打包。

- [ ] **步骤 2：检查近期修改文件诊断**

运行：`GetDiagnostics` 针对以下文件：

```text
app/web/src/app/pages/Chat.tsx
app/web/src/app/hooks/useChatSession.ts
app/web/src/app/components/chat/ChatMessageList.tsx
app/web/src/app/components/workflow/ExecutionProgressBlock.tsx
app/web/src/app/components/charts/ChartMessageCard.tsx
```

预期：无新增错误诊断。

- [ ] **步骤 3：手工验证聊天主链路**

运行：打开本地开发服务 `http://localhost:5175/`
预期：
- 发送问题后出现用户消息
- 当返回澄清块时可展开 / 折叠
- 当返回执行块时可展开 / 折叠
- 图表消息能显示
- 附件卡片能显示

- [ ] **步骤 4：检查 git 工作区**

运行：`git status --short`
预期：只包含本次计划涉及的前端文件和必要文档变更。

- [ ] **步骤 5：Commit**

```bash
git add app/web
git commit -m "feat: integrate chat workflow ui"
```

## 自检结果

- 规格覆盖度：已覆盖消息模型、状态机、API 层、hook、聊天组件、工作流组件、图表和最终页面接入，没有遗漏你刚确认的“单线程聊天 + 可折叠澄清 / 进度”要求。
- 占位符扫描：计划中没有使用“TODO”“待补充”“后续实现”等占位描述，每个任务都给出文件路径、代码骨架和验证命令。
- 类型一致性：全计划统一使用 `ChatMessage`、`WorkflowStage`、`ApiChatSession`、`ChartMessageCard`、`useChatSession` 这些名称，没有前后命名漂移。
