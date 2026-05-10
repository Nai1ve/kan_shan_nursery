"use client";

import {
  BookOpen,
  Check,
  Copy,
  Droplets,
  History,
  Home,
  Leaf,
  Loader2,
  MessageCircleQuestion,
  PenLine,
  Plus,
  RefreshCw,
  Save,
  Send,
  Sparkles,
  Sprout,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import type { ComponentType, Dispatch, KeyboardEvent, MouseEvent, SetStateAction } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  fetchContent,
  fetchFeedbackArticles,
  fetchProfile,
  fetchSeeds,
  fetchSproutOpportunities,
} from "@/lib/api-client";
import type {
  ContentSource,
  DemoState,
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  MemorySummary,
  ProfileData,
  SeedQuestion,
  SeedReaction,
  SeedStatus,
  SproutOpportunity,
  TabId,
  Tone,
  WateringMaterial,
  WateringMaterialType,
  WorthReadingCard,
  WritingSession,
} from "@/lib/types";

const STORAGE_KEY = "kanshan:nursery:demo-state:v1";

const tabs: { id: TabId; label: string; icon: ComponentType<{ size?: number }> }[] = [
  { id: "today", label: "今日看什么", icon: BookOpen },
  { id: "seeds", label: "我的种子库", icon: Leaf },
  { id: "sprout", label: "今日发芽", icon: Sprout },
  { id: "write", label: "写作苗圃", icon: PenLine },
  { id: "history", label: "历史反馈", icon: History },
  { id: "profile", label: "个人画像", icon: UserRound },
];

const heroMap: Record<TabId, [string, string]> = {
  onboarding: ["建立你的创作画像。", "通过兴趣小类和写作问卷，让系统知道你关心什么、怎么表达。"],
  today: ["看到好内容，形成好观点。", "每次阅读都能沉淀表态、疑问、来源和可写角度。"],
  seeds: ["收藏的不是内容，是下一篇文章的种子。", "每颗种子都有来源、疑问、浇水材料和成熟度。"],
  sprout: ["旧想法，遇到新热点，就会发芽。", "用今日热点、关注流和用户画像激活历史观点种子。"],
  write: ["一步一步，把观点养成文章。", "从观点确认到论证蓝图，再到圆桌审稿、定稿草案和反馈回流。"],
  history: ["历史反馈，不只是数据。", "读者反馈会反哺 Memory、种子库和下一篇文章。"],
  profile: ["你的画像，是系统理解你的方式。", "可见、可编辑的 Memory 会影响推荐、浇水和写作。"],
};

const writingSteps = [
  { title: "选择观点种子", desc: "确定这篇文章从哪颗种子发芽。" },
  { title: "确认核心观点", desc: "AI 先提炼，用户确认立场边界。" },
  { title: "选择文章类型", desc: "深度分析、经验复盘、知乎回答等。" },
  { title: "生成论证蓝图", desc: "先搭骨架，不急着写正文。" },
  { title: "生成表达初稿", desc: "基于观点、资料和用户画像生成初稿。" },
  { title: "圆桌审稿会", desc: "逻辑、人味、反方、传播四类 Agent 讨论。" },
  { title: "定稿草案", desc: "用户满意后点击定稿，生成最终草稿。" },
  { title: "发布与反馈", desc: "提示用户修改后发布，并进入反馈监控。" },
];

const articleTypes = [
  ["deep_analysis", "深度分析", "强调逻辑、推演和资料支撑。"],
  ["experience_review", "经验复盘", "加入真实项目经验，提高人味和可信度。"],
  ["zhihu_answer", "知乎回答", "更直接，适合回答具体问题。"],
  ["opinion_commentary", "观点评论", "更贴近热点，强调立场和反差。"],
] as const;

const onboardingQuestions = [
  "你希望文章逻辑严密到什么程度？",
  "你愿意在文章中表达鲜明立场吗？",
  "你喜欢加入个人经历和踩坑案例吗？",
  "你能接受比较犀利的表达吗？",
  "你希望文章更像知乎回答还是公众号长文？",
  "你希望多引用资料还是多讲自己的判断？",
  "你是否希望系统主动提出反方质疑？",
  "你希望文章开头更直接还是更有故事感？",
  "你希望标题更克制还是更有传播性？",
  "你是否愿意暴露自己的不确定和纠结？",
  "你希望风格更冷静还是更有情绪？",
  "你希望 AI 帮你写到什么程度？",
];

const materialMeta: Record<WateringMaterialType, { title: string; desc: string; tone: Tone }> = {
  evidence: { title: "事实证据", desc: "来源、数据、案例、摘要。", tone: "blue" },
  counterargument: { title: "反方质疑", desc: "反对意见、漏洞、需要回应的问题。", tone: "orange" },
  personal_experience: { title: "个人经验", desc: "项目经历、观察、踩坑。", tone: "green" },
  open_question: { title: "待解决问题", desc: "尚未回答的疑问，可继续问 Agent。", tone: "purple" },
};

const materialTypes: WateringMaterialType[] = ["evidence", "counterargument", "personal_experience", "open_question"];

export function KanshanApp() {
  const [entered, setEntered] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("today");
  const [toast, setToast] = useState("");
  const [data, setData] = useState<DemoState | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("ai-coding");
  const [selectedSeedId, setSelectedSeedId] = useState("seed-ai-coding-moat");
  const [writingStep, setWritingStep] = useState(0);
  const [questionCard, setQuestionCard] = useState<WorthReadingCard | null>(null);
  const [newSeedOpen, setNewSeedOpen] = useState(false);
  const [wateringSeedId, setWateringSeedId] = useState<string | null>(null);
  const [mergeSeedId, setMergeSeedId] = useState<string | null>(null);
  const [commentArticle, setCommentArticle] = useState<FeedbackArticle | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadMockData() {
      const [profile, content, seeds, sproutOpportunities, feedbackArticles] = await Promise.all([
        fetchProfile(),
        fetchContent(),
        fetchSeeds(),
        fetchSproutOpportunities(),
        fetchFeedbackArticles(),
      ]);

      if (!mounted) return;

      const initialState: DemoState = {
        hasEntered: false,
        activeTab: "today",
        selectedCategoryId: "ai-coding",
        selectedSeedId: "seed-ai-coding-moat",
        profile,
        categories: content.categories,
        cards: content.cards,
        seeds,
        sproutOpportunities,
        feedbackArticles,
        reactions: {},
        expandedCardIds: [],
        expandedSourceIds: {},
        categoryRefreshState: {},
        sproutStarted: false,
      };

      const nextState = readStoredState(initialState);
      setData(nextState);
      setEntered(nextState.hasEntered);
      setActiveTab(nextState.activeTab);
      setSelectedCategory(nextState.selectedCategoryId);
      setSelectedSeedId(nextState.selectedSeedId);
    }

    loadMockData().catch(() => {
      showToast("Mock API 加载失败");
    });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!data) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, [data]);

  function showToast(message: string) {
    setToast(message);
    window.clearTimeout(window.__kanshanToastTimer);
    window.__kanshanToastTimer = window.setTimeout(() => setToast(""), 1900);
  }

  function updateData(updater: (current: DemoState) => DemoState) {
    setData((current) => (current ? updater(current) : current));
  }

  function enterApp(mode: "zhihu" | "onboarding" | "demo") {
    setEntered(true);
    const nextTab = mode === "onboarding" ? "onboarding" : "today";
    setActiveTab(nextTab);
    updateData((current) => ({
      ...current,
      hasEntered: true,
      activeTab: nextTab,
    }));
    if (mode === "zhihu") {
      updateData((current) => ({
        ...current,
        profile: { ...current.profile, accountStatus: "已模拟关联知乎账号 · 关注流已同步" },
      }));
    }
    showToast(mode === "onboarding" ? "进入首次画像采集" : mode === "zhihu" ? "已模拟关联知乎账号" : "进入演示模式");
  }

  function goTab(tab: TabId) {
    setActiveTab(tab);
    updateData((current) => ({ ...current, activeTab: tab }));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function selectCategory(categoryId: string) {
    setSelectedCategory(categoryId);
    updateData((current) => ({ ...current, selectedCategoryId: categoryId }));
  }

  function selectSeed(seedId: string) {
    selectSeed(seedId);
    updateData((current) => ({ ...current, selectedSeedId: seedId }));
  }

  function ensureSeedFromCard(card: WorthReadingCard, reaction: SeedReaction, note?: string) {
    if (!data) return "";
    const existing = data.seeds.find((seed) => seed.createdFromCardId === card.id);
    const seedId = existing?.id ?? createId("seed", card.id);
    const newSeed = existing ? null : buildSeedFromCard(card, data.categories, reaction, note, seedId);

    updateData((current) => {
      const nextSeeds = existing
        ? current.seeds.map((seed) =>
            seed.id === existing.id
              ? recalcSeed({
                  ...seed,
                  userReaction: reaction,
                  userNote: note || seed.userNote,
                  updatedAt: now(),
                })
              : seed,
          )
        : [newSeed as IdeaSeed, ...current.seeds];

      return {
        ...current,
        seeds: nextSeeds,
        reactions: { ...current.reactions, [card.id]: reaction },
      };
    });

    setSelectedSeedId(seedId);
    return seedId;
  }

  function recordReaction(card: WorthReadingCard, reaction: Extract<SeedReaction, "agree" | "disagree">) {
    ensureSeedFromCard(card, reaction, reaction === "agree" ? "我认同这个方向，后续可以继续补证据。" : "我反对当前结论，需要整理反方理由。");
    showToast(reaction === "agree" ? "已记录认同，并沉淀到种子库" : "已记录反对，并加入反方材料");
  }

  function answerQuestion(card: WorthReadingCard, question: string) {
    const seedId = ensureSeedFromCard(card, "question", `我的疑问：${question}`);
    const currentSeed = data?.seeds.find((seed) => seed.id === seedId);
    const turnIndex = currentSeed?.questions.length ?? 0;
    const answer = buildAgentAnswer(card, question, turnIndex);
    const answerMaterialType: WateringMaterialType = /反方|质疑|漏洞|风险|不足|边界/.test(question) ? "counterargument" : "evidence";
    const questionId = createId("question", card.id);
    const questionRecord: SeedQuestion = {
      id: questionId,
      question,
      agentAnswer: answer,
      citedSourceIds: card.originalSources.map((source) => source.sourceId),
      status: "answered",
      createdAt: now(),
    };
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((seed) => {
        if (seed.id !== seedId) return seed;
        return recalcSeed({
          ...seed,
          questions: [questionRecord, ...seed.questions],
          wateringMaterials: [
            buildMaterial("open_question", "用户疑问", question, "有疑问按钮", false),
            buildMaterial(answerMaterialType, turnIndex ? "Agent 继续追问回答" : "Agent 初步回答", answer, "Agent 问答", true),
            ...seed.wateringMaterials,
          ],
          updatedAt: now(),
        });
      }),
    }));
    showToast("疑问已记录，Agent 回答已回写到浇水材料");
    return { seedId, questionId, question, agentAnswer: answer, citedSourceIds: card.originalSources.map((source) => source.sourceId) };
  }

  function markQuestion(seedId: string, questionId: string, status: SeedQuestion["status"]) {
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((seed) => {
        if (seed.id !== seedId) return seed;
        const targetQuestion = seed.questions.find((question) => question.id === questionId);
        return recalcSeed({
          ...seed,
          questions: seed.questions.map((question) => (question.id === questionId ? { ...question, status } : question)),
          wateringMaterials: targetQuestion
            ? seed.wateringMaterials.map((material) =>
                material.type === "open_question" && material.content === targetQuestion.question
                  ? { ...material, adopted: status === "resolved" }
                  : material,
              )
            : seed.wateringMaterials,
          updatedAt: now(),
        });
      }),
    }));
    showToast(status === "resolved" ? "疑问已标记为已解决" : "疑问已标记为仍需补资料");
  }

  function addSeedFromCard(card: WorthReadingCard) {
    const seedId = ensureSeedFromCard(card, "supplement", "我想把这条内容先沉淀成可继续培养的观点种子。");
    selectSeed(seedId);
    showToast("已加入种子库");
  }

  function writeFromCard(card: WorthReadingCard) {
    if (!data) return;
    const existing = data.seeds.find((seed) => seed.createdFromCardId === card.id);
    const seedId = ensureSeedFromCard(card, "want_to_write", "这条内容已经触发表达欲，准备进入写作。");
    const seedForWriting =
      existing ??
      buildSeedFromCard(card, data.categories, "want_to_write", "这条内容已经触发表达欲，准备进入写作。", seedId);
    startWriting(seedId, seedForWriting);
  }

  function addManualSeed(seed: Pick<IdeaSeed, "title" | "interestId" | "coreClaim" | "userNote" | "requiredMaterials">) {
    if (!data) return;
    const category = data.categories.find((item) => item.id === seed.interestId);
    const newSeed: IdeaSeed = recalcSeed({
      id: createId("seed", "manual"),
      interestId: seed.interestId,
      title: seed.title,
      interestName: category?.name ?? seed.interestId,
      source: "用户手动创建",
      sourceTitle: seed.title,
      sourceSummary: seed.userNote || "用户手动创建的想法种子。",
      sourceType: "manual",
      userReaction: "manual",
      userNote: seed.userNote,
      coreClaim: seed.coreClaim,
      possibleAngles: [seed.coreClaim, `${seed.title}可以写成经验复盘`, `${seed.title}可以写成知乎回答`],
      counterArguments: ["这个判断是否有足够证据？", "读者可能会从什么角度反驳？"],
      requiredMaterials: seed.requiredMaterials,
      wateringMaterials: seed.requiredMaterials.map((item) => buildMaterial("open_question", "待补材料", item, "手动种子", false)),
      questions: [],
      status: "water_needed",
      maturityScore: 35,
      createdAt: now(),
      updatedAt: now(),
    });
    updateData((current) => ({ ...current, seeds: [newSeed, ...current.seeds] }));
    selectSeed(newSeed.id);
    setNewSeedOpen(false);
    showToast("新种子已创建，进入待浇水状态");
  }

  function addMaterial(seedId: string, material: Omit<WateringMaterial, "id" | "createdAt">) {
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((seed) =>
        seed.id === seedId
          ? recalcSeed({
              ...seed,
              wateringMaterials: [{ ...material, id: createId("material", material.type), createdAt: now() }, ...seed.wateringMaterials],
              updatedAt: now(),
            })
          : seed,
      ),
    }));
    showToast("材料已补充，成熟度已更新");
  }

  function updateMaterial(seedId: string, materialId: string, patch: Partial<WateringMaterial>) {
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((seed) =>
        seed.id === seedId
          ? recalcSeed({
              ...seed,
              wateringMaterials: seed.wateringMaterials.map((item) => (item.id === materialId ? { ...item, ...patch } : item)),
              updatedAt: now(),
            })
          : seed,
      ),
    }));
  }

  function deleteMaterial(seedId: string, materialId: string) {
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((seed) =>
        seed.id === seedId
          ? recalcSeed({
              ...seed,
              wateringMaterials: seed.wateringMaterials.filter((item) => item.id !== materialId),
              updatedAt: now(),
            })
          : seed,
      ),
    }));
    showToast("已删除材料，成熟度已更新");
  }

  function resolveOpenQuestion(seedId: string, material: WateringMaterial) {
    const seed = data?.seeds.find((item) => item.id === seedId);
    if (!seed) return;
    const answer = `基于当前来源和反方材料，Agent 的初步回答是：${material.content} 需要拆成事实判断和价值判断两层。事实层先补来源证据，价值层保留你的工程经验和边界说明。`;
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((item) =>
        item.id === seedId
          ? recalcSeed({
              ...item,
              questions: [
                {
                  id: createId("question", seedId),
                  question: material.content,
                  agentAnswer: answer,
                  citedSourceIds: [],
                  status: "answered",
                  createdAt: now(),
                },
                ...item.questions,
              ],
              wateringMaterials: [
                { ...material, adopted: true },
                buildMaterial("evidence", "Agent 回答待解决问题", answer, "继续浇水 / Agent 问答", true),
                ...item.wateringMaterials.filter((currentMaterial) => currentMaterial.id !== material.id),
              ],
              updatedAt: now(),
            })
          : item,
      ),
    }));
    showToast("Agent 已回答待解决问题，并写入事实证据");
  }

  function supplementMaterialWithAgent(seedId: string, type: Extract<WateringMaterialType, "evidence" | "counterargument">) {
    const seed = data?.seeds.find((item) => item.id === seedId);
    if (!seed) return;
    const material =
      type === "evidence"
        ? {
            type,
            title: "Agent 补充事实证据",
            content: `围绕“${seed.sourceTitle}”，Agent 建议补充一条可验证事实：先引用原始来源中的具体场景，再说明它如何支撑“${seed.coreClaim}”。这条材料应在正式接 API 后替换成真实回答或原文片段。`,
            sourceLabel: "继续浇水 / Agent 补证据",
            adopted: true,
          }
        : {
            type,
            title: "Agent 找到反方质疑",
            content: `针对“${seed.coreClaim}”，反方可能会质疑：${seed.counterArguments[0] ?? "当前材料是否足够支持这个判断？"} 建议在文章中明确适用边界，并补充一个不成立的场景。`,
            sourceLabel: "继续浇水 / Agent 找反方",
            adopted: true,
          };
    addMaterial(seedId, material);
  }

  function mergeSeeds(targetId: string, sourceId: string) {
    updateData((current) => {
      const target = current.seeds.find((seed) => seed.id === targetId);
      const source = current.seeds.find((seed) => seed.id === sourceId);
      if (!target || !source) return current;
      const [merged] = ensureUniqueMaterialIds([recalcSeed({
        ...target,
        possibleAngles: unique([...target.possibleAngles, ...source.possibleAngles]),
        counterArguments: unique([...target.counterArguments, ...source.counterArguments]),
        requiredMaterials: unique([...target.requiredMaterials, ...source.requiredMaterials]),
        wateringMaterials: [...target.wateringMaterials, ...source.wateringMaterials],
        questions: [...target.questions, ...source.questions],
        userNote: `${target.userNote}\n合并补充：${source.userNote}`,
        updatedAt: now(),
      })]);
      return { ...current, seeds: current.seeds.filter((seed) => seed.id !== sourceId).map((seed) => (seed.id === targetId ? merged : seed)) };
    });
    setMergeSeedId(null);
    showToast("相似种子已合并，材料和疑问已归并");
  }

  function startSprout(seedId?: string) {
    if (!data) return;
    const targetSeeds = seedId ? data.seeds.filter((seed) => seed.id === seedId) : data.seeds.filter((seed) => seed.status !== "published");
    const generated = targetSeeds.slice(0, 4).map((seed, index) => buildSproutOpportunity(seed, index));
    updateData((current) => ({
      ...current,
      sproutStarted: true,
      sproutOpportunities: mergeOpportunities(generated, current.sproutOpportunities),
    }));
    if (seedId) selectSeed(seedId);
    goTab("sprout");
    showToast("已开始：历史种子 × 今日热点 × 用户画像");
  }

  function updateOpportunity(id: string, patch: Partial<SproutOpportunity>) {
    updateData((current) => ({
      ...current,
      sproutOpportunities: current.sproutOpportunities.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    }));
  }

  function supplementFromOpportunity(opportunity: SproutOpportunity) {
    addMaterial(opportunity.seedId, {
      type: opportunity.score >= 82 ? "evidence" : "counterargument",
      title: "今日发芽补充资料",
      content: opportunity.suggestedMaterials,
      sourceLabel: "今日发芽",
      adopted: true,
    });
    updateOpportunity(opportunity.id, { status: "supplemented", tags: [...opportunity.tags, { label: "已补资料", tone: "green" }] });
  }

  function switchOpportunityAngle(opportunity: SproutOpportunity) {
    updateOpportunity(opportunity.id, {
      status: "angle_changed",
      suggestedTitle: opportunity.suggestedTitle.includes("真正")
        ? opportunity.suggestedTitle.replace("真正", "新的")
        : `${opportunity.suggestedTitle}：真正值得讨论的不是表层能力`,
      suggestedAngle: `${opportunity.suggestedAngle} 同时加入反方质疑，避免写成单向判断。`,
    });
    showToast("已切换写作角度");
  }

  function startWriting(seedId: string, seedOverride?: IdeaSeed) {
    const seed = seedOverride ?? data?.seeds.find((item) => item.id === seedId);
    if (!seed) return;
    const session = createWritingSession(seed, data?.profile);
    updateData((current) => ({
      ...current,
      writingSession: session,
      seeds: current.seeds.some((item) => item.id === seedId)
        ? current.seeds.map((item) => (item.id === seedId ? { ...item, status: "writing", updatedAt: now() } : item))
        : [{ ...seed, status: "writing", updatedAt: now() }, ...current.seeds],
    }));
    selectSeed(seedId);
    setWritingStep(0);
    goTab("write");
    showToast("已进入写作苗圃，Memory 已按兴趣分类注入");
  }

  function updateWritingSession(patch: Partial<WritingSession>) {
    updateData((current) => {
      const fallbackSeed = current.seeds.find((seed) => seed.id === selectedSeedId) ?? current.seeds[0];
      return {
        ...current,
        writingSession: current.writingSession
          ? { ...current.writingSession, ...patch }
          : fallbackSeed
            ? { ...createWritingSession(fallbackSeed, current.profile), ...patch }
            : undefined,
      };
    });
  }

  function publishWriting() {
    const session = data?.writingSession;
    const seed = data?.seeds.find((item) => item.id === session?.seedId);
    if (!session || !seed) return;
    const articleId = createId("article", seed.id);
    const article: FeedbackArticle = {
      id: articleId,
      title: seed.possibleAngles[0] ?? seed.title,
      interestId: seed.interestId,
      linkedSeedId: seed.id,
      status: "新发布",
      statusTone: "blue",
      performanceSummary: "刚发布，系统已进入 2-3 周反馈观察期。当前先记录首批评论和收藏趋势。",
      commentInsights: ["等待第一批评论进入。", "建议重点关注反方是否质疑证据不足。", "收藏率会影响下一轮选题判断。"],
      memoryAction: `把“${seed.interestName}：发布后需要观察反方质疑”写入 Memory 候选。`,
      metrics: [
        { label: "阅读完成率", value: 18 },
        { label: "收藏率", value: 7 },
        { label: "评论争议度", value: 12 },
      ],
    };
    updateData((current) => ({
      ...current,
      writingSession: { ...session, draftStatus: "published", publishedArticleId: articleId },
      feedbackArticles: [article, ...current.feedbackArticles],
      seeds: current.seeds.map((item) => (item.id === seed.id ? { ...item, status: "published", maturityScore: 96, updatedAt: now() } : item)),
    }));
    goTab("history");
    showToast("已模拟发布，并进入历史反馈监控");
  }

  function syncFeedback() {
    updateData((current) => ({
      ...current,
      feedbackArticles: current.feedbackArticles.map((article) => ({
        ...article,
        metrics: article.metrics.map((metric, index) => ({ ...metric, value: Math.min(96, metric.value + 3 + index) })),
      })),
    }));
    showToast("已同步最新互动数据");
  }

  function generateSecondArticle(article: FeedbackArticle) {
    const newSeed = recalcSeed({
      id: createId("seed", article.id),
      interestId: article.interestId,
      title: `二次文章：回应《${article.title}》评论区的关键质疑`,
      interestName: data?.categories.find((item) => item.id === article.interestId)?.name ?? article.interestId,
      source: "历史文章反馈",
      sourceTitle: article.title,
      sourceSummary: article.performanceSummary,
      sourceType: "feedback",
      userReaction: "supplement",
      userNote: "评论区出现了值得单独展开的新问题。",
      coreClaim: article.commentInsights[1] ?? article.memoryAction,
      possibleAngles: ["把评论区反方写成一篇回应文章", "从读者反馈看原观点的边界", "把补充材料整理为后续长文"],
      counterArguments: article.commentInsights,
      requiredMaterials: ["评论原文", "补充案例", "反方回应"],
      wateringMaterials: article.commentInsights.map((item) => buildMaterial("counterargument", "评论反馈", item, "历史反馈", true)),
      questions: [],
      status: "water_needed",
      maturityScore: 52,
      createdAt: now(),
      updatedAt: now(),
    });
    updateData((current) => ({ ...current, seeds: [newSeed, ...current.seeds] }));
    selectSeed(newSeed.id);
    goTab("seeds");
    showToast("已从历史反馈生成二次文章种子");
  }

  function saveProfile(profile: ProfileData) {
    updateData((current) => ({ ...current, profile }));
    showToast("个人画像已保存，并写入本地 Memory");
  }

  function resetDemoState() {
    window.localStorage.removeItem(STORAGE_KEY);
    window.location.reload();
  }

  const selectedCards = useMemo(() => {
    if (!data) return [];
    return cardsForCategory(data.cards, selectedCategory, data.categoryRefreshState[selectedCategory]);
  }, [data, selectedCategory]);

  const selectedCategoryRefresh = data?.categoryRefreshState[selectedCategory];

  function refreshSelectedCategory() {
    if (!data) return;
    const currentCards = data.cards.filter((card) => card.categoryId === selectedCategory);
    if (!currentCards.length) return;
    const current = data.categoryRefreshState[selectedCategory];
    const nextCount = (current?.refreshCount ?? 0) + 1;
    const baseIds = current?.visibleCardIds?.length ? current.visibleCardIds : currentCards.map((card) => card.id);
    const rotated = rotateIds(baseIds, 1);
    updateData((state) => ({
      ...state,
      categoryRefreshState: {
        ...state.categoryRefreshState,
        [selectedCategory]: {
          refreshCount: nextCount,
          refreshedAt: now(),
          visibleCardIds: rotated,
        },
      },
      expandedSourceIds: {},
    }));
    showToast(`已刷新${sectionTitle(data.categories, selectedCategory)}，本地状态已保留`);
  }

  function toggleSource(cardId: string, sourceId: string) {
    updateData((current) => ({
      ...current,
      expandedSourceIds: {
        ...current.expandedSourceIds,
        [cardId]: current.expandedSourceIds[cardId] === sourceId ? "" : sourceId,
      },
    }));
  }

  const selectedSeed = useMemo(() => {
    if (!data) return null;
    return data.seeds.find((seed) => seed.id === selectedSeedId) ?? data.seeds[0] ?? null;
  }, [data, selectedSeedId]);

  const wateringSeed = useMemo(() => {
    if (!data || !wateringSeedId) return null;
    return data.seeds.find((seed) => seed.id === wateringSeedId) ?? null;
  }, [data, wateringSeedId]);

  const writingSeed = useMemo(() => {
    if (!data?.writingSession) return selectedSeed;
    return data.seeds.find((seed) => seed.id === data.writingSession?.seedId) ?? selectedSeed;
  }, [data, selectedSeed]);

  const writingBaseMemory = useMemo(() => {
    if (!data || !writingSeed) return null;
    return findMemory(data.profile, writingSeed.interestId);
  }, [data, writingSeed]);

  const writingMemory = useMemo(() => {
    if (!writingBaseMemory || !writingSeed) return null;
    const override = data?.writingSession?.memoryOverride;
    return override?.interestId === writingSeed.interestId ? override : writingBaseMemory;
  }, [data, writingBaseMemory, writingSeed]);

  if (!data) {
    return (
      <main className="loading-screen">
        <Loader2 className="spin" size={28} />
        <span>正在加载看山小苗圃 mock 数据...</span>
      </main>
    );
  }

  if (!entered) {
    return <LoginScreen onEnter={enterApp} />;
  }

  const activeHero = heroMap[activeTab];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">苗</div>
          <div>
            <div className="brand-title">看山小苗圃</div>
            <div className="brand-subtitle">知乎读写一体创作 Agent</div>
          </div>
        </div>

        <nav className="nav" aria-label="主导航">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button className={activeTab === tab.id ? "active" : ""} key={tab.id} onClick={() => goTab(tab.id)} type="button">
                <span className="nav-icon">
                  <Icon size={16} />
                </span>
                {tab.label}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-card">
          <div className="eyebrow">今日苗圃状态</div>
          <p>
            {data.seeds.length} 颗观点种子，{data.seeds.filter((seed) => seed.status === "sproutable").length} 颗可发芽，
            {data.seeds.reduce((sum, seed) => sum + seed.questions.length, 0)} 个疑问已沉淀。
          </p>
        </div>
        <div className="sidebar-card">
          <div className="eyebrow">本地持久化</div>
          <p>所有演示操作会写入 localStorage。需要重置时可清空演示状态。</p>
          <button className="btn ghost compact" onClick={resetDemoState} type="button">
            重置演示状态
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1 className="hero-title">{activeHero[0]}</h1>
            {activeHero[1] ? <p className="hero-desc">{activeHero[1]}</p> : null}
          </div>
          <button className="user-pill" onClick={() => goTab("profile")} type="button">
            <div className="avatar">山</div>
            <div>
              <div className="user-name">{data.profile.nickname}</div>
              <div className="user-mode">主编模式 · {data.profile.accountStatus}</div>
            </div>
          </button>
        </header>

        {activeTab === "onboarding" ? <OnboardingSection profile={data.profile} onSave={saveProfile} goProfile={() => goTab("profile")} /> : null}
        {activeTab === "today" ? (
          <TodaySection
            categories={data.categories}
            cards={selectedCards}
            reactions={data.reactions}
            expandedCardIds={data.expandedCardIds}
            expandedSourceIds={data.expandedSourceIds}
            refreshState={selectedCategoryRefresh}
            selectedCategory={selectedCategory}
            setSelectedCategory={selectCategory}
            onRefresh={refreshSelectedCategory}
            onToggleSource={toggleSource}
            onToggleSummary={(cardId) => {
              updateData((current) => ({
                ...current,
                expandedCardIds: current.expandedCardIds.includes(cardId)
                  ? current.expandedCardIds.filter((id) => id !== cardId)
                  : [...current.expandedCardIds, cardId],
              }));
            }}
            onReact={recordReaction}
            onQuestion={setQuestionCard}
            onAddSeed={addSeedFromCard}
            onWrite={writeFromCard}
          />
        ) : null}
        {activeTab === "seeds" && selectedSeed ? (
          <SeedsSection
            seeds={data.seeds}
            selectedSeed={selectedSeed}
            setSelectedSeedId={selectSeed}
            openNewSeed={() => setNewSeedOpen(true)}
            openWatering={(seedId) => setWateringSeedId(seedId)}
            startWriting={startWriting}
            openMerge={(seedId) => setMergeSeedId(seedId)}
          />
        ) : null}
        {activeTab === "sprout" ? (
          <SproutSection
            started={data.sproutStarted}
            opportunities={data.sproutOpportunities}
            onStart={() => startSprout()}
            openSeeds={() => goTab("seeds")}
            startWriting={startWriting}
            onSupplement={supplementFromOpportunity}
            onSwitchAngle={switchOpportunityAngle}
            onDismiss={(id) => {
              updateOpportunity(id, { status: "dismissed", tags: [{ label: "已暂缓", tone: "purple" }] });
              showToast("已标记为暂时不写");
            }}
          />
        ) : null}
        {activeTab === "write" && writingSeed && writingMemory && writingBaseMemory ? (
          <WritingSection
            seed={writingSeed}
            memory={writingMemory}
            baseMemory={writingBaseMemory}
            session={data.writingSession}
            step={writingStep}
            setStep={setWritingStep}
            updateSession={updateWritingSession}
            addMaterial={(material) => addMaterial(writingSeed.id, material)}
            publishWriting={publishWriting}
            showToast={showToast}
          />
        ) : null}
        {activeTab === "history" ? (
          <HistorySection
            articles={data.feedbackArticles}
            syncFeedback={syncFeedback}
            generateSecondArticle={generateSecondArticle}
            openComments={setCommentArticle}
          />
        ) : null}
        {activeTab === "profile" ? <ProfileSection profile={data.profile} categories={data.categories} onSave={saveProfile} /> : null}
      </main>

      {questionCard ? (
        <QuestionDialog
          card={questionCard}
          onClose={() => setQuestionCard(null)}
          onAnswer={(question) => answerQuestion(questionCard, question)}
          onMark={markQuestion}
        />
      ) : null}
      {newSeedOpen ? <NewSeedModal categories={data.categories} onClose={() => setNewSeedOpen(false)} onCreate={addManualSeed} /> : null}
      {wateringSeed ? (
        <WateringModal
          seed={wateringSeed}
          onClose={() => setWateringSeedId(null)}
          onAdd={(material) => addMaterial(wateringSeed.id, material)}
          onToggle={(material) => updateMaterial(wateringSeed.id, material.id, { adopted: !material.adopted })}
          onEdit={(material, patch) => updateMaterial(wateringSeed.id, material.id, patch)}
          onDelete={(materialId) => deleteMaterial(wateringSeed.id, materialId)}
          onResolve={resolveOpenQuestion}
          onAgentSupplement={(type) => supplementMaterialWithAgent(wateringSeed.id, type)}
        />
      ) : null}
      {mergeSeedId ? (
        <MergeSeedModal
          seedId={mergeSeedId}
          seeds={data.seeds}
          onClose={() => setMergeSeedId(null)}
          onMerge={mergeSeeds}
        />
      ) : null}
      {commentArticle ? <CommentDialog article={commentArticle} onClose={() => setCommentArticle(null)} /> : null}
      <div className={`floating-toast ${toast ? "show" : ""}`}>{toast}</div>
    </div>
  );
}

function LoginScreen({ onEnter }: { onEnter: (mode: "zhihu" | "onboarding" | "demo") => void }) {
  return (
    <section className="login-shell">
      <div className="login-hero">
        <div className="login-logo">苗</div>
        <h1>看到好内容，形成好观点，写出好文章。</h1>
        <p>
          看山小苗圃是一个面向知乎生态的读写一体创作 Agent。它先帮你筛选值得看的内容，再把你的阅读反应沉淀成观点种子，最后在合适的热点时机发芽成文。
        </p>
        <div className="action-row">
          <button className="btn primary" onClick={() => onEnter("zhihu")} type="button">
            关联知乎账号
          </button>
          <button className="btn ghost" onClick={() => onEnter("onboarding")} type="button">
            首次使用，先建立画像
          </button>
        </div>
      </div>

      <div className="login-panel">
        <h2>开始之前</h2>
        <p>如果允许关联知乎账号，系统会读取关注流、圈子互动和内容偏好；如果暂不关联，可以通过首次画像问卷建立本地 Memory。</p>
        <LoginOption icon="知" title="关联知乎账号" desc="读取关注流、圈子、热榜互动偏好，快速生成你的创作输入画像。" onClick={() => onEnter("zhihu")} />
        <LoginOption icon="问" title="首次登录画像采集" desc="选择兴趣小类，并通过 12 个问题形成你的写作风格画像。" onClick={() => onEnter("onboarding")} />
        <LoginOption icon="演" title="直接进入演示模式" desc="使用预置画像和示例数据，适合黑客松路演展示。" onClick={() => onEnter("demo")} />
      </div>
    </section>
  );
}

function LoginOption({ icon, title, desc, onClick }: { icon: string; title: string; desc: string; onClick: () => void }) {
  return (
    <button className="login-option" onClick={onClick} type="button">
      <span className="login-option-icon">{icon}</span>
      <span>
        <strong>{title}</strong>
        <span>{desc}</span>
      </span>
    </button>
  );
}

function OnboardingSection({ profile, onSave, goProfile }: { profile: ProfileData; onSave: (profile: ProfileData) => void; goProfile: () => void }) {
  const [draft, setDraft] = useState(profile);
  const [answers, setAnswers] = useState(() => onboardingQuestions.map((_, index) => scaleValues(index)[2] ?? "3"));

  function save() {
    onSave({
      ...draft,
      globalMemory: {
        ...draft.globalMemory,
        writingStyle: `${draft.globalMemory.writingStyle} 问卷偏好：${answers.join(" / ")}。`,
      },
    });
    goProfile();
  }

  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">首次登录：建立你的创作画像</h2>
            <p className="panel-subtitle">兴趣不只按大类保存，而是细化到兴趣小类，用于后续推荐、发芽和写作 Memory 注入。</p>
          </div>
          <button className="btn primary" onClick={save} type="button">
            保存画像并进入首页
          </button>
        </div>
        <div className="panel-body profile-layout">
          <div className="form-grid">
            <EditableField label="你希望系统怎么称呼你？" value={draft.nickname} onChange={(nickname) => setDraft({ ...draft, nickname })} />
            <EditableField label="你的身份 / 创作背景" value={draft.role} onChange={(role) => setDraft({ ...draft, role })} />
            <div className="field">
              <label>你最希望系统帮你避免什么？</label>
              <textarea className="textarea" value={draft.avoidances} onChange={(event) => setDraft({ ...draft, avoidances: event.target.value })} />
            </div>
            <button className="btn primary" onClick={save} type="button">
              生成我的画像
            </button>
          </div>
          <div>
            <div className="category-header no-top">
              <div>
                <h3>写作风格问卷</h3>
                <p>点击选项会写入画像 Memory。1 表示低，5 表示高。</p>
              </div>
            </div>
            <div className="grid-2">
              {onboardingQuestions.map((question, index) => (
                <div className="question-card" key={question}>
                  <h4>
                    {index + 1}. {question}
                  </h4>
                  <div className="scale">
                    {scaleValues(index).map((value) => (
                      <button
                        className={answers[index] === value ? "selected" : ""}
                        key={value}
                        onClick={() => setAnswers(answers.map((answer, answerIndex) => (answerIndex === index ? value : answer)))}
                        type="button"
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function TodaySection({
  categories,
  cards,
  reactions,
  expandedCardIds,
  expandedSourceIds,
  refreshState,
  selectedCategory,
  setSelectedCategory,
  onRefresh,
  onToggleSource,
  onToggleSummary,
  onReact,
  onQuestion,
  onAddSeed,
  onWrite,
}: {
  categories: InputCategory[];
  cards: WorthReadingCard[];
  reactions: Record<string, SeedReaction>;
  expandedCardIds: string[];
  expandedSourceIds: Record<string, string>;
  refreshState?: DemoState["categoryRefreshState"][string];
  selectedCategory: string;
  setSelectedCategory: (category: string) => void;
  onRefresh: () => void;
  onToggleSource: (cardId: string, sourceId: string) => void;
  onToggleSummary: (cardId: string) => void;
  onReact: (card: WorthReadingCard, reaction: Extract<SeedReaction, "agree" | "disagree">) => void;
  onQuestion: (card: WorthReadingCard) => void;
  onAddSeed: (card: WorthReadingCard) => void;
  onWrite: (card: WorthReadingCard) => void;
}) {
  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">今日看什么</h2>
            <p className="panel-subtitle">选择兴趣小类、关注流或偶遇输入，只展示当前分类下的内容。</p>
          </div>
          <button className="btn primary" onClick={onRefresh} type="button">
            <RefreshCw size={14} />
            刷新输入
          </button>
        </div>
        <div className="panel-body">
          <div className="interest-rail">
            {categories.map((category) => (
              <button
                className={`subinterest-card ${selectedCategory === category.id ? "active" : ""}`}
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                type="button"
              >
                <strong>{category.name}</strong>
                <span>{category.meta}</span>
              </button>
            ))}
          </div>

          <div className="category-section">
            <div className="category-header">
              <div>
                <h3>{sectionTitle(categories, selectedCategory)}</h3>
                <p>{sectionDescription(selectedCategory)}</p>
              </div>
              <div className="tag-row">
                <span className="tag blue">当前分类</span>
                {refreshState ? (
                  <span className="tag green">
                    刚刚刷新 · 第 {refreshState.refreshCount} 次 · {formatTime(refreshState.refreshedAt)}
                  </span>
                ) : null}
              </div>
            </div>
            <div className="grid-2">
              {cards.map((card, index) => (
                <ContentCard
                  card={card}
                  featured={index === 0}
                  key={card.id}
                  reaction={reactions[card.id]}
                  expanded={expandedCardIds.includes(card.id)}
                  expandedSourceId={expandedSourceIds[card.id] || ""}
                  onToggleSource={(sourceId) => onToggleSource(card.id, sourceId)}
                  onToggleSummary={() => onToggleSummary(card.id)}
                  onReact={(reaction) => onReact(card, reaction)}
                  onQuestion={() => onQuestion(card)}
                  onAddSeed={() => onAddSeed(card)}
                  onWrite={() => onWrite(card)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ContentCard({
  card,
  featured,
  reaction,
  expanded,
  expandedSourceId,
  onToggleSource,
  onToggleSummary,
  onReact,
  onQuestion,
  onAddSeed,
  onWrite,
}: {
  card: WorthReadingCard;
  featured: boolean;
  reaction?: SeedReaction;
  expanded: boolean;
  expandedSourceId: string;
  onToggleSource: (sourceId: string) => void;
  onToggleSummary: () => void;
  onReact: (reaction: Extract<SeedReaction, "agree" | "disagree">) => void;
  onQuestion: () => void;
  onAddSeed: () => void;
  onWrite: () => void;
}) {
  const cardExpanded = featured || expanded;

  function handleCardClick(event: MouseEvent<HTMLElement>) {
    if (featured) return;
    const target = event.target;
    if (target instanceof HTMLElement && target.closest("button, a, input, textarea, select")) return;
    onToggleSummary();
  }

  function handleCardKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (featured) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target;
    if (target instanceof HTMLElement && target.closest("button, a, input, textarea, select")) return;
    event.preventDefault();
    onToggleSummary();
  }

  return (
    <article
      className={`card structured-card ${featured ? "featured-card" : "expandable-card"} ${expanded && !featured ? "expanded-card" : ""}`}
      data-expanded={cardExpanded}
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      tabIndex={featured ? undefined : 0}
    >
      <div className="tag-row">
        {card.tags.map((tag) => (
          <span className={`tag ${tag.tone}`} key={`${card.id}-${tag.label}`}>
            {tag.label}
          </span>
        ))}
        {reaction ? <span className="tag green">已记录：{reactionLabel(reaction)}</span> : null}
        {!featured ? <span className={`tag ${expanded ? "green" : "blue"}`}>{expanded ? "完整卡片已展开" : "点击卡片展开完整来源"}</span> : null}
      </div>
      <h3>标题：{card.title}</h3>
      <InfoBlock title="推荐理由" text={card.recommendationReason} />

      <div className="field-block">
        <div className="field-title">原始内容来源：</div>
        <div className={cardExpanded ? "source-list" : "source-chip-list"}>
          {card.originalSources.map((source) =>
            cardExpanded ? (
              <button
                className={`source-card source-button ${expandedSourceId === source.sourceId ? "selected" : ""}`}
                key={source.sourceId}
                onClick={() => onToggleSource(source.sourceId)}
                type="button"
              >
                <div className="source-meta">
                  <span>{source.sourceType}</span>
                  {source.meta.map((item) => (
                    <span key={item}>{item}</span>
                  ))}
                </div>
                <strong>{source.title}</strong>
                <p>来源要点：{source.rawExcerpt}</p>
                <p>贡献：{source.contribution}</p>
              </button>
            ) : (
              <button
                className={`source-chip ${expandedSourceId === source.sourceId ? "selected" : ""}`}
                key={source.sourceId}
                onClick={() => onToggleSource(source.sourceId)}
                type="button"
              >
                <BookOpen size={13} />
                {source.sourceType}
              </button>
            ),
          )}
        </div>
        {expandedSourceId ? <InlineSourcePanel source={card.originalSources.find((source) => source.sourceId === expandedSourceId)} /> : null}
      </div>

      <InfoBlock title="内容摘要" text={card.contentSummary} />
      {expanded ? (
        <div className="ai-summary">
          <div className="tag-row">
            <span className="tag blue">AI 摘要已展开</span>
            <span className="tag green">可沉淀种子</span>
          </div>
          <p>
            这张卡片当前可写性为 {card.relevanceScore} 分，争议度为 {card.controversyScore} 分。建议先记录立场，再通过“有疑问”把不确定性转成可浇水材料。
          </p>
        </div>
      ) : null}
      <ListBlock ordered title="主要争议" items={card.controversies} />
      <ListBlock title="可写角度" items={card.writingAngles} />
      <div className="action-row">
        <button className={`btn ghost ${expanded ? "selected" : ""}`} onClick={onToggleSummary} type="button">
          {featured ? "总结一下" : expanded ? "收起卡片" : "展开卡片"}
        </button>
        <button className={`btn ghost ${reaction === "agree" ? "selected" : ""}`} onClick={() => onReact("agree")} type="button">
          我认同
        </button>
        <button className={`btn ghost ${reaction === "disagree" ? "selected" : ""}`} onClick={() => onReact("disagree")} type="button">
          我反对
        </button>
        <button className={`btn ghost ${reaction === "question" ? "selected" : ""}`} onClick={onQuestion} type="button">
          有疑问
        </button>
        <button className="btn primary" onClick={onAddSeed} type="button">
          加入种子库
        </button>
        <button className="btn ghost" onClick={onWrite} type="button">
          基于它写一篇
        </button>
      </div>
    </article>
  );
}

function SeedsSection({
  seeds,
  selectedSeed,
  setSelectedSeedId,
  openNewSeed,
  openWatering,
  startWriting,
  openMerge,
}: {
  seeds: IdeaSeed[];
  selectedSeed: IdeaSeed;
  setSelectedSeedId: (id: string) => void;
  openNewSeed: () => void;
  openWatering: (id: string) => void;
  startWriting: (id: string) => void;
  openMerge: (id: string) => void;
}) {
  return (
    <section className="section active">
      <div className="two-column-layout">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">我的种子库</h2>
              <p className="panel-subtitle">种子卡片包含来源、反应、疑问、浇水材料、成熟度和下一步操作。</p>
            </div>
            <button className="btn primary" onClick={openNewSeed} type="button">
              <Plus size={14} />
              新建种子
            </button>
          </div>
          <div className="panel-body seed-list">
            {seeds.map((seed) => (
              <button
                className={`card structured-card seed-card ${seed.id === selectedSeed.id ? "selected" : ""}`}
                key={seed.id}
                onClick={() => setSelectedSeedId(seed.id)}
                type="button"
              >
                <SeedHeader seed={seed} />
                <h3>观点种子：{seed.title}</h3>
                <InfoBlock title="来源" text={seed.source} />
                <InfoBlock title="我的反应" text={reactionLabel(seed.userReaction)} />
                <InfoBlock title="核心观点" text={seed.coreClaim} />
                <Progress value={seed.maturityScore} label="成熟度" />
                <div className="material-mini-row">
                  {materialTypes.map((type) => (
                    <span className={`tag ${materialMeta[type].tone}`} key={type}>
                      {materialMeta[type].title} {seed.wateringMaterials.filter((item) => item.type === type).length}
                    </span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">种子详情</h2>
              <p className="panel-subtitle">把模糊想法培养成可写作结构。</p>
            </div>
          </div>
          <div className="panel-body">
            <div className="card no-hover structured-card">
              <SeedHeader seed={selectedSeed} />
              <h3>{selectedSeed.coreClaim}</h3>
              <InfoBlock title="原始内容摘要" text={selectedSeed.sourceSummary} />
              <InfoBlock title="用户笔记" text={selectedSeed.userNote || "暂无补充。"} />
              <ListBlock ordered title="可写方向" items={selectedSeed.possibleAngles} />
              <ListBlock title="反方问题" items={selectedSeed.counterArguments} />
              <ListBlock title="需要补充" items={selectedSeed.requiredMaterials} />
              <Progress value={selectedSeed.maturityScore} label="成熟度" />
              <div className="action-row">
                <button className="btn ghost" onClick={() => openWatering(selectedSeed.id)} type="button">
                  <Droplets size={14} />
                  继续浇水
                </button>
                <button className="btn primary" onClick={() => startWriting(selectedSeed.id)} type="button">
                  开始写作
                </button>
                <button className="btn ghost" onClick={() => openMerge(selectedSeed.id)} type="button">
                  合并相似种子
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SproutSection({
  started,
  opportunities,
  onStart,
  openSeeds,
  startWriting,
  onSupplement,
  onSwitchAngle,
  onDismiss,
}: {
  started: boolean;
  opportunities: SproutOpportunity[];
  onStart: () => void;
  openSeeds: () => void;
  startWriting: (seedId: string) => void;
  onSupplement: (opportunity: SproutOpportunity) => void;
  onSwitchAngle: (opportunity: SproutOpportunity) => void;
  onDismiss: (id: string) => void;
}) {
  const visibleOpportunities = opportunities.filter((item) => item.status !== "dismissed");

  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">今日发芽</h2>
            <p className="panel-subtitle">历史种子 × 今日热点 × 用户画像，捕捉最适合动笔的时机。默认由用户主动触发。</p>
          </div>
          <button className="btn primary" onClick={onStart} type="button">
            开始今日发芽
          </button>
        </div>
        {!started ? (
          <div className="panel-body">
            <article className="card structured-card no-hover">
              <div className="tag-row">
                <span className="tag green">小刘看山</span>
                <span className="tag orange">用户主动触发</span>
              </div>
              <h3>今天要不要给你的种子浇浇水？</h3>
              <InfoBlock title="我会帮你检查" text="历史观点种子、今日热榜、知乎搜索、关注流和你的兴趣画像之间是否出现新的写作机会。" />
              <InfoBlock title="为什么需要你确认" text="今日发芽涉及搜索、语义匹配和 LLM 判断，会产生接口调用和 Token 成本，所以不自动频繁计算。" />
              <div className="action-row">
                <button className="btn primary" onClick={onStart} type="button">
                  开始今日发芽
                </button>
                <button className="btn ghost" onClick={openSeeds} type="button">
                  先看看种子库
                </button>
              </div>
            </article>
          </div>
        ) : (
          <div className="panel-body grid-2">
            {visibleOpportunities.map((opportunity) => (
              <article className="card structured-card sprout-card" key={opportunity.id}>
                <div className="sprout-badge">{opportunity.score}</div>
                <div className="tag-row">
                  {opportunity.tags.map((tag, index) => (
                    <span className={`tag ${tag.tone}`} key={`${opportunity.id}-${tag.label}-${index}`}>
                      {tag.label}
                    </span>
                  ))}
                  {opportunity.status ? <span className="tag purple">{opportunityStatus(opportunity.status)}</span> : null}
                </div>
                <h3>今日发芽机会</h3>
                <InfoBlock title="被激活的种子" text={opportunity.activatedSeed} />
                <InfoBlock title="触发热点" text={opportunity.triggerTopic} />
                <InfoBlock title="为什么值得写" text={opportunity.whyWorthWriting} />
                <InfoBlock title="建议标题" text={opportunity.suggestedTitle} />
                <InfoBlock title="建议角度" text={opportunity.suggestedAngle} />
                <InfoBlock title="建议补充" text={opportunity.suggestedMaterials} />
                <div className="action-row">
                  <button className="btn primary" onClick={() => startWriting(opportunity.seedId)} type="button">
                    开始写作
                  </button>
                  <button className="btn ghost" onClick={() => onSupplement(opportunity)} type="button">
                    补充资料
                  </button>
                  <button className="btn ghost" onClick={() => onSwitchAngle(opportunity)} type="button">
                    换个角度
                  </button>
                  <button className="btn ghost" onClick={() => onDismiss(opportunity.id)} type="button">
                    暂时不写
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function WritingSection({
  seed,
  memory,
  baseMemory,
  session,
  step,
  setStep,
  updateSession,
  addMaterial,
  publishWriting,
  showToast,
}: {
  seed: IdeaSeed;
  memory: MemorySummary;
  baseMemory: MemorySummary;
  session?: WritingSession;
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  updateSession: (patch: Partial<WritingSession>) => void;
  addMaterial: (material: Omit<WateringMaterial, "id" | "createdAt">) => void;
  publishWriting: () => void;
  showToast: (message: string) => void;
}) {
  const currentSession = session ?? {
    articleType: "deep_analysis",
    coreClaim: seed.coreClaim,
    tone: "balanced" as const,
    confirmed: false,
    adoptedSuggestions: [],
    draftStatus: "claim_confirming" as const,
    savedDraft: false,
    memoryOverride: memory,
  };

  return (
    <section className="section active">
      <div className="wizard-layout">
        <aside className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">写作流程</h2>
              <p className="panel-subtitle">流程可交互，状态写入本地写作 session。</p>
            </div>
          </div>
          <div className="panel-body stepper">
            {writingSteps.map((item, index) => (
              <button
                className={`step-item ${index === step ? "active" : ""} ${index < step ? "done" : ""}`}
                key={item.title}
                onClick={() => setStep(index)}
                type="button"
              >
                <span className="step-num">{index < step ? <Check size={15} /> : index + 1}</span>
                <span className="step-copy">
                  <strong>{item.title}</strong>
                  <span>{item.desc}</span>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <article className="panel writing-stage">
          <div className="stage-content">
            <MemoryInjection
              baseMemory={baseMemory}
              memory={memory}
              onChange={(nextMemory) => updateSession({ memoryOverride: nextMemory })}
              onReset={() => {
                updateSession({ memoryOverride: baseMemory });
                showToast("已恢复画像默认 Memory 注入");
              }}
            />
            <WritingStageContent
              seed={seed}
              memory={memory}
              session={currentSession}
              step={step}
              setStep={setStep}
              updateSession={updateSession}
              addMaterial={addMaterial}
              publishWriting={publishWriting}
              showToast={showToast}
            />
            <div className="action-row stage-nav">
              <button className="btn ghost" disabled={step === 0} onClick={() => setStep(Math.max(0, step - 1))} type="button">
                上一步
              </button>
              <button
                className="btn primary"
                disabled={step === writingSteps.length - 1}
                onClick={() => setStep(Math.min(writingSteps.length - 1, step + 1))}
                type="button"
              >
                下一步
              </button>
            </div>
          </div>
        </article>

        <aside className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">看山圆桌</h2>
              <p className="panel-subtitle">不同 Agent 共同评判，采纳结果会写入 session。</p>
            </div>
          </div>
          <div className="panel-body form-grid">
            <div className="check-item">
              <h4>
                <span className="tag blue">当前状态</span>
              </h4>
              <p>
                类型：{articleTypes.find(([id]) => id === currentSession.articleType)?.[1] ?? "深度分析"}；语气：
                {toneLabel(currentSession.tone)}；已采纳 {currentSession.adoptedSuggestions.length} 条建议。
              </p>
            </div>
            {currentSession.adoptedSuggestions.map((item) => (
              <div className="check-item compact-check" key={item}>
                <span className="tag green">已采纳</span>
                <p>{item}</p>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}

function WritingStageContent({
  seed,
  memory,
  session,
  step,
  setStep,
  updateSession,
  addMaterial,
  publishWriting,
  showToast,
}: {
  seed: IdeaSeed;
  memory: MemorySummary;
  session: Pick<WritingSession, "articleType" | "coreClaim" | "tone" | "confirmed" | "adoptedSuggestions" | "draftStatus" | "savedDraft">;
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  updateSession: (patch: Partial<WritingSession>) => void;
  addMaterial: (material: Omit<WateringMaterial, "id" | "createdAt">) => void;
  publishWriting: () => void;
  showToast: (message: string) => void;
}) {
  if (step === 0) {
    return (
      <>
        <h2 className="stage-title">选择观点种子</h2>
        <p className="stage-desc">当前写作基于选中的观点种子，材料和疑问会进入写作上下文。</p>
        <div className="draft-box">
          <SeedHeader seed={seed} />
          <h2>观点种子：{seed.title}</h2>
          <p>
            <strong>核心观点：</strong>
            {seed.coreClaim}
          </p>
          <p>
            <strong>已有浇水材料：</strong>
            {seed.wateringMaterials.length} 条；疑问 {seed.questions.length} 条。
          </p>
        </div>
      </>
    );
  }

  if (step === 1) {
    return (
      <>
        <h2 className="stage-title">核心观点确认</h2>
        <p className="stage-desc">AI 可以提炼观点，但最终立场必须由用户确认。</p>
        <div className="draft-box">
          <h2>我理解你想表达的是：</h2>
          <p>
            <strong>核心观点：</strong>
            <br />
            {session.coreClaim}
          </p>
          <p>
            <strong>文章基调：</strong>
            <br />
            {toneLabel(session.tone)}。不是替你决定立场，而是把你已经沉淀的材料组织清楚。
          </p>
          <p>
            <strong>读者应带走的判断：</strong>
            <br />
            {seed.possibleAngles[0] ?? seed.coreClaim}
          </p>
          <div className="action-row">
            <button
              className={`btn primary ${session.confirmed ? "selected" : ""}`}
              onClick={() => {
                updateSession({ confirmed: true, draftStatus: "blueprint_ready" });
                showToast("已确认核心观点");
              }}
              type="button"
            >
              确认
            </button>
            <button
              className="btn ghost"
              onClick={() => {
                updateSession({ coreClaim: `${session.coreClaim} 但需要明确它成立的边界。` });
                showToast("已调整观点边界");
              }}
              type="button"
            >
              调整观点
            </button>
            <button className="btn ghost" onClick={() => updateSession({ tone: "sharp" })} type="button">
              更犀利一点
            </button>
            <button className="btn ghost" onClick={() => updateSession({ tone: "steady" })} type="button">
              更稳健一点
            </button>
            <button
              className="btn ghost"
              onClick={() => {
                addMaterial({
                  type: "personal_experience",
                  title: "写作阶段补充个人经历",
                  content: "用户需要补充一个真实项目场景：代码本身不难，难的是需求边界、状态变化和交付责任。",
                  sourceLabel: "写作苗圃",
                  adopted: true,
                });
              }}
              type="button"
            >
              补充个人经历
            </button>
          </div>
        </div>
      </>
    );
  }

  if (step === 2) {
    return (
      <>
        <h2 className="stage-title">选择文章类型</h2>
        <p className="stage-desc">不同文章类型会影响结构、语气、证据密度和情绪强度。</p>
        <div className="grid-2">
          {articleTypes.map(([id, title, desc]) => (
            <button
              className={`card no-hover type-card ${session.articleType === id ? "selected" : ""}`}
              key={id}
              onClick={() => {
                updateSession({ articleType: id, draftStatus: "blueprint_ready" });
                showToast(`已选择文章类型：${title}`);
              }}
              type="button"
            >
              {id === "deep_analysis" ? (
                <div className="tag-row">
                  <span className="tag blue">推荐</span>
                </div>
              ) : null}
              <h3>{title}</h3>
              <p>{desc}</p>
            </button>
          ))}
        </div>
      </>
    );
  }

  if (step === 3) {
    const blueprint = buildWritingBlueprint(seed, memory);

    return (
      <>
        <h2 className="stage-title">论证蓝图</h2>
        <p className="stage-desc">先把文章骨架搭好，再进入正文。</p>
        <div className="draft-box">
          <p>
            <strong>中心观点：</strong>
            <br />
            {session.coreClaim}
          </p>
          {blueprint.map((item) => (
            <Blueprint items={item.items} key={item.title} title={item.title} />
          ))}
          <ListBlock title="需要回应的反方" items={seed.counterArguments} />
          <button
            className="btn primary"
            onClick={() => {
              updateSession({ draftStatus: "draft_ready" });
              showToast("论证蓝图已生成，可进入初稿");
            }}
            type="button"
          >
            确认蓝图
          </button>
        </div>
      </>
    );
  }

  if (step === 4) {
    return (
      <>
        <h2 className="stage-title">生成表达初稿</h2>
        <p className="stage-desc">这不是最终发布稿，而是基于观点种子和浇水材料生成的可编辑表达稿。</p>
        <DraftBox memory={memory} seed={seed} session={session} />
      </>
    );
  }

  if (step === 5) {
    return (
      <>
        <h2 className="stage-title">圆桌审稿会</h2>
        <p className="stage-desc">逻辑压测和人味检查合并为圆桌会议，由不同 Agent 从不同视角评判讨论。</p>
        <div className="roundtable">
          <AgentReview avatar="逻" title="逻辑审稿 Agent" text="需要把“能力同质化”和“工作流壁垒”之间的推导补充得更明确。" />
          <AgentReview avatar="人" title="人味编辑 Agent" text="文章仍需要一个你的真实项目经验，否则会像行业分析而不像你的判断。" tone="orange" />
          <AgentReview avatar="反" title="反方读者 Agent" text="未来长上下文模型能吸收整个代码库，为什么上下文仍是壁垒？" tone="purple" />
          <AgentReview avatar="传" title="社区传播 Agent" text="标题可保留，但开头建议从工程场景切入。" tone="green" />
        </div>
        <div className="action-row">
          {["采纳逻辑建议", "补充个人经历", "生成反方回应"].map((item) => (
            <button
              className={`btn ghost ${session.adoptedSuggestions.includes(item) ? "selected" : ""}`}
              key={item}
              onClick={() => {
                updateSession({ adoptedSuggestions: unique([...session.adoptedSuggestions, item]), draftStatus: "reviewing" });
                showToast(`${item}已写入审稿状态`);
              }}
              type="button"
            >
              {item}
            </button>
          ))}
          <button
            className="btn primary"
            onClick={() => {
              updateSession({ draftStatus: "finalized" });
              setStep(6);
              showToast("已进入定稿草案");
            }}
            type="button"
          >
            我觉得可以，进入定稿
          </button>
        </div>
      </>
    );
  }

  if (step === 6) {
    return (
      <>
        <h2 className="stage-title">定稿草案</h2>
        <p className="stage-desc">系统根据圆桌会议整理出最终草稿，但要求用户修改后再发布。</p>
        <div className="draft-box">
          <div className="tag-row">
            <span className="tag green">可定稿</span>
            <span className="tag orange">发布前请人工修改</span>
          </div>
          <FinalDraft memory={memory} seed={seed} session={session} />
          <div className="action-row">
            <button className={`btn primary ${session.draftStatus === "finalized" ? "selected" : ""}`} onClick={() => updateSession({ draftStatus: "finalized" })} type="button">
              确认定稿
            </button>
            <button
              className="btn ghost"
              onClick={() => {
                updateSession({ draftStatus: "draft_ready" });
                setStep(4);
              }}
              type="button"
            >
              继续修改
            </button>
            <button className="btn ghost" onClick={() => copyText(finalDraftText(seed, session, memory), showToast)} type="button">
              复制草稿
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <h2 className="stage-title">发布与反馈</h2>
      <p className="stage-desc">要求用户修改后发布，并进入历史文章监控反馈页面。</p>
      <div className="draft-box">
        <h2>发布前提醒</h2>
        <ul className="field-list">
          <li>请补充一个真实经历中的工程场景，避免文章过于抽象。</li>
          <li>请确认文中观点是你认可的表达，不要直接发布未检查版本。</li>
          <li>建议先发布到圈子收集评论，再发布为长文。</li>
          <li>发布后进入“历史反馈”页面，系统会提取评论中的支持、反对和补充材料。</li>
        </ul>
        <div className="action-row">
          <button className="btn primary" onClick={publishWriting} type="button">
            <Send size={14} />
            我已修改，模拟发布
          </button>
          <button
            className={`btn ghost ${session.savedDraft ? "selected" : ""}`}
            onClick={() => {
              updateSession({ savedDraft: true });
              showToast("草稿已保存到本地写作 session");
            }}
            type="button"
          >
            <Save size={14} />
            保存为草稿
          </button>
          <button className="btn ghost" onClick={() => copyText(finalDraftText(seed, session, memory), showToast)} type="button">
            <Copy size={14} />
            复制最终稿
          </button>
        </div>
      </div>
    </>
  );
}

function HistorySection({
  articles,
  syncFeedback,
  generateSecondArticle,
  openComments,
}: {
  articles: FeedbackArticle[];
  syncFeedback: () => void;
  generateSecondArticle: (article: FeedbackArticle) => void;
  openComments: (article: FeedbackArticle) => void;
}) {
  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">历史文章监控反馈</h2>
            <p className="panel-subtitle">监控已发布文章表现，提取反馈信号，反哺用户画像、种子库和下一篇文章。</p>
          </div>
          <button className="btn primary" onClick={syncFeedback} type="button">
            同步反馈
          </button>
        </div>
        <div className="panel-body grid-1">
          {articles.map((article) => (
            <article className="card history-card" key={article.id}>
              <div>
                <div className="tag-row">
                  <span className="tag blue">已发布</span>
                  <span className={`tag ${article.statusTone}`}>{article.status}</span>
                </div>
                <h3>{article.title}</h3>
                <InfoBlock title="表现摘要" text={article.performanceSummary} />
                <ListBlock ordered title="评论反馈提取" items={article.commentInsights} />
                <InfoBlock title="反哺动作" text={article.memoryAction} />
                <div className="action-row">
                  <button className="btn primary" onClick={() => generateSecondArticle(article)} type="button">
                    生成二次文章
                  </button>
                  <button className="btn ghost" onClick={() => openComments(article)} type="button">
                    查看评论摘要
                  </button>
                </div>
              </div>
              <div className="mini-bars">
                {article.metrics.map((metric) => (
                  <div key={metric.label}>
                    <div className="field-title">
                      {metric.label} {metric.value}%
                    </div>
                    <div className="mini-bar">
                      <span style={{ width: `${metric.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProfileSection({
  profile,
  categories,
  onSave,
}: {
  profile: ProfileData;
  categories: InputCategory[];
  onSave: (profile: ProfileData) => void;
}) {
  const [draft, setDraft] = useState(profile);

  function toggleInterest(interest: string) {
    const interests = draft.interests.includes(interest)
      ? draft.interests.filter((item) => item !== interest)
      : [...draft.interests, interest];
    setDraft({ ...draft, interests });
  }

  return (
    <section className="section active">
      <div className="profile-layout">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">个人信息管理</h2>
              <p className="panel-subtitle">独立部署时，这里用于建立和维护你的本地用户画像 Memory。</p>
            </div>
            <button className="btn primary" onClick={() => onSave(draft)} type="button">
              保存画像
            </button>
          </div>
          <div className="panel-body form-grid">
            <EditableField label="昵称" value={draft.nickname} onChange={(nickname) => setDraft({ ...draft, nickname })} />
            <EditableField label="账号状态" value={draft.accountStatus} onChange={(accountStatus) => setDraft({ ...draft, accountStatus })} />
            <EditableField label="身份标签" value={draft.role} onChange={(role) => setDraft({ ...draft, role })} />
            <div className="field">
              <label>兴趣小类</label>
              <div className="tag-row">
                {categories.filter((category) => category.kind === "interest").map((category) => (
                  <button className={`chip ${draft.interests.includes(category.name) ? "selected" : ""}`} key={category.id} onClick={() => toggleInterest(category.name)} type="button">
                    {category.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="field">
              <label>不希望系统做什么</label>
              <textarea className="textarea" value={draft.avoidances} onChange={(event) => setDraft({ ...draft, avoidances: event.target.value })} />
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">用户画像 Memory</h2>
              <p className="panel-subtitle">可展示、可编辑。真实产品中用于推荐、发芽和写作风格控制。</p>
            </div>
          </div>
          <div className="panel-body form-grid">
            {Object.entries(draft.globalMemory).map(([key, value]) => (
              <MemoryCard
                key={key}
                title={globalMemoryLabel(key)}
                text={value}
                onChange={(nextValue) => setDraft({ ...draft, globalMemory: { ...draft.globalMemory, [key]: nextValue } })}
              />
            ))}
          </div>
        </div>

        <div className="panel profile-wide">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">兴趣分类画像</h2>
              <p className="panel-subtitle">不同兴趣小类有不同的知识水平、证据偏好、推荐策略和写作风险提醒。</p>
            </div>
          </div>
          <div className="panel-body grid-3">
            {draft.interestMemories.map((memory) => (
              <div className="memory-card" key={memory.interestId}>
                <strong>{memory.interestName}</strong>
                <p className="field-text">
                  知识水平：{memory.knowledgeLevel}；偏好视角：{memory.preferredPerspective.join("、")}。
                </p>
                <textarea
                  className="textarea"
                  value={`证据偏好：${memory.evidencePreference}。写作提醒：${memory.writingReminder}`}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      interestMemories: draft.interestMemories.map((item) =>
                        item.interestId === memory.interestId ? { ...item, writingReminder: event.target.value } : item,
                      ),
                    })
                  }
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function InlineSourcePanel({ source }: { source?: ContentSource }) {
  if (!source) return null;

  return (
    <div className="source-detail-panel">
      <div className="source-detail-head">
        <div>
          <span className="tag blue">{source.sourceType}</span>
          <h4>{source.title}</h4>
        </div>
        <span className="tag green">API 原文 mock</span>
      </div>
      <div className="source-detail-grid">
        <InfoBlock title="作者 / 来源" text={source.author ?? "未知"} />
        <InfoBlock title="发布时间" text={source.publishedAt ?? "未知"} />
        <InfoBlock title="权威与热度" text={source.authorityMeta ?? source.meta.join(" / ")} />
        <InfoBlock title="Source ID" text={source.sourceId} />
      </div>
      <InfoBlock title="原文要点" text={source.rawExcerpt} />
      <div className="source-full-content">
        <div className="field-title">完整内容：</div>
        <p>{source.fullContent}</p>
      </div>
      <InfoBlock title="对当前卡片的贡献" text={source.contribution} />
    </div>
  );
}

function QuestionDialog({
  card,
  onClose,
  onAnswer,
  onMark,
}: {
  card: WorthReadingCard;
  onClose: () => void;
  onAnswer: (question: string) => { seedId: string; questionId: string; question: string; agentAnswer: string; citedSourceIds: string[] };
  onMark: (seedId: string, questionId: string, status: SeedQuestion["status"]) => void;
}) {
  const [question, setQuestion] = useState(`这个判断的反方证据是什么？`);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [answerThread, setAnswerThread] = useState<
    { seedId: string; questionId: string; question: string; agentAnswer: string; citedSourceIds: string[] }[]
  >([]);
  const [markedStatuses, setMarkedStatuses] = useState<Record<string, SeedQuestion["status"]>>({});
  const latestAnswer = answerThread[answerThread.length - 1];
  const latestStatus = latestAnswer ? markedStatuses[latestAnswer.questionId] : "";
  const flowResolved = latestStatus === "resolved";

  function submitQuestion() {
    const nextQuestion = latestAnswer ? followUpQuestion.trim() : question.trim();
    if (!nextQuestion || flowResolved) return;
    const nextAnswer = onAnswer(nextQuestion);
    setAnswerThread((current) => [...current, nextAnswer]);
    setMarkedStatuses((current) => {
      const next = { ...current };
      delete next[nextAnswer.questionId];
      return next;
    });
    setFollowUpQuestion("");
  }

  function markAnswer(
    answer: { seedId: string; questionId: string; question: string; agentAnswer: string; citedSourceIds: string[] },
    status: SeedQuestion["status"],
  ) {
    onMark(answer.seedId, answer.questionId, status);
    setMarkedStatuses((current) => ({ ...current, [answer.questionId]: status }));
    if (status === "needs_material") {
      setFollowUpQuestion(`请继续补充“${answer.question}”背后的事实证据、反方材料和可引用来源。`);
    }
  }

  return (
    <div className="overlay">
      <section className="modal">
        <div className="modal-header">
          <div>
            <span className="tag purple">有疑问</span>
            <h2>记录疑问，并让 Agent 先帮你求证</h2>
          </div>
          <button className="icon-btn" onClick={onClose} type="button" aria-label="关闭疑问弹窗">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body form-grid">
          <InfoBlock title="关联卡片" text={card.title} />
          <div className="field">
            <label>我的具体疑问</label>
            <textarea className="textarea" value={question} onChange={(event) => setQuestion(event.target.value)} disabled={!!latestAnswer} />
          </div>
          {answerThread.length ? (
            <div className="answer-thread">
              {answerThread.map((answer, index) => {
                const status = markedStatuses[answer.questionId];
                const isLatest = answer.questionId === latestAnswer?.questionId;
                return (
                  <div className="answer-box" key={answer.questionId}>
                    <div className="tag-row">
                      <span className="tag green">{index === 0 ? "Agent 初步回答" : `第 ${index + 1} 轮追问`}</span>
                      <span className="tag blue">已回写浇水材料</span>
                      {status === "resolved" ? <span className="tag green">已解决</span> : null}
                      {status === "needs_material" ? <span className="tag orange">仍需补资料</span> : null}
                    </div>
                    <p>
                      <strong>问题：</strong>
                      {answer.question}
                    </p>
                    <p>{answer.agentAnswer}</p>
                    <p className="field-text">引用来源：{answer.citedSourceIds.join("、")}</p>
                    {isLatest && !flowResolved ? (
                      <div className="action-row tight-row">
                        <button
                          className={`btn ghost compact ${status === "resolved" ? "selected" : ""}`}
                          onClick={() => markAnswer(answer, "resolved")}
                          type="button"
                        >
                          标记已解决
                        </button>
                        <button
                          className={`btn ghost compact ${status === "needs_material" ? "selected" : ""}`}
                          onClick={() => markAnswer(answer, "needs_material")}
                          type="button"
                        >
                          仍需补资料
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })}
              {flowResolved ? (
                <div className="answer-flow-done">
                  <span className="tag green">流程已结束</span>
                  <p>当前疑问已经标记解决。后续如果有新问题，可以重新从卡片点击“有疑问”开启新的追问线程。</p>
                </div>
              ) : (
                <div className="field">
                  <label>继续追问 / 新问题</label>
                  <textarea
                    className="textarea"
                    value={followUpQuestion}
                    onChange={(event) => setFollowUpQuestion(event.target.value)}
                    placeholder="例如：请继续补充真实案例、反方证据或可引用来源。"
                  />
                </div>
              )}
            </div>
          ) : null}
          <div className="action-row">
            <button
              className="btn primary"
              onClick={submitQuestion}
              type="button"
              disabled={flowResolved || (latestAnswer ? !followUpQuestion.trim() : !question.trim())}
            >
              <MessageCircleQuestion size={14} />
              {latestAnswer ? "继续追问并记录" : "让 Agent 回答并记录"}
            </button>
            <button className="btn ghost" onClick={onClose} type="button">
              完成
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function NewSeedModal({
  categories,
  onClose,
  onCreate,
}: {
  categories: InputCategory[];
  onClose: () => void;
  onCreate: (seed: Pick<IdeaSeed, "title" | "interestId" | "coreClaim" | "userNote" | "requiredMaterials">) => void;
}) {
  const interestCategories = categories.filter((category) => category.kind === "interest");
  const [title, setTitle] = useState("我想写一个关于 AI 工具和工程判断的观点");
  const [interestId, setInterestId] = useState(interestCategories[0]?.id ?? "agent");
  const [coreClaim, setCoreClaim] = useState("AI 可以降低实现门槛，但不能替代工程判断。");
  const [userNote, setUserNote] = useState("这是我看完今天内容后的初步想法，还需要补案例和反方。");
  const [requiredMaterials, setRequiredMaterials] = useState("个人项目经历\n反方观点\n可引用来源");

  return (
    <div className="overlay">
      <section className="modal">
        <div className="modal-header">
          <div>
            <span className="tag green">新建种子</span>
            <h2>手动记录一颗观点种子</h2>
          </div>
          <button className="icon-btn" onClick={onClose} type="button" aria-label="关闭新建种子">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body form-grid">
          <EditableField label="种子标题" value={title} onChange={setTitle} />
          <div className="field">
            <label>兴趣分类</label>
            <select className="select" value={interestId} onChange={(event) => setInterestId(event.target.value)}>
              {interestCategories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>核心观点</label>
            <textarea className="textarea" value={coreClaim} onChange={(event) => setCoreClaim(event.target.value)} />
          </div>
          <div className="field">
            <label>用户笔记</label>
            <textarea className="textarea" value={userNote} onChange={(event) => setUserNote(event.target.value)} />
          </div>
          <div className="field">
            <label>需要补充，每行一条</label>
            <textarea className="textarea" value={requiredMaterials} onChange={(event) => setRequiredMaterials(event.target.value)} />
          </div>
          <div className="action-row">
            <button
              className="btn primary"
              onClick={() =>
                onCreate({
                  title,
                  interestId,
                  coreClaim,
                  userNote,
                  requiredMaterials: requiredMaterials.split("\n").filter(Boolean),
                })
              }
              type="button"
            >
              保存种子
            </button>
            <button className="btn ghost" onClick={onClose} type="button">
              取消
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function WateringModal({
  seed,
  onClose,
  onAdd,
  onToggle,
  onEdit,
  onDelete,
  onResolve,
  onAgentSupplement,
}: {
  seed: IdeaSeed;
  onClose: () => void;
  onAdd: (material: Omit<WateringMaterial, "id" | "createdAt">) => void;
  onToggle: (material: WateringMaterial) => void;
  onEdit: (material: WateringMaterial, patch: Partial<WateringMaterial>) => void;
  onDelete: (materialId: string) => void;
  onResolve: (seedId: string, material: WateringMaterial) => void;
  onAgentSupplement: (type: Extract<WateringMaterialType, "evidence" | "counterargument">) => void;
}) {
  const [drafts, setDrafts] = useState<Record<WateringMaterialType, string>>({
    evidence: "",
    counterargument: "",
    personal_experience: "",
    open_question: "",
  });

  return (
    <div className="overlay">
      <section className="modal wide-modal">
        <div className="modal-header">
          <div>
            <span className="tag green">继续浇水</span>
            <h2>{seed.title}</h2>
            <p className="field-text">补齐事实、反方、个人经验和待解决问题会提升成熟度。</p>
          </div>
          <button className="icon-btn" onClick={onClose} type="button" aria-label="关闭浇水面板">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <Progress value={seed.maturityScore} label="当前成熟度" />
          <div className="material-board">
            {materialTypes.map((type) => {
              const meta = materialMeta[type];
              const materials = seed.wateringMaterials.filter((item) => item.type === type);
              return (
                <section className="material-column" key={type}>
                  <div className="tag-row">
                    <span className={`tag ${meta.tone}`}>{meta.title}</span>
                    <span className="tag blue">{materials.length}</span>
                  </div>
                  <p className="field-text">{meta.desc}</p>
                  <textarea
                    className="textarea compact-textarea"
                    placeholder={`补充${meta.title}`}
                    value={drafts[type]}
                    onChange={(event) => setDrafts({ ...drafts, [type]: event.target.value })}
                  />
                  <button
                    className="btn primary compact"
                    disabled={!drafts[type].trim()}
                    onClick={() => {
                      onAdd({
                        type,
                        title: meta.title,
                        content: drafts[type],
                        sourceLabel: "继续浇水",
                        adopted: type !== "open_question",
                      });
                      setDrafts({ ...drafts, [type]: "" });
                    }}
                    type="button"
                  >
                    添加
                  </button>
                  {type === "evidence" || type === "counterargument" ? (
                    <button className="btn ghost compact" onClick={() => onAgentSupplement(type)} type="button">
                      {type === "evidence" ? "Agent 补证据" : "Agent 找反方"}
                    </button>
                  ) : null}
                  <div className="material-list">
                    {materials.map((material) => (
                      <MaterialItem
                        key={material.id}
                        material={material}
                        onToggle={() => onToggle(material)}
                        onEdit={(patch) => onEdit(material, patch)}
                        onDelete={() => onDelete(material.id)}
                        onResolve={type === "open_question" ? () => onResolve(seed.id, material) : undefined}
                      />
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}

function MaterialItem({
  material,
  onToggle,
  onEdit,
  onDelete,
  onResolve,
}: {
  material: WateringMaterial;
  onToggle: () => void;
  onEdit: (patch: Partial<WateringMaterial>) => void;
  onDelete: () => void;
  onResolve?: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(material.content);

  return (
    <article className="material-item">
      <div className="tag-row">
        <span className={`tag ${material.adopted ? "green" : "orange"}`}>{material.adopted ? "已采纳" : "待采纳"}</span>
        {material.sourceLabel ? <span className="tag blue">{material.sourceLabel}</span> : null}
      </div>
      <strong>{material.title}</strong>
      {editing ? (
        <textarea className="textarea compact-textarea" value={content} onChange={(event) => setContent(event.target.value)} />
      ) : (
        <p>{material.content}</p>
      )}
      <div className="action-row tight-row">
        <button className="btn ghost compact" onClick={onToggle} type="button">
          {material.adopted ? "取消采纳" : "标记采纳"}
        </button>
        <button
          className="btn ghost compact"
          onClick={() => {
            if (editing) onEdit({ content });
            setEditing(!editing);
          }}
          type="button"
        >
          {editing ? "保存编辑" : "编辑"}
        </button>
        {onResolve ? (
          <button className="btn ghost compact" onClick={onResolve} type="button">
            问 Agent
          </button>
        ) : null}
        <button className="btn ghost compact danger" onClick={onDelete} type="button">
          <Trash2 size={13} />
        </button>
      </div>
    </article>
  );
}

function MergeSeedModal({
  seedId,
  seeds,
  onClose,
  onMerge,
}: {
  seedId: string;
  seeds: IdeaSeed[];
  onClose: () => void;
  onMerge: (targetId: string, sourceId: string) => void;
}) {
  const seed = seeds.find((item) => item.id === seedId);
  const candidates = seeds.filter((item) => item.id !== seedId && (item.interestId === seed?.interestId || item.coreClaim.includes(seed?.title.slice(0, 4) ?? "")));

  return (
    <div className="overlay">
      <section className="modal">
        <div className="modal-header">
          <div>
            <span className="tag purple">合并相似种子</span>
            <h2>{seed?.title ?? "种子"}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} type="button" aria-label="关闭合并弹窗">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body form-grid">
          {candidates.length ? (
            candidates.map((candidate) => (
              <article className="card structured-card no-hover" key={candidate.id}>
                <SeedHeader seed={candidate} />
                <h3>{candidate.title}</h3>
                <p>{candidate.coreClaim}</p>
                <button className="btn primary" onClick={() => onMerge(seedId, candidate.id)} type="button">
                  合并到当前种子
                </button>
              </article>
            ))
          ) : (
            <p className="field-text">暂未发现同兴趣下的相似种子。</p>
          )}
        </div>
      </section>
    </div>
  );
}

function CommentDialog({ article, onClose }: { article: FeedbackArticle; onClose: () => void }) {
  return (
    <div className="overlay">
      <section className="modal">
        <div className="modal-header">
          <div>
            <span className="tag blue">评论摘要</span>
            <h2>{article.title}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} type="button" aria-label="关闭评论摘要">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <ListBlock ordered title="评论反馈提取" items={article.commentInsights} />
          <InfoBlock title="Memory 候选更新" text={article.memoryAction} />
        </div>
      </section>
    </div>
  );
}

function SeedHeader({ seed }: { seed: IdeaSeed }) {
  const status = seedStatus(seed.status);
  return (
    <div className="tag-row">
      <span className={`tag ${status.tone}`}>{status.label}</span>
      <span className="tag blue">{seed.interestName}</span>
      <span className="tag green">成熟度 {seed.maturityScore}</span>
    </div>
  );
}

function Progress({ value, label }: { value: number; label: string }) {
  return (
    <div className="progress-block">
      <div className="field-title">
        {label} {value}%
      </div>
      <div className="mini-bar">
        <span style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function DraftBox({ seed, session, memory }: { seed: IdeaSeed; memory: MemorySummary; session: Pick<WritingSession, "tone" | "articleType" | "adoptedSuggestions" | "coreClaim"> }) {
  return (
    <div className="draft-box">
      <h2>{seed.possibleAngles[0] ?? seed.title}</h2>
      <p>{draftLead(seed, session, memory)}</p>
      <p>{session.coreClaim}</p>
      <p>这篇文章会采用{articleTypes.find(([id]) => id === session.articleType)?.[1] ?? "深度分析"}结构，语气保持{toneLabel(session.tone)}。</p>
      <p>已有浇水材料会补入正文：事实证据 {seed.wateringMaterials.filter((item) => item.type === "evidence").length} 条，反方质疑 {seed.wateringMaterials.filter((item) => item.type === "counterargument").length} 条，个人经验 {seed.wateringMaterials.filter((item) => item.type === "personal_experience").length} 条。</p>
    </div>
  );
}

function FinalDraft({ seed, session, memory }: { seed: IdeaSeed; memory: MemorySummary; session: Pick<WritingSession, "coreClaim" | "tone" | "adoptedSuggestions"> }) {
  return (
    <>
      <h2>{seed.possibleAngles[0] ?? seed.title}</h2>
      <p>{finalDraftText(seed, session, memory)}</p>
      {session.adoptedSuggestions.length ? <ListBlock title="已采纳圆桌建议" items={session.adoptedSuggestions} /> : null}
    </>
  );
}

function MemoryInjection({
  baseMemory,
  memory,
  onChange,
  onReset,
}: {
  baseMemory: MemorySummary;
  memory: MemorySummary;
  onChange: (memory: MemorySummary) => void;
  onReset: () => void;
}) {
  const preferredPerspective = memory.preferredPerspective.join("、");

  function updateMemory(patch: Partial<MemorySummary>) {
    onChange({ ...memory, ...patch });
  }

  return (
    <div className="memory-injection">
      <div className="tag-row">
        <span className="tag blue">已匹配兴趣分类画像：{memory.interestName}</span>
        <span className="tag green">Memory 已注入</span>
        <span className="tag purple">本次写作可编辑</span>
      </div>
      <div className="memory-injection-head">
        <div>
          <h3>本次写作使用的画像 Memory</h3>
          <p>修改只写入当前写作 session，不会直接覆盖全局个人画像。</p>
        </div>
        <button className="btn ghost compact" onClick={onReset} type="button" disabled={JSON.stringify(baseMemory) === JSON.stringify(memory)}>
          恢复画像默认
        </button>
      </div>
      <div className="memory-edit-grid">
        <div className="field">
          <label>偏好视角</label>
          <textarea
            className="textarea compact-textarea"
            value={preferredPerspective}
            onChange={(event) =>
              updateMemory({
                preferredPerspective: event.target.value
                  .split(/[、,\n]/)
                  .map((item) => item.trim())
                  .filter(Boolean),
              })
            }
          />
        </div>
        <div className="field">
          <label>证据偏好</label>
          <textarea
            className="textarea compact-textarea"
            value={memory.evidencePreference}
            onChange={(event) => updateMemory({ evidencePreference: event.target.value })}
          />
        </div>
        <div className="field">
          <label>写作提醒</label>
          <textarea
            className="textarea compact-textarea"
            value={memory.writingReminder}
            onChange={(event) => updateMemory({ writingReminder: event.target.value })}
          />
        </div>
        <div className="field">
          <label>历史反馈注入</label>
          <textarea
            className="textarea compact-textarea"
            value={memory.feedbackSummary ?? ""}
            onChange={(event) => updateMemory({ feedbackSummary: event.target.value })}
            placeholder="可补充本次写作需要特别注意的读者反馈。"
          />
        </div>
      </div>
    </div>
  );
}

function InfoBlock({ title, text }: { title: string; text: string }) {
  return (
    <div className="field-block">
      <div className="field-title">{title}：</div>
      <p className="field-text">{text}</p>
    </div>
  );
}

function ListBlock({ title, items, ordered }: { title: string; items: string[]; ordered?: boolean }) {
  const Tag = ordered ? "ol" : "ul";
  return (
    <div className="field-block">
      <div className="field-title">{title}：</div>
      <Tag className="field-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </Tag>
    </div>
  );
}

function Blueprint({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="outline-item">
      <strong>{title}</strong>
      <ul className="field-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function AgentReview({ avatar, title, text, tone = "blue" }: { avatar: string; title: string; text: string; tone?: "blue" | "orange" | "purple" | "green" }) {
  return (
    <div className="agent-card">
      <div className="agent-head">
        <div className={`agent-avatar ${tone}`}>{avatar}</div>
        <strong>{title}</strong>
      </div>
      <p>{text}</p>
    </div>
  );
}

function EditableField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div className="field">
      <label>{label}</label>
      <input className="input" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function MemoryCard({ title, text, onChange }: { title: string; text: string; onChange: (value: string) => void }) {
  return (
    <div className="memory-card">
      <strong>{title}</strong>
      <textarea className="textarea" value={text} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function readStoredState(initialState: DemoState): DemoState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialState;
    const stored = JSON.parse(raw) as Partial<DemoState>;
    return {
      ...initialState,
      ...stored,
      hasEntered: stored.hasEntered ?? false,
      activeTab: stored.activeTab ?? initialState.activeTab,
      selectedCategoryId: stored.selectedCategoryId ?? initialState.selectedCategoryId,
      selectedSeedId: stored.selectedSeedId ?? initialState.selectedSeedId,
      profile: stored.profile ?? initialState.profile,
      categories: initialState.categories,
      cards: initialState.cards,
      seeds: ensureUniqueMaterialIds(stored.seeds?.length ? stored.seeds : initialState.seeds),
      sproutOpportunities: stored.sproutOpportunities?.length ? stored.sproutOpportunities : initialState.sproutOpportunities,
      feedbackArticles: stored.feedbackArticles?.length ? stored.feedbackArticles : initialState.feedbackArticles,
      reactions: stored.reactions ?? {},
      expandedCardIds: stored.expandedCardIds ?? [],
      expandedSourceIds: stored.expandedSourceIds ?? {},
      categoryRefreshState: stored.categoryRefreshState ?? {},
      sproutStarted: stored.sproutStarted ?? false,
    };
  } catch {
    return initialState;
  }
}

function buildSeedFromCard(card: WorthReadingCard, categories: InputCategory[], reaction: SeedReaction, note: string | undefined, id: string): IdeaSeed {
  const category = categories.find((item) => item.id === card.categoryId);
  return recalcSeed({
    id,
    interestId: card.categoryId,
    title: card.writingAngles[0] ?? card.title,
    interestName: category?.name ?? card.categoryId,
    source: card.tags.map((tag) => tag.label).join(" / "),
    sourceTitle: card.title,
    sourceSummary: card.contentSummary,
    sourceUrl: card.originalSources[0]?.sourceUrl,
    sourceType: card.originalSources[0]?.sourceType ?? "mock",
    userReaction: reaction,
    userNote: note ?? reactionLabel(reaction),
    coreClaim: card.writingAngles[0] ?? card.title,
    possibleAngles: card.writingAngles,
    counterArguments: card.controversies,
    requiredMaterials: ["补充个人经验", "补充反方回应", "补充可引用来源"],
    wateringMaterials: [
      buildMaterial("evidence", "来源证据", card.originalSources[0]?.rawExcerpt ?? card.contentSummary, card.originalSources[0]?.sourceType ?? "来源", true),
      buildMaterial("counterargument", "主要争议", card.controversies[0] ?? "需要补充反方观点", "内容卡片", reaction === "disagree"),
    ],
    questions: [],
    status: "water_needed",
    maturityScore: 45,
    createdFromCardId: card.id,
    createdAt: now(),
    updatedAt: now(),
  });
}

function createWritingSession(seed: IdeaSeed, profile?: ProfileData): WritingSession {
  return {
    sessionId: createId("writing", seed.id),
    seedId: seed.id,
    interestId: seed.interestId,
    articleType: "deep_analysis",
    coreClaim: seed.coreClaim,
    memoryOverride: profile ? findMemory(profile, seed.interestId) : undefined,
    tone: "balanced",
    confirmed: false,
    adoptedSuggestions: [],
    draftStatus: "claim_confirming",
    savedDraft: false,
  };
}

function buildAgentAnswer(card: WorthReadingCard, question: string, turnIndex = 0) {
  const sourceNames = card.originalSources.map((source) => source.sourceType).join("、");
  const counter = card.controversies[0] ?? "目前缺少反方材料";
  const evidence = card.originalSources[turnIndex % card.originalSources.length];
  if (turnIndex === 0) {
    return `针对“${question}”，Agent 基于 ${sourceNames} 的初步判断是：这个问题不能直接下结论。正方材料支持“${card.writingAngles[0]}”，但仍需回应“${counter}”。建议把它沉淀为反方回应材料，并在写作前补一个真实案例。`;
  }
  if (turnIndex % 2 === 1) {
    return `第 ${turnIndex + 1} 轮继续求证：我会优先从“${evidence.sourceType}”补材料。当前可引用的方向是“${evidence.rawExcerpt}”。它能帮助回答“${question}”，但仍需要把来源中的具体场景和你的个人经验连接起来，否则文章容易停留在概念判断。`;
  }
  return `第 ${turnIndex + 1} 轮继续求证：围绕“${question}”，更值得补的是反方边界。可以把“${counter}”作为文章中必须回应的问题，再用“${evidence.contribution}”说明为什么你的主张不是绝对结论，而是有适用条件的判断。`;
}

function buildSproutOpportunity(seed: IdeaSeed, index: number): SproutOpportunity {
  const score = Math.min(94, seed.maturityScore + 10 + index * 3);
  return {
    id: `sprout-${seed.id}`,
    seedId: seed.id,
    interestId: seed.interestId,
    score,
    tags: [
      { label: score > 82 ? "高时效" : "可发芽", tone: score > 82 ? "green" : "blue" },
      { label: `发芽指数 ${score}`, tone: "blue" },
    ],
    activatedSeed: seed.coreClaim,
    triggerTopic: `${seed.interestName} 今日出现新讨论：${seed.sourceTitle}`,
    whyWorthWriting: `这条热点和你已有种子高度相关，能补充新的时效背景，并把已有疑问转化为反方回应。`,
    suggestedTitle: seed.possibleAngles[0] ?? seed.title,
    suggestedAngle: seed.possibleAngles[1] ?? seed.coreClaim,
    suggestedMaterials: seed.requiredMaterials[0] ?? "补充一个真实项目案例和一条反方评论。",
    status: "new",
  };
}

function mergeOpportunities(next: SproutOpportunity[], current: SproutOpportunity[]) {
  const map = new Map(current.map((item) => [item.id, item]));
  next.forEach((item) => map.set(item.id, { ...map.get(item.id), ...item }));
  return Array.from(map.values());
}

function buildMaterial(type: WateringMaterialType, title: string, content: string, sourceLabel: string, adopted: boolean): WateringMaterial {
  return {
    id: createId("material", type),
    type,
    title,
    content,
    sourceLabel,
    adopted,
    createdAt: now(),
  };
}

function ensureUniqueMaterialIds(seeds: IdeaSeed[]) {
  return seeds.map((seed) => {
    const seen = new Set<string>();
    return {
      ...seed,
      wateringMaterials: seed.wateringMaterials.map((material) => {
        if (!material.id || seen.has(material.id)) {
          const next = { ...material, id: createId("material", `${material.type}-${material.title}`) };
          seen.add(next.id);
          return next;
        }
        seen.add(material.id);
        return material;
      }),
    };
  });
}

function recalcSeed(seed: IdeaSeed): IdeaSeed {
  const adoptedTypes = new Set(seed.wateringMaterials.filter((material) => material.adopted).map((material) => material.type));
  const resolvedQuestions = seed.questions.filter((question) => question.status === "resolved").length;
  const score = Math.min(96, 32 + adoptedTypes.size * 14 + seed.questions.length * 3 + resolvedQuestions * 4);
  return {
    ...seed,
    maturityScore: score,
    status: seed.status === "published" || seed.status === "writing" ? seed.status : score >= 70 ? "sproutable" : "water_needed",
  };
}

function seedStatus(status: SeedStatus): { label: string; tone: Tone } {
  const map: Record<SeedStatus, { label: string; tone: Tone }> = {
    dormant: { label: "休眠中", tone: "purple" },
    water_needed: { label: "需要浇水", tone: "orange" },
    sproutable: { label: "可发芽", tone: "green" },
    high_timeliness: { label: "高时效", tone: "green" },
    writing: { label: "写作中", tone: "blue" },
    published: { label: "已发布", tone: "blue" },
    expired: { label: "时效已过", tone: "red" },
  };
  return map[status];
}

function reactionLabel(reaction: SeedReaction) {
  const labels: Record<SeedReaction, string> = {
    agree: "我认同",
    disagree: "我反对",
    question: "有疑问",
    supplement: "想补充",
    want_to_write: "想写一篇",
    manual: "手动创建",
  };
  return labels[reaction];
}

function opportunityStatus(status: NonNullable<SproutOpportunity["status"]>) {
  const labels: Record<NonNullable<SproutOpportunity["status"]>, string> = {
    new: "新机会",
    supplemented: "已补资料",
    angle_changed: "已换角度",
    dismissed: "已暂缓",
    writing: "写作中",
  };
  return labels[status];
}

function findMemory(profile: ProfileData, interestId: string) {
  return profile.interestMemories.find((memory) => memory.interestId === interestId) ?? profile.interestMemories[0];
}

function sectionTitle(categories: InputCategory[], categoryId: string) {
  const category = categories.find((item) => item.id === categoryId);
  if (!category) return "当前分类";
  if (category.kind === "following") return "关注流精选";
  if (category.kind === "serendipity") return "偶遇输入";
  return `兴趣小类：${category.name}`;
}

function sectionDescription(category: string) {
  if (category === "following") return "来自你关注的人和圈子动态，优先筛选观点密度高、讨论价值高的内容。";
  if (category === "serendipity") return "保留少量远端关联信息，避免推荐只在同温层内自我强化。";
  return "基于你的兴趣画像、阅读反应、热榜、搜索和关注流信号筛选。";
}

function cardsForCategory(cards: WorthReadingCard[], categoryId: string, refreshState?: DemoState["categoryRefreshState"][string]) {
  const categoryCards = cards.filter((card) => card.categoryId === categoryId);
  const ordered = refreshState?.visibleCardIds?.length
    ? [...categoryCards].sort((a, b) => orderIndex(refreshState.visibleCardIds, a.id) - orderIndex(refreshState.visibleCardIds, b.id))
    : categoryCards;

  if (!refreshState?.refreshCount) return ordered;

  return ordered.map((card, index) => ({
    ...card,
    relevanceScore: Math.min(99, card.relevanceScore + refreshState.refreshCount + index),
    tags: [
      ...card.tags.filter((tag) => !tag.label.startsWith("刷新")),
      { label: `刷新 ${refreshState.refreshCount}`, tone: "green" as Tone },
    ],
  }));
}

function orderIndex(ids: string[], id: string) {
  const index = ids.indexOf(id);
  return index === -1 ? ids.length : index;
}

function rotateIds(ids: string[], step: number) {
  if (ids.length <= 1) return ids;
  const offset = step % ids.length;
  return [...ids.slice(offset), ...ids.slice(0, offset)];
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "刚刚";
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function scaleValues(index: number) {
  if (index === 4) return ["答", "中", "文", "专", "稿"];
  if (index === 5) return ["料", "2", "平", "4", "判"];
  if (index === 7) return ["直", "2", "中", "4", "事"];
  if (index === 8) return ["克", "2", "中", "4", "传"];
  if (index === 10) return ["冷", "2", "中", "4", "情"];
  if (index === 11) return ["纲", "段", "稿", "修", "发"];
  return ["1", "2", "3", "4", "5"];
}

function globalMemoryLabel(key: string) {
  const labels: Record<string, string> = {
    longTermBackground: "长期背景",
    contentPreference: "内容偏好",
    writingStyle: "写作风格",
    recommendationStrategy: "推荐策略",
    riskReminder: "写作风险提醒",
  };
  return labels[key] ?? key;
}

function toneLabel(tone: "balanced" | "sharp" | "steady") {
  if (tone === "sharp") return "更有锋芒";
  if (tone === "steady") return "更稳健克制";
  return "平衡但有立场";
}

function buildWritingBlueprint(seed: IdeaSeed, memory: MemorySummary) {
  const adoptedMaterials = seed.wateringMaterials.filter((item) => item.adopted);
  const evidence = adoptedMaterials.filter((item) => item.type === "evidence");
  const counter = adoptedMaterials.filter((item) => item.type === "counterargument");
  const personal = adoptedMaterials.filter((item) => item.type === "personal_experience");
  const perspective = memory.preferredPerspective[0] ?? seed.interestName;
  const sourceTitle = seed.sourceTitle || seed.source;

  return [
    {
      title: `分论点一：先界定「${compactText(seed.coreClaim, 18)}」的讨论范围`,
      items: [
        `不要只复述「${compactText(sourceTitle, 20)}」，先说明它和${perspective}有关。`,
        seed.sourceSummary,
        `写作提醒：${memory.writingReminder}`,
      ],
    },
    {
      title: "分论点二：用已采纳材料证明它为什么成立",
      items: materialLines(evidence, ["至少引用一条原始来源或数据", "把材料转成自己的判断，而不是堆摘要"]),
    },
    {
      title: "分论点三：提前回应反方和边界条件",
      items: materialLines(counter, seed.counterArguments.slice(0, 2).length ? seed.counterArguments.slice(0, 2) : ["补充一条反方质疑", "说明观点成立的前提"]),
    },
    {
      title: "分论点四：补入个人经验，避免像模板稿",
      items: materialLines(personal, seed.requiredMaterials.filter((item) => item.includes("个人")).length ? seed.requiredMaterials.filter((item) => item.includes("个人")) : ["补一个真实经历、观察或踩坑"]),
    },
  ];
}

function materialLines(materials: WateringMaterial[], fallback: string[]) {
  const lines = materials.slice(0, 2).map((item) => `${item.title}：${compactText(item.content, 42)}`);
  return lines.length ? lines : fallback;
}

function compactText(text: string, maxLength: number) {
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function draftLead(seed: IdeaSeed, session: Pick<WritingSession, "coreClaim" | "tone">, memory: MemorySummary) {
  const perspective = memory.preferredPerspective[0] ?? seed.interestName;
  const counter = seed.counterArguments[0] ?? "这个判断是否过度概括";
  const personal = seed.wateringMaterials.find((item) => item.type === "personal_experience" && item.adopted);
  const experienceLine = personal ? `我会把“${compactText(personal.content, 36)}”作为文章里最具体的一段经验。` : "这篇还需要补一个真实经验，否则容易停留在资料复述。";

  return `讨论「${seed.sourceTitle}」时，我不想只停在热点本身，而是把它拉回到${perspective}这个具体场景里。我的核心判断是：${session.coreClaim} 这个判断需要同时回应“${counter}”这样的反方问题。${experienceLine}`;
}

function finalDraftText(seed: IdeaSeed, session: Pick<WritingSession, "coreClaim" | "tone">, memory?: MemorySummary) {
  const perspective = memory?.preferredPerspective[0] ?? seed.interestName;
  const counter = seed.counterArguments[0] ?? "相反意见";
  const evidenceCount = seed.wateringMaterials.filter((item) => item.type === "evidence" && item.adopted).length;
  const personal = seed.wateringMaterials.find((item) => item.type === "personal_experience" && item.adopted);

  return `很多人讨论「${seed.sourceTitle}」时，容易先站队。但我更想把问题拆回到${perspective}：${session.coreClaim} 这不是一句结论，而是一条需要证据支撑的判断。当前已有 ${evidenceCount} 条事实证据，仍要回应“${counter}”这样的反方质疑。${personal ? `我会补入自己的观察：${compactText(personal.content, 48)}` : "如果要发布，还需要补一个真实项目或阅读场景。"} 只有观点、反方和个人经验都成立，这篇文章才像作者自己的判断，而不是一篇顺滑的 AI 文。`;
}

function copyText(text: string, showToast: (message: string) => void) {
  navigator.clipboard
    ?.writeText(text)
    .then(() => showToast("已复制到剪贴板"))
    .catch(() => showToast("复制失败，请手动选择文本"));
}

function createId(prefix: string, seed: string) {
  const normalized = seed.replace(/[^a-z0-9-]/gi, "-").toLowerCase();
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  return `${prefix}-${normalized}-${suffix}`;
}

function now() {
  return new Date().toISOString();
}

function unique<T>(items: T[]) {
  return Array.from(new Set(items));
}

declare global {
  interface Window {
    __kanshanToastTimer: number | undefined;
  }
}
