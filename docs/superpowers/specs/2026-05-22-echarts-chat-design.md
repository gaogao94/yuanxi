# ECharts Chat Design

## 背景

`app/web/src/app/pages/Chat.tsx` 当前用 `recharts` 渲染柱状图和折线图，但这些图表只用于 demo。用户希望前端后续直接接入 `ECharts`，并且先沉淀一个可复用的图表组件，再在 `Chat.tsx` 中落地。

## 目标

- 在 `app/web` 中新增 `echarts` 和 `echarts-for-react` 依赖。
- 抽离一个可复用的 ECharts 基础组件，供后续多个页面共享。
- 将 `Chat.tsx` 中现有的 demo 柱状图和折线图改为通过 ECharts 渲染。
- 保持当前消息流、分析流、附件流不变，只替换图表展示实现。

## 非目标

- 不做全站 `recharts` 到 `ECharts` 的统一迁移。
- 不删除现有 `recharts` 依赖，避免影响代码库其他位置。
- 不引入全局图表主题系统，只满足当前页面视觉和复用需求。

## 方案

### 依赖层

在 `app/web/package.json` 中新增：

- `echarts`
- `echarts-for-react`

安装后更新 `app/web/package-lock.json`。

### 组件层

新增 `app/web/src/app/components/charts/EChart.tsx`，作为通用封装组件。

职责：

- 接收标准 `EChartsOption`
- 透传 `className`、`style`、`loading`
- 统一默认高度和 `notMerge`/`lazyUpdate` 等安全默认值
- 对外暴露一个稳定的 React 组件接口，屏蔽 `echarts-for-react` 的初始化细节

不在组件内耦合任何业务字段或图表类型判断。

### 页面层

修改 `app/web/src/app/pages/Chat.tsx`：

- 删除 `recharts` 相关 import
- 保留现有 `step.chart = { type, data }` 的消息结构
- 在页面文件中新增两个轻量 option 构造函数：
  - `buildBarChartOption(data)`
  - `buildLineChartOption(data)`
- 分析过程中的图表区域改为：
  - 根据 `step.chart.type` 构造 `option`
  - 使用通用 `EChart` 组件渲染

### 样式层

维持当前页面风格：

- 白色图表容器
- 浅灰网格线
- 蓝色主柱状图
- 低于阈值的柱子使用红色强调
- 绿色趋势折线
- 简洁 tooltip 和坐标轴样式

### 数据映射

柱状图数据保持兼容现有结构：

```ts
{ name: string; value: number; ideal?: number }
```

折线图数据保持兼容现有结构：

```ts
{ name: string; rate: number }
```

如果后续图表种类增加，再将 option builder 抽离到独立文件；当前不提前设计。

## 风险与权衡

- `Chat.tsx` 当前文件较大，但这次只替换图表层，避免顺带做无关重构。
- `echarts` 包体积比 demo 图表更大，但对当前页面场景可接受。
- 先保留 `recharts` 依赖，等确认没有其他页面使用后再统一清理，避免误伤。

## 验证

- `npm install` 成功安装新依赖
- `npm run dev` 可正常启动
- `Chat.tsx` 无 TypeScript/编辑器诊断错误
- 页面中的柱状图和折线图区域能正常渲染，不再依赖 `recharts`
