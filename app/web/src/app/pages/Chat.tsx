import { useState, useRef, useEffect, useMemo } from 'react';
import {
  Sparkles, Send, Activity, PieChart, Presentation,
  Calendar, X, Database, ChevronDown,
  Download, CheckSquare, Loader2, CheckCircle2, Eye, ChevronRight, ChevronLeft, Copy, Clock
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { clsx } from 'clsx';
import type { EChartsOption } from 'echarts';
import { EChart } from '../components/charts/EChart';

// Configuration
const DEFAULT_PROMPTS = [
  { 
    id: 'analyze_renewal', title: '分析续卡率低的原因', icon: Activity, color: 'text-blue-500', isCustom: false,
    text: '帮我分析极橙仙乐斯店近30天续卡率低的原因'
  },
  { 
    id: 'analyze_conversion', title: '分析初诊转化漏斗', icon: PieChart, color: 'text-purple-500', isCustom: false,
    text: '帮我分析极橙徐汇店上个月的初诊转化漏斗'
  },
  { 
    id: 'generate_report', title: '生成本月经营报告', icon: Presentation, color: 'text-orange-500', isCustom: false,
    text: '帮我生成全部门诊近30天的经营PPT报告'
  },
  { 
    id: 'check_appointment', title: '查看近期预约饱和度', icon: Calendar, color: 'text-green-500', isCustom: false,
    text: '查看极橙仙乐斯店刘主任近7天的预约饱和度'
  },
  { 
    id: 'analyze_lost', title: '流失高风险患者预警', icon: Activity, color: 'text-rose-500', isCustom: false,
    text: '预警极橙大宁店第一季度流失高风险患者，并生成待办SOP'
  },
  { 
    id: 'doctor_performance', title: '核心医生业绩环比分析', icon: PieChart, color: 'text-indigo-500', isCustom: false,
    text: '分析极橙仙乐斯店张大夫今年的业绩环比数据'
  },
];

const RECENT_HISTORY = [
  {
    id: 'h1', type: 'ppt', title: '极橙大宁店-流失患者分析报告.pptx', date: '今天 10:30', size: '2.4 MB', icon: Presentation, color: 'text-orange-500',
    preview: [
      "幻灯片 1：本季度流失率概览\n- 大宁店流失率：12%\n- 显著改善：复诊等待时间减少",
      "幻灯片 2：重点改进建议\n- 继续加强正畸复诊提醒\n- 完善初诊未成交患者的7天追踪SOP"
    ]
  },
  {
    id: 'h2', type: 'todo', title: '极橙徐汇店-前台回访规范(SOP)', date: '昨天 16:45', size: '5 项待办', icon: CheckSquare, color: 'text-green-500',
    preview: [
      "[ ] 确认每日预约名单并发送提醒",
      "[ ] 发送复诊提醒微信（正畸及种植患者）",
      "[ ] 电话回访逾期未归患者，记录未归原因",
      "[ ] 整理患者反馈记录并录入HIS系统",
      "[ ] 每日晨会播报前日客诉及处理进度"
    ]
  }
];

type BarChartPoint = {
  name: string;
  value: number;
  ideal?: number;
};

type LineChartPoint = {
  name: string;
  rate: number;
};

function buildBarChartOption(data: BarChartPoint[]): EChartsOption {
  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
        shadowStyle: {
          color: '#f8fafd',
        },
      },
      backgroundColor: '#ffffff',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: {
        color: '#1f2937',
        fontSize: 12,
      },
    },
    grid: {
      top: 16,
      right: 12,
      bottom: 20,
      left: 24,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: data.map((item) => item.name),
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: '#888888',
        fontSize: 10,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed',
        },
      },
      axisLabel: {
        color: '#888888',
        fontSize: 10,
      },
    },
    series: [
      {
        name: '周留存率(%)',
        type: 'bar',
        barMaxWidth: 30,
        data: data.map((item) => ({
          value: item.value,
          itemStyle: {
            color: item.value < 80 ? '#f43f5e' : '#1a73e8',
            borderRadius: [4, 4, 0, 0],
          },
        })),
        markLine: data.some((item) => typeof item.ideal === 'number')
          ? {
              symbol: 'none',
              label: {
                formatter: '目标',
                color: '#64748b',
                fontSize: 11,
              },
              lineStyle: {
                color: '#94a3b8',
                type: 'dashed',
              },
              data: [
                {
                  yAxis: data.find((item) => typeof item.ideal === 'number')?.ideal ?? 0,
                },
              ],
            }
          : undefined,
      },
    ],
  };
}

function buildLineChartOption(data: LineChartPoint[]): EChartsOption {
  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: {
        color: '#1f2937',
        fontSize: 12,
      },
    },
    grid: {
      top: 16,
      right: 12,
      bottom: 20,
      left: 24,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map((item) => item.name),
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: '#888888',
        fontSize: 10,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed',
        },
      },
      axisLabel: {
        color: '#888888',
        fontSize: 10,
      },
    },
    series: [
      {
        name: '预估流失率(%)',
        type: 'line',
        smooth: true,
        data: data.map((item) => item.rate),
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          color: '#10b981',
          width: 3,
        },
        itemStyle: {
          color: '#10b981',
          borderColor: '#ffffff',
          borderWidth: 2,
        },
        areaStyle: {
          color: 'rgba(16, 185, 129, 0.08)',
        },
      },
    ],
  };
}

export function Chat() {
  const [messages, setMessages] = useState<any[]>([]);
  const [prompts] = useState<any[]>(DEFAULT_PROMPTS);
  const [inputText, setInputText] = useState('');
  const [previewPpt, setPreviewPpt] = useState<any | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSelectPrompt = (prompt: any) => {
    setInputText(prompt.text);
  };

  const handleViewHistory = (item: any) => {
    if (item.type === 'ppt') {
      setPreviewPpt(item);
      return;
    }
    setMessages(prev => [
      ...prev,
      { id: Date.now().toString(), role: 'user', text: `查看历史待办：${item.title}` },
      {
        id: Date.now().toString() + '-ast',
        role: 'assistant',
        text: `这是您之前生成的记录：**${item.title}**\n创建时间：${item.date}`,
        attachments: [item]
      }
    ]);
  };

  const handleSend = (overrideText?: string) => {
    const textToSend = overrideText || inputText;
    if (!textToSend.trim()) return;

    const query = textToSend.trim();
    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      text: query,
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    
    // Check for ambiguity
    const isAmbiguous = query.length <= 6 || ['续卡', '分析', '数据', '报告', '复诊'].includes(query);
    
    if (isAmbiguous) {
      const assistantId = Date.now().toString() + '-assistant';
      setTimeout(() => {
        setMessages(prev => [...prev, {
          id: assistantId,
          role: 'assistant',
          text: `检测到您的提问“${query}”比较宽泛，语义有些模糊。您是否想分析以下具体内容？（点击即可查询）`,
          options: [
            `分析近期${query}下降的根本原因`,
            `查看各门诊${query}数据对比`,
            `生成提升${query}指标的待办SOP`
          ]
        }]);
      }, 600);
      return;
    }

    // Determine if it should be a report based on fields or prompt title
    const wantsReport = query.includes('报告') || query.includes('PPT');
    const clinicName = query.includes('大宁') ? '大宁店' : (query.includes('仙乐斯') ? '仙乐斯店' : '全部门诊');

    const assistantId = Date.now().toString() + '-assistant';
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      isAnalyzing: true,
      thinking: [
        { text: '正在验证权限并连接诊所管理系统(HIS)...' }
      ]
    }]);

    setTimeout(() => {
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m, thinking: [...m.thinking, { text: `正在提取 ${clinicName} 的相关就诊及回访记录`, source: 'HIS - 就诊表' }]
      } : m));
    }, 800);

    setTimeout(() => {
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m, thinking: [...m.thinking, { 
          text: `数据清洗完成，发现以下核心指标异常波动：`,
          chart: {
            type: 'bar',
            data: [
              { name: '第1周', value: 85, ideal: 90 },
              { name: '第2周', value: 82, ideal: 90 },
              { name: '第3周', value: 68, ideal: 90 },
              { name: '第4周', value: 71, ideal: 90 }
            ]
          }
        }]
      } : m));
    }, 1800);

    setTimeout(() => {
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m, 
        isAnalyzing: false,
        text: `我已初步拉取了 **${clinicName}** 的数据。在分析过程中，我发现指标异常主要集中在两个显著方面：\n\n一是"候诊时间超过30分钟"引发的抱怨，二是"部分高客单价项目未提供灵活分期"。\n\n为了让产出物更符合您的执行需求，您希望我优先深挖并生成哪个方向的应对策略？`,
        options: [
          '深挖"等待时间长"的服务体验问题', 
          '深挖"高单价转化低"的价格敏感问题', 
          '全面综合分析并输出'
        ],
        meta: { wantsReport, clinicName }
      } : m));
    }, 3000);
  };

  const handleOptionSelect = (msgId: string, option: string, meta: any) => {
    // Disable options
    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, options: undefined } : m));

    // If there's no meta, it was an ambiguity clarification option
    if (!meta) {
      handleSend(option);
      return;
    }

    // Add user message
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      text: option
    }]);

    const newAstId = Date.now().toString() + '-ast-2';
    setMessages(prev => [...prev, {
      id: newAstId,
      role: 'assistant',
      isAnalyzing: true,
      thinking: [
        { text: `正在基于您的选择：「${option}」进行深度数据下钻...` }
      ]
    }]);

    setTimeout(() => {
      setMessages(prev => prev.map(m => m.id === newAstId ? {
        ...m, thinking: [...m.thinking, { text: `交叉比对行业基准库，生成结构化策略...` }]
      } : m));
    }, 1000);

    setTimeout(() => {
      setMessages(prev => prev.map(m => m.id === newAstId ? {
        ...m, thinking: [...m.thinking, { 
          text: `策略执行后的目标留存率预估模型：`,
          chart: {
            type: 'line',
            data: [
              { name: '现状', rate: 12 },
              { name: '实施1周', rate: 9 },
              { name: '实施2周', rate: 6 },
              { name: '实施1月', rate: 4 }
            ]
          }
        }]
      } : m));
    }, 2000);

    setTimeout(() => {
      // Choose attachment type based on original intent (PPT vs Todo)
      const isReport = meta.wantsReport;
      const attachments = isReport ? [
        { 
          id: `ppt-${Date.now()}`, type: 'ppt', title: `${meta.clinicName}提升执行方案.pptx`, size: '3.2 MB', icon: Presentation, color: 'text-orange-500',
          preview: [
            `幻灯片 1：本季度诊断结论 (${meta.clinicName})\n- 核心痛点：${option}\n- 影响占比：导致近期约 35% 的意向患者流失`,
            `幻灯片 2：应对策略规划\n1. 针对性优化现有SOP流程\n2. 引入前台预警机制\n3. 提升咨询师应对相关抗性的话术能力`
          ]
        }
      ] : [
        { 
          id: `todo-${Date.now()}`, type: 'todo', title: `${meta.clinicName}行动待办 (SOP)`, size: '共 4 项', icon: CheckSquare, color: 'text-green-500',
          preview: [
            "[ ] 每日由前台主管导出逾期未复诊名单",
            "[ ] 建立针对该痛点的标准回讲话术",
            "[ ] 客服专员介入，对流失高风险患者进行针对性安抚",
            "[ ] 院长/店长每周复盘该项指标改善情况"
          ]
        }
      ];

      setMessages(prev => prev.map(m => m.id === newAstId ? {
        ...m,
        isAnalyzing: false,
        thinking: [...m.thinking, { text: '处理完成。' }],
        text: `已根据您的指示完成了深入分析。\n\n结合您的选择，我发现只要我们在执行层面上解决这个卡点，预计能挽回约 15%-20% 的流失率。\n\n相关的执行方案已为您生成，请查阅下方附件。`,
        attachments
      } : m));
    }, 3500);
  };

  const timelineItems = useMemo(() => {
    const items: any[] = [];
    
    // Add current session items first (Newest at the top)
    [...messages].reverse().forEach(msg => {
      // Current session attachments (PPTs, Todos)
      if (msg.attachments) {
        // Reverse attachments if needed, but usually they are displayed together
        [...msg.attachments].reverse().forEach((att: any) => {
          items.push({
            type: 'attachment',
            isSession: true,
            data: { ...att, date: '刚刚', _sessionAttachmentId: `session-att-${msg.id}-${att.id}` }
          });
        });
      }
      
      // Current session charts
      if (msg.thinking) {
        [...msg.thinking].reverse().forEach((step: any, idx: number) => {
          if (step.chart) {
            items.push({
              type: 'chart',
              isSession: true,
              data: { ...step, date: '刚刚', id: `session-chart-${msg.id}-${idx}` }
            });
          }
        });
      }
    });

    // Add static history items (Older)
    RECENT_HISTORY.forEach(h => {
      items.push({
        type: 'attachment',
        isSession: false,
        data: h
      });
    });

    return items;
  }, [messages]);

  return (
    <div className="flex-1 flex h-full relative overflow-hidden">
      <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-white">
        <header className="h-[72px] border-b border-gray-100 flex items-center justify-between px-8 shrink-0 bg-white/80 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-medium text-gray-800">续卡助手</h1>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth" ref={chatContainerRef}>
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto w-full mt-12 pb-20">
            <div className="w-16 h-16 bg-gradient-to-br from-[#1a73e8] to-[#4285f4] rounded-[20px] flex items-center justify-center shadow-lg shadow-blue-500/20 mb-8">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-semibold text-gray-800 mb-3">���好，我是口腔诊所续卡助手</h2>
            <p className="text-gray-500 mb-10 text-center text-[15px]">
              我可以帮您深度分析诊所运营数据、追踪患者复诊与续卡情况，并自动生成解决方案。
            </p>
          </div>
        ) : (
          <div className="space-y-8 pb-60 max-w-4xl mx-auto w-full px-4">
            {messages.map(msg => (
              msg.role === 'user' ? (
                <div key={msg.id} className="flex justify-end w-full">
                  <div className="bg-[#f4f7fc] border border-[#e8f0fe] rounded-[24px] rounded-tr-sm p-5 max-w-[85%] shadow-sm">
                    {msg.title && (
                      <div className="text-[15px] font-medium text-gray-800 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-[#1a73e8]" />
                        {msg.title}
                      </div>
                    )}
                    {msg.text && (
                      <div className={clsx("text-[15px] text-gray-800 leading-relaxed whitespace-pre-wrap", msg.title && "mt-3")}>
                        {msg.text}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div key={msg.id} className="flex gap-4 w-full max-w-3xl">
                  <div className="w-10 h-10 rounded-[14px] bg-gradient-to-br from-[#1a73e8] to-[#4285f4] flex items-center justify-center shrink-0 shadow-md shadow-blue-500/20">
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1 space-y-4 pt-1">
                    {msg.thinking && (
                      <div className="border border-gray-200 rounded-[20px] bg-[#f8fafd] overflow-hidden group">
                        <details className="open:pb-1 group-details">
                          <summary className="flex items-center justify-between p-3.5 cursor-pointer text-sm text-gray-600 hover:bg-gray-100/50 transition-colors list-none outline-none">
                            <span className="flex items-center gap-2.5 font-medium">
                              {msg.isAnalyzing ? (
                                <Loader2 className="w-4 h-4 animate-spin text-[#1a73e8]" />
                              ) : (
                                <CheckCircle2 className="w-4 h-4 text-green-500" />
                              )}
                              分析过程 {msg.isAnalyzing ? '...' : '(完成)'}
                            </span>
                            <ChevronDown className="w-4 h-4 transition-transform group-open:-rotate-180 text-gray-400" />
                          </summary>
                          <div className="px-3.5 pb-3 pt-1 border-t border-gray-100/60 space-y-4">
                            {msg.thinking.map((step: any, idx: number) => (
                              <div key={`${msg.id}-step-${idx}`} className="flex flex-col gap-2.5">
                                <div className="text-[13px] text-gray-600 flex items-start gap-2">
                                  <span className="text-gray-400 mt-0.5 w-4 font-mono shrink-0">{idx + 1}.</span>
                                  <div className="flex-1 leading-relaxed">
                                    {step.text}
                                    {step.source && (
                                      <button className="inline-flex items-center gap-1 bg-[#e8f0fe] text-[#1a73e8] px-2 py-0.5 rounded-md border border-blue-100/50 hover:bg-blue-100 transition-colors ml-2 font-medium cursor-pointer">
                                        <Database className="w-3 h-3" /> {step.source}
                                      </button>
                                    )}
                                  </div>
                                </div>
                                {step.chart && (
                                  <div className="ml-6 mr-2 h-40 bg-white border border-gray-100 rounded-xl p-3 shadow-sm">
                                    <EChart
                                      option={
                                        step.chart.type === 'bar'
                                          ? buildBarChartOption(step.chart.data as BarChartPoint[])
                                          : buildLineChartOption(step.chart.data as LineChartPoint[])
                                      }
                                      style={{ height: '100%' }}
                                    />
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}
                    
                    {msg.text && (
                      <div className="text-gray-800 text-[15px] leading-relaxed whitespace-pre-wrap font-sans">
                        {msg.text}
                      </div>
                    )}

                    {msg.options && (
                      <div className="flex flex-col gap-2.5 pt-2">
                        {msg.options.map((opt: string, idx: number) => (
                          <button
                            key={`opt-${msg.id}-${idx}`}
                            onClick={() => handleOptionSelect(msg.id, opt, msg.meta)}
                            className="text-left px-5 py-3 rounded-[16px] border border-blue-200 bg-[#f8fafd] text-[#1a73e8] text-[14px] hover:bg-blue-50 hover:border-blue-300 transition-colors cursor-pointer font-medium shadow-sm hover:shadow group w-full pr-10 relative flex items-center justify-between"
                          >
                            <span className="flex items-center gap-3">
                              <span className="w-6 h-6 shrink-0 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">{String.fromCharCode(65 + idx)}</span>
                              <span>{opt}</span>
                            </span>
                            <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                          </button>
                        ))}
                      </div>
                    )}

                    {msg.attachments && (
                      <div className="flex flex-col gap-3 pt-2">
                        {msg.attachments.map((att: any) => (
                          <AttachmentCard key={att.id} att={att} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
            ))}
          </div>
        )}
      </div>

      <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-white via-white/90 to-transparent pt-12 shrink-0 pointer-events-none z-10">
        <div className="max-w-4xl mx-auto w-full relative pointer-events-auto flex flex-col justify-end px-4">
          
          {/* Prompts as tags above input */}
          <div className="mb-4 relative w-full">
            <div className="flex items-center gap-2.5 overflow-x-auto w-full [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] pb-1 pr-12">
              {prompts.map(p => (
                <button 
                  key={p.id}
                  onClick={() => handleSelectPrompt(p)}
                  className={clsx(
                    "shrink-0 px-4 py-2 bg-white/90 backdrop-blur-md border border-gray-200/80 rounded-full text-[13px] font-medium text-gray-700 hover:border-blue-300 transition-all flex items-center gap-2 shadow-sm hover:shadow-md hover:bg-white cursor-pointer",
                    "hover:text-[#1a73e8]"
                  )}
                >
                  <p.icon className={clsx("w-3.5 h-3.5", p.color)} />
                  {p.title}
                </button>
              ))}
            </div>
            
          </div>

          <div 
            className="bg-white border border-gray-200 shadow-[0_4px_20px_rgba(0,0,0,0.06)] rounded-[20px] p-2 relative z-10 w-full transition-shadow hover:shadow-[0_8px_30px_rgba(0,0,0,0.08)] flex items-end gap-2"
          >
            <textarea
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="直接输入您的分析需求..."
              className="flex-1 bg-transparent border-none px-4 py-3 text-[15px] text-gray-800 placeholder-gray-400 focus:outline-none resize-none min-h-[48px] max-h-[120px]"
              rows={1}
            />
            <button 
              onClick={() => handleSend()} 
              disabled={!inputText.trim()}
              className="bg-[#1a73e8] hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-[#1a73e8] text-white w-[48px] h-[48px] rounded-xl flex items-center justify-center transition-colors cursor-pointer shrink-0"
            >
              <Send className="w-5 h-5 ml-0.5" />
            </button>
          </div>
        </div>
      </div>

    </div>
    
    {/* PPT Preview Drawer */}
    <AnimatePresence>
      {previewPpt && (
        <>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-gray-900/10 backdrop-blur-[1px] z-20"
            onClick={() => setPreviewPpt(null)}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="absolute top-0 right-0 bottom-0 w-full sm:w-[560px] bg-white border-l border-gray-200 shadow-2xl z-30 flex flex-col"
          >
            <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-100 shrink-0 gap-4">
              <div className="flex items-center gap-3 w-full sm:w-auto overflow-hidden">
                <div className="w-10 h-10 rounded-xl bg-orange-50 text-orange-500 flex items-center justify-center shrink-0">
                  <Presentation className="w-5 h-5" />
                </div>
                <div className="overflow-hidden flex-1">
                  <h3 className="text-base font-semibold text-gray-800 truncate" title={previewPpt.title}>{previewPpt.title}</h3>
                  <div className="text-sm text-gray-500 mt-0.5 truncate">{previewPpt.date} · {previewPpt.size}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-[#1a73e8] bg-[#e8f0fe] hover:bg-blue-100 rounded-full transition-colors cursor-pointer">
                  <Download className="w-4 h-4" /> 下载
                </button>
                <button 
                  onClick={() => setPreviewPpt(null)}
                  className="p-2 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-[#f8fafd] space-y-6">
              {previewPpt.preview.map((slideText: string, idx: number) => {
                const lines = slideText.split('\n');
                const title = lines[0];
                const content = lines.slice(1);
                
                return (
                  <div key={idx} className="aspect-[16/9] bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col relative group">
                    <div className="absolute inset-0 border-4 border-transparent group-hover:border-blue-500/20 transition-colors pointer-events-none z-10" />
                    
                    <div className="h-1.5 w-full bg-gradient-to-r from-orange-400 to-orange-500 shrink-0" />
                    
                    <div className="p-8 flex flex-col h-full">
                      <h2 className="text-[22px] font-bold text-gray-800 mb-6 pb-4 border-b border-gray-100 leading-tight">
                        {title}
                      </h2>
                      
                      <div className="space-y-4 flex-1">
                        {content.map((line, lineIdx) => {
                          const cleanLine = line.replace(/^- /, '');
                          if (!cleanLine.trim()) return null;
                          
                          return (
                            <div key={lineIdx} className="flex items-start gap-3">
                              <div className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-2 shrink-0" />
                              <p className="text-[16px] text-gray-600 leading-relaxed">
                                {cleanLine}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                      
                      <div className="flex justify-between items-end mt-auto pt-4">
                        <span className="text-sm font-medium text-gray-300">{idx + 1}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>

    {/* Right History Panel - always visible on desktop, hidden on small screens */}
    <div className="hidden md:flex w-[320px] border-l border-gray-200/80 bg-gray-50 flex-col shrink-0 z-10 transition-all duration-300 ease-in-out shadow-[-4px_0_24px_rgba(0,0,0,0.02)]">
      <div className="h-[72px] px-5 border-b border-gray-200/80 bg-white/80 backdrop-blur-md shrink-0 sticky top-0 z-20 shadow-sm flex items-center justify-between">
        <h3 className="text-[15px] font-medium text-gray-800 flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#1a73e8]" />
          工作台
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto p-4 pt-6 relative">
        <div className="absolute top-8 bottom-0 left-[23px] w-px bg-gray-200/80 z-0"></div>
        <div className="space-y-6 relative z-10">
          {timelineItems.map((item) => {
            const isChart = item.type === 'chart';
            const isTodo = item.type === 'attachment' && item.data.type === 'todo';
            const history = item.data;

            return (
              <div key={isChart ? history.id : (history._sessionAttachmentId || history.id)} className="relative pl-8">
                {/* Timeline Dot */}
                <div className="absolute left-[3px] top-1 w-2 h-2 rounded-full bg-blue-400 ring-4 ring-[#f9fafb] z-10"></div>
                
                {/* Time Label */}
                <div className="mb-2 text-[11px] font-medium text-gray-500 flex items-center gap-1.5">
                  <Clock className="w-3 h-3" />
                  {history.date}
                </div>

                {isChart ? (
                  <div className="bg-white rounded-[20px] p-4 border border-gray-200/60 shadow-sm hover:shadow-md transition-all">
                    <div className="text-[13px] font-medium text-gray-800 mb-3 leading-snug flex items-center gap-1.5">
                      <PieChart className="w-3.5 h-3.5 text-blue-500" />
                      {history.text}
                    </div>
                    <div className="h-40 w-full">
                      <EChart
                        option={
                          history.chart.type === 'bar'
                            ? buildBarChartOption(history.chart.data as BarChartPoint[])
                            : buildLineChartOption(history.chart.data as LineChartPoint[])
                        }
                        style={{ height: '100%' }}
                      />
                    </div>
                  </div>
                ) : isTodo ? (
                  <SidebarTodoCard history={history} />
                ) : (
                  <div className="bg-white rounded-[20px] border border-gray-200/60 shadow-sm hover:shadow-md hover:border-blue-200 flex flex-col group overflow-hidden transition-all">
                    <div 
                      onClick={() => handleViewHistory(history)}
                      className="flex items-start gap-3 p-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
                    >
                      <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-105", history.color, 'bg-orange-50')}>
                        <history.icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 overflow-hidden pt-0.5">
                        <div className="text-[13px] font-medium text-gray-800 line-clamp-2 leading-snug group-hover:text-[#1a73e8] transition-colors">{history.title}</div>
                        <div className="text-[11px] text-gray-400 mt-1.5 flex items-center gap-2">
                          <span className="text-[10px] bg-gray-50 px-1.5 py-0.5 rounded text-gray-500">{history.size}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 px-3 pb-3">
                      <button 
                        onClick={() => handleViewHistory(history)}
                        className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-[12px] font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 hover:text-gray-900 transition-colors cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5" /> 预览
                      </button>
                      <button 
                        className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-[12px] font-medium text-[#1a73e8] bg-[#e8f0fe] hover:bg-blue-100 transition-colors cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" /> 下载
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>



    </div>
  );
}





function SidebarTodoCard({ history }: { history: any }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (history.preview) {
      const textToCopy = history.preview.map((t: string) => t.replace('[ ] ', '')).join('\n');
      
      const copyWithFallback = () => {
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy;
        textArea.style.position = "absolute";
        textArea.style.left = "-999999px";
        document.body.prepend(textArea);
        textArea.select();
        try {
          document.execCommand('copy');
        } catch (error) {
          console.error(error);
        } finally {
          textArea.remove();
        }
      };

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).catch((err) => {
          console.warn('Clipboard API blocked, using fallback.', err);
          copyWithFallback();
        });
      } else {
        copyWithFallback();
      }
      
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-white rounded-[20px] p-4 border border-gray-200/60 shadow-sm hover:shadow-md hover:border-blue-200 transition-all">
      <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-50">
        <div className="flex items-center gap-2 overflow-hidden flex-1">
          <div className="w-8 h-8 rounded-xl bg-green-50 text-green-600 flex items-center justify-center shrink-0">
            <CheckSquare className="w-4 h-4" />
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="text-[13px] font-medium text-gray-800 truncate">{history.title}</div>
          </div>
        </div>
        <button 
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 text-[12px] font-medium text-green-700 bg-white border border-green-200 hover:bg-green-50 rounded-full transition-colors cursor-pointer shrink-0"
        >
          {copied ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? '已复制' : '复制'}
        </button>
      </div>
      <div className="space-y-3.5">
        {history.preview.map((task: string, i: number) => (
          <div key={i} className="flex items-start gap-2.5 group/task cursor-pointer">
            <div className="mt-0.5 w-4 h-4 rounded border border-gray-300 shrink-0 bg-white group-hover/task:border-green-400 transition-colors flex items-center justify-center">
            </div>
            <span className="text-[12px] text-gray-600 leading-[1.4] group-hover/task:text-gray-900 transition-colors flex-1">
              {task.replace('[ ] ', '')}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AttachmentCard({ att }: { att: any }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (att.preview) {
      const textToCopy = att.preview.map((t: string) => t.replace('[ ] ', '')).join('\n');
      
      const copyWithFallback = () => {
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy;
        textArea.style.position = "absolute";
        textArea.style.left = "-999999px";
        document.body.prepend(textArea);
        textArea.select();
        try {
          document.execCommand('copy');
        } catch (error) {
          console.error(error);
        } finally {
          textArea.remove();
        }
      };

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).catch((err) => {
          console.warn('Clipboard API blocked, using fallback.', err);
          copyWithFallback();
        });
      } else {
        copyWithFallback();
      }
      
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (att.type === 'todo') {
    return (
      <div className="border border-gray-200 rounded-[24px] bg-white overflow-hidden w-full max-w-lg mt-2 shadow-sm">
        <div className="bg-[#f0fdf4] border-b border-gray-100 p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-700 font-medium text-[15px]">
            <CheckSquare className="w-5 h-5" />
            {att.title}
          </div>
          <button 
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-green-700 bg-white border border-green-200 hover:bg-green-50 rounded-full transition-colors cursor-pointer shadow-sm"
          >
            {copied ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? '已复制' : '复制待办'}
          </button>
        </div>
        <div className="p-5 space-y-4">
          {att.preview.map((task: string, i: number) => (
            <div key={i} className="flex items-start gap-3 group">
              <div className="mt-[3px] w-5 h-5 rounded border border-gray-300 flex-shrink-0 bg-white flex items-center justify-center group-hover:border-green-400 transition-colors shadow-sm" />
              <span className="text-[14px] text-gray-700 leading-relaxed select-text flex-1">{task.replace('[ ] ', '')}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-[24px] bg-white overflow-hidden w-full max-w-lg mt-2 shadow-sm flex flex-col">
      <div className="flex items-center gap-3 p-4 border-b border-gray-100">
        <div className={clsx("w-12 h-12 rounded-[14px] flex items-center justify-center bg-orange-50 border border-orange-100 shrink-0", att.color)}>
          <att.icon className="w-6 h-6" />
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="text-[15px] font-medium text-gray-800 truncate mb-1">{att.title}</div>
          <div className="text-[13px] text-gray-500 flex items-center gap-2">
            <span>{att.size}</span>
          </div>
        </div>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#1a73e8] bg-[#e8f0fe] hover:bg-blue-100 rounded-full transition-colors cursor-pointer shadow-sm">
          <Download className="w-4 h-4" /> 下载 PPT
        </button>
      </div>

      <div className="bg-[#f8fafd] p-5">
        <div className="aspect-video bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col p-6 relative">
          <div className="text-[15px] text-gray-800 font-medium whitespace-pre-wrap leading-relaxed flex-1 select-text">
            {att.preview[currentSlide]}
          </div>
          
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
            <button 
              onClick={() => setCurrentSlide(prev => Math.max(0, prev - 1))}
              disabled={currentSlide === 0}
              className="p-1.5 rounded-full hover:bg-gray-100 disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm text-gray-500 font-medium">
              {currentSlide + 1} / {att.preview.length}
            </span>
            <button 
              onClick={() => setCurrentSlide(prev => Math.min(att.preview.length - 1, prev + 1))}
              disabled={currentSlide === att.preview.length - 1}
              className="p-1.5 rounded-full hover:bg-gray-100 disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
