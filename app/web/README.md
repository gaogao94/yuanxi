# `app/web` 前端项目说明

本文档只说明 `app/web` 这个前端子项目，帮助新接手的同学快速理解项目结构、页面职责和关键技术点。

## 1. 项目定位

`app/web` 是 `yuanxi` 项目的前端界面，基于 React + Vite 构建，当前主要承载两类页面：

- `Chat`：对话式分析页面，用于输入分析需求、展示分析过程、图表和生成的附件。
- `History`：历史文件与待办页面，用于展示已生成的报告、SOP 和其他历史产物。

整体 UI 风格偏白色卡片式工作台，适合做业务分析、结果展示和后续扩展。

## 2. 技术栈

- React 18
- Vite 6
- TypeScript
- React Router 7
- Tailwind CSS 4
- MUI
- Radix UI
- Lucide React
- Motion
- ECharts + `echarts-for-react`

说明：

- 当前项目已经接入 `ECharts`，用于渲染 `Chat` 页面中的图表。
- `package.json` 里仍保留了 `recharts` 依赖，但当前 `Chat` 页面已改为 `ECharts`，后续是否清理可按实际使用情况决定。

## 3. 启动方式

在 `app/web` 目录下执行：

```bash
npm install
npm run dev
```

默认开发地址通常是：

```text
http://localhost:5175/
```

如果 `5173` 或 `5174` 已被占用，Vite 会自动切换到其他端口。

生产构建命令：

```bash
npm run build
```

## 4. 目录结构

核心目录如下：

```text
app/web/
├── guidelines/
│   └── Guidelines.md
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   └── EChart.tsx
│   │   │   ├── figma/
│   │   │   ├── ui/
│   │   │   └── Layout.tsx
│   │   ├── pages/
│   │   │   ├── Chat.tsx
│   │   │   └── History.tsx
│   │   ├── App.tsx
│   │   └── routes.tsx
│   ├── imports/
│   ├── styles/
│   │   ├── fonts.css
│   │   ├── index.css
│   │   ├── tailwind.css
│   │   └── theme.css
│   └── main.tsx
├── index.html
├── package.json
├── package-lock.json
├── postcss.config.mjs
└── vite.config.ts
```

## 5. 入口关系

前端启动链路如下：

1. `src/main.tsx`
2. `src/app/App.tsx`
3. `src/app/routes.tsx`
4. `src/app/components/Layout.tsx`
5. 具体页面组件（`Chat.tsx` / `History.tsx`）

对应关系：

- `main.tsx`：挂载 React 根节点，并引入全局样式 `src/styles/index.css`
- `App.tsx`：只负责注入 `RouterProvider`
- `routes.tsx`：定义页面路由
- `Layout.tsx`：提供统一页面壳和内容容器

## 6. 页面说明

### 6.1 `Chat.tsx`

这是当前最核心的页面，负责模拟“分析助手”的完整交互体验。

主要职责：

- 展示推荐分析提示词
- 接收用户输入
- 模拟分析过程
- 展示分析步骤和过程说明
- 渲染图表
- 生成并展示附件卡片（如 PPT、SOP）
- 在右侧时间线中回看当前会话内的图表和附件

页面内目前包含较多 UI 和交互逻辑，主要状态有：

- `messages`：对话消息列表
- `prompts`：默认推荐提示词
- `inputText`：输入框内容
- `previewPpt`：PPT 预览抽屉状态

图表相关逻辑：

- 页面内部通过轻量函数把业务数据转换成 `ECharts option`
- 当前内置了两类图表配置：
  - 柱状图：用于展示阶段性指标对比
  - 折线图：用于展示趋势变化

### 6.2 `History.tsx`

该页面展示历史生成结果，目前以静态数据为主，适合作为后续“历史记录中心”的基础页面。

主要职责：

- 搜索历史文件
- 展示不同类型的历史产物卡片
- 区分报告、待办、文档等类型

当前数据写死在页面内部，后续如果接入后端，可将其替换为接口返回数据。

## 7. 组件说明

### 7.1 `Layout.tsx`

用于包裹所有页面内容，提供统一的：

- 整体背景
- 最大宽度
- 圆角白色容器
- 边框和阴影

如果后续新增导航栏、顶部栏或侧边栏，这个文件通常是第一落点。

### 7.2 `components/charts/EChart.tsx`

这是当前新增的通用图表基础组件，负责把 `ECharts option` 渲染到页面上。

组件职责：

- 封装 `echarts-for-react`
- 接收标准 `EChartsOption`
- 支持 `className`
- 支持 `style`
- 支持 `loading`

这个组件不直接耦合任何业务字段，后续其他页面如果需要图表，可以直接复用。

### 7.3 `components/ui/`

这里主要是通用 UI 基础组件，包含：

- 表单类组件
- 弹窗类组件
- 导航类组件
- 表格类组件
- 标签页、抽屉、提示等基础能力

大多数文件属于通用组件层，适合复用，不建议在这里直接写业务逻辑。

### 7.4 `components/figma/`

这里放的是从设计稿生成或适配的组件，目前可以视作设计稿相关辅助层。

## 8. 样式体系

样式入口是：

```text
src/styles/index.css
```

它继续引入：

- `fonts.css`
- `tailwind.css`
- `theme.css`

这意味着当前项目的样式来源主要包括：

- Tailwind 原子类
- 自定义字体
- 项目主题变量

页面里大量使用 `Tailwind className` 直接写结构和视觉，因此看页面样式时，优先从组件 JSX 入手。

## 9. 路由结构

当前路由非常简单：

```text
/          -> Chat
/history   -> History
```

如果后续增加更多业务页面，建议继续在 `src/app/routes.tsx` 中集中管理。

## 10. 配置文件说明

### 10.1 `vite.config.ts`

当前 Vite 配置有几个关键点：

- 使用 React 插件
- 使用 Tailwind 插件
- 配置了 `@` 到 `src` 的路径别名
- 配置了 `figma:asset/` 自定义资源解析器

需要注意：

- React 和 Tailwind 插件都属于必需项，不要随意删除
- `assetsInclude` 当前只允许 `.svg` 和 `.csv`
- 不要把 `.css`、`.tsx`、`.ts` 加到 `assetsInclude`

### 10.2 `package.json`

当前只保留了两个常用脚本：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  }
}
```

说明这个前端项目目前比较轻量，重点在页面原型和交互演示。

## 11. 当前实现特点

这个前端项目目前更偏“高保真交互原型”而不是完整业务系统，主要特点如下：

- 页面体验完整
- 组件资源较丰富
- 业务数据大量采用前端内置 mock
- 页面已经具备后续对接真实接口的结构基础

可以把它理解为：

- 当前阶段：前端分析助手工作台原型
- 下一阶段：逐步替换 mock 数据，接入后端接口和真实分析结果

## 12. 新同学建议阅读顺序

如果你第一次接手这个前端，建议按下面顺序阅读：

1. `package.json`
2. `vite.config.ts`
3. `src/main.tsx`
4. `src/app/App.tsx`
5. `src/app/routes.tsx`
6. `src/app/components/Layout.tsx`
7. `src/app/pages/Chat.tsx`
8. `src/app/pages/History.tsx`
9. `src/app/components/charts/EChart.tsx`
10. `src/app/components/ui/`

这样可以先建立整体认知，再进入具体页面和组件。

## 13. 后续维护建议

- 若 `Chat.tsx` 持续变大，建议把图表 option 构造函数和附件卡片逻辑继续拆分出去
- 若多个页面都开始使用图表，建议在 `components/charts/` 下继续扩展图表组件层
- 若接入真实接口，建议先把页面中的 mock 数据和模拟流程抽离成单独的数据层或 service 层
- 若确认 `recharts` 没有其他页面使用，可后续统一移除相关依赖

## 14. 一句话总结

`app/web` 是一个基于 React + Vite 的诊所分析助手前端工作台，当前核心页面是 `Chat` 和 `History`，页面体验已经较完整，图表层已接入 `ECharts`，后续适合在此基础上逐步对接真实业务数据和接口。
