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
  { id: "shuma", name: "数码科技", meta: "2 张卡 · 1 条发芽", kind: "interest", active: true },
  { id: "zhichang", name: "职场教育", meta: "2 张卡 · 2 条观点", kind: "interest" },
  { id: "chuangzuo", name: "创作表达", meta: "2 张卡 · 1 条缺资料", kind: "interest" },
  { id: "shenghuo", name: "生活方式", meta: "2 张卡", kind: "interest" },
  { id: "shehui", name: "社会人文", meta: "2 张卡", kind: "interest" },
  { id: "bendi", name: "本地城市", meta: "2 张卡", kind: "interest" },
  { id: "following", name: "关注流精选", meta: "3 条社交输入", kind: "following" },
  { id: "serendipity", name: "偶遇输入", meta: "2 条远端关联", kind: "serendipity" },
];

const categoryName = new Map(categories.map((item) => [item.id, item.name]));

export const profile: ProfileData = {
  nickname: "看山编辑",
  accountStatus: "已关联知乎账号 · 演示模式",
  role: "技术创作者 / Java 后端转 AI Agent / 研究生",
  interests: ["数码科技", "职场教育", "创作表达", "生活方式", "社会人文", "本地城市"],
  avoidances:
    "不要替我决定立场；不要生成空泛、油滑、过度平衡的 AI 味文章；不要只追逐热度而牺牲我的工程视角。",
  globalMemory: {
    longTermBackground:
      "有三年工作经验，关注科技、职场和个人成长领域；当前希望通过阅读和写作沉淀自己的观点。",
    contentPreference:
      "偏好真实经历、问题拆解、反方质疑。更重视'为什么这样想'而不是单纯罗列信息。",
    writingStyle:
      "清晰、克制；允许有观点锋芒，但避免标题党和情绪煽动。",
    recommendationStrategy:
      "按兴趣小类展开；关注流和偶遇输入作为平级入口。每次推荐都要说明为什么值得看。",
    riskReminder:
      "容易写成逻辑完整但缺少个人经历的文章；需要在写作阶段主动补充真实案例。",
  },
  interestMemories: [
    memory("shuma", "进阶", ["设备", "软件", "AI", "消费电子"], "案例优先", "避免停留在概念层，需要给出可落地的评估维度和真实使用场景。"),
    memory("zhichang", "中级", ["职业判断", "学习路径", "个人经历"], "个人经验+案例", "允许表达鲜明立场，但要回应焦虑和反方质疑。"),
    memory("chuangzuo", "中级", ["表达结构", "社区语境", "读者反馈"], "案例+反馈", "要避免模板化写作，强调作者主体性和观点形成过程。"),
    memory("shenghuo", "入门", ["生活经验", "实用建议"], "个人经验优先", "真实体验比框架更重要，允许轻松但不空泛。"),
    memory("shehui", "中级", ["社会观察", "人文思考"], "资料+观点平衡", "需要有论据支撑，避免情绪化判断。"),
    memory("bendi", "入门", ["本地生活", "城市观察"], "个人体验优先", "以真实体验为主，不需要宏大叙事。"),
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
  // shuma (数码科技) - 2 cards
  spec("ai-coding-growth", "shuma", "AI 编程工具会不会改变程序员的成长路径？", "这个话题近期讨论热度较高，并且和你过往关注的 AI、编程、职业转型内容相关。", "当前讨论主要集中在 AI 是否会压缩初级程序员岗位，以及程序员是否还需要传统编码训练。", ["AI 是否会替代初级开发？", "编码能力和工程能力是否会分化？", "程序员学习路径是否需要重构？"], ["AI 时代，程序员真正需要训练的是什么？", "会写代码和能交付系统之间的差距会不会变大？"], "知乎热榜", true),
  spec("ai-coding-moat", "shuma", "AI Coding 产品的壁垒到底在哪里？", "多个高赞回答都在讨论代码生成能力是否会同质化，与你已有观点种子高度相关。", "讨论集中在模型能力、IDE 入口、私有代码库上下文、企业研发流程接入等方向。", ["模型能力是否足以形成壁垒？", "上下文积累是否真的难迁移？", "企业工作流是否比单点生成更重要？"], ["AI 编程工具的护城河，可能不在会写代码。", "企业真正需要的是代码生成，还是可控交付？"], "知乎搜索"),

  // zhichang (职场教育) - 2 cards
  spec("tech-to-management", "zhichang", "技术人转型管理，最难的不是带团队而是放手", "技术管理者转型是职场教育中的高频话题，适合用个人经验切入。", "技术深度和管理广度之间的取舍，放手是否等于放弃技术。", ["技术深度 vs 管理广度？", "放手是否等于放弃技术？"], ["从写代码到带团队的思维转变。"], "职场教育"),
  spec("online-degree", "zhichang", "在线课程真的能替代传统学位吗？", "在线教育和传统学位的争论持续存在，适合用个人学习经历回应。", "学习效率和认证价值的权衡，不同场景下结论不同。", ["学习效率 vs 认证价值？"], ["个人学习经历的判断。"], "职场教育"),

  // chuangzuo (创作表达) - 2 cards
  spec("writing-method", "chuangzuo", "好的技术长文，通常不是资料多，而是问题问得准", "关注作者的方法论总结，与看山小苗圃的产品定位直接相关。", "资料充分不等于有价值，技术文章需要强观点和好问题。", ["资料充分=有价值？", "技术文章必须有强观点？"], ["关键不是堆概念而是建立问题。"], "关注作者"),
  spec("content-strategy", "chuangzuo", "知乎回答的开头为什么这么重要？", "开头策略是创作表达中的实用技巧，适合用案例说明。", "开头决定阅读率，但不能沦为标题党。", ["开头决定阅读率？"], ["开头策略。"], "创作表达"),

  // shenghuo (生活方式) - 2 cards
  spec("minimalism", "shenghuo", "极简生活一年后，我真正丢掉了什么？", "生活方式话题适合用个人经历切入，容易引发共鸣。", "极简是消费升级还是降级，每个人答案不同。", ["极简是消费升级还是降级？"], ["个人经历。"], "生活方式"),
  spec("cooking-efficiency", "shenghuo", "做饭这件事，效率和幸福感真的矛盾吗？", "日常话题容易引发讨论，适合轻松但有观点的写法。", "效率做饭和享受过程之间的取舍。", ["效率做饭 vs 享受过程？"], ["个人经验。"], "生活方式"),

  // shehui (社会人文) - 2 cards
  spec("ai-education", "shehui", "AI 会不会让教育更不公平？", "AI 与教育公平是社会人文中的热点议题，适合用社会观察视角写。", "AI 缩小还是扩大教育差距，取决于基础设施和资源分配。", ["AI 缩小还是扩大教育差距？"], ["社会观察。"], "社会人文"),
  spec("reading-habit", "shehui", "为什么年轻人越来越不爱读书了？", "文化观察类话题适合用数据和个人体验结合写。", "碎片化阅读算不算阅读，定义本身就在变化。", ["碎片化阅读算不算阅读？"], ["文化观察。"], "社会人文"),

  // bendi (本地城市) - 2 cards
  spec("city-life", "bendi", "在一线城市租房，最不值得花的钱是什么？", "本地生活经验是知乎高互动话题，适合用真实体验写。", "花钱提升租房体验是否值得，每个人标准不同。", ["花钱提升租房体验值不值？"], ["本地生活经验。"], "本地城市"),
  spec("hidden-spots", "bendi", "你所在城市有哪些被低估的角落？", "城市观察类话题适合轻松分享，互动性强。", "被低估的角落往往藏着城市的真实面貌。", [], ["城市观察。"], "本地城市"),

  // following (关注流精选) - 3 cards
  spec("following-product", "following", "Product thinking from a followed author", "关注作者的产品思考，可以触发观点交叉。", "作者从产品设计角度讨论了用户任务和工作流。", ["产品设计是否需要更关注用户任务？"], ["产品思考可以跨领域迁移。"], "关注作者"),
  spec("following-ring", "following", "圈子讨论：一个有意思的观点", "圈子里的讨论往往有不同视角，适合做反方材料。", "圈子讨论中的观点碰撞。", ["不同视角是否都能成立？"], ["圈子讨论。"], "圈子讨论"),
  spec("following-method", "following", "好的技术长文方法论", "关注作者的方法论分享，可以补充写作策略。", "方法论层面的总结对写作有直接帮助。", ["方法论是否可迁移？"], ["方法论。"], "关注作者"),

  // serendipity (偶遇输入) - 2 cards
  spec("serendipity-finance", "serendipity", "金融风控领域的 AI 应用", "偶遇卡片帮助拓展视野，从远端关联中发现新角度。", "金融风控中的 AI 应用涉及风险暴露、审计和追责。", ["AI 在金融风控中是否可靠？", "风险控制能否成为产品壁垒？"], ["今天的技术热点", "远端关联", "可能产生的观点"], "偶遇卡片"),
  spec("serendipity-medical", "serendipity", "医学 AI 的伦理边界", "偶遇卡片帮助从不同领域获得启发。", "医学 AI 涉及伦理边界、错误代价和临床风险。", ["医学 AI 的伦理边界在哪里？", "错误代价如何进入评估？"], ["远端关联。"], "偶遇卡片"),
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
    interestId: "shuma",
    title: "AI 编程工具的护城河可能不在代码生成",
    interestName: "数码科技",
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
    interestId: "shuma",
    title: "Agent Quality 不能只看任务完成率",
    interestName: "数码科技",
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
    interestId: "shuma",
    score: 87,
    tags: [
      { label: "高时效", tone: "green" },
      { label: "发芽指数 87", tone: "blue" },
    ],
    activatedSeed: "单纯代码生成工具的护城河很浅。",
    triggerTopic: "某 AI 编程工具发布企业协作能力，引发工作流入口讨论。",
    whyWorthWriting: "这个热点验证了你之前的判断：当代码生成能力逐渐同质化，产品竞争重点会转向工作流入口、上下文管理和企业协作数据。",
    suggestedTitle: "AI 编程工具的护城河，可能不在会写代码",
    suggestedAngle: "从代码生成能力商品化切入，讨论 AI 编程产品真正的长期壁垒。",
    suggestedMaterials: "你过去做复杂系统时可以强调，真正困难的不是写代码，而是需求边界、状态变化、系统约束和交付责任。",
    status: "new",
  },
  {
    id: "sprout-quality",
    seedId: "seed-agent-quality",
    interestId: "shuma",
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
    title: "AI 编程工具的护城河，可能不在会写代码",
    interestId: "shuma",
    linkedSeedId: "seed-ai-coding-moat",
    status: "表现良好",
    statusTone: "green",
    performanceSummary: "阅读完成率较高，收藏率高于平均值。评论区主要围绕上下文是否真的构成壁垒展开。",
    commentInsights: ["支持观点：企业研发流程确实比单次生成更重要。", "反方观点：未来长上下文模型可能会弱化这个壁垒。", "补充材料：多人提到权限、安全审计和团队知识库。"],
    memoryAction: "生成新种子：AI Coding 的企业壁垒可能在权限、安全和组织知识库。",
    metrics: [
      { label: "阅读完成率", value: 78 },
      { label: "收藏率", value: 42 },
      { label: "评论争议度", value: 69 },
    ],
  },
  {
    id: "article-quality",
    title: "Agent Quality 到底评估什么？",
    interestId: "shuma",
    linkedSeedId: "seed-agent-quality",
    status: "需要复盘",
    statusTone: "orange",
    performanceSummary: "点赞不错，但评论指出文章偏框架化，缺少真实失败案例。",
    commentInsights: ["读者希望看到更多真实工具调用失败案例。", "有人质疑质量体系是否会增加开发负担。", "高赞评论建议补充可观测性和回放机制。"],
    memoryAction: "将真实案例不足写入写作风险 Memory，下次自动提醒补案例。",
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
      rawExcerpt: `围绕"${base}"的讨论正在升温，评论区出现了支持与反对两类判断。`,
      fullContent: [
        `问题背景：${base} 近期在${category}相关讨论中持续出现。提问者关心的不只是结论，而是这个判断背后的适用范围、证据质量和反方意见。`,
        `核心信息：讨论区把问题拆成两层，一层是当前可观察到的趋势，另一层是趋势能否长期成立。支持者认为这个议题已经影响真实工作流，反对者则提醒不要把局部案例推广成行业规律。`,
        `可引用细节：热榜下的高赞互动集中在"为什么值得现在讨论""这个问题和普通用户有什么关系""写作者应该补充哪些经验"三个方向。`,
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
        `回答主线：作者从${category}的实际场景切入，先界定"${base}"不是一个单点能力问题，而是输入质量、执行流程、验证责任共同作用的结果。`,
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
        `评论焦点：反方评论主要质疑"${base}"是否被过度概括，以及当前材料是否足以支撑这么强的结论。`,
        `典型问题：有人要求补充失败案例，有人认为不同业务场景差异很大，也有人提醒写作者不要只引用支持自己观点的材料。`,
        `潜在反方：如果未来工具能力继续增强，当前的瓶颈是否会自然消失？如果只看少数高赞回答，会不会忽略沉默的大多数使用场景？`,
        `对写作的启发：适合作为文章中"我知道这个观点可能被这样反驳"的段落来源。`,
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
      .replace(/[^a-zA-Z0-9一-龥-]+/g, "-")
      .slice(0, 96),
    type,
    title,
    content,
    sourceLabel,
    adopted,
    createdAt,
  };
}
