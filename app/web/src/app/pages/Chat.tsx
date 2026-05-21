import { useState, useRef, useEffect } from 'react';
import { 
  Sparkles, Send, Search, Activity, PieChart, Presentation,
  Building, Stethoscope, Calendar, X, Plus, ChevronDown, Database,
  Download, CheckSquare, Loader2, CheckCircle2, Eye, ChevronRight, ChevronLeft, Copy, Clock, FileText,
  Settings2, Bookmark, Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { clsx } from 'clsx';

// Configuration
const AVAILABLE_FIELDS: Record<string, any> = {
  clinic: { label: '门诊', icon: Building, options: ['全部门诊', '极橙仙乐斯店', '极橙徐汇店', '极橙大宁店', '极橙金桥店'] },
  doctor: { label: '医生', icon: Stethoscope, options: ['全部医生', '张大夫', '李大夫', '王大夫', '刘主任'] },
  time: { label: '时间段', icon: Calendar, options: ['近7天', '近30天', '上个月', '第一季度', '今年'] },
  output: { label: '产出格式', icon: FileText, options: ['自动判断', '生成待办 SOP', '生成 PPT 报告'] }
};

const DEFAULT_PROMPTS = [
  { id: 'analyze_renewal', title: '分析续卡率低的原因', icon: Activity, color: 'text-blue-500', isCustom: false },
  { id: 'analyze_conversion', title: '分析初诊转化漏斗', icon: PieChart, color: 'text-purple-500', isCustom: false },
  { id: 'generate_report', title: '生成本月经营报告', icon: Presentation, color: 'text-orange-500', isCustom: false },
  { id: 'check_appointment', title: '查看近期预约饱和度', icon: Calendar, color: 'text-green-500', isCustom: false },
  { id: 'analyze_lost', title: '流失高风险患者预警', icon: Activity, color: 'text-rose-500', isCustom: false },
  { id: 'doctor_performance', title: '核心医生业绩环比分析', icon: PieChart, color: 'text-indigo-500', isCustom: false },
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

export function Chat() {
  const [messages, setMessages] = useState<any[]>([]);
  const [prompts, setPrompts] = useState<any[]>(DEFAULT_PROMPTS);
  const [showPromptManager, setShowPromptManager] = useState(false);
  const [isSavingPrompt, setIsSavingPrompt] = useState(false);
  const [newPromptTitle, setNewPromptTitle] = useState('');
  const [activePrompt, setActivePrompt] = useState<any | null>(null);
  const [draftFields, setDraftFields] = useState<{key: string, value: string}[]>([
    { key: 'clinic', value: '极橙仙乐斯店' },
    { key: 'time', value: '近7天' }
  ]);
  const [previewPpt, setPreviewPpt] = useState<any | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, draftFields]);

  const handleSelectPrompt = (prompt: any) => {
    setActivePrompt(prompt);
    if (prompt.fields) {
      setDraftFields(prompt.fields);
    } else {
      setDraftFields([
        { key: 'clinic', value: '极橙仙乐斯店' },
        { key: 'doctor', value: '全部医生' },
        { key: 'time', value: '近30天' }
      ]);
    }
  };

  const handleSavePrompt = () => {
    if (!newPromptTitle.trim()) return;
    const newPrompt = {
      id: `custom_${Date.now()}`,
      title: newPromptTitle,
      icon: Search,
      color: 'text-[#1a73e8]',
      isCustom: true,
      fields: [...draftFields]
    };
    setPrompts(prev => [newPrompt, ...prev]);
    setIsSavingPrompt(false);
    setNewPromptTitle('');
    setActivePrompt(newPrompt);
  };

  const handleDeletePrompt = (id: string) => {
    setPrompts(prev => prev.filter(p => p.id !== id));
    if (activePrompt?.id === id) {
      setActivePrompt(null);
    }
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

  const handleSend = () => {
    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      title: activePrompt ? activePrompt.title : '自定义条件分析',
      fields: [...draftFields]
    };
    
    setMessages(prev => [...prev, userMsg]);
    setActivePrompt(null);
    setDraftFields([
      { key: 'clinic', value: '极橙仙乐斯店' },
      { key: 'time', value: '近7天' }
    ]);
    
    // Determine if it should be a report based on fields or prompt title
    const wantsReport = userMsg.title.includes('报告') || draftFields.some(f => f.value.includes('PPT') || f.value.includes('报告'));
    const clinicName = draftFields.find(f => f.key === 'clinic')?.value || '所选门诊';

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
        ...m, thinking: [...m.thinking, { text: `正在提取 ${clinicName} 在指定时间段内的就诊及回访记录`, source: 'HIS - 就诊表' }]
      } : m));
    }, 1000);

    setTimeout(() => {
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m, 
        isAnalyzing: false,
        text: `我已初步拉取了 **${clinicName}** 的数据。在分析过程中，我发现患者流失集中在两个显著方面：\n\n一是"候诊时间超过30分钟"引发的抱怨，二是"部分高客单价项目未提供灵活分期"。\n\n为了让产出物更符合您的执行需求，您希望我优先深挖并生成哪个方向的应对策略？`,
        options: [
          '深挖"等待时间长"的服务体验问题', 
          '深挖"高单价转化低"的价格敏感问题', 
          '全面综合分析并输出'
        ],
        meta: { wantsReport, clinicName }
      } : m));
    }, 2500);
  };

  const handleOptionSelect = (msgId: string, option: string, meta: any) => {
    // Disable options
    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, options: undefined } : m));

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
    }, 2500);
  };

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
            <h2 className="text-2xl font-semibold text-gray-800 mb-3">您好，我是口腔诊所续卡助手</h2>
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
                      <div className="text-[15px] font-medium text-gray-800 mb-3 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-[#1a73e8]" />
                        {msg.title}
                      </div>
                    )}
                    {msg.text && !msg.title && (
                      <div className="text-[15px] text-gray-800 leading-relaxed whitespace-pre-wrap">
                        {msg.text}
                      </div>
                    )}
                    {msg.fields && msg.fields.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {msg.fields.map((field: any, idx: number) => {
                          const def = AVAILABLE_FIELDS[field.key];
                          const Icon = def?.icon;
                          return (
                            <div key={idx} className="flex items-center bg-white border border-gray-200 rounded-full px-3.5 py-1.5 text-[13px] text-gray-700 shadow-sm">
                              <span className="text-gray-400 mr-2 flex items-center gap-1.5">
                                {Icon && <Icon className="w-3.5 h-3.5" />}
                                {def?.label || field.key}:
                              </span> 
                              <span className="font-medium text-[#1a73e8]">{field.value}</span>
                            </div>
                          )
                        })}
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
                          <div className="px-3.5 pb-3 pt-1 border-t border-gray-100/60 space-y-3">
                            {msg.thinking.map((step: any, idx: number) => (
                              <div key={idx} className="text-[13px] text-gray-600 flex items-start gap-2">
                                <span className="text-gray-400 mt-0.5 w-4 font-mono">{idx + 1}.</span>
                                <div className="flex-1 leading-relaxed">
                                  {step.text}
                                  {step.source && (
                                    <button className="inline-flex items-center gap-1 bg-[#e8f0fe] text-[#1a73e8] px-2 py-0.5 rounded-md border border-blue-100/50 hover:bg-blue-100 transition-colors ml-2 font-medium cursor-pointer">
                                      <Database className="w-3 h-3" /> {step.source}
                                    </button>
                                  )}
                                </div>
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
                            key={idx}
                            onClick={() => handleOptionSelect(msg.id, opt, msg.meta)}
                            className="text-left px-5 py-3 rounded-[16px] border border-blue-200 bg-[#f8fafd] text-[#1a73e8] text-[14px] hover:bg-blue-50 hover:border-blue-300 transition-colors cursor-pointer font-medium shadow-sm hover:shadow group w-fit pr-10 relative"
                          >
                            <span className="flex items-center gap-2">
                              <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs">{String.fromCharCode(65 + idx)}</span>
                              {opt}
                            </span>
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
          <div className="mb-4 flex items-center gap-2.5 overflow-x-auto w-full [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] pb-1 relative pr-10">
            {prompts.map(p => (
              <button 
                key={p.id}
                onClick={() => handleSelectPrompt(p)}
                className={clsx(
                  "shrink-0 px-4 py-2 bg-white/90 backdrop-blur-md border border-gray-200/80 rounded-full text-[13px] font-medium text-gray-700 hover:border-blue-300 transition-all flex items-center gap-2 shadow-sm hover:shadow-md hover:bg-white cursor-pointer",
                  activePrompt?.id === p.id ? "border-[#1a73e8] text-[#1a73e8] bg-blue-50/50" : "hover:text-[#1a73e8]"
                )}
              >
                <p.icon className={clsx("w-3.5 h-3.5", p.color)} />
                {p.title}
              </button>
            ))}
            
            <div className="absolute right-0 top-0 bottom-1 w-12 bg-gradient-to-l from-white/95 via-white/80 to-transparent flex items-center justify-end z-10 pointer-events-none">
              <button 
                onClick={() => setShowPromptManager(true)}
                className="p-1.5 rounded-full bg-white border border-gray-200 shadow-sm hover:border-blue-300 hover:text-[#1a73e8] text-gray-400 transition-colors cursor-pointer pointer-events-auto mr-1"
                title="管理建议"
              >
                <Settings2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div 
            className="bg-white border border-gray-200 shadow-[0_4px_20px_rgba(0,0,0,0.06)] rounded-[28px] p-6 relative z-10 w-full transition-shadow hover:shadow-[0_8px_30px_rgba(0,0,0,0.08)]"
          >
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2 text-[#1a73e8] font-medium text-[15px]">
                {activePrompt ? (
                  <><activePrompt.icon className="w-5 h-5" /> {activePrompt.title}</>
                ) : (
                  <><Search className="w-5 h-5" /> 自定义分析条件</>
                )}
              </div>
              {activePrompt && (
                <button onClick={() => setActivePrompt(null)} className="p-1.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer text-xs flex items-center gap-1">
                  <X className="w-3.5 h-3.5" /> 清除建议
                </button>
              )}
            </div>
            
            <div className="flex flex-wrap gap-3 mb-6">
                  {draftFields.map((field, index) => (
                    <FieldPill 
                      key={index} 
                      field={field} 
                      onRemove={() => {
                        const newFields = [...draftFields];
                        newFields.splice(index, 1);
                        setDraftFields(newFields);
                        setActivePrompt(null);
                      }}
                      onChange={(newVal: string) => {
                        const newFields = [...draftFields];
                        newFields[index].value = newVal;
                        setDraftFields(newFields);
                        setActivePrompt(null);
                      }} 
                    />
                  ))}
                  
                  {/* Add Field Button */}
                  {Object.keys(AVAILABLE_FIELDS).filter(k => !draftFields.find(f => f.key === k)).length > 0 && (
                    <AddDropdown 
                      availableKeys={Object.keys(AVAILABLE_FIELDS).filter(k => !draftFields.find(f => f.key === k))}
                      onAdd={(key: string, val: string) => {
                        setDraftFields([...draftFields, { key, value: val }]);
                        setActivePrompt(null);
                      }}
                    />
                  )}
                </div>

            <div className="flex justify-between items-center w-full">
              <div className="flex-1">
                {!activePrompt && draftFields.length > 0 && (
                  isSavingPrompt ? (
                    <div className="flex items-center gap-2">
                      <input 
                        type="text" 
                        autoFocus
                        value={newPromptTitle}
                        onChange={e => setNewPromptTitle(e.target.value)}
                        placeholder="输入配置名称..." 
                        className="text-[14px] border border-gray-200 rounded-[12px] px-3 py-1.5 w-48 focus:outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all bg-gray-50/50"
                        onKeyDown={e => e.key === 'Enter' && handleSavePrompt()}
                      />
                      <button onClick={handleSavePrompt} className="text-[13px] font-medium text-white bg-[#1a73e8] px-3.5 py-1.5 rounded-[10px] hover:bg-blue-600 transition-colors shadow-sm cursor-pointer">保存</button>
                      <button onClick={() => setIsSavingPrompt(false)} className="text-[13px] font-medium text-gray-500 hover:text-gray-700 px-2 py-1.5 transition-colors cursor-pointer">取消</button>
                    </div>
                  ) : (
                    <button 
                      onClick={() => setIsSavingPrompt(true)}
                      className="text-[13px] text-gray-500 hover:text-[#1a73e8] flex items-center gap-1.5 transition-colors font-medium px-2 py-1 rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <Bookmark className="w-3.5 h-3.5" /> 保存为常用配置
                    </button>
                  )
                )}
              </div>
              <div className="flex justify-end">
                <button 
                  onClick={handleSend} 
                  disabled={draftFields.length === 0}
                  className="bg-[#1a73e8] hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-[#1a73e8] text-white px-7 py-3 rounded-full text-[15px] font-medium transition-colors flex items-center gap-2 shadow-sm shadow-blue-500/20 cursor-pointer"
                >
                  <Sparkles className="w-4 h-4" /> 开始智能分析
                </button>
              </div>
            </div>
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
            className="absolute top-0 right-0 bottom-0 w-[560px] bg-white border-l border-gray-200 shadow-2xl z-30 flex flex-col"
          >
            <div className="flex items-center justify-between p-6 border-b border-gray-100 shrink-0">
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="w-10 h-10 rounded-xl bg-orange-50 text-orange-500 flex items-center justify-center shrink-0">
                  <Presentation className="w-5 h-5" />
                </div>
                <div className="overflow-hidden">
                  <h3 className="text-base font-semibold text-gray-800 truncate">{previewPpt.title}</h3>
                  <div className="text-sm text-gray-500 mt-0.5">{previewPpt.date} · {previewPpt.size}</div>
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

    {/* Right History Panel - always visible */}
    <div className="w-[280px] border-l border-gray-100 bg-[#f8fafd]/30 flex flex-col shrink-0 z-10 transition-all duration-300 ease-in-out">
      <div className="p-5 border-b border-gray-100/60 bg-white/50 backdrop-blur-sm sticky top-0">
        <h3 className="text-[14px] font-medium text-gray-800 flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#1a73e8]" />
          历史生成文件
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {RECENT_HISTORY.map(history => {
          if (history.type === 'todo') {
            return (
              <div key={history.id} className="bg-white rounded-[20px] p-4 border border-gray-100 shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                <div className="flex items-center gap-2 mb-3 pb-3 border-b border-gray-50">
                  <div className="w-8 h-8 rounded-xl bg-green-50 text-green-600 flex items-center justify-center shrink-0">
                    <CheckSquare className="w-4 h-4" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <div className="text-[13px] font-medium text-gray-800 truncate">{history.title}</div>
                    <div className="text-[11px] text-gray-400">{history.date}</div>
                  </div>
                </div>
                <div className="space-y-2.5">
                  {history.preview.map((task: string, i: number) => (
                    <div key={i} className="flex items-start gap-2.5 group/task cursor-pointer">
                      <div className="w-4 h-4 rounded border border-gray-300 mt-0.5 shrink-0 bg-white group-hover/task:border-green-400 transition-colors" />
                      <span className="text-[12px] text-gray-600 leading-snug group-hover/task:text-gray-900 transition-colors">
                        {task.replace('[ ] ', '')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          }

          return (
            <div 
              key={history.id} 
              className="bg-white rounded-[20px] border border-gray-100 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col group overflow-hidden"
            >
              <div 
                onClick={() => handleViewHistory(history)}
                className="flex items-start gap-3 p-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
              >
                <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-105", history.color, history.type === 'ppt' ? 'bg-orange-50' : 'bg-green-50')}>
                  <history.icon className="w-5 h-5" />
                </div>
                <div className="flex-1 overflow-hidden pt-0.5">
                  <div className="text-[13px] font-medium text-gray-800 line-clamp-2 leading-snug group-hover:text-[#1a73e8] transition-colors">{history.title}</div>
                  <div className="text-[11px] text-gray-400 mt-1.5 flex items-center gap-2">
                    <span>{history.date}</span>
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
          );
        })}
      </div>
    </div>

    {/* Prompt Manager Modal */}
    <AnimatePresence>
      {showPromptManager && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-gray-900/20 backdrop-blur-[2px] z-50 flex items-center justify-center p-4"
          onClick={() => setShowPromptManager(false)}
        >
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            onClick={e => e.stopPropagation()}
            className="bg-white rounded-[24px] shadow-2xl w-full max-w-md overflow-hidden flex flex-col max-h-[80vh]"
          >
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-medium text-gray-800 flex items-center gap-2">
                <Settings2 className="w-5 h-5 text-gray-400" />
                管理常用条件配置
              </h3>
              <button onClick={() => setShowPromptManager(false)} className="p-1.5 hover:bg-gray-100 rounded-full text-gray-400 transition-colors cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-2 overflow-y-auto">
              {prompts.length === 0 ? (
                <div className="py-8 text-center text-gray-400 text-sm">暂无常用配置</div>
              ) : (
                <div className="space-y-1">
                  {prompts.map(p => (
                    <div key={p.id} className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-xl group transition-colors">
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className={clsx("w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-white shadow-sm border border-gray-100", p.color)}>
                          <p.icon className="w-4 h-4" />
                        </div>
                        <div className="truncate">
                          <div className="text-[14px] font-medium text-gray-700 truncate">{p.title}</div>
                          {p.isCustom && <div className="text-[11px] text-gray-400 mt-0.5">自定义条件</div>}
                        </div>
                      </div>
                      <button 
                        onClick={() => handleDeletePrompt(p.id)}
                        className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all cursor-pointer shrink-0"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-100 bg-gray-50/50">
              <button 
                onClick={() => setShowPromptManager(false)}
                className="w-full py-2.5 bg-white border border-gray-200 rounded-xl text-[14px] font-medium text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer shadow-sm"
              >
                完成
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>

    </div>
  );
}

function FieldPill({ field, onRemove, onChange }: any) {
  const [isOpen, setIsOpen] = useState(false);
  const def = AVAILABLE_FIELDS[field.key];
  if (!def) return null;

  return (
    <div className="relative">
      <div className="flex items-center bg-[#f8fafd] border border-gray-200 hover:border-blue-200 hover:bg-white rounded-full pl-3.5 pr-1.5 py-1.5 shadow-sm transition-all group">
        <span className="text-[13px] text-gray-500 mr-2 flex items-center gap-1.5">
          <def.icon className="w-3.5 h-3.5" />
          {def.label}:
        </span>
        <button 
          onClick={() => setIsOpen(!isOpen)} 
          className="text-[14px] font-medium text-[#1a73e8] hover:text-blue-800 mr-2 outline-none cursor-pointer flex items-center gap-1"
        >
          {field.value}
          <ChevronDown className="w-3 h-3 opacity-50" />
        </button>
        <button onClick={onRemove} className="w-6 h-6 rounded-full flex items-center justify-center text-gray-400 hover:bg-gray-100 hover:text-red-500 transition-colors cursor-pointer">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      
      {isOpen && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-2 w-56 bg-white border border-gray-100 rounded-[20px] shadow-xl shadow-black/5 z-30 py-2 overflow-hidden transform origin-top animate-in fade-in zoom-in-95 duration-200">
            {def.options.map((opt: string) => (
              <button 
                key={opt} 
                onClick={() => { onChange(opt); setIsOpen(false); }}
                className="w-full text-left px-5 py-3 text-[14px] text-gray-700 hover:bg-[#f4f7fc] hover:text-[#1a73e8] transition-colors flex items-center justify-between cursor-pointer group-btn"
              >
                {opt}
                {field.value === opt && <CheckCircle2 className="w-4 h-4 text-[#1a73e8]" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function AddDropdown({ availableKeys, onAdd }: any) {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-4 py-2 rounded-full border border-dashed border-gray-300 text-[14px] text-gray-500 hover:border-[#1a73e8] hover:text-[#1a73e8] transition-colors bg-white cursor-pointer"
      >
        <Plus className="w-4 h-4" /> 添加条件
      </button>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setIsOpen(false)} />
          <div className="absolute bottom-full left-0 mb-2 w-48 bg-white border border-gray-100 rounded-[20px] shadow-xl shadow-black/5 z-30 py-2 transform origin-bottom animate-in fade-in zoom-in-95 duration-200">
            {availableKeys.map((k: string) => {
              const def = AVAILABLE_FIELDS[k];
              return (
                <button 
                  key={k}
                  onClick={() => { onAdd(k, def.options[0]); setIsOpen(false); }}
                  className="w-full text-left px-5 py-3 text-[14px] text-gray-700 hover:bg-[#f4f7fc] hover:text-[#1a73e8] transition-colors flex items-center gap-3 cursor-pointer"
                >
                  <def.icon className="w-4 h-4 text-gray-400" />
                  {def.label}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  )
}

function AttachmentCard({ att }: { att: any }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (att.preview) {
      const textToCopy = att.preview.map((t: string) => t.replace('[ ] ', '')).join('\n');
      
      try {
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(textToCopy);
        } else {
          // Fallback for restricted iframes
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
        }
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('Failed to copy text: ', err);
      }
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
        <div className="p-5 space-y-3.5">
          {att.preview.map((task: string, i: number) => (
            <div key={i} className="flex items-start gap-3 group">
              <div className="w-5 h-5 rounded border border-gray-300 mt-0.5 flex-shrink-0 bg-white flex items-center justify-center group-hover:border-green-400 transition-colors shadow-sm" />
              <span className="text-[14px] text-gray-700 leading-relaxed select-text">{task.replace('[ ] ', '')}</span>
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
