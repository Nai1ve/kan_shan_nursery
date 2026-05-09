import type {
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  MockBootstrap,
  ProfileData,
  SproutOpportunity,
  WorthReadingCard,
} from "./types";

export const profile: ProfileData = {
  nickname: "看山编辑",
  accountStatus: "已关联知乎账号 · 演示模式",
  role: "技术创作者 / Java 后端转 AI Agent / 研究生",
  interests: [
    "Agent 工程化",
    "RAG",
    "AI Coding",
    "Java 后端",
    "分布式系统",
    "程序员成长",
    "金融软件",
  ],
  avoidances:
    "不要替我决定立场；不要生成空泛、油滑、过度平衡的 AI 味文章；不要只追逐热度而牺牲我的工程视角。",
  globalMemory: {
    longTermBackground:
      "有三年 Java 后端开发经验，做过金融软件与复杂数据同步相关项目；当前关注 AI / LLM / Agent 工程化落地。",
    contentPreference:
      "偏好工程复盘、问题拆解、反方质疑、真实案例。更重视“为什么这样设计”，而不是单纯罗列概念。",
    writingStyle:
      "清晰、克制、偏工程师复盘视角；允许有观点锋芒，但避免标题党和情绪煽动。需要减少排比和 AI 套话。",
    recommendationStrategy:
      "按兴趣小类展开；关注流和偶遇输入作为平级入口。每次推荐都要说明为什么值得看，以及能否沉淀为观点种子。",
    riskReminder:
      "容易写成逻辑很完整但不够有个人经历的文章；需要在圆桌审稿阶段主动要求补充项目踩坑、个人判断和反方边界。",
  },
  interestMemories: [
    {
      interestName: "AI Coding",
      knowledgeLevel: "中级",
      preferredPerspective: ["工程交付", "研发工作流", "程序员成长"],
      evidencePreference: "案例优先",
      writingReminder:
        "不要只讲工具趋势，需要补充具体工程场景和使用 AI 编程时的真实判断。",
    },
    {
      interestName: "Agent 工程化",
      knowledgeLevel: "进阶",
      preferredPerspective: ["系统设计", "质量评估", "失败恢复"],
      evidencePreference: "框架 + 案例平衡",
      writingReminder:
        "避免停留在概念层，需要给出可落地的评估维度和失败模式。",
    },
    {
      interestName: "程序员成长",
      knowledgeLevel: "中级",
      preferredPerspective: ["职业判断", "学习路径", "个人经历"],
      evidencePreference: "个人经验 + 社区反馈",
      writingReminder: "允许表达鲜明立场，但要回应焦虑和反方质疑。",
    },
  ],
};

export const categories: InputCategory[] = [
  { id: "agent", name: "Agent 工程化", meta: "6 条输入 · 2 条可写", kind: "interest", available: true },
  { id: "ai-coding", name: "AI Coding", meta: "5 条输入 · 1 条发芽", kind: "interest", active: true, available: true },
  { id: "rag", name: "RAG / 检索", meta: "4 条输入", kind: "interest" },
  { id: "backend", name: "后端工程", meta: "3 条输入", kind: "interest" },
  { id: "growth", name: "程序员成长", meta: "4 条输入", kind: "interest" },
  { id: "following", name: "关注流精选", meta: "5 条社交输入", kind: "following", available: true },
  { id: "serendipity", name: "偶遇输入", meta: "2 条远端关联", kind: "serendipity", available: true },
];

export const cards: WorthReadingCard[] = [
  {
    id: "ai-coding-growth",
    categoryId: "ai-coding",
    featured: true,
    tags: [
      { label: "知乎热榜", tone: "blue" },
      { label: "争议度高", tone: "orange" },
    ],
    title: "AI 编程工具会不会改变程序员的成长路径？",
    recommendationReason:
      "这个话题近期讨论热度较高，并且和你过往关注的 Agent、编程、职业转型内容相关。",
    originalSources: [
      {
        sourceType: "知乎热榜",
        title: "AI 编程工具普及后，初级程序员的成长路径会被改写吗？",
        meta: ["2 小时前", "热度 86"],
        rawExcerpt:
          "讨论集中在初级开发是否会被工具替代，以及新人是否还有足够的真实任务训练机会。",
        contribution: "提供时效背景和职业焦虑入口。",
      },
      {
        sourceType: "知乎高赞回答",
        title: "AI 降低的是机械编码门槛，不是问题抽象能力",
        meta: ["作者：后端工程师 A", "赞同 3.2k"],
        rawExcerpt:
          "代码实现会被加速，但需求拆解、边界判断、复杂度分析仍依赖工程经验。",
        contribution: "支撑“刷题目标要变化”的正方论据。",
      },
      {
        sourceType: "圈子评论",
        title: "如果模型能读完整代码库，上下文还会是壁垒吗？",
        meta: ["反方材料", "精选 18 条"],
        rawExcerpt:
          "评论区提出反方质疑：长上下文模型和企业知识库可能会削弱工程上下文壁垒。",
        contribution: "作为后续写作中的反方回应入口。",
      },
    ],
    contentSummary:
      "当前讨论主要集中在 AI 是否会压缩初级程序员岗位，以及程序员是否还需要传统编码训练。",
    controversies: [
      "AI 是否会替代初级开发？",
      "编码能力和工程能力是否会分化？",
      "程序员学习路径是否需要重构？",
    ],
    writingAngles: [
      "AI 时代，程序员真正需要训练的是什么？",
      "会写代码和能交付系统之间的差距会不会变大？",
      "初级程序员的成长路径是否正在被改写？",
    ],
  },
  {
    id: "ai-coding-moat",
    categoryId: "ai-coding",
    tags: [
      { label: "知乎搜索", tone: "blue" },
      { label: "高质量讨论", tone: "green" },
    ],
    title: "AI Coding 产品的壁垒到底在哪里？",
    recommendationReason:
      "多个高赞回答都在讨论“代码生成能力是否会同质化”，与你已有观点种子高度相关。",
    contentSummary:
      "讨论集中在模型能力、IDE 入口、私有代码库上下文、企业研发流程接入等方向。",
    controversies: [
      "模型能力是否足以形成壁垒？",
      "上下文积累是否真的难迁移？",
      "企业工作流是否比单点生成更重要？",
    ],
    writingAngles: [
      "AI 编程工具的护城河，可能不在“会写代码”。",
      "企业真正需要的是代码生成，还是可控交付？",
      "从工程上下文看 AI Coding 的长期竞争。",
    ],
  },
  {
    id: "agent-quality",
    categoryId: "agent",
    tags: [{ label: "Agent Quality", tone: "blue" }],
    title: "Agent Quality 到底评估什么？",
    recommendationReason:
      "与你近期 Agent 质量系列内容高度相关，且站内讨论仍集中在表层指标。",
    contentSummary:
      "任务完成率被频繁讨论，但工具调用可靠性、上下文治理、失败恢复较少被系统化整理。",
    controversies: [
      "Agent 是否需要软件测试式质量体系？",
      "任务成功率是否足够？",
      "上下文污染如何评估？",
    ],
    writingAngles: ["Agent 不是一次问答，而是可控工作流。", "Agent Quality 应该关注失败模式。"],
  },
  {
    id: "agent-memory",
    categoryId: "agent",
    tags: [{ label: "Memory", tone: "blue" }],
    title: "Agent 的 Memory 不只是聊天记录摘要",
    recommendationReason:
      "和你的“观点种子库”产品机制相关，可以作为产品设计方法论文章。",
    contentSummary:
      "长期记忆需要区分事实、偏好、任务状态、写作风格和反馈信号。",
    controversies: ["记忆越多是否越好？", "用户是否应该可见、可编辑？", "如何避免自我强化？"],
    writingAngles: ["为什么创作 Agent 需要可编辑 Memory？", "Memory 应该服务于观点发芽。"],
  },
  {
    id: "following-workflow",
    categoryId: "following",
    tags: [
      { label: "关注作者", tone: "green" },
      { label: "产品思考", tone: "blue" },
    ],
    title: "AI Coding 产品正在从插件走向工作流入口",
    recommendationReason:
      "与你“代码生成护城河浅”的旧种子强相关，可以直接触发今日发芽。",
    contentSummary:
      "作者认为未来竞争点不是补全几行代码，而是谁能进入需求、开发、测试和发布的完整链路。",
    controversies: ["插件级工具是否也能积累足够上下文？", "工作流入口是否会被平台垄断？"],
    writingAngles: ["AI 编程产品的壁垒在组织流程。", "代码生成只是入口，工程上下文才是资产。"],
  },
  {
    id: "following-opponent",
    categoryId: "following",
    tags: [
      { label: "圈子讨论", tone: "green" },
      { label: "反方多", tone: "orange" },
    ],
    title: "很多人反对“AI 替代初级程序员”的简单判断",
    recommendationReason: "适合作为文章中的反方材料，能避免文章变成单向输出。",
    contentSummary:
      "评论区出现更细分歧：不是岗位是否消失，而是训练路径、任务来源和团队分工正在变化。",
    controversies: ["初级岗位是否真的减少？", "AI 是否会减少新人训练机会？"],
    writingAngles: ["初级成长路径被重塑，而非简单消失。"],
  },
  {
    id: "serendipity-risk",
    categoryId: "serendipity",
    tags: [
      { label: "偶遇卡片", tone: "purple" },
      { label: "金融风控", tone: "green" },
    ],
    title: "Agent 产品的护城河，不在单次任务完成率",
    recommendationReason:
      "这和金融风控中的“风险暴露”很像：真正重要的是极端场景下是否可控、可追责、可回滚。",
    contentSummary:
      "AI 编程工具进入企业协作场景后，单次代码生成效果不再是全部，持续上下文和风险控制变得更重要。",
    controversies: ["单次生成能力是否会快速商品化？", "风险控制能否成为产品壁垒？"],
    writingAngles: ["Agent 产品的护城河在持续上下文、风险控制和工作流闭环。"],
  },
  {
    id: "serendipity-medical",
    categoryId: "serendipity",
    tags: [
      { label: "偶遇卡片", tone: "purple" },
      { label: "医学 AI", tone: "blue" },
    ],
    title: "高召回不等于可交付",
    recommendationReason:
      "医学检测模型不仅要看 mAP，还要看错误类型和临床后果。Agent 也类似，不能只看总体成功率。",
    contentSummary:
      "Agent 评测榜单开始关注任务成功率，但失败模式、错误代价和恢复机制仍未被充分讨论。",
    controversies: ["任务成功率是否足够？", "失败代价如何进入评估体系？"],
    writingAngles: ["Agent 评估应该关注失败模式、错误代价和恢复机制，而非只看均值指标。"],
  },
];

export const seeds: IdeaSeed[] = [
  {
    id: "seed-ai-coding-moat",
    title: "AI 编程工具的护城河可能不在代码生成",
    interestName: "AI 编程",
    statusLabel: "当前状态：可发芽",
    statusTone: "green",
    source: "知乎热榜 / 搜索结果 / 用户手动记录",
    sourceSummary:
      "近期讨论集中在 AI 编程工具是否会替代程序员，以及代码生成能力是否会快速同质化。",
    userReaction: "我认同代码生成会越来越普遍，但不认为这就是最终壁垒。",
    coreClaim:
      "单纯代码生成工具的护城河很浅，真正的壁垒可能在上下文积累、工作流入口、团队协作和企业数据闭环。",
    possibleAngles: [
      "AI 编程工具为什么会快速同质化？",
      "企业真正需要的是代码，还是可控的工程交付？",
      "Agent 产品的护城河到底在哪里？",
    ],
    requiredMaterials: ["AI 编程产品案例", "企业研发流程", "自己做复杂工程项目的经历"],
  },
  {
    id: "seed-agent-quality",
    title: "Agent Quality 不能只看任务完成率",
    interestName: "Agent 工程",
    statusLabel: "当前状态：缺案例",
    statusTone: "orange",
    source: "知乎搜索 / 关注作者 / 用户手动记录",
    sourceSummary:
      "任务完成率被频繁讨论，但工具调用、上下文污染和失败恢复仍缺系统性框架。",
    userReaction: "我认为 Agent 质量体系应该更接近工程可靠性评估，而不是单次问答评测。",
    coreClaim:
      "Agent 不是一次回答，而是持续执行的工作流，质量评估应覆盖失败模式和可恢复性。",
    possibleAngles: ["Agent Quality 的失败模式清单", "为什么任务完成率不是唯一指标"],
    requiredMaterials: ["真实工具调用失败案例", "可观测性和回放机制"],
  },
];

export const sproutOpportunities: SproutOpportunity[] = [
  {
    id: "sprout-moat",
    score: 87,
    tags: [
      { label: "高时效", tone: "green" },
      { label: "发芽指数 87", tone: "blue" },
    ],
    activatedSeed: "单纯代码生成工具的护城河很浅。",
    triggerTopic: "某 AI 编程工具宣布被收购 / 发布企业版 / 引发讨论。",
    whyWorthWriting:
      "这个热点验证了你之前的判断：当代码生成能力逐渐同质化，产品竞争重点会转向工作流入口、上下文管理和企业协作数据。",
    suggestedTitle: "AI 编程工具的护城河，可能不在“会写代码”",
    suggestedAngle: "从“代码生成能力商品化”切入，讨论 AI 编程产品真正的长期壁垒。",
    suggestedMaterials:
      "你过去做复杂系统时可以强调，真正困难的不是写代码，而是需求边界、状态变化、系统约束和交付责任。",
  },
  {
    id: "sprout-leetcode",
    score: 79,
    tags: [
      { label: "适合回答", tone: "orange" },
      { label: "发芽指数 79", tone: "blue" },
    ],
    activatedSeed: "AI 时代不是不需要刷题，而是刷题目标要变化。",
    triggerTopic: "程序员就业与 AI 编程工具讨论升温。",
    whyWorthWriting: "这个话题能连接职业焦虑和学习方法，容易形成知乎回答。",
    suggestedTitle: "AI 时代，程序员还需要刷 LeetCode 吗？",
    suggestedAngle: "LeetCode 的价值从代码熟练度转向问题建模。",
    suggestedMaterials:
      "补充你自己用 AI 写代码时，哪些任务变快了，哪些任务仍需要人工判断。",
  },
];

export const feedbackArticles: FeedbackArticle[] = [
  {
    id: "article-moat",
    title: "AI 编程工具的护城河，可能不在“会写代码”",
    status: "表现良好",
    statusTone: "green",
    performanceSummary:
      "阅读完成率较高，收藏率高于平均值。评论区主要围绕“上下文是否真的构成壁垒”展开。",
    commentInsights: [
      "支持观点：企业研发流程确实比单次生成更重要。",
      "反方观点：未来长上下文模型可能会弱化这个壁垒。",
      "补充材料：多人提到权限、安全审计和团队知识库。",
    ],
    memoryAction:
      "生成新种子：“AI Coding 的企业壁垒可能在权限、安全和组织知识库”。",
    metrics: [
      { label: "阅读完成率", value: 78 },
      { label: "收藏率", value: 42 },
      { label: "评论争议度", value: 69 },
    ],
  },
  {
    id: "article-quality",
    title: "Agent Quality 到底评估什么？",
    status: "需要复盘",
    statusTone: "orange",
    performanceSummary: "点赞不错，但评论指出文章偏框架化，缺少真实失败案例。",
    commentInsights: [
      "读者希望看到更多真实工具调用失败案例。",
      "有人质疑“质量体系是否会增加开发负担”。",
      "高赞评论建议补充可观测性和回放机制。",
    ],
    memoryAction: "将“真实案例不足”写入写作风险 Memory，下次自动提醒补案例。",
    metrics: [
      { label: "阅读完成率", value: 61 },
      { label: "收藏率", value: 35 },
      { label: "案例需求", value: 82 },
    ],
  },
];

export const mockBootstrap: MockBootstrap = {
  profile,
  categories,
  cards,
  seeds,
  sproutOpportunities,
  feedbackArticles,
};
