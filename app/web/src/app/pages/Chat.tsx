import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  Activity,
  Calendar,
  CheckSquare,
  Clock,
  Download,
  Eye,
  PieChart,
  Presentation,
  Sparkles,
  X,
} from "lucide-react";
import { clsx } from "clsx";

import { EChart } from "../components/charts/EChart";
import { ChatComposer } from "../components/chat/ChatComposer";
import { ChatMessageList } from "../components/chat/ChatMessageList";
import { useChatSession } from "../hooks/useChatSession";
import type { ApiArtifact } from "../types/api";
import type { ChartChatMessage } from "../types/chat";

type PromptItem = {
  id: string;
  title: string;
  icon: typeof Activity;
  color: string;
  text: string;
};

const DEFAULT_PROMPTS: PromptItem[] = [
  {
    id: "analyze_renewal",
    title: "分析续卡率低的原因",
    icon: Activity,
    color: "text-blue-500",
    text: "帮我分析极橙仙乐斯店近30天续卡率低的原因",
  },
  {
    id: "analyze_conversion",
    title: "分析初诊转化漏斗",
    icon: PieChart,
    color: "text-purple-500",
    text: "帮我分析极橙徐汇店上个月的初诊转化漏斗",
  },
  {
    id: "generate_report",
    title: "生成本月经营报告",
    icon: Presentation,
    color: "text-orange-500",
    text: "帮我生成全部门诊近30天的经营PPT报告",
  },
  {
    id: "check_appointment",
    title: "查看近期预约饱和度",
    icon: Calendar,
    color: "text-green-500",
    text: "查看极橙仙乐斯店刘主任近7天的预约饱和度",
  },
  {
    id: "analyze_lost",
    title: "流失高风险患者预警",
    icon: Activity,
    color: "text-rose-500",
    text: "预警极橙大宁店第一季度流失高风险患者，并生成待办SOP",
  },
  {
    id: "doctor_performance",
    title: "核心医生业绩环比分析",
    icon: PieChart,
    color: "text-indigo-500",
    text: "分析极橙仙乐斯店张大夫今年的业绩环比数据",
  },
];

const RECENT_HISTORY: ApiArtifact[] = [
  {
    id: "history-ppt-1",
    type: "ppt",
    title: "极橙大宁店-流失患者分析报告.pptx",
    createdAt: "今天 10:30",
    size: "2.4 MB",
    preview: [
      "幻灯片 1：本季度流失率概览\n- 大宁店流失率：12%\n- 显著改善：复诊等待时间减少",
      "幻灯片 2：重点改进建议\n- 继续加强正畸复诊提醒\n- 完善初诊未成交患者的7天追踪SOP",
    ],
  },
  {
    id: "history-todo-1",
    type: "todo",
    title: "极橙徐汇店-前台回访规范（SOP）",
    createdAt: "昨天 16:45",
    size: "5 项待办",
    preview: [
      "[ ] 确认每日预约名单并发送提醒",
      "[ ] 发送复诊提醒微信（正畸及种植患者）",
      "[ ] 电话回访逾期未归患者，记录未归原因",
      "[ ] 整理患者反馈记录并录入 HIS 系统",
      "[ ] 每日晨会播报前日客诉及处理进度",
    ],
  },
];

const artifactIconMap = {
  ppt: Presentation,
  todo: CheckSquare,
  report: Presentation,
  file: Presentation,
};

type TimelineItem =
  | {
      id: string;
      type: "chart";
      title: string;
      createdAt: string;
      option: ChartChatMessage["option"];
    }
  | {
      id: string;
      type: "artifact";
      createdAt: string;
      artifact: ApiArtifact;
      isSession: boolean;
    };

export function Chat() {
  const [inputText, setInputText] = useState("");
  const [previewArtifact, setPreviewArtifact] = useState<ApiArtifact | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const {
    messages,
    stage,
    isSubmitting,
    activeClarificationId,
    submitQuestion,
    answerClarification,
  } = useChatSession();

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const timelineItems = useMemo<TimelineItem[]>(() => {
    const sessionItems = messages.flatMap<TimelineItem>((message) => {
      if (message.type === "chart") {
        return [
          {
            id: message.id,
            type: "chart",
            title: message.title,
            createdAt: message.createdAt ?? "刚刚",
            option: message.option,
          },
        ];
      }

      if (message.type === "artifact") {
        return message.artifacts.map((artifact) => ({
          id: `${message.id}-${artifact.id}`,
          type: "artifact" as const,
          createdAt: artifact.createdAt ?? message.createdAt ?? "刚刚",
          artifact,
          isSession: true,
        }));
      }

      return [];
    });

    const historyItems: TimelineItem[] = RECENT_HISTORY.map((artifact) => ({
      id: artifact.id,
      type: "artifact",
      createdAt: artifact.createdAt ?? "较早",
      artifact,
      isSession: false,
    }));

    return [...sessionItems.reverse(), ...historyItems];
  }, [messages]);

  const handleSubmit = async () => {
    const value = inputText.trim();
    if (!value) {
      return;
    }

    if (stage === "clarifying" && activeClarificationId) {
      await answerClarification(activeClarificationId, value);
    } else {
      await submitQuestion(value);
    }

    setInputText("");
  };

  const handleOpenArtifact = (artifact: ApiArtifact) => {
    if (artifact.preview?.length) {
      setPreviewArtifact(artifact);
    }
  };

  const composerPlaceholder =
    stage === "clarifying"
      ? "请输入补充说明，或直接点击上方澄清选项..."
      : "直接输入您的分析需求...";

  return (
    <div className="relative flex h-full flex-1 overflow-hidden">
      <div className="relative flex h-full flex-1 flex-col overflow-hidden bg-white">
        <header className="z-10 flex h-[72px] shrink-0 items-center justify-between border-b border-gray-100 bg-white/80 px-8 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-medium text-gray-800">续卡助手</h1>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-8 scroll-smooth" ref={chatContainerRef}>
          {messages.length === 0 ? (
            <div className="mx-auto mt-12 flex max-w-2xl flex-col items-center justify-center pb-20 text-center">
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-[20px] bg-gradient-to-br from-[#1a73e8] to-[#4285f4] shadow-lg shadow-blue-500/20">
                <Sparkles className="h-8 w-8 text-white" />
              </div>
              <h2 className="mb-3 text-2xl font-semibold text-gray-800">你好，我是口腔诊所续卡助手</h2>
              <p className="text-[15px] text-gray-500">
                我可以帮您串联澄清、执行分析、图表展示和报告输出，逐步完成一轮完整的经营分析流程。
              </p>
            </div>
          ) : (
            <ChatMessageList
              messages={messages}
              onClarificationAnswer={answerClarification}
              onOpenArtifact={handleOpenArtifact}
            />
          )}
        </div>

        <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-10 bg-gradient-to-t from-white via-white/90 to-transparent p-6 pt-12">
          <div className="pointer-events-auto mx-auto flex w-full max-w-4xl flex-col justify-end px-4">
            <div className="relative mb-4 w-full">
              <div className="flex w-full items-center gap-2.5 overflow-x-auto pb-1 pr-12 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {DEFAULT_PROMPTS.map((prompt) => (
                  <button
                    key={prompt.id}
                    type="button"
                    onClick={() => setInputText(prompt.text)}
                    className={clsx(
                      "flex shrink-0 items-center gap-2 rounded-full border border-gray-200/80 bg-white/90 px-4 py-2 text-[13px] font-medium text-gray-700 shadow-sm transition-all hover:bg-white hover:text-[#1a73e8] hover:shadow-md",
                    )}
                  >
                    <prompt.icon className={clsx("h-3.5 w-3.5", prompt.color)} />
                    {prompt.title}
                  </button>
                ))}
              </div>
            </div>

            <ChatComposer
              value={inputText}
              onChange={setInputText}
              onSubmit={handleSubmit}
              disabled={isSubmitting}
              placeholder={composerPlaceholder}
            />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {previewArtifact ? (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-20 bg-gray-900/10 backdrop-blur-[1px]"
              onClick={() => setPreviewArtifact(null)}
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="absolute right-0 top-0 bottom-0 z-30 flex w-full flex-col border-l border-gray-200 bg-white shadow-2xl sm:w-[560px]"
            >
              <div className="flex shrink-0 items-center justify-between gap-4 border-b border-gray-100 p-4 sm:p-6">
                <div className="flex min-w-0 flex-1 items-center gap-3 overflow-hidden">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-500">
                    <Presentation className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1 overflow-hidden">
                    <h3 className="truncate text-base font-semibold text-gray-800" title={previewArtifact.title}>
                      {previewArtifact.title}
                    </h3>
                    <div className="mt-0.5 truncate text-sm text-gray-500">
                      {previewArtifact.createdAt ?? "刚刚"}
                      {previewArtifact.size ? ` · ${previewArtifact.size}` : ""}
                    </div>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    className="flex cursor-pointer items-center gap-1.5 rounded-full bg-[#e8f0fe] px-4 py-2 text-sm font-medium text-[#1a73e8] transition-colors hover:bg-blue-100"
                  >
                    <Download className="h-4 w-4" /> 下载
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewArtifact(null)}
                    className="cursor-pointer rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              <div className="flex-1 space-y-6 overflow-y-auto bg-[#f8fafd] p-6">
                {(previewArtifact.preview ?? []).map((slideText, index) => {
                  const lines = slideText.split("\n");
                  const title = lines[0];
                  const content = lines.slice(1);

                  return (
                    <div
                      key={`${previewArtifact.id}-${index}`}
                      className="group relative flex aspect-[16/9] flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm"
                    >
                      <div className="pointer-events-none absolute inset-0 z-10 border-4 border-transparent transition-colors group-hover:border-blue-500/20" />
                      <div className="h-1.5 w-full shrink-0 bg-gradient-to-r from-orange-400 to-orange-500" />
                      <div className="flex h-full flex-col p-8">
                        <h2 className="mb-6 border-b border-gray-100 pb-4 text-[22px] font-bold leading-tight text-gray-800">
                          {title}
                        </h2>
                        <div className="flex-1 space-y-4">
                          {content.length > 0 ? (
                            content.map((line, lineIndex) => {
                              const cleanLine = line.replace(/^- /, "");
                              if (!cleanLine.trim()) return null;

                              return (
                                <div key={lineIndex} className="flex items-start gap-3">
                                  <div className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" />
                                  <p className="text-[16px] leading-relaxed text-gray-600">{cleanLine}</p>
                                </div>
                              );
                            })
                          ) : (
                            <p className="text-[16px] leading-relaxed text-gray-600">暂无更多预览内容。</p>
                          )}
                        </div>
                        <div className="mt-auto flex items-end justify-between pt-4">
                          <span className="text-sm font-medium text-gray-300">{index + 1}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      <div className="z-10 hidden w-[320px] shrink-0 flex-col border-l border-gray-200/80 bg-gray-50 shadow-[-4px_0_24px_rgba(0,0,0,0.02)] md:flex">
        <div className="sticky top-0 z-20 flex h-[72px] shrink-0 items-center justify-between border-b border-gray-200/80 bg-white/80 px-5 shadow-sm backdrop-blur-md">
          <h3 className="flex items-center gap-2 text-[15px] font-medium text-gray-800">
            <Activity className="h-4 w-4 text-[#1a73e8]" /> 工作台
          </h3>
        </div>
        <div className="relative flex-1 overflow-y-auto p-4 pt-6">
          <div className="absolute bottom-0 left-[23px] top-8 z-0 w-px bg-gray-200/80" />
          <div className="relative z-10 space-y-6">
            {timelineItems.map((item) => {
              if (item.type === "chart") {
                return (
                  <div key={item.id} className="relative pl-8">
                    <div className="absolute left-[3px] top-1 z-10 h-2 w-2 rounded-full bg-blue-400 ring-4 ring-[#f9fafb]" />
                    <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium text-gray-500">
                      <Clock className="h-3 w-3" />
                      {item.createdAt}
                    </div>
                    <div className="rounded-[20px] border border-gray-200/60 bg-white p-4 shadow-sm">
                      <div className="mb-3 flex items-center gap-1.5 text-[13px] font-medium text-gray-800">
                        <PieChart className="h-3.5 w-3.5 text-blue-500" />
                        {item.title}
                      </div>
                      <div className="h-40 w-full">
                        <EChart option={item.option} style={{ height: "100%" }} />
                      </div>
                    </div>
                  </div>
                );
              }

              const Icon = artifactIconMap[item.artifact.type] ?? Presentation;
              return (
                <div key={item.id} className="relative pl-8">
                  <div className="absolute left-[3px] top-1 z-10 h-2 w-2 rounded-full bg-blue-400 ring-4 ring-[#f9fafb]" />
                  <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium text-gray-500">
                    <Clock className="h-3 w-3" />
                    {item.createdAt}
                  </div>
                  <div className="overflow-hidden rounded-[20px] border border-gray-200/60 bg-white shadow-sm transition-all hover:border-blue-200 hover:shadow-md">
                    <div className="flex cursor-pointer items-start gap-3 p-4 transition-colors hover:bg-gray-50/50" onClick={() => handleOpenArtifact(item.artifact)}>
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-500">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1 pt-0.5">
                        <div className="line-clamp-2 text-[13px] font-medium leading-snug text-gray-800">{item.artifact.title}</div>
                        <div className="mt-1.5 flex items-center gap-2 text-[11px] text-gray-400">
                          <span className="rounded bg-gray-50 px-1.5 py-0.5 text-[10px] text-gray-500">{item.artifact.size ?? "可预览"}</span>
                          {item.isSession ? <span className="text-blue-500">本轮输出</span> : null}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 px-3 pb-3">
                      <button
                        type="button"
                        onClick={() => handleOpenArtifact(item.artifact)}
                        className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-xl bg-gray-50 py-2 text-[12px] font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
                      >
                        <Eye className="h-3.5 w-3.5" /> 预览
                      </button>
                      <button
                        type="button"
                        className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-xl bg-[#e8f0fe] py-2 text-[12px] font-medium text-[#1a73e8] transition-colors hover:bg-blue-100"
                      >
                        <Download className="h-3.5 w-3.5" /> 下载
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
