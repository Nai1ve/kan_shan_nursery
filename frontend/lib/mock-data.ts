import type {
  ContentSource,
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  MockBootstrap,
  ProfileData,
  SproutOpportunity,
  Tone,
  WateringMaterial,
  WorthReadingCard,
} from "./types";

const createdAt = "2026-05-09T09:00:00+08:00";

export const categories: InputCategory[] = [
  { id: "agent", name: "Agent 工程化", meta: "3 张卡 · 2 条可写", kind: "interest", active: true },
  { id: "ai-coding", name: "AI Coding", meta: "3 张卡 · 1 条发芽", kind: "interest" },
  { id: "rag", name: "RAG / 检索", meta: "3 张卡 · 1 条缺资料", kind: "interest" },
  { id: "backend", name: "后端工程", meta: "3 张卡 · 2 条经验", kind: "interest" },
  { id: "growth", name: "程序员成长", meta: "3 张卡 · 2 条观点", kind: "interest" },
  { id: "finance-risk", name: "金融风控", meta: "2 张卡 · 跨域输入", kind: "interest" },
  { id: "medical-ai", name: "医学 AI", meta: "2 张卡 · 严谨证据", kind: "interest" },
  { id: "product-design", name: "产品设计", meta: "2 张卡 · 工作流", kind: "interest" },
  { id: "content-creation", name: "内容创作", meta: "2 张卡 · 表达策略", kind: "interest" },
  { id: "following", name: "关注流精选", meta: "3 条社交输入", kind: "following" },
  { id: "serendipity", name: "偶遇输入", meta: "2 条远端关联", kind: "serendipity" },
];

const categoryName = new Map(categories.map((item) => [item.id, item.name]));

export const profile: ProfileData = {
  nickname: "看山编辑",
  accountStatus: "已关联知乎账号 · 演示模式",
  role: "技术创作者 / Java 后端转 AI Agent / 研究生",
  interests: categories.filter((item) => item.kind === "interest").map((item) => item.name),
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
    memory("agent", "进阶", ["系统设计", "质量评估", "失败恢复"], "框架 + 案例平衡", "避免停留在概念层，需要给出可落地的评估维度和失败模式。"),
    memory("ai-coding", "中级", ["工程交付", "研发工作流", "程序员成长"], "案例优先", "不要只讲工具趋势，需要补充具体工程场景和使用 AI 编程时的真实判断。"),
    memory("rag", "中级", ["检索质量", "文档解析", "评估指标"], "框架 + 数据平衡", "需要把召回、重排、上下文污染和业务失败案例讲清楚。"),
    memory("backend", "进阶", ["系统边界", "数据一致性", "工程交付"], "个人经验 + 案例", "适合加入 Java 后端、金融软件和数据同步项目中的真实判断。"),
    memory("growth", "中级", ["职业判断", "学习路径", "个人经历"], "个人经验 + 社区反馈", "允许表达鲜明立场，但要回应焦虑和反方质疑。"),
    memory("finance-risk", "中级", ["风险暴露", "可追责", "流程控制"], "案例 + 风险框架", "避免把金融风控类比套得太满，需要说明类比边界。"),
    memory("medical-ai", "入门", ["指标解释", "错误代价", "临床风险"], "论文 + 案例", "要谨慎，不做医疗建议，只讨论评估方法和风险意识。"),
    memory("product-design", "中级", ["用户任务", "协作流程", "信息架构"], "产品案例", "需要落到真实工作流，不只讲交互表层。"),
    memory("content-creation", "中级", ["表达结构", "社区语境", "读者反馈"], "案例 + 反馈", "要避免模板化写作，强调作者主体性和观点形成过程。"),
  ],
};

const cardSpecs: Array<{
  id: string;
  categoryId: string;
  title: string;
  recommendationReason: string;
  contentSummary: string;
  controversies: string[];
  writingAngles: string[];
  tags: { label: string; tone: Tone }[];
  featured?: boolean;
}> = [
  spec("agent-quality", "agent", "Agent Quality 到底评估什么？", "与你近期 Agent 质量系列内容高度相关，且站内讨论仍集中在表层指标。", "任务完成率被频繁讨论，但工具调用可靠性、上下文治理、失败恢复较少被系统化整理。", ["Agent 是否需要软件测试式质量体系？", "任务成功率是否足够？", "上下文污染如何评估？"], ["Agent 不是一次问答，而是可控工作流。", "Agent Quality 应该关注失败模式。"], "Agent Quality"),
  spec("agent-memory", "agent", "Agent 的 Memory 不只是聊天记录摘要", "和你的“观点种子库”产品机制相关，可以作为产品设计方法论文章。", "长期记忆需要区分事实、偏好、任务状态、写作风格和反馈信号。", ["记忆越多是否越好？", "用户是否应该可见、可编辑？", "如何避免自我强化？"], ["为什么创作 Agent 需要可编辑 Memory？", "Memory 应该服务于观点发芽。"], "Memory"),
  spec("agent-observe", "agent", "Agent 工程化为什么需要可观测性？", "多个开发者讨论 Agent 失败后很难复盘，适合转成工程实践文章。", "问题集中在工具调用链路、上下文变更、重试和回放能力。", ["Agent 失败算模型问题还是系统问题？", "日志是否足够复盘？", "如何避免黑盒执行？"], ["Agent 的可观测性应该记录什么？", "为什么 Agent 要能回放失败现场？"], "工程实践"),

  spec("ai-coding-growth", "ai-coding", "AI 编程工具会不会改变程序员的成长路径？", "这个话题近期讨论热度较高，并且和你过往关注的 Agent、编程、职业转型内容相关。", "当前讨论主要集中在 AI 是否会压缩初级程序员岗位，以及程序员是否还需要传统编码训练。", ["AI 是否会替代初级开发？", "编码能力和工程能力是否会分化？", "程序员学习路径是否需要重构？"], ["AI 时代，程序员真正需要训练的是什么？", "会写代码和能交付系统之间的差距会不会变大？", "初级程序员的成长路径是否正在被改写？"], "知乎热榜", true),
  spec("ai-coding-moat", "ai-coding", "AI Coding 产品的壁垒到底在哪里？", "多个高赞回答都在讨论“代码生成能力是否会同质化”，与你已有观点种子高度相关。", "讨论集中在模型能力、IDE 入口、私有代码库上下文、企业研发流程接入等方向。", ["模型能力是否足以形成壁垒？", "上下文积累是否真的难迁移？", "企业工作流是否比单点生成更重要？"], ["AI 编程工具的护城河，可能不在“会写代码”。", "企业真正需要的是代码生成，还是可控交付？"], "知乎搜索"),
  spec("ai-coding-leetcode", "ai-coding", "AI 时代还需要刷 LeetCode 吗？", "职业成长话题天然适合知乎回答，也能连接你对工程能力的判断。", "争论焦点从代码熟练度转向问题建模、边界分析和复杂度判断。", ["刷题价值是否降低？", "AI 是否会让基础训练失效？", "面试是否会改变？"], ["LeetCode 的价值正在从背模板转向建模训练。", "AI 时代初级程序员应该如何训练？"], "程序员成长"),

  spec("rag-eval", "rag", "RAG 系统真正难评估的是什么？", "站内讨论常停留在召回率，缺少业务失败案例和闭环评估。", "RAG 质量不仅是检索命中，还包括解析、切分、重排、引用和回答可用性。", ["召回率是否足够？", "重排能否解决所有问题？", "业务答案错了如何定位？"], ["RAG 评估应该从失败链路开始。", "为什么 RAG 不是检索组件堆叠？"], "RAG"),
  spec("rag-parser", "rag", "文档解析为什么会拖垮 RAG？", "这和工程落地高度相关，适合做技术拆解。", "PDF、表格、图片和权限边界会让知识库质量在入口处就出问题。", ["解析失败算算法问题还是工程问题？", "表格和图片如何进入上下文？"], ["RAG 的第一道难题是文档进入系统。", "为什么文档解析决定知识库上限？"], "文档解析"),
  spec("rag-context", "rag", "上下文越长，RAG 越不重要吗？", "这是一个高争议问题，可以通过反方视角写出深度。", "长上下文模型降低了一部分检索压力，但并没有消除数据治理和证据追踪。", ["长上下文会替代检索吗？", "引用和权限如何处理？"], ["长上下文不是知识治理。", "RAG 的价值可能从召回转向证据组织。"], "反方观点"),

  spec("backend-boundary", "backend", "后端系统里最难的往往不是写代码", "很适合承接你的 Java 后端经历，形成个人经验型文章。", "复杂系统的难点通常在边界、状态、兼容性和交付责任。", ["代码实现和系统交付差距在哪里？", "经验如何迁移到 AI Coding？"], ["为什么会写代码不等于能交付系统？", "从后端经验看 AI 编程的真实边界。"], "工程复盘"),
  spec("backend-consistency", "backend", "数据一致性问题为什么总在边界处爆炸？", "可用你的金融软件和同步系统经历补充案例。", "分布式系统的复杂性常来自补偿、幂等、重试和状态同步。", ["一致性是否只是数据库问题？", "业务补偿如何设计？"], ["数据同步系统最怕什么？", "幂等和补偿为什么是工程基本功？"], "分布式"),
  spec("backend-refactor", "backend", "AI 生成代码后，谁来负责系统演进？", "AI Coding 与后端工程交叉，适合写成工程判断文章。", "生成代码只是短期效率，长期维护仍依赖结构、边界和审查。", ["AI 代码是否增加技术债？", "审查责任如何划分？"], ["AI 时代代码审查更重要。", "后端工程师的价值会从实现转向判断。"], "代码审查"),

  spec("growth-junior", "growth", "初级程序员的训练机会会不会变少？", "这是知乎高讨论度问题，适合用稳健立场回应焦虑。", "AI 工具可能改变任务分配，但也会提高新人对抽象和验证能力的要求。", ["初级岗位是否减少？", "新人如何获得真实任务？"], ["初级程序员要从完成任务转向解释任务。", "AI 时代新人更需要工程基本功。"], "职业成长"),
  spec("growth-learning", "growth", "程序员学习路径要不要重排？", "和你的转 AI Agent 路径相关，有个人视角。", "从语言框架优先，转向问题建模、系统设计和工具协作。", ["基础还重要吗？", "项目经验如何替代刷课？"], ["AI 时代学习路线不该只追工具。", "工程判断力怎么训练？"], "学习路径"),
  spec("growth-expression", "growth", "技术人为什么写不出自己的观点？", "直接贴合看山小苗圃的产品定位，可作为项目介绍内容。", "技术人常有经验但缺少观点沉淀和表达结构。", ["表达是不是浪费时间？", "观点和经验如何区分？"], ["不动笔墨不读书在 AI 时代更重要。", "技术写作的核心是判断，不是排版。"], "内容表达"),

  spec("finance-risk-agent", "finance-risk", "Agent 的风险控制能不能借鉴金融风控？", "这是偶遇输入的远端关联来源，可形成差异化观点。", "金融风控关注风险暴露、审计、追责和极端场景，这些也适用于 Agent。", ["类比是否过度？", "Agent 风险是否可量化？"], ["Agent 产品的护城河可能在风险控制。", "从金融风控看 Agent 可控交付。"], "跨域类比"),
  spec("finance-audit", "finance-risk", "企业 AI 工具为什么绕不开审计？", "与企业级 AI Coding 落地强相关，适合补充论证材料。", "企业更关心权限、安全、日志、回滚和责任链。", ["审计会不会降低效率？", "开发者是否愿意被记录？"], ["可审计性是企业 AI 工具的底座。", "效率工具进入企业后会变成治理工具。"], "企业治理"),

  spec("medical-ai-metric", "medical-ai", "医学 AI 的指标为什么不能只看平均值？", "可帮助用户从高风险领域理解 Agent 评估。", "高召回不等于可交付，错误类型和错误代价同样重要。", ["总体指标是否掩盖风险？", "错误代价如何进入评估？"], ["Agent 评估也应该关注失败代价。", "不要只看成功率，要看错误类型。"], "医学 AI"),
  spec("medical-ai-human", "medical-ai", "AI 辅助决策里，人类确认环节为什么重要？", "能反哺“AI 代理表达但不代理立场”的产品原则。", "高风险场景要求人类保留最终判断，并理解模型输出边界。", ["人类确认是否只是形式？", "责任边界如何划分？"], ["创作 Agent 也需要作者主体性。", "AI 可以组织表达，但不能替用户决定相信什么。"], "风险边界"),

  spec("product-workbench", "product-design", "写作工具为什么应该做成工作台而不是聊天框？", "适合解释看山小苗圃的多页面产品架构。", "创作链路包含输入、观点、材料、写作、反馈，单一聊天框难以承载状态。", ["聊天框是否足够？", "工作台会不会太重？"], ["创作 Agent 需要状态可见。", "为什么观点种子比 prompt 更重要？"], "产品设计"),
  spec("product-memory", "product-design", "可编辑 Memory 是不是 AI 产品的基础设施？", "和个人画像页直接相关，可做产品方法论。", "用户需要知道系统为什么推荐、为什么这样写，也要能修正系统记忆。", ["Memory 是否会形成信息茧房？", "用户是否愿意维护？"], ["可见 Memory 能提高信任。", "AI 推荐要能解释也能被修正。"], "Memory"),

  spec("content-ai-declare", "content-creation", "AI 辅助创作应该如何保留作者主体性？", "回应知乎平台语境和 AI 声明风险，适合黑客松答辩。", "平台反对的不是高质量辅助，而是无立场、无营养的大水漫灌。", ["AI 参与度如何声明？", "作者观点如何证明？"], ["AI 代理表达，但不代理立场。", "高质量 AI 创作的前提是真实思考。"], "知乎语境"),
  spec("content-feedback", "content-creation", "文章反馈如何变成下一篇文章的资产？", "贴合历史反馈模块，可形成产品闭环解释。", "阅读完成率、收藏率和评论反方可以更新 Memory 和新种子。", ["数据会不会绑架表达？", "负反馈如何使用？"], ["反馈不是 KPI，而是下一轮思考材料。", "评论区可以反哺观点种子。"], "反馈闭环"),

  spec("following-workflow", "following", "AI Coding 产品正在从插件走向工作流入口", "与你“代码生成护城河浅”的旧种子强相关，可以直接触发今日发芽。", "作者认为未来竞争点不是补全几行代码，而是谁能进入需求、开发、测试和发布的完整链路。", ["插件级工具是否也能积累足够上下文？", "工作流入口是否会被平台垄断？"], ["AI 编程产品的壁垒在组织流程。", "代码生成只是入口，工程上下文才是资产。"], "关注作者"),
  spec("following-opponent", "following", "很多人反对“AI 替代初级程序员”的简单判断", "适合作为文章中的反方材料，能避免文章变成单向输出。", "评论区出现更细分歧：不是岗位是否消失，而是训练路径、任务来源和团队分工正在变化。", ["初级岗位是否真的减少？", "AI 是否会减少新人训练机会？"], ["初级成长路径被重塑，而非简单消失。"], "圈子讨论"),
  spec("following-rag", "following", "一位知识库产品作者复盘了 RAG 项目失败原因", "关注流里出现真实项目复盘，可以给 RAG 种子补案例。", "失败点集中在文档质量、权限边界、业务验收和引用可信度。", ["RAG 失败是技术问题还是业务问题？", "知识库怎样验收？"], ["RAG 项目失败通常不是模型一个点的问题。"], "关注流"),

  spec("serendipity-risk", "serendipity", "Agent 产品的护城河，不在单次任务完成率", "这和金融风控中的“风险暴露”很像：真正重要的是极端场景下是否可控、可追责、可回滚。", "AI 编程工具进入企业协作场景后，单次代码生成效果不再是全部，持续上下文和风险控制变得更重要。", ["单次生成能力是否会快速商品化？", "风险控制能否成为产品壁垒？"], ["Agent 产品的护城河在持续上下文、风险控制和工作流闭环。"], "偶遇卡片"),
  spec("serendipity-medical", "serendipity", "高召回不等于可交付", "医学检测模型不仅要看 mAP，还要看错误类型和临床后果。Agent 也类似，不能只看总体成功率。", "Agent 评测榜单开始关注任务成功率，但失败模式、错误代价和恢复机制仍未被充分讨论。", ["任务成功率是否足够？", "失败代价如何进入评估体系？"], ["Agent 评估应该关注失败模式、错误代价和恢复机制，而非只看均值指标。"], "偶遇卡片"),
];

export const cards: WorthReadingCard[] = cardSpecs.map((item, index) => ({
  ...item,
  originalSources: makeSources(item.categoryId, item.title, index),
  relevanceScore: 92 - (index % 8) * 3,
  authorityScore: 82 - (index % 5) * 4,
  popularityScore: 76 + (index % 6) * 3,
  controversyScore: 58 + (index % 7) * 5,
  createdAt,
}));

const seedMaterials: WateringMaterial[] = [
  material("evidence", "代码生成能力正在同质化", "多个 AI Coding 产品都把补全、生成测试、解释代码作为基础能力，差异正在从单点生成转向工作流。", "知乎搜索 / 高赞回答", true),
  material("counterargument", "长上下文模型可能削弱上下文壁垒", "反方认为模型窗口和企业知识库能力提升后，上下文积累不一定形成长期壁垒。", "圈子评论", true),
  material("personal_experience", "复杂后端系统的真实难点", "过去做金融软件和数据同步时，真正麻烦的是需求边界、状态变化、回滚追责，而不是写出某段代码。", "用户经验", false),
];

export const seeds: IdeaSeed[] = [
  {
    id: "seed-ai-coding-moat",
    interestId: "ai-coding",
    title: "AI 编程工具的护城河可能不在代码生成",
    interestName: "AI Coding",
    source: "知乎热榜 / 搜索结果 / 用户手动记录",
    sourceTitle: "AI Coding 产品的壁垒到底在哪里？",
    sourceSummary: "近期讨论集中在 AI 编程工具是否会替代程序员，以及代码生成能力是否会快速同质化。",
    sourceType: "zhihu_search",
    userReaction: "agree",
    userNote: "我认同代码生成会越来越普遍，但不认为这就是最终壁垒。",
    coreClaim: "单纯代码生成工具的护城河很浅，真正的壁垒可能在上下文积累、工作流入口、团队协作和企业数据闭环。",
    possibleAngles: ["AI 编程工具为什么会快速同质化？", "企业真正需要的是代码，还是可控的工程交付？", "Agent 产品的护城河到底在哪里？"],
    counterArguments: ["如果模型足够强，是否也能理解上下文？", "工作流入口是否会被平台垄断？"],
    requiredMaterials: ["AI 编程产品案例", "企业研发流程", "自己做复杂工程项目的经历"],
    wateringMaterials: seedMaterials,
    questions: [
      {
        id: "q-ai-context",
        question: "如果长上下文模型能读完整代码库，上下文还会是壁垒吗？",
        agentAnswer: "长上下文能降低读取门槛，但企业上下文还包括权限、历史决策、流程责任和团队协作数据，这些不是一次性塞进窗口就能稳定使用的资产。",
        citedSourceIds: ["source-ai-coding-moat-1", "source-ai-coding-moat-2"],
        status: "answered",
        createdAt,
      },
    ],
    status: "sproutable",
    maturityScore: 76,
    activationScore: 87,
    createdFromCardId: "ai-coding-moat",
    createdAt,
    updatedAt: createdAt,
  },
  {
    id: "seed-agent-quality",
    interestId: "agent",
    title: "Agent Quality 不能只看任务完成率",
    interestName: "Agent 工程化",
    source: "知乎搜索 / 关注作者 / 用户手动记录",
    sourceTitle: "Agent Quality 到底评估什么？",
    sourceSummary: "任务完成率被频繁讨论，但工具调用、上下文污染和失败恢复仍缺系统性框架。",
    sourceType: "zhihu_search",
    userReaction: "agree",
    userNote: "我认为 Agent 质量体系应该更接近工程可靠性评估，而不是单次问答评测。",
    coreClaim: "Agent 不是一次回答，而是持续执行的工作流，质量评估应覆盖失败模式和可恢复性。",
    possibleAngles: ["Agent Quality 的失败模式清单", "为什么任务完成率不是唯一指标"],
    counterArguments: ["质量体系是否会增加开发负担？", "小团队是否需要完整测试框架？"],
    requiredMaterials: ["真实工具调用失败案例", "可观测性和回放机制"],
    wateringMaterials: [
      material("evidence", "任务完成率不能解释失败链路", "只看最终成功与否无法定位工具调用、上下文污染、外部 API 异常等问题。", "关注流复盘", true),
      material("open_question", "Agent 质量体系会不会太重？", "需要找到轻量化的 P0 质量清单，避免把原型做成大而全平台。", "用户疑问", false),
    ],
    questions: [],
    status: "water_needed",
    maturityScore: 58,
    createdFromCardId: "agent-quality",
    createdAt,
    updatedAt: createdAt,
  },
];

export const sproutOpportunities: SproutOpportunity[] = [
  {
    id: "sprout-moat",
    seedId: "seed-ai-coding-moat",
    interestId: "ai-coding",
    score: 87,
    tags: [
      { label: "高时效", tone: "green" },
      { label: "发芽指数 87", tone: "blue" },
    ],
    activatedSeed: "单纯代码生成工具的护城河很浅。",
    triggerTopic: "某 AI 编程工具发布企业协作能力，引发“工作流入口”讨论。",
    whyWorthWriting: "这个热点验证了你之前的判断：当代码生成能力逐渐同质化，产品竞争重点会转向工作流入口、上下文管理和企业协作数据。",
    suggestedTitle: "AI 编程工具的护城河，可能不在“会写代码”",
    suggestedAngle: "从“代码生成能力商品化”切入，讨论 AI 编程产品真正的长期壁垒。",
    suggestedMaterials: "你过去做复杂系统时可以强调，真正困难的不是写代码，而是需求边界、状态变化、系统约束和交付责任。",
    status: "new",
  },
  {
    id: "sprout-quality",
    seedId: "seed-agent-quality",
    interestId: "agent",
    score: 79,
    tags: [
      { label: "缺案例", tone: "orange" },
      { label: "发芽指数 79", tone: "blue" },
    ],
    activatedSeed: "Agent Quality 不能只看任务完成率。",
    triggerTopic: "多个开发者讨论 Agent 调工具失败后无法复盘。",
    whyWorthWriting: "这个话题能连接 Agent 工程化和软件质量体系，适合写成可落地的清单。",
    suggestedTitle: "Agent Quality 到底评估什么？",
    suggestedAngle: "从失败模式、工具调用、上下文污染和回放能力切入。",
    suggestedMaterials: "补充一次真实工具调用失败或上下文污染导致错误输出的案例。",
    status: "new",
  },
];

export const feedbackArticles: FeedbackArticle[] = [
  {
    id: "article-moat",
    title: "AI 编程工具的护城河，可能不在“会写代码”",
    interestId: "ai-coding",
    linkedSeedId: "seed-ai-coding-moat",
    status: "表现良好",
    statusTone: "green",
    performanceSummary: "阅读完成率较高，收藏率高于平均值。评论区主要围绕“上下文是否真的构成壁垒”展开。",
    commentInsights: ["支持观点：企业研发流程确实比单次生成更重要。", "反方观点：未来长上下文模型可能会弱化这个壁垒。", "补充材料：多人提到权限、安全审计和团队知识库。"],
    memoryAction: "生成新种子：“AI Coding 的企业壁垒可能在权限、安全和组织知识库”。",
    metrics: [
      { label: "阅读完成率", value: 78 },
      { label: "收藏率", value: 42 },
      { label: "评论争议度", value: 69 },
    ],
  },
  {
    id: "article-quality",
    title: "Agent Quality 到底评估什么？",
    interestId: "agent",
    linkedSeedId: "seed-agent-quality",
    status: "需要复盘",
    statusTone: "orange",
    performanceSummary: "点赞不错，但评论指出文章偏框架化，缺少真实失败案例。",
    commentInsights: ["读者希望看到更多真实工具调用失败案例。", "有人质疑“质量体系是否会增加开发负担”。", "高赞评论建议补充可观测性和回放机制。"],
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

function memory(
  interestId: string,
  knowledgeLevel: string,
  preferredPerspective: string[],
  evidencePreference: string,
  writingReminder: string,
) {
  return {
    interestId,
    interestName: categoryName.get(interestId) ?? interestId,
    knowledgeLevel,
    preferredPerspective,
    evidencePreference,
    writingReminder,
  };
}

function spec(
  id: string,
  categoryId: string,
  title: string,
  recommendationReason: string,
  contentSummary: string,
  controversies: string[],
  writingAngles: string[],
  tagLabel: string,
  featured = false,
) {
  return {
    id,
    categoryId,
    title,
    recommendationReason,
    contentSummary,
    controversies,
    writingAngles,
    tags: [
      { label: tagLabel, tone: "blue" as Tone },
      { label: categoryId === "serendipity" ? "远端关联" : "高质量输入", tone: categoryId === "following" ? "green" as Tone : "orange" as Tone },
    ],
    featured,
  };
}

function makeSources(categoryId: string, title: string, index: number): ContentSource[] {
  const category = categoryName.get(categoryId) ?? "兴趣内容";
  const base = title.replace(/[？?]/g, "");
  return [
    {
      sourceId: `source-${categoryId}-${index}-hot`,
      sourceType: categoryId === "following" ? "关注流" : categoryId === "serendipity" ? "全网搜索" : "知乎热榜",
      sourceUrl: `https://mock.zhihu.local/${categoryId}/${index}/hot`,
      title: `${base}：热议问题`,
      author: categoryId === "following" ? "关注作者" : "知乎热榜",
      publishedAt: "2 小时前",
      authorityMeta: `热度 ${82 - (index % 5) * 4}`,
      meta: ["2 小时前", `热度 ${82 - (index % 5) * 4}`],
      rawExcerpt: `围绕“${base}”的讨论正在升温，评论区出现了支持与反对两类判断。`,
      fullContent: [
        `问题背景：${base} 近期在${category}相关讨论中持续出现。提问者关心的不只是结论，而是这个判断背后的适用范围、证据质量和反方意见。`,
        `核心信息：讨论区把问题拆成两层，一层是当前可观察到的趋势，另一层是趋势能否长期成立。支持者认为这个议题已经影响真实工作流，反对者则提醒不要把局部案例推广成行业规律。`,
        `可引用细节：热榜下的高赞互动集中在“为什么值得现在讨论”“这个问题和普通用户有什么关系”“写作者应该补充哪些经验”三个方向。`,
        `对写作的启发：适合作为文章开头的时效背景，但不能直接当作论证结论；进入写作前还需要补充具体案例、反方回应和个人观察。`,
      ].join("\n\n"),
      contribution: "提供时效背景和社区分歧入口。",
    },
    {
      sourceId: `source-${categoryId}-${index}-answer`,
      sourceType: categoryId === "serendipity" ? "跨域资料" : "知乎高赞回答",
      sourceUrl: `https://mock.zhihu.local/${categoryId}/${index}/answer`,
      title: `${category}视角下的关键论据`,
      author: "高赞答主",
      publishedAt: "昨天",
      authorityMeta: `赞同 ${(2.1 + (index % 4) * 0.6).toFixed(1)}k`,
      meta: ["昨天", `赞同 ${(2.1 + (index % 4) * 0.6).toFixed(1)}k`],
      rawExcerpt: `作者从${category}角度解释了为什么这个问题不能只看表层结论。`,
      fullContent: [
        `回答主线：作者从${category}的实际场景切入，先界定“${base}”不是一个单点能力问题，而是输入质量、执行流程、验证责任共同作用的结果。`,
        `关键论据：回答中把正方观点拆成三个支撑点：真实需求已经出现、旧方法存在明显成本、AI 或自动化能力需要被放进完整流程里评估。`,
        `边界提醒：作者没有把这个判断说满，强调不同团队、不同风险场景和不同使用深度会得到不同结论。`,
        `对写作的启发：可以抽取其中的结构作为论证骨架，但需要用自己的项目经验替换泛化表述。`,
      ].join("\n\n"),
      contribution: "提供正方论证材料和可引用表述。",
    },
    {
      sourceId: `source-${categoryId}-${index}-comment`,
      sourceType: "精选评论",
      sourceUrl: `https://mock.zhihu.local/${categoryId}/${index}/comments`,
      title: `${base}的反方质疑`,
      author: "圈子评论",
      publishedAt: "今天",
      authorityMeta: "精选 18 条",
      meta: ["今天", "精选 18 条"],
      rawExcerpt: "评论区集中质疑这个判断是否过度概括，并要求补充真实案例。",
      fullContent: [
        `评论焦点：反方评论主要质疑“${base}”是否被过度概括，以及当前材料是否足以支撑这么强的结论。`,
        `典型问题：有人要求补充失败案例，有人认为不同业务场景差异很大，也有人提醒写作者不要只引用支持自己观点的材料。`,
        `潜在反方：如果未来工具能力继续增强，当前的瓶颈是否会自然消失？如果只看少数高赞回答，会不会忽略沉默的大多数使用场景？`,
        `对写作的启发：适合作为文章中“我知道这个观点可能被这样反驳”的段落来源。`,
      ].join("\n\n"),
      contribution: "作为后续写作中的反方回应入口。",
    },
  ];
}

function material(
  type: WateringMaterial["type"],
  title: string,
  content: string,
  sourceLabel: string,
  adopted: boolean,
): WateringMaterial {
  return {
    id: `material-${type}-${sourceLabel}-${title}-${content.slice(0, 18)}`
      .replace(/[^a-zA-Z0-9\u4e00-\u9fa5-]+/g, "-")
      .slice(0, 96),
    type,
    title,
    content,
    sourceLabel,
    adopted,
    createdAt,
  };
}
