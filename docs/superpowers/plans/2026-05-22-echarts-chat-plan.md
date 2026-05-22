# ECharts Chat 接入实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 `app/web` 引入 `echarts-for-react`，抽离通用 ECharts 基础组件，并在 `Chat.tsx` 中替换现有 demo 图表。

**架构：** 保留 `Chat.tsx` 当前消息和图表数据结构，只替换图表渲染层。新增一个通用 `EChart` 基础组件封装 `echarts-for-react`，页面侧通过轻量 option builder 将柱状图和折线图数据转换为 ECharts option。

**技术栈：** React、Vite、TypeScript、echarts、echarts-for-react

---

### 任务 1：接入图表依赖

**文件：**
- 修改：`/Users/wen/Desktop/myfisrt project/Ai project/yuanxi/app/web/package.json`
- 修改：`/Users/wen/Desktop/myfisrt project/Ai project/yuanxi/app/web/package-lock.json`

- [ ] **步骤 1：在 `package.json` 中新增依赖**

```json
{
  "dependencies": {
    "echarts": "^5.x",
    "echarts-for-react": "^3.x"
  }
}
```

- [ ] **步骤 2：安装依赖并更新锁文件**

运行：`npm install`
预期：生成或更新 `app/web/package-lock.json`，安装 `echarts` 和 `echarts-for-react`

- [ ] **步骤 3：验证依赖已安装**

运行：`npm ls echarts echarts-for-react`
预期：输出已安装版本，不报 `missing`

### 任务 2：新增通用 ECharts 组件

**文件：**
- 创建：`/Users/wen/Desktop/myfisrt project/Ai project/yuanxi/app/web/src/app/components/charts/EChart.tsx`

- [ ] **步骤 1：创建基础组件文件**

```tsx
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

type EChartProps = {
  option: EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  loading?: boolean;
};
```

- [ ] **步骤 2：实现通用包装逻辑**

```tsx
export function EChart({ option, className, style, loading = false }: EChartProps) {
  return (
    <ReactECharts
      option={option}
      notMerge
      lazyUpdate
      showLoading={loading}
      className={className}
      style={{ height: 220, width: "100%", ...style }}
    />
  );
}
```

- [ ] **步骤 3：确保组件不耦合业务**

```tsx
// 不在组件内部判断 bar/line，不读取业务字段，只渲染传入的 option
```

### 任务 3：在 `Chat.tsx` 替换 demo 图表

**文件：**
- 修改：`/Users/wen/Desktop/myfisrt project/Ai project/yuanxi/app/web/src/app/pages/Chat.tsx`

- [ ] **步骤 1：移除 `recharts` import，改为引入 ECharts 组件和类型**

```tsx
import type { EChartsOption } from "echarts";
import { EChart } from "../components/charts/EChart";
```

- [ ] **步骤 2：新增图表 option builder**

```tsx
function buildBarChartOption(data: Array<{ name: string; value: number; ideal?: number }>): EChartsOption {
  return { /* bar option */ };
}

function buildLineChartOption(data: Array<{ name: string; rate: number }>): EChartsOption {
  return { /* line option */ };
}
```

- [ ] **步骤 3：在消息渲染区替换图表 JSX**

```tsx
{step.chart && (
  <div className="ml-6 mr-2 rounded-xl border border-gray-100 bg-white p-3 shadow-sm">
    <EChart option={step.chart.type === "bar" ? buildBarChartOption(step.chart.data) : buildLineChartOption(step.chart.data)} />
  </div>
)}
```

- [ ] **步骤 4：保留原消息结构和业务流程**

```tsx
chart: {
  type: "bar",
  data: [...]
}
```

### 任务 4：验证与收尾

**文件：**
- 修改：`/Users/wen/Desktop/myfisrt project/Ai project/yuanxi/.agents/ACTIVE_WORK.md`
- 修改：`/Users/wen/Desktop/myfisrt project/Ai project/yuanxi/.agents/CHANGELOG.md`

- [ ] **步骤 1：获取编辑器诊断**

运行：获取 `Chat.tsx` 和 `EChart.tsx` 的 diagnostics
预期：无新增 TypeScript 错误

- [ ] **步骤 2：启动前端并验证页面可运行**

运行：`npm run dev -- --host 0.0.0.0`
预期：Vite 正常启动，图表区域可渲染

- [ ] **步骤 3：记录协作信息**

```md
- 前端影响：Chat 页面改为通过 ECharts 渲染分析过程图表
- 配置影响：新增 `echarts` 和 `echarts-for-react` 依赖
```

- [ ] **步骤 4：Commit**

```bash
git add app/web/package.json app/web/package-lock.json app/web/src/app/components/charts/EChart.tsx app/web/src/app/pages/Chat.tsx .agents/ACTIVE_WORK.md .agents/CHANGELOG.md docs/superpowers/specs/2026-05-22-echarts-chat-design.md docs/superpowers/plans/2026-05-22-echarts-chat-plan.md
git commit -m "feat: replace chat demo charts with echarts"
```
