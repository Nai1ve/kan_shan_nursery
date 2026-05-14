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
  LogOut,
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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addSeedQuestion,
  agentSupplementSeed,
  analyzeFeedback,
  applyMemoryUpdate,
  createFeedbackFromSession,
  createManualSeed,
  createSeedFromCard,
  enrichCard,
  fetchContent,
  fetchContentCards,
  fetchFeedbackArticles,
  fetchProfile,
  fetchProfileInterests,
  fetchSeeds,
  fetchSproutOpportunities,
  startSproutRun,
  supplementSproutOpportunity,
  switchSproutAngle,
  dismissSproutOpportunity,
  getLLMConfig,
  getLLMQuota,
  getMemoryUpdateRequests,
  KANSHAN_BACKEND_MODE,
  KANSHAN_LLM_NOTICE_EVENT,
  markSeedQuestion,
  mergeSeedsApi,
  refreshCategory,
  refreshFeedback,
  rejectMemoryUpdate,
  updateBasicProfile,
  updateInterests,
  updateLLMConfig,
  updateSeed,
  createWritingSessionBackend,
  confirmWritingClaimBackend,
  updateWritingSessionBackend,
  generateBlueprintBackend,
  confirmBlueprintBackend,
  patchBlueprintBackend,
  regenerateBlueprintBackend,
  generateOutlineBackend,
  confirmOutlineBackend,
  generateDraftBackend,
  startRoundtableBackend,
  roundtableAuthorMessageBackend,
  continueRoundtableBackend,
  adoptSuggestionBackend,
  finalizeWritingBackend,
  publishMockBackend,
  runLlmTaskBackend,
} from "@/lib/api-client";
import type {
  ContentSource,
  CurrentUser,
  DemoState,
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  MemorySummary,
  MemoryUpdateRequest,
  ProfileData,
  RoundtableState,
  RoundtableSuggestion,
  SeedQuestion,
  SeedReaction,
  SeedStatus,
  SproutOpportunity,
  TabId,
  Tone,
  WateringMaterial,
  WateringMaterialType,
  WorthReadingCard,
  WritingBlueprint,
  WritingDraft,
  WritingSession,
  ZhihuBindingViewModel,
} from "@/lib/types";
import { gatewayGetWritingSession } from "@/lib/gateway-client";
import { AuthEntry } from "./auth/AuthEntry";
import { getMe, getZhihuAuthorizeUrl, getZhihuBinding, logout } from "@/lib/auth/auth-client";

const STORAGE_KEY = "kanshan:nursery:demo-state:v2";

const tabs: { id: TabId; label: string; icon: ComponentType<{ size?: number }> }[] = [
  { id: "today", label: "今日看什么", icon: BookOpen },
  { id: "seeds", label: "我的种子库", icon: Leaf },
  { id: "sprout", label: "今日发芽", icon: Sprout },
  { id: "write", label: "写作苗圃", icon: PenLine },
  { id: "history", label: "历史反馈", icon: History },
  { id: "profile", label: "用户管理", icon: UserRound },
];

const heroMap: Record<TabId, [string, string]> = {
  onboarding: ["建立你的创作画像。", "通过兴趣小类和写作问卷，让系统知道你关心什么、怎么表达。"],
  today: ["看到好内容，形成好观点。", "每次阅读都能沉淀表态、疑问、来源和可写角度。"],
  seeds: ["收藏的不是内容，是下一篇文章的种子。", "每颗种子都有来源、疑问、浇水材料和成熟度。"],
  sprout: ["旧想法，遇到新热点，就会发芽。", "用今日热点、关注流和用户画像激活历史观点种子。"],
  write: ["一步一步，把观点养成文章。", "从观点确认到论证蓝图，再到圆桌审稿、定稿草案和反馈回流。"],
  history: ["历史反馈，不只是数据。", "读者反馈会反哺 Memory、种子库和下一篇文章。"],
  profile: ["用户管理", ""],
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

type ProfilePanelId = "llm" | "interests" | "memory" | "style";

const profilePanels: { id: ProfilePanelId; label: string }[] = [
  { id: "llm", label: "LLM 配置" },
  { id: "interests", label: "兴趣画像" },
  { id: "memory", label: "Memory 管理" },
  { id: "style", label: "写作风格" },
];

const profileInterestOptions = [
  { id: "shuma", name: "数码科技", desc: "设备、软件、AI、消费电子" },
  { id: "zhichang", name: "职场教育", desc: "职业成长、学习路径、技能提升" },
  { id: "chuangzuo", name: "创作表达", desc: "写作方法、内容策略、表达技巧" },
  { id: "shenghuo", name: "生活方式", desc: "日常生活、健康、兴趣爱好" },
  { id: "shehui", name: "社会人文", desc: "社会观察、人文思考、文化评论" },
  { id: "yule", name: "文娱体育", desc: "影视、音乐、游戏、运动" },
  { id: "caijing", name: "财经商业", desc: "投资、理财、商业分析" },
  { id: "jiankang", name: "健康医学", desc: "身心健康、医疗科普" },
  { id: "qiche", name: "汽车出行", desc: "新能源、驾驶、出行方式" },
  { id: "bendi", name: "本地城市", desc: "本地生活、城市观察、区域话题" },
  { id: "lishi", name: "历史考古", desc: "历史事件、文化遗迹、考古发现" },
  { id: "huanjing", name: "环境自然", desc: "环保、自然生态、户外探索" },
];

const materialMeta: Record<WateringMaterialType, { title: string; desc: string; tone: Tone }> = {
  evidence: { title: "事实证据", desc: "来源、数据、案例、摘要。", tone: "blue" },
  counterargument: { title: "反方质疑", desc: "反对意见、漏洞、需要回应的问题。", tone: "orange" },
  personal_experience: { title: "个人经验", desc: "项目经历、观察、踩坑。", tone: "green" },
  open_question: { title: "待解决问题", desc: "尚未回答的疑问，可继续问 Agent。", tone: "purple" },
};

const materialTypes: WateringMaterialType[] = ["evidence", "counterargument", "personal_experience", "open_question"];

const LLM_TASK_LABELS: Record<string, string> = {
  // kebab-case (backend config 转换后)
  "summarize-content": "内容摘要",
  "answer-seed-question": "疑问回答",
  "supplement-material": "补充素材",
  "sprout-opportunities": "发芽机会",
  "argument-blueprint": "论点蓝图",
  "generate-outline": "大纲生成",
  "draft": "写作草稿",
  "roundtable-review": "圆桌审稿",
  "feedback-summary": "反馈摘要",
  "profile-memory-synthesis": "画像记忆合成",
  "extract-controversies": "争议提取",
  "generate-writing-angles": "写作角度生成",
  // camelCase 兼容（旧 mock 数据）
  "profileSignalSummarize": "画像信号提炼",
  "profileMemorySynthesize": "画像记忆合成",
  "profileRiskReview": "画像风险审查",
  "summarizeContent": "内容摘要",
  "answerSeedQuestion": "疑问回答",
  "supplementMaterial": "补充素材",
  "argumentBlueprint": "论点蓝图",
  "roundtableReview": "圆桌审稿",
};

export function KanshanApp() {
  const [entered, setEntered] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("today");
  const [toast, setToast] = useState("");
  const [data, setData] = useState<DemoState | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("shuma");
  const [selectedSeedId, setSelectedSeedId] = useState("seed-ai-coding-moat");
  const [writingStep, setWritingStep] = useState(0);
  const [questionCard, setQuestionCard] = useState<WorthReadingCard | null>(null);
  const [newSeedOpen, setNewSeedOpen] = useState(false);
  const [wateringSeedId, setWateringSeedId] = useState<string | null>(null);
  const [mergeSeedId, setMergeSeedId] = useState<string | null>(null);
  const [commentArticle, setCommentArticle] = useState<FeedbackArticle | null>(null);
  const [sproutLoading, setSproutLoading] = useState(false);
  const [sproutActionLoading, setSproutActionLoading] = useState<Set<string>>(new Set());
  const [todayRefreshing, setTodayRefreshing] = useState(false);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [zhihuBinding, setZhihuBinding] = useState<ZhihuBindingViewModel | null>(null);
  const enrichingCardIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    function handleLlmNotice(event: Event) {
      const detail = (event as CustomEvent<{ message?: string }>).detail;
      if (detail?.message) {
        showToast(detail.message);
      }
    }
    window.addEventListener(KANSHAN_LLM_NOTICE_EVENT, handleLlmNotice);
    return () => window.removeEventListener(KANSHAN_LLM_NOTICE_EVENT, handleLlmNotice);
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadMockData() {
      const prefetchOptionalDemoData = KANSHAN_BACKEND_MODE !== "gateway";
      const [profile, content, seeds, sproutOpportunities, feedbackArticles] = await Promise.all([
        fetchProfile(),
        fetchContent(),
        fetchSeeds(),
        prefetchOptionalDemoData ? fetchSproutOpportunities() : Promise.resolve([] as SproutOpportunity[]),
        prefetchOptionalDemoData ? fetchFeedbackArticles() : Promise.resolve([] as FeedbackArticle[]),
      ]);

      // Fetch real user info and Zhihu binding status (sequential: need userId for binding)
      try {
        const me = await getMe();
        if (mounted && me.user) {
          setCurrentUser(me.user);
          const binding = await getZhihuBinding(me.user.userId);
          if (mounted) setZhihuBinding(binding);
        }
      } catch {
        // ignore — will show fallback values
      }

      if (!mounted) return;

      let selectedInterestIds: string[] = [];
      if (KANSHAN_BACKEND_MODE === "gateway") {
        try {
          const interestMemories = await fetchProfileInterests();
          selectedInterestIds = interestMemories.map((item) => item.interestId).filter(Boolean);
        } catch {
          selectedInterestIds = [];
        }
      }

      const normalizedIncoming = normalizeContentPayload(content);
      const baseInterestIds = selectedInterestIds.length
        ? selectedInterestIds
        : normalizedIncoming.categories.filter((category) => category.kind === "interest").map((category) => category.id);
      const targetCategoryIds = [...baseInterestIds, "following", "serendipity"];

      const filteredContent = filterContentByTargetCategoryIds(normalizedIncoming, targetCategoryIds);
      const normalizedContent = ensureTargetCategories(
        filteredContent,
        normalizedIncoming.categories,
        targetCategoryIds,
      );
      const initialState: DemoState = {
        hasEntered: false,
        activeTab: "today",
        selectedCategoryId: normalizedContent.categories.find((c) => c.kind === "interest")?.id ?? "shuma",
        selectedSeedId: "seed-ai-coding-moat",
        profile,
        categories: normalizedContent.categories,
        cards: normalizedContent.cards,
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
      showToast("数据加载失败，请检查后端服务");
    });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!data || activeTab !== "history" || KANSHAN_BACKEND_MODE !== "gateway") return;
    if (data.feedbackArticles.length > 0) return;
    let mounted = true;

    fetchFeedbackArticles()
      .then((feedbackArticles) => {
        if (!mounted) return;
        updateData((current) => ({ ...current, feedbackArticles }));
      })
      .catch((error) => {
        console.error("Load feedback articles failed", error);
        showToast("历史反馈加载失败，请检查反馈服务");
      });

    return () => {
      mounted = false;
    };
  }, [activeTab, data]);

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

  function persistSeed(seed: IdeaSeed) {
    if (KANSHAN_BACKEND_MODE !== "gateway") return;
    void (async () => {
      try {
        await updateSeed(seed.id, seed);
      } catch (err) {
        try {
          await createManualSeed(seed);
        } catch (createErr) {
          console.error("Persist seed failed", err, createErr);
          showToast("数据已记录，但同步到服务端失败");
        }
      }
    })();
  }

  function enterApp(mode: "onboarding" | "demo") {
    setEntered(true);
    const nextTab = mode === "onboarding" ? "onboarding" : "today";
    setActiveTab(nextTab);
    updateData((current) => ({
      ...current,
      hasEntered: true,
      activeTab: nextTab,
    }));
    showToast(mode === "onboarding" ? "进入首次画像采集" : "进入演示模式");
  }

  async function completeAuthEntry(profile?: ProfileData) {
    setEntered(true);
    setActiveTab("today");

    // Re-fetch content on login/onboarding so categories/cards
    // reflect the user's actual interests from the backend.
    let nextCategories = data?.categories;
    let nextCards = data?.cards;
    if (KANSHAN_BACKEND_MODE === "gateway") {
      try {
        const [content, interestMemories] = await Promise.all([
          fetchContent(),
          fetchProfileInterests(),
        ]);
        const normalizedIncoming = normalizeContentPayload(content);
        const selectedInterestIds = interestMemories.map((item) => item.interestId).filter(Boolean);
        const baseInterestIds = selectedInterestIds.length
          ? selectedInterestIds
          : normalizedIncoming.categories.filter((category) => category.kind === "interest").map((category) => category.id);
        const targetCategoryIds = [...baseInterestIds, "following", "serendipity"];
        const filteredContent = filterContentByTargetCategoryIds(normalizedIncoming, targetCategoryIds);
        const normalizedContent = ensureTargetCategories(
          filteredContent,
          normalizedIncoming.categories,
          targetCategoryIds,
        );
        nextCategories = normalizedContent.categories;
        nextCards = normalizedContent.cards;
      } catch {
        showToast("内容刷新失败，使用缓存数据");
      }
    }

    const fallbackCategory =
      nextCategories?.find((c) => c.kind === "interest")?.id ?? "shuma";

    updateData((current) => {
      const effectiveCategories = nextCategories ?? current.categories;
      const effectiveCards = nextCards ?? current.cards;
      // Validate selectedCategoryId against the new categories
      const validCategoryIds = new Set(effectiveCategories.map((c) => c.id));
      const nextSelectedCategory = validCategoryIds.has(current.selectedCategoryId)
        ? current.selectedCategoryId
        : fallbackCategory;
      if (nextSelectedCategory !== current.selectedCategoryId) {
        setSelectedCategory(nextSelectedCategory);
      }
      return {
        ...current,
        hasEntered: true,
        activeTab: "today",
        profile: profile ?? current.profile,
        categories: effectiveCategories,
        cards: effectiveCards,
        selectedCategoryId: nextSelectedCategory,
      };
    });
    showToast(profile ? "临时画像已生成，进入工作台" : "欢迎回来，进入工作台");
  }

  function goTab(tab: TabId) {
    setActiveTab(tab);
    updateData((current) => ({ ...current, activeTab: tab }));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function selectCategory(categoryId: string) {
    if (!data?.categories.some((category) => category.id === categoryId)) {
      showToast("该分类不在当前可见范围");
      return;
    }

    setSelectedCategory(categoryId);
    updateData((current) => ({ ...current, selectedCategoryId: categoryId }));

    if (KANSHAN_BACKEND_MODE !== "gateway") return;

    try {
      const cards = normalizeCards(await fetchContentCards(categoryId, { limit: 2 }));
      updateData((current) => {
        const otherCards = current.cards.filter((card) => card.categoryId !== categoryId);
        return {
          ...current,
          cards: [...otherCards, ...cards],
          categoryRefreshState: {
            ...current.categoryRefreshState,
            [categoryId]: {
              refreshCount: current.categoryRefreshState[categoryId]?.refreshCount ?? 0,
              refreshedAt: now(),
              visibleCardIds: cards.map((card) => card.id),
            },
          },
        };
      });
    } catch (err) {
      console.error("Load category cards failed", err);
      showToast("分类内容加载失败，暂时显示缓存");
    }
  }

  function selectSeed(seedId: string) {
    setSelectedSeedId(seedId);
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

  function recordReaction(
    card: WorthReadingCard,
    reaction: Extract<SeedReaction, "agree" | "disagree">,
    note: string,
  ) {
    const finalNote =
      note.trim() ||
      (reaction === "agree"
        ? "我认同这个方向，后续可以继续补证据。"
        : "我反对当前结论，需要整理反方理由。");
    const seedId = ensureSeedFromCard(card, reaction, finalNote);
    if (KANSHAN_BACKEND_MODE === "gateway") {
      void createSeedFromCard({ cardId: card.id, reaction, userNote: finalNote, card, seedId }).catch((err) => {
        console.error("Persist seed failed", err);
        showToast("种子已记录，但同步到服务端失败，请检查后端");
      });
    }
    showToast(reaction === "agree" ? "已记录认同，并沉淀到种子库" : "已记录反对，并加入反方材料");
  }

  function clearCardReaction(cardId: string) {
    if (!data) return;
    const seed = data.seeds.find((item) => item.createdFromCardId === cardId);
    let nextSeed: IdeaSeed | null = null;
    if (seed) {
      nextSeed = recalcSeed({ ...seed, userReaction: "supplement", updatedAt: now() });
    }
    updateData((current) => {
      const newReactions = { ...current.reactions };
      delete newReactions[cardId];
      const seeds = nextSeed
        ? current.seeds.map((item) => (item.id === nextSeed!.id ? nextSeed! : item))
        : current.seeds;
      return { ...current, seeds, reactions: newReactions };
    });
    if (nextSeed) persistSeed(nextSeed);
    showToast("已清除表态");
  }

  async function answerQuestion(card: WorthReadingCard, question: string) {
    if (!data) throw new Error("data not ready");
    const existing = data.seeds.find((seed) => seed.createdFromCardId === card.id);
    const seedId = existing?.id ?? createId("seed", card.id);

    // Ensure seed exists locally first
    if (!existing) {
      const newSeed = buildSeedFromCard(card, data.categories, "question", `用户提出疑问：${question}`, seedId);
      updateData((current) => ({
        ...current,
        seeds: [newSeed, ...current.seeds],
        reactions: { ...current.reactions, [card.id]: "question" as SeedReaction },
      }));
    }
    setSelectedSeedId(seedId);

    // Call backend API to get real Agent answer
    try {
      if (KANSHAN_BACKEND_MODE === "gateway") {
        // First ensure seed exists on backend
        if (!existing) {
          await createSeedFromCard({ cardId: card.id, reaction: "question", userNote: `用户提出疑问：${question}`, card, seedId });
        }

        // Call addSeedQuestion to get Agent answer from backend
        const updatedSeed = await addSeedQuestion(seedId, { question });
        if (updatedSeed) {
          // Extract the latest question record from the updated seed
          const latestQuestion = updatedSeed.questions[0]; // questions are prepended, so first is latest
          if (latestQuestion) {
            // Update local state with backend response
            updateData((current) => ({
              ...current,
              seeds: current.seeds.map((seed) => (seed.id === seedId ? updatedSeed : seed)),
            }));
            persistSeed(updatedSeed);
            showToast("疑问已记录，Agent 回答已回写到浇水材料");
            return {
              seedId,
              questionId: latestQuestion.id,
              question: latestQuestion.question,
              agentAnswer: latestQuestion.agentAnswer,
              citedSourceIds: latestQuestion.citedSourceIds || [],
            };
          }
        }
      }
    } catch (err) {
      console.error("Agent answer failed, falling back to local answer:", err);
      showToast("Agent 回答失败，使用本地回答");
    }

    // Fallback to local answer if backend fails or not in gateway mode
    const turnIndex = existing?.questions.length ?? 0;
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
    const baseSeed = existing
      ? data.seeds.find((seed) => seed.id === seedId)!
      : buildSeedFromCard(card, data.categories, "question", `用户提出疑问：${question}`, seedId);
    const nextSeed = recalcSeed({
      ...baseSeed,
      questions: [questionRecord, ...baseSeed.questions],
      wateringMaterials: [
        buildMaterial("open_question", "用户疑问", question, "有疑问按钮", false),
        buildMaterial(answerMaterialType, turnIndex ? "Agent 继续追问回答" : "Agent 初步回答", answer, "Agent 问答", true),
        ...baseSeed.wateringMaterials,
      ],
      updatedAt: now(),
    });
    updateData((current) => {
      const seeds = current.seeds.map((seed) => (seed.id === seedId ? nextSeed : seed));
      return { ...current, seeds };
    });
    persistSeed(nextSeed);
    showToast("疑问已记录，Agent 回答已回写到浇水材料");
    return { seedId, questionId, question, agentAnswer: answer, citedSourceIds: card.originalSources.map((source) => source.sourceId) };
  }

  async function markQuestion(seedId: string, questionId: string, status: SeedQuestion["status"]) {
    if (!data) return;
    const seed = data.seeds.find((item) => item.id === seedId);
    if (!seed) return;

    // Update local state first (optimistic UI)
    const targetQuestion = seed.questions.find((question) => question.id === questionId);
    const nextSeed = recalcSeed({
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
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((item) => (item.id === seedId ? nextSeed : item)),
    }));

    // Sync with backend
    try {
      if (KANSHAN_BACKEND_MODE === "gateway") {
        const updatedSeed = await markSeedQuestion(seedId, questionId, status);
        if (updatedSeed) {
          updateData((current) => ({
            ...current,
            seeds: current.seeds.map((item) => (item.id === seedId ? updatedSeed : item)),
          }));
          persistSeed(updatedSeed);
        }
      } else {
        persistSeed(nextSeed);
      }
    } catch (err) {
      console.error("Mark question failed:", err);
      persistSeed(nextSeed);
    }

    showToast(status === "resolved" ? "疑问已标记为已解决" : "疑问已标记为仍需补资料");
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
    persistSeed(newSeed);
    showToast("新种子已创建，进入待浇水状态");
  }

  function addMaterial(seedId: string, material: Omit<WateringMaterial, "id" | "createdAt">) {
    if (!data) return;
    const seed = data.seeds.find((item) => item.id === seedId);
    if (!seed) return;
    const newMaterial: WateringMaterial = { ...material, id: createId("material", material.type), createdAt: now() };
    const nextSeed = recalcSeed({
      ...seed,
      wateringMaterials: [newMaterial, ...seed.wateringMaterials],
      updatedAt: now(),
    });
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((item) => (item.id === seedId ? nextSeed : item)),
    }));
    persistSeed(nextSeed);
    showToast("材料已补充，成熟度已更新");
  }

  function updateMaterial(seedId: string, materialId: string, patch: Partial<WateringMaterial>) {
    if (!data) return;
    const seed = data.seeds.find((item) => item.id === seedId);
    if (!seed) return;
    const nextSeed = recalcSeed({
      ...seed,
      wateringMaterials: seed.wateringMaterials.map((item) => (item.id === materialId ? { ...item, ...patch } : item)),
      updatedAt: now(),
    });
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((item) => (item.id === seedId ? nextSeed : item)),
    }));
    persistSeed(nextSeed);
  }

  function deleteMaterial(seedId: string, materialId: string) {
    if (!data) return;
    const seed = data.seeds.find((item) => item.id === seedId);
    if (!seed) return;
    const nextSeed = recalcSeed({
      ...seed,
      wateringMaterials: seed.wateringMaterials.filter((item) => item.id !== materialId),
      updatedAt: now(),
    });
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((item) => (item.id === seedId ? nextSeed : item)),
    }));
    persistSeed(nextSeed);
    showToast("已删除材料，成熟度已更新");
  }

  async function resolveOpenQuestion(seedId: string, material: WateringMaterial) {
    const seed = data?.seeds.find((item) => item.id === seedId);
    if (!seed) return;

    // Call backend API to get Agent answer
    try {
      if (KANSHAN_BACKEND_MODE === 'gateway') {
        const updatedSeed = await addSeedQuestion(seedId, { question: material.content });
        if (updatedSeed) {
          // Update local state with backend response
          updateData((current) => ({
            ...current,
            seeds: current.seeds.map((item) => (item.id === seedId ? updatedSeed : item)),
          }));
          persistSeed(updatedSeed);
          showToast('Agent 已回答待解决问题，并写入事实证据');
          return;
        }
      }
    } catch (err) {
      console.error('Agent answer failed, falling back to local:', err);
      showToast('Agent 回答失败，使用本地回答');
    }

    // Fallback to local answer if backend fails or not in gateway mode
    const answer = `基于当前来源和反方材料，Agent 的初步回答是：${material.content} 需要拆成事实判断和价值判断两层。事实层先补来源证据，价值层保留你的工程经验和边界说明。`;
    const nextSeed = recalcSeed({
      ...seed,
      questions: [
        {
          id: createId('question', seedId),
          question: material.content,
          agentAnswer: answer,
          citedSourceIds: [],
          status: 'answered',
          createdAt: now(),
        },
        ...seed.questions,
      ],
      wateringMaterials: [
        { ...material, adopted: true },
        buildMaterial('evidence', 'Agent 回答待解决问题', answer, '继续浇水 / Agent 问答', true),
        ...seed.wateringMaterials.filter((currentMaterial) => currentMaterial.id !== material.id),
      ],
      updatedAt: now(),
    });
    updateData((current) => ({
      ...current,
      seeds: current.seeds.map((item) => (item.id === seedId ? nextSeed : item)),
    }));
    persistSeed(nextSeed);
    showToast('Agent 已回答待解决问题，并写入事实证据');
  }

  async function supplementMaterialWithAgent(seedId: string, type: Extract<WateringMaterialType, 'evidence' | 'counterargument'>) {
    const seed = data?.seeds.find((item) => item.id === seedId);
    if (!seed) return;

    // Call backend API to get Agent-generated material
    try {
      if (KANSHAN_BACKEND_MODE === 'gateway') {
        const updatedSeed = await agentSupplementSeed(seedId, { type });
        if (updatedSeed) {
          // Find the new material added by the Agent
          const existingMaterialIds = new Set(seed.wateringMaterials.map((m) => m.id));
          const newMaterials = updatedSeed.wateringMaterials.filter((m) => !existingMaterialIds.has(m.id));
          if (newMaterials.length > 0) {
            // Update local state with backend response
            updateData((current) => ({
              ...current,
              seeds: current.seeds.map((item) => (item.id === seedId ? updatedSeed : item)),
            }));
            persistSeed(updatedSeed);
            showToast(type === 'evidence' ? 'Agent 已补充事实证据' : 'Agent 已找到反方质疑');
            return;
          }
        }
      }
    } catch (err) {
      console.error('Agent supplement failed, falling back to local:', err);
      showToast('Agent 补充失败，使用本地回答');
    }

    // Fallback to local material if backend fails or not in gateway mode
    const material =
      type === 'evidence'
        ? {
            type,
            title: 'Agent 补充事实证据',
            content: `围绕"${seed.sourceTitle}"，Agent 建议补充一条可验证事实：先引用原始来源中的具体场景，再说明它如何支撑"${seed.coreClaim}"。`,
            sourceLabel: '继续浇水 / Agent 补证据',
            adopted: true,
          }
        : {
            type,
            title: 'Agent 找到反方质疑',
            content: `针对"${seed.coreClaim}"，反方可能会质疑：${seed.counterArguments[0] ?? '当前材料是否足够支持这个判断？'} 建议在文章中明确适用边界，并补充一个不成立的场景。`,
            sourceLabel: '继续浇水 / Agent 找反方',
            adopted: true,
          };
    addMaterial(seedId, material);
  }

  function mergeSeeds(targetId: string, sourceId: string) {
    if (!data) return;
    const target = data.seeds.find((seed) => seed.id === targetId);
    const source = data.seeds.find((seed) => seed.id === sourceId);
    if (!target || !source) return;
    const [merged] = ensureUniqueMaterialIds([
      recalcSeed({
        ...target,
        possibleAngles: unique([...target.possibleAngles, ...source.possibleAngles]),
        counterArguments: unique([...target.counterArguments, ...source.counterArguments]),
        requiredMaterials: unique([...target.requiredMaterials, ...source.requiredMaterials]),
        wateringMaterials: [...target.wateringMaterials, ...source.wateringMaterials],
        questions: [...target.questions, ...source.questions],
        userNote: `${target.userNote}\n合并补充：${source.userNote}`,
        updatedAt: now(),
      }),
    ]);
    updateData((current) => ({
      ...current,
      seeds: current.seeds.filter((seed) => seed.id !== sourceId).map((seed) => (seed.id === targetId ? merged : seed)),
    }));
    setMergeSeedId(null);
    if (KANSHAN_BACKEND_MODE === "gateway") {
      void mergeSeedsApi(targetId, sourceId).catch((err) => {
        console.error("Persist merge failed", err);
        showToast("合并已记录，但同步到服务端失败");
      });
    }
    showToast("相似种子已合并，材料和疑问已归并");
  }

  async function startSprout(seedId?: string) {
    if (!data) return;
    goTab("sprout");
    setSproutLoading(true);
    showToast("正在匹配种子 × 热点 × 画像...");
    try {
      const result = await startSproutRun({ forceRefresh: !!seedId });
      updateData((current) => ({
        ...current,
        sproutStarted: true,
        sproutOpportunities: mergeOpportunities(result.opportunities ?? [], current.sproutOpportunities),
      }));
      if (seedId) selectSeed(seedId);
      showToast(result.cacheHit ? "已加载上次发芽结果" : "已找到发芽机会");
    } catch (err) {
      console.error("startSprout failed", err);
      showToast("发芽请求失败，请稍后重试");
    } finally {
      setSproutLoading(false);
    }
  }

  function updateOpportunity(id: string, patch: Partial<SproutOpportunity>) {
    updateData((current) => ({
      ...current,
      sproutOpportunities: current.sproutOpportunities.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    }));
  }

  function setSproutActionBusy(id: string, busy: boolean) {
    setSproutActionLoading((prev) => {
      const next = new Set(prev);
      if (busy) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  async function supplementFromOpportunity(opportunity: SproutOpportunity) {
    setSproutActionBusy(opportunity.id, true);
    try {
      const result = await supplementSproutOpportunity(opportunity.id);
      if (result.seedMaterial) {
        addMaterial(opportunity.seedId, result.seedMaterial);
      }
      updateOpportunity(opportunity.id, {
        ...result.opportunity,
        tags: [...opportunity.tags, { label: "已补资料", tone: "green" as const }],
      });
      showToast("已补充资料到种子");
    } catch (err) {
      console.error("supplementOpportunity failed", err);
      showToast("补充资料失败，请稍后重试");
    } finally {
      setSproutActionBusy(opportunity.id, false);
    }
  }

  async function switchOpportunityAngle(opportunity: SproutOpportunity) {
    setSproutActionBusy(opportunity.id, true);
    try {
      const updated = await switchSproutAngle(opportunity.id);
      updateOpportunity(opportunity.id, {
        ...updated,
        tags: [...opportunity.tags, { label: "已换角度", tone: "purple" as const }],
      });
      showToast("已切换写作角度");
    } catch (err) {
      console.error("switchAngle failed", err);
      showToast("切换角度失败，请稍后重试");
    } finally {
      setSproutActionBusy(opportunity.id, false);
    }
  }

  function startWriting(seedId: string, seedOverride?: IdeaSeed) {
    const seed = seedOverride ?? data?.seeds.find((item) => item.id === seedId);
    if (!seed) return;
    const session = createWritingSession(seed, data?.profile);
    const seedUpdate = (current: DemoState) => ({
      ...current,
      writingSession: session,
      seeds: current.seeds.some((item) => item.id === seedId)
        ? current.seeds.map((item) => (item.id === seedId ? { ...item, status: "writing" as SeedStatus, updatedAt: now() } : item))
        : [{ ...seed, status: "writing" as SeedStatus, updatedAt: now() }, ...current.seeds],
    });
    selectSeed(seedId);
    setWritingStep(0);
    goTab("write");
    showToast("已进入写作苗圃，Memory 已按兴趣分类注入");

    if (KANSHAN_BACKEND_MODE === "gateway") {
      createWritingSessionBackend({
        seedId: seed.id,
        interestId: seed.interestId,
        articleType: session.articleType,
        coreClaim: session.coreClaim,
        tone: session.tone,
      }).then((backendSession) => {
        updateData((current) => ({
          ...seedUpdate(current),
          writingSession: { ...session, backendSessionId: backendSession.sessionId },
        }));
      }).catch((err) => {
        console.error("Backend session creation failed, using local session", err);
        updateData(seedUpdate);
      });
    } else {
      updateData(seedUpdate);
    }
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

  async function publishWriting() {
    const session = data?.writingSession;
    const seed = data?.seeds.find((item) => item.id === session?.seedId);
    if (!session || !seed) return;
    const articleId = createId("article", seed.id);

    let article: FeedbackArticle;

    if (KANSHAN_BACKEND_MODE === "gateway") {
      try {
        let backendArticle: FeedbackArticle;
        if (session.backendSessionId) {
          // Use backend writing publish/mock endpoint
          const result = await publishMockBackend(session.backendSessionId, {
            title: seed.possibleAngles[0] ?? seed.title,
          });
          const pa = result.publishedArticle as Record<string, unknown>;
          backendArticle = {
            id: (pa?.articleId as string) || articleId,
            title: (pa?.title as string) || (seed.possibleAngles[0] ?? seed.title),
            interestId: seed.interestId,
            linkedSeedId: seed.id,
            status: "tracking",
            statusTone: "blue",
            performanceSummary: "文章已发布，等待读者反馈。",
            commentInsights: [],
            memoryAction: "等待反馈分析",
            metrics: [],
          };
        } else {
          // Fallback: direct feedback creation
          backendArticle = await createFeedbackFromSession({
            writingSessionId: session.sessionId,
            seedId: seed.id,
            interestId: seed.interestId,
            title: seed.possibleAngles[0] ?? seed.title,
            coreClaim: seed.coreClaim,
            articleType: session.articleType,
            publishMode: "mock",
            publishedAt: new Date().toISOString(),
          });
        }
        article = {
          ...backendArticle,
          id: backendArticle.id || articleId,
          statusTone: backendArticle.statusTone || "blue",
          performanceSummary: backendArticle.performanceSummary || "文章已发布，等待读者反馈。",
          commentInsights: backendArticle.commentInsights || [],
          memoryAction: backendArticle.memoryAction || "等待反馈分析",
          metrics: backendArticle.metrics || [],
        };
        article = {
          ...backendArticle,
          // Ensure backward-compatible fields exist
          id: backendArticle.id || articleId,
          statusTone: backendArticle.statusTone || "blue",
          performanceSummary: backendArticle.performanceSummary || "文章已发布，等待读者反馈。",
          commentInsights: backendArticle.commentInsights || [],
          memoryAction: backendArticle.memoryAction || "等待反馈分析",
          metrics: backendArticle.metrics || [],
        };
      } catch (err) {
        console.error("Failed to create feedback article in backend:", err);
        // Fallback to client-side mock
        article = {
          id: articleId,
          title: seed.possibleAngles[0] ?? seed.title,
          interestId: seed.interestId,
          linkedSeedId: seed.id,
          status: "tracking",
          statusTone: "blue",
          performanceSummary: "文章已发布，等待读者反馈。",
          commentInsights: [],
          memoryAction: "等待反馈分析",
          metrics: [],
          publishMode: "mock",
          publishedAt: new Date().toISOString(),
        };
      }
    } else {
      // Mock mode: client-side only
      article = {
        id: articleId,
        title: seed.possibleAngles[0] ?? seed.title,
        interestId: seed.interestId,
        linkedSeedId: seed.id,
        status: "tracking",
        statusTone: "blue",
        performanceSummary: "刚发布，系统已进入 2-3 周反馈观察期。当前先记录首批评论和收藏趋势。",
        commentInsights: ["等待第一批评论进入。", "建议重点关注反方是否质疑证据不足。", "收藏率会影响下一轮选题判断。"],
        memoryAction: `把"${seed.interestName}：发布后需要观察反方质疑"写入 Memory 候选。`,
        metrics: [
          { label: "阅读完成率", value: 18 },
          { label: "收藏率", value: 7 },
          { label: "评论争议度", value: 12 },
        ],
      };
    }

    updateData((current) => ({
      ...current,
      writingSession: { ...session, draftStatus: "published", publishedArticleId: articleId },
      feedbackArticles: [article, ...current.feedbackArticles],
      seeds: current.seeds.map((item) => (item.id === seed.id ? { ...item, status: "published", maturityScore: 96, updatedAt: now() } : item)),
    }));
    goTab("history");
    showToast("已模拟发布，并进入历史反馈监控");
  }

  async function syncFeedback() {
    if (KANSHAN_BACKEND_MODE === "gateway") {
      // Refresh each article from backend
      const articles = data?.feedbackArticles || [];
      for (const article of articles) {
        try {
          await refreshFeedback(article.id);
        } catch (err) {
          console.error(`Failed to refresh article ${article.id}:`, err);
        }
      }
      // Re-fetch articles to get updated data
      try {
        const updatedArticles = await fetchFeedbackArticles();
        updateData((current) => ({ ...current, feedbackArticles: updatedArticles }));
      } catch (err) {
        console.error("Failed to re-fetch feedback articles:", err);
      }
      showToast("已同步最新互动数据");
    } else {
      // Mock mode: client-side simulation
      updateData((current) => ({
        ...current,
        feedbackArticles: current.feedbackArticles.map((article) => ({
          ...article,
          metrics: article.metrics.map((metric, index) => ({ ...metric, value: Math.min(96, metric.value + 3 + index) })),
        })),
      }));
      showToast("已同步最新互动数据");
    }
  }

  async function handleAnalyzeFeedback(articleId: string) {
    if (KANSHAN_BACKEND_MODE === "gateway") {
      try {
        const analysis = await analyzeFeedback(articleId);
        updateData((current) => ({
          ...current,
          feedbackArticles: current.feedbackArticles.map((a) =>
            a.id === articleId
              ? {
                  ...a,
                  latestAnalysis: analysis,
                  status: "analyzed",
                  performanceSummary: analysis.performanceSummary || a.performanceSummary,
                  commentInsights: [
                    ...analysis.positiveFeedback.slice(0, 2),
                    ...analysis.negativeFeedback.slice(0, 2),
                  ],
                  memoryAction: analysis.memoryUpdateCandidates?.[0]?.reason || a.memoryAction,
                }
              : a,
          ),
        }));
        showToast("反馈分析完成");
      } catch (err) {
        console.error("Failed to analyze feedback:", err);
        showToast("反馈分析失败，请稍后重试");
      }
    } else {
      showToast("Mock 模式下无需分析");
    }
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

  async function saveProfile(profile: ProfileData) {
    try {
      if (KANSHAN_BACKEND_MODE === "gateway") {
        const updated = await updateBasicProfile(profile);
        updateData((current) => ({ ...current, profile: updated }));
        showToast("个人画像已保存并同步到服务器");
      } else {
        updateData((current) => ({ ...current, profile }));
        showToast("个人画像已保存（本地 mock）");
      }
    } catch (err) {
      console.error("Save profile failed:", err);
      showToast("保存失败，请检查网络连接");
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // ignore errors, clear local state anyway
    }
    window.localStorage.removeItem(STORAGE_KEY);
    window.location.reload();
  }

  const selectedQueue = useMemo(() => {
    if (!data) return [];
    return cardsForCategory(data.cards, selectedCategory, data.categoryRefreshState[selectedCategory]);
  }, [data, selectedCategory]);

  const selectedCards = useMemo(() => selectedQueue.slice(0, 1), [selectedQueue]);
  const bufferedCount = Math.max(0, selectedQueue.length - selectedCards.length);
  const selectedCategoryRefresh = data?.categoryRefreshState[selectedCategory];

  const enrichCardInBackground = useCallback((cardId: string) => {
    if (enrichingCardIdsRef.current.has(cardId)) return;
    enrichingCardIdsRef.current.add(cardId);
    void enrichCard(cardId)
      .then((card) => {
        const normalized = normalizeCard(card);
        setData((current) =>
          current
            ? {
                ...current,
                cards: current.cards.map((item) => (item.id === cardId ? { ...item, ...normalized, enriched: true } : item)),
              }
            : current,
        );
      })
      .catch((error) => {
        console.warn("background enrich failed", error);
      })
      .finally(() => {
        enrichingCardIdsRef.current.delete(cardId);
      });
  }, []);

  useEffect(() => {
    if (!data || activeTab !== "today" || KANSHAN_BACKEND_MODE !== "gateway") return;
    for (const card of selectedQueue.slice(0, 2)) {
      if (!card.enriched && card.categoryId !== "following") enrichCardInBackground(card.id);
    }
  }, [activeTab, data, enrichCardInBackground, selectedQueue]);

  async function refreshSelectedCategory() {
    if (!data) return;
    const queue = cardsForCategory(data.cards, selectedCategory, data.categoryRefreshState[selectedCategory]);
    const restQueue = queue.slice(1);
    const currentCategoryCards = data.cards.filter((card) => card.categoryId === selectedCategory);
    const excludeIds = Array.from(new Set(currentCategoryCards.map((card) => card.id)));
    const nextCount = (data.categoryRefreshState[selectedCategory]?.refreshCount ?? 0) + 1;
    const refreshedAt = now();

    if (restQueue.length) {
      updateData((state) => ({
        ...state,
        categoryRefreshState: {
          ...state.categoryRefreshState,
          [selectedCategory]: {
            refreshCount: nextCount,
            refreshedAt,
            visibleCardIds: restQueue.map((card) => card.id),
          },
        },
        expandedSourceIds: {},
        expandedCardIds: [],
      }));
      showToast("已换一条，后台继续预取真实内容");
    }

    if (KANSHAN_BACKEND_MODE === "gateway") {
      if (restQueue.length >= 2 || todayRefreshing) return;
      setTodayRefreshing(true);
      try {
        const refreshed = await refreshCategory(selectedCategory, { limit: 2, excludeIds });
        const incomingCards = normalizeCards(refreshed.cards);
        updateData((state) => {
          const otherCards = state.cards.filter((card) => card.categoryId !== selectedCategory);
          const existingCategoryCards = state.cards.filter((card) => card.categoryId === selectedCategory);
          const byId = new Map(existingCategoryCards.map((card) => [card.id, card]));
          for (const card of incomingCards) byId.set(card.id, card);
          const previousVisibleIds = state.categoryRefreshState[selectedCategory]?.visibleCardIds ?? restQueue.map((card) => card.id);
          const incomingIds = incomingCards.map((card) => card.id).filter((id) => !previousVisibleIds.includes(id));
          return {
            ...state,
            cards: [...otherCards, ...Array.from(byId.values())],
            categoryRefreshState: {
              ...state.categoryRefreshState,
              [selectedCategory]: refreshed.refreshState
                ? {
                    refreshCount: nextCount,
                    refreshedAt: refreshed.refreshState.refreshedAt,
                    visibleCardIds: [...previousVisibleIds, ...incomingIds],
                  }
                : {
                    refreshCount: nextCount,
                    refreshedAt,
                    visibleCardIds: [...previousVisibleIds, ...incomingIds],
                  },
            },
            expandedSourceIds: {},
            expandedCardIds: [],
          };
        });
        showToast(restQueue.length ? "新内容已预取" : `已补充${sectionTitle(data.categories, selectedCategory)}真实输入`);
      } catch (err) {
        console.error("Refresh category failed", err);
        if (!restQueue.length) showToast("补充真实输入失败，请稍后重试");
      } finally {
        setTodayRefreshing(false);
      }
      return;
    }

    const currentCards = data.cards.filter((card) => card.categoryId === selectedCategory);
    if (!currentCards.length) return;
    const current = data.categoryRefreshState[selectedCategory];
    const mockNextCount = (current?.refreshCount ?? 0) + 1;
    const mockRefreshedAt = now();
    const newCards: WorthReadingCard[] = currentCards.slice(0, 2).map((card, idx) => ({
      ...card,
      id: `${card.id}-r${mockNextCount}-${idx}`,
      relevanceScore: Math.min(99, (card.relevanceScore ?? 80) + mockNextCount),
      tags: [
        ...card.tags.filter((tag) => tag.label && !tag.label.startsWith("刷新")),
        { label: `刷新 ${mockNextCount}`, tone: "green" as Tone },
      ],
      createdAt: mockRefreshedAt,
    }));
    const newIds = newCards.map((card) => card.id);
    const prevIds = current?.visibleCardIds?.length
      ? current.visibleCardIds
      : currentCards.map((card) => card.id);
    updateData((state) => ({
      ...state,
      cards: [...newCards, ...state.cards],
      categoryRefreshState: {
        ...state.categoryRefreshState,
        [selectedCategory]: {
          refreshCount: mockNextCount,
          refreshedAt: mockRefreshedAt,
          visibleCardIds: [...newIds, ...prevIds],
        },
      },
      expandedSourceIds: {},
    }));
    showToast(`已为${sectionTitle(data.categories, selectedCategory)}追加新内容，旧卡片保留可比对`);
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
        <span>正在加载看山小苗圃真实内容...</span>
      </main>
    );
  }

  if (!entered) {
    return <AuthEntry onComplete={completeAuthEntry} onShowDemo={() => enterApp("demo")} />;
  }

  const activeHero = heroMap[activeTab];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/images/oauth/miao-240.png" alt="苗" className="brand-mark" />
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

        <div style={{ textAlign: "center", padding: "12px 0 8px", marginTop: "auto" }}>
          <img src="/images/sidebar-mascot.png" alt="看山小苗" style={{ width: "140px", height: "auto" }} />
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1 className="hero-title">{activeHero[0]}</h1>
            {activeHero[1] ? <p className="hero-desc">{activeHero[1]}</p> : null}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button className="user-pill" onClick={() => goTab("profile")} type="button">
              <img src="/images/roundtable/agent-human.png" alt="用户" className="avatar" style={{ objectFit: "cover" }} />
              <div>
                <div className="user-name">{data.profile.nickname}</div>
                <div className="user-mode">{data.profile.accountStatus}</div>
              </div>
            </button>
            <button className="btn ghost compact" onClick={handleLogout} type="button" title="退出登录">
              <LogOut size={16} />
            </button>
          </div>
        </header>

        {activeTab === "onboarding" ? <OnboardingSection profile={data.profile} onSave={saveProfile} goProfile={() => goTab("profile")} /> : null}
        {activeTab === "today" ? (
          <TodaySection
            categories={data.categories}
            cards={selectedCards}
            bufferedCount={bufferedCount}
            refreshing={todayRefreshing}
            reactions={data.reactions}
            expandedCardIds={data.expandedCardIds}
            expandedSourceIds={data.expandedSourceIds}
            refreshState={selectedCategoryRefresh}
            selectedCategory={selectedCategory}
            setSelectedCategory={selectCategory}
            onRefresh={refreshSelectedCategory}
            onToggleSource={toggleSource}
            onToggleSummary={async (cardId) => {
              // Check if card needs enrichment
              const card = data?.cards.find((c) => c.id === cardId);
              if (card && !card.enriched && !card.contentSummary) {
                try {
                  const enriched = await enrichCard(cardId);
                  const normalized = normalizeCard(enriched);
                  updateData((current) => ({
                    ...current,
                    cards: current.cards.map((c) => (c.id === cardId ? { ...c, ...normalized, enriched: true } : c)),
                  }));
                } catch (e) {
                  console.warn("enrich failed", e);
                }
              }
              updateData((current) => ({
                ...current,
                expandedCardIds: current.expandedCardIds.includes(cardId)
                  ? current.expandedCardIds.filter((id) => id !== cardId)
                  : [...current.expandedCardIds, cardId],
              }));
            }}
            onReact={recordReaction}
            onClearReaction={clearCardReaction}
            onQuestion={setQuestionCard}
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
            loading={sproutLoading}
            opportunities={data.sproutOpportunities}
            actionLoading={sproutActionLoading}
            onStart={() => startSprout()}
            openSeeds={() => goTab("seeds")}
            startWriting={startWriting}
            onSupplement={supplementFromOpportunity}
            onSwitchAngle={switchOpportunityAngle}
            onDismiss={async (id) => {
              try {
                await dismissSproutOpportunity(id);
                updateOpportunity(id, { status: "dismissed", tags: [{ label: "已暂缓", tone: "purple" }] });
                showToast("已标记为暂时不写");
              } catch (err) {
                console.error("dismissOpportunity failed", err);
                showToast("操作失败，请稍后重试");
              }
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
            analyzeFeedbackHandler={handleAnalyzeFeedback}
            generateSecondArticle={generateSecondArticle}
            openComments={setCommentArticle}
          />
        ) : null}
        {activeTab === "profile" ? (
          <ProfileSection profile={data.profile} categories={data.categories} onSave={saveProfile} onNotify={showToast} currentUser={currentUser} zhihuBinding={zhihuBinding} onZhihuBindingChange={setZhihuBinding} />
        ) : null}
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
        <img src="/images/oauth/miao-320.png" alt="苗" className="login-logo" />
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
  bufferedCount,
  refreshing,
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
  onClearReaction,
  onQuestion,
  onWrite,
}: {
  categories: InputCategory[];
  cards: WorthReadingCard[];
  bufferedCount: number;
  refreshing: boolean;
  reactions: Record<string, SeedReaction>;
  expandedCardIds: string[];
  expandedSourceIds: Record<string, string>;
  refreshState?: DemoState["categoryRefreshState"][string];
  selectedCategory: string;
  setSelectedCategory: (category: string) => void;
  onRefresh: () => void;
  onToggleSource: (cardId: string, sourceId: string) => void;
  onToggleSummary: (cardId: string) => void;
  onReact: (card: WorthReadingCard, reaction: Extract<SeedReaction, "agree" | "disagree">, note: string) => void;
  onClearReaction: (cardId: string) => void;
  onQuestion: (card: WorthReadingCard) => void;
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
          <button className="btn primary" disabled={refreshing} onClick={onRefresh} type="button">
            {refreshing ? <Loader2 className="spin" size={14} /> : <RefreshCw size={14} />}
            {cards.length ? "补充真实输入" : "加载内容"}
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
                <span className="tag blue">后台预取 {bufferedCount} 条</span>
              </div>
            </div>
            <div className="reading-controls">
              <div>
                <strong>单卡浏览</strong>
                <span>一次只看一张，避免信息流压力；换一条时优先使用已预取内容。</span>
              </div>
              <button className="btn primary" disabled={refreshing} onClick={onRefresh} type="button">
                {refreshing ? <Loader2 className="spin" size={14} /> : <RefreshCw size={14} />}
                换一条
              </button>
            </div>
            {cards.length ? null : (
              <div className="empty-state">
                {selectedCategory === "following"
                  ? "关注流需要完成知乎 OAuth 授权后才能获取真实动态。"
                  : "当前分类暂未获取到真实内容，请稍后刷新。"}
              </div>
            )}
            <div className="today-single-card">
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
                  onReact={(reaction, note) => onReact(card, reaction, note)}
                  onClearReaction={() => onClearReaction(card.id)}
                  onQuestion={() => onQuestion(card)}
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
  onClearReaction,
  onQuestion,
  onWrite,
}: {
  card: WorthReadingCard;
  featured: boolean;
  reaction?: SeedReaction;
  expanded: boolean;
  expandedSourceId: string;
  onToggleSource: (sourceId: string) => void;
  onToggleSummary: () => void;
  onReact: (reaction: Extract<SeedReaction, "agree" | "disagree">, note: string) => void;
  onClearReaction: () => void;
  onQuestion: () => void;
  onWrite: () => void;
}) {
  const cardExpanded = featured || expanded;
  const [pendingReaction, setPendingReaction] = useState<Extract<SeedReaction, "agree" | "disagree"> | null>(null);
  const [reactionNote, setReactionNote] = useState("");
  const hasReaction = reaction === "agree" || reaction === "disagree";

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
          <span className={`tag ${tag.tone}`} key={`${card.id}-${tag.label || 'unknown'}`}>
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
                  {source.meta.map((item, metaIndex) => (
                    <span key={`${source.sourceId}-meta-${metaIndex}`}>{item}</span>
                  ))}
                </div>
                <strong>{source.title}</strong>
                <p>要点：{compactSourceDigest(source)}</p>
                <span className="source-open-hint">点击展开完整来源</span>
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
      {!hasReaction && !pendingReaction ? (
        <div className="action-row">
          <button className="btn ghost" onClick={() => setPendingReaction("agree")} type="button">
            认同
          </button>
          <button className="btn ghost" onClick={() => setPendingReaction("disagree")} type="button">
            反对
          </button>
          <button className="btn ghost" onClick={onQuestion} type="button">
            疑问
          </button>
        </div>
      ) : pendingReaction ? (
        <div className="reaction-result">
          <div className="reaction-header">
            <span className={`tag ${pendingReaction === "agree" ? "green" : "orange"}`}>
              准备提交：{reactionLabel(pendingReaction)}
            </span>
          </div>
          <textarea
            className="textarea"
            placeholder="说说你的想法（可选）..."
            value={reactionNote}
            onChange={(e) => setReactionNote(e.target.value)}
            style={{ minHeight: 60, marginTop: 8, marginBottom: 8 }}
          />
          <div className="action-row">
            <button
              className="btn primary"
              onClick={() => {
                onReact(pendingReaction, reactionNote);
                setPendingReaction(null);
                setReactionNote("");
              }}
              type="button"
            >
              提交并加入种子库
            </button>
            <button
              className="btn ghost"
              onClick={() => {
                setPendingReaction(null);
                setReactionNote("");
              }}
              type="button"
            >
              取消
            </button>
          </div>
        </div>
      ) : (
        <div className="reaction-result">
          <div className="reaction-header">
            <span className={`tag ${reaction === "agree" ? "green" : "orange"}`}>
              已记录：{reactionLabel(reaction as SeedReaction)} · 已存入种子库
            </span>
            <button
              className="btn ghost compact"
              onClick={() => {
                setReactionNote("");
                onClearReaction();
              }}
              type="button"
              style={{ fontSize: 12, padding: "4px 10px" }}
            >
              清除表态
            </button>
          </div>
          <div className="action-row">
            <button className={`btn ghost ${expanded ? "selected" : ""}`} onClick={onToggleSummary} type="button">
              总结一下
            </button>
            <button className="btn ghost" onClick={onQuestion} type="button">
              有疑问
            </button>
            <button className="btn primary" onClick={onWrite} type="button">
              基于它写一篇
            </button>
          </div>
        </div>
      )}
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
  loading,
  opportunities,
  actionLoading,
  onStart,
  openSeeds,
  startWriting,
  onSupplement,
  onSwitchAngle,
  onDismiss,
}: {
  started: boolean;
  loading: boolean;
  opportunities: SproutOpportunity[];
  actionLoading: Set<string>;
  onStart: () => void;
  openSeeds: () => void;
  startWriting: (seedId: string) => void;
  onSupplement: (opportunity: SproutOpportunity) => void | Promise<void>;
  onSwitchAngle: (opportunity: SproutOpportunity) => void | Promise<void>;
  onDismiss: (id: string) => void | Promise<void>;
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
        {!started && !loading ? (
          <div className="panel-body">
            <div style={{ display: "flex", alignItems: "center", gap: "32px", flexWrap: "wrap" }}>
              <WateringAnimation />
              <div style={{ flex: 1, minWidth: "260px" }}>
                <article className="card structured-card no-hover">
                  <div className="tag-row">
                    <span className="tag green">小刘看山</span>
                    <span className="tag orange">用户主动触发</span>
                  </div>
                  <h3>今天要不要给你的种子浇浇水？</h3>
                  <p style={{ color: "var(--muted)", margin: "6px 0 14px", fontSize: "14px" }}>点击下方按钮，为观点种子注入新的活力。浇水会激活种子与今日热点的关联机会。</p>
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
            </div>
          </div>
        ) : loading ? (
          <div className="sprout-loading" style={{ display: "block" }}>
            <div className="spinner" />
            <p>正在匹配种子 × 热点 × 画像...</p>
          </div>
        ) : (
          <div className="panel-body grid-2">
            {visibleOpportunities.map((opportunity) => {
              const isBusy = actionLoading.has(opportunity.id);
              return (
                <article className="card structured-card sprout-card" key={opportunity.id}>
                  <div className="sprout-badge">{opportunity.score}</div>
                  <div className="tag-row">
                    {opportunity.tags.map((tag, index) => (
                      <span className={`tag ${tag.tone}`} key={`${opportunity.id}-${tag.label || 'unknown'}-${index}`}>
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
                  {opportunity.previousAngles && opportunity.previousAngles.length > 0 && (
                    <details className="sprout-previous-angles">
                      <summary>历史角度（{opportunity.previousAngles.length}）</summary>
                      {opportunity.previousAngles.map((prev, i) => (
                        <div key={i} className="sprout-prev-angle">
                          <strong>{prev.title}</strong>
                          <p>{prev.angle}</p>
                        </div>
                      ))}
                    </details>
                  )}
                  <div className="action-row">
                    <button className="btn primary" onClick={() => startWriting(opportunity.seedId)} type="button" disabled={isBusy}>
                      开始写作
                    </button>
                    <button className="btn ghost" onClick={() => onSupplement(opportunity)} type="button" disabled={isBusy}>
                      {isBusy ? <Loader2 className="spin" size={14} /> : null}
                      {isBusy ? "补充中..." : "补充资料"}
                    </button>
                    <button className="btn ghost" onClick={() => onSwitchAngle(opportunity)} type="button" disabled={isBusy}>
                      {isBusy ? <Loader2 className="spin" size={14} /> : null}
                      {isBusy ? "生成中..." : "换个角度"}
                    </button>
                    <button className="btn ghost" onClick={() => onDismiss(opportunity.id)} type="button" disabled={isBusy}>
                      暂时不写
                    </button>
                  </div>
                </article>
              );
            })}
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
  const effectiveMemory = currentSession.memoryOverride ?? memory;

  function updateSessionMemory(nextMemory: MemorySummary) {
    updateSession({ memoryOverride: nextMemory });
    if (session?.backendSessionId && KANSHAN_BACKEND_MODE === "gateway") {
      updateWritingSessionBackend(session.backendSessionId, { memoryOverride: nextMemory }).catch((err) => {
        console.error("Backend memory override update failed", err);
        showToast("本次写作 Memory 已在前端更新，后端同步失败");
      });
    }
  }

  const [showMemoryWriteBackDialog, setShowMemoryWriteBackDialog] = useState(false);
  const maxAllowedStep = getMaxAllowedWritingStep(currentSession);
  const nextStepAllowed = step < writingSteps.length - 1 && step + 1 <= maxAllowedStep;

  function goWritingStep(targetStep: number) {
    if (targetStep <= maxAllowedStep) {
      setStep(targetStep);
      return;
    }
    showToast(writingStepBlockedMessage(targetStep, currentSession));
  }

  useEffect(() => {
    if (step <= maxAllowedStep) return undefined;
    const timer = window.setTimeout(() => {
      setStep(maxAllowedStep);
      showToast(writingStepBlockedMessage(step, currentSession));
    }, 0);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, maxAllowedStep]);

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
                className={`step-item ${index === step ? "active" : ""} ${index < step ? "done" : ""} ${index > maxAllowedStep ? "disabled" : ""}`}
                key={item.title}
                onClick={() => goWritingStep(index)}
                type="button"
                disabled={index > maxAllowedStep}
                title={index > maxAllowedStep ? writingStepBlockedMessage(index, currentSession) : item.desc}
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
              memory={effectiveMemory}
              onChange={updateSessionMemory}
              onReset={() => {
                updateSessionMemory(baseMemory);
                showToast("已恢复画像默认 Memory 注入");
              }}
              onWriteBack={() => setShowMemoryWriteBackDialog(true)}
            />
            {showMemoryWriteBackDialog && (
              <ConfirmDialog
                title="写入 Memory"
                tagLabel="Memory"
                tagColor="purple"
                message={`确认将修改后的 Memory 写入「${effectiveMemory.interestName}」分类 Memory？写入后会影响后续所有写作和推荐。`}
                confirmLabel="确认写入"
                onConfirm={() => {
                  setShowMemoryWriteBackDialog(false);
                  showToast(`已写入 Memory：${effectiveMemory.interestName} 分类画像已更新`);
                }}
                onCancel={() => setShowMemoryWriteBackDialog(false)}
              />
            )}
            <WritingStageContent
              seed={seed}
              memory={effectiveMemory}
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
                disabled={step === writingSteps.length - 1 || !nextStepAllowed}
                onClick={() => goWritingStep(Math.min(writingSteps.length - 1, step + 1))}
                type="button"
                title={!nextStepAllowed && step < writingSteps.length - 1 ? writingStepBlockedMessage(step + 1, currentSession) : "进入下一步"}
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
  session: Pick<WritingSession, "articleType" | "coreClaim" | "tone" | "confirmed" | "adoptedSuggestions" | "draftStatus" | "savedDraft"> & { backendSessionId?: string; memoryOverride?: MemorySummary; blueprint?: WritingBlueprint; draft?: WritingDraft; roundtable?: RoundtableState };
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  updateSession: (patch: Partial<WritingSession>) => void;
  addMaterial: (material: Omit<WateringMaterial, "id" | "createdAt">) => void;
  publishWriting: () => void;
  showToast: (message: string) => void;
}) {
  // Backend state for blueprint and draft (hooks must be at top level)
  const [blueprintLoading, setBlueprintLoading] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [claimAdjusting, setClaimAdjusting] = useState(false);
  const [showExperienceInput, setShowExperienceInput] = useState(false);
  const [experienceText, setExperienceText] = useState("");
  const [blueprintEditMode, setBlueprintEditMode] = useState(false);
  const [blueprintEditText, setBlueprintEditText] = useState("");
  const [blueprintRegenerating, setBlueprintRegenerating] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [showClaimAdjustDialog, setShowClaimAdjustDialog] = useState(false);
  const [showBlueprintRegenDialog, setShowBlueprintRegenDialog] = useState(false);
  const backendBlueprint = session.blueprint;
  const backendDraft = session.draft;
  const backendBusy = blueprintLoading || draftLoading || claimAdjusting || blueprintRegenerating;

  async function adjustClaimWithBackend(instruction: string, tone?: "balanced" | "sharp" | "steady") {
    setClaimAdjusting(true);
    try {
      const result = await runLlmTaskBackend("answer-seed-question", {
        seed: { coreClaim: session.coreClaim, title: seed.title, wateringMaterials: seed.wateringMaterials },
        question: `请根据以下指令改写核心观点。要求：只输出改写后的核心观点本身；不要解释；不要复述原始观点；不要追加括号备注；不要输出列表。\n指令：${instruction}\n原始观点：${session.coreClaim}`,
      });
      const adjustedClaim = normalizeAdjustedClaim(result.answer, session.coreClaim, tone ?? session.tone);
      let replacementBackendSessionId: string | undefined;
      if (KANSHAN_BACKEND_MODE === "gateway") {
        const recreated = await createWritingSessionBackend({
          seedId: seed.id,
          interestId: seed.interestId,
          articleType: session.articleType,
          coreClaim: adjustedClaim,
          tone: tone ?? session.tone,
          memoryOverride: session.memoryOverride ?? memory,
        });
        replacementBackendSessionId = recreated.sessionId;
      }
      updateSession({
        ...(replacementBackendSessionId ? { backendSessionId: replacementBackendSessionId } : {}),
        coreClaim: adjustedClaim,
        tone: tone ?? session.tone,
        confirmed: false,
        draftStatus: "claim_confirming",
        blueprint: undefined,
        draft: undefined,
        roundtable: undefined,
      });
      showToast("已用 Agent 调整核心观点，请重新确认");
    } catch (err) {
      console.error("Claim adjustment failed", err);
      showToast("观点调整失败，请检查 LLM 服务或稍后重试");
    } finally {
      setClaimAdjusting(false);
    }
  }

  // Auto-generate blueprint from backend
  useEffect(() => {
    if (step === 3 && session.backendSessionId && KANSHAN_BACKEND_MODE === "gateway" && !backendBlueprint && !blueprintLoading) {
      let cancelled = false;
      const timer = window.setTimeout(() => {
        setBlueprintLoading(true);
        (async () => {
        try {
          // Step 1: Confirm claim (idempotent - ignore error if already confirmed or wrong state)
          await confirmWritingClaimBackend(session.backendSessionId!, {
            coreClaim: session.coreClaim,
            articleType: session.articleType,
            tone: session.tone,
          }).catch(() => {});
          // Step 2: Generate blueprint
          const result = await generateBlueprintBackend(session.backendSessionId!);
          updateSession({ blueprint: result.blueprint });
        } catch (genErr) {
          // Step 3: If generate fails (e.g. already generated), try fetching existing session
          try {
            const existing = await gatewayGetWritingSession(session.backendSessionId!);
            if (existing.blueprint) {
              updateSession({ blueprint: existing.blueprint });
            }
          } catch (fetchErr) {
            console.error("Blueprint generation and fetch both failed", genErr, fetchErr);
          }
        } finally {
          if (!cancelled) setBlueprintLoading(false);
        }
        })();
      }, 0);
      return () => {
        cancelled = true;
        window.clearTimeout(timer);
      };
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, session.backendSessionId, !!backendBlueprint]);

  // Draft is triggered manually via button, not auto-generated

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
              disabled={backendBusy}
              onClick={async () => {
                if (session.backendSessionId && KANSHAN_BACKEND_MODE === "gateway") {
                  try {
                    const nextSession = await confirmWritingClaimBackend(session.backendSessionId, {
                      coreClaim: session.coreClaim,
                      articleType: session.articleType,
                      tone: session.tone,
                    });
                    updateSession({ confirmed: nextSession.confirmed, draftStatus: nextSession.draftStatus });
                  } catch (err) {
                    console.error("Backend confirm claim failed", err);
                    showToast("确认观点失败，请稍后重试");
                    return;
                  }
                } else {
                  updateSession({ confirmed: true, draftStatus: "blueprint_ready" });
                }
                showToast("已确认核心观点");
              }}
              type="button"
            >
              {backendBusy ? "处理中..." : "确认"}
            </button>
            <button
              className="btn ghost"
              disabled={claimAdjusting}
              onClick={() => setShowClaimAdjustDialog(true)}
              type="button"
            >
              {claimAdjusting ? "调整中..." : "调整观点"}
            </button>
            <button
              className="btn ghost"
              disabled={claimAdjusting}
              onClick={async () => {
                await adjustClaimWithBackend("请将当前观点改写得更犀利、更有锋芒，但不要变成情绪化表达。", "sharp");
              }}
              type="button"
            >
              {claimAdjusting ? "调整中..." : "更犀利一点"}
            </button>
            <button
              className="btn ghost"
              disabled={claimAdjusting}
              onClick={async () => {
                await adjustClaimWithBackend("请将当前观点改写得更稳健、更谨慎，补足前提边界，但保留明确立场。", "steady");
              }}
              type="button"
            >
              {claimAdjusting ? "调整中..." : "更稳健一点"}
            </button>
            <button
              className="btn ghost"
              onClick={() => setShowExperienceInput(!showExperienceInput)}
              type="button"
            >
              {showExperienceInput ? "收起" : "补充个人经历"}
            </button>
          </div>
          {showExperienceInput && (
            <div style={{ marginTop: 12, padding: 12, background: "var(--surface-soft)", borderRadius: 8, border: "1px solid var(--line)" }}>
              <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, display: "block" }}>请写下你的个人经历或真实项目场景</label>
              <textarea
                className="textarea"
                style={{ minHeight: 80, fontSize: 13 }}
                placeholder="例如：去年参与的一个金融数据同步项目中，真正麻烦的不是写代码，而是需求边界不清、状态变化频繁、回滚追责困难..."
                value={experienceText}
                onChange={(e) => setExperienceText(e.target.value)}
              />
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <button
                  className="btn primary compact"
                  disabled={!experienceText.trim()}
                  onClick={() => {
                    addMaterial({
                      type: "personal_experience",
                      title: "个人经历",
                      content: experienceText.trim(),
                      sourceLabel: "用户补充",
                      adopted: true,
                    });
                    setExperienceText("");
                    setShowExperienceInput(false);
                    showToast("已添加个人经历材料");
                  }}
                  type="button"
                >
                  添加
                </button>
                <button className="btn ghost compact" onClick={() => { setShowExperienceInput(false); setExperienceText(""); }} type="button">
                  取消
                </button>
              </div>
            </div>
          )}
          {showClaimAdjustDialog && (
            <InstructionDialog
              title="用 AI 调整核心观点"
              tagLabel="调整观点"
              tagColor="blue"
              currentContext={session.coreClaim}
              placeholder="输入你想如何调整这个观点，例如：补充适用边界、加入反方前提..."
              confirmLabel="确认调整"
              presets={[
                { label: "补充适用边界", value: "请补充这个观点成立的适用边界和前提条件" },
                { label: "加入反方前提", value: "请加入反方可能的前提假设，使观点更严谨" },
                { label: "限定适用场景", value: "请限定这个观点的适用场景，避免过度概括" },
                { label: "增加量化条件", value: "请增加量化或可验证的条件" },
              ]}
              onClose={() => setShowClaimAdjustDialog(false)}
              onConfirm={async (instruction) => {
                setShowClaimAdjustDialog(false);
                await adjustClaimWithBackend(instruction);
              }}
            />
          )}
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
                updateSession({ articleType: id });
                if (session.backendSessionId && KANSHAN_BACKEND_MODE === "gateway") {
                  updateWritingSessionBackend(session.backendSessionId, { articleType: id }).catch((err) => {
                    console.error("Backend article type update failed", err);
                    showToast("文章类型已在前端更新，后端同步失败");
                  });
                }
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
    const clientBlueprint = buildWritingBlueprint(seed, memory);

    if (blueprintLoading) {
      return (
        <>
          <h2 className="stage-title">论证蓝图</h2>
          <p className="stage-desc">Agent 正在生成论证蓝图...</p>
          <div className="draft-box" style={{ textAlign: "center", padding: "48px" }}>
            <Loader2 className="spin" size={32} />
            <p style={{ marginTop: 12, color: "var(--muted)" }}>正在调用论证结构 Agent...</p>
          </div>
        </>
      );
    }

    // Use backend blueprint if available, fall back to client-side
    const blueprintItems = backendBlueprint
      ? [
          { title: "中心论点", items: [backendBlueprint.centralClaim, backendBlueprint.mainThread].filter(Boolean) },
          ...backendBlueprint.argumentSteps.map((s) => ({ title: s.title, items: s.keyPoints })),
          { title: "需要回应的反方", items: backendBlueprint.counterArguments },
          { title: "回应策略", items: [backendBlueprint.responseStrategy].filter(Boolean) },
        ]
      : clientBlueprint;

    const editableBlueprint = backendBlueprint ?? clientBlueprintToStructuredBlueprint(session.coreClaim, clientBlueprint);
    const blueprintText = formatBlueprintForEditing(editableBlueprint);

    return (
      <>
        <h2 className="stage-title">论证蓝图</h2>
        <p className="stage-desc">先把文章骨架搭好，再进入正文。{backendBlueprint ? "（由 Agent 生成）" : ""}</p>
        <div className="draft-box">
          <p>
            <strong>中心观点：</strong>
            <br />
            {session.coreClaim}
          </p>

          {blueprintEditMode ? (
            <div style={{ margin: "12px 0" }}>
              <textarea
                className="textarea"
                style={{ minHeight: 320, fontSize: 13, lineHeight: 1.7 }}
                value={blueprintEditText}
                onChange={(e) => setBlueprintEditText(e.target.value)}
              />
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <button
                  className="btn primary compact"
                  onClick={async () => {
                    try {
                      const parsed = parseBlueprintEditText(blueprintEditText, editableBlueprint);
                      if (session.backendSessionId && KANSHAN_BACKEND_MODE === "gateway") {
                        const result = await patchBlueprintBackend(session.backendSessionId, parsed);
                        updateSession({ blueprint: result.blueprint, draftStatus: result.session.draftStatus });
                      } else {
                        updateSession({ blueprint: parsed });
                      }
                      setBlueprintEditMode(false);
                      showToast("蓝图已保存");
                    } catch (err) {
                      console.error("Blueprint save failed", err);
                      showToast("蓝图保存失败，请检查文本格式");
                    }
                  }}
                  type="button"
                >
                  保存
                </button>
                <button className="btn ghost compact" onClick={() => setBlueprintEditMode(false)} type="button">
                  取消
                </button>
              </div>
            </div>
          ) : (
            <>
              {blueprintItems.map((item) => (
                <Blueprint items={item.items} key={item.title} title={item.title} />
              ))}
              <ListBlock title="需要回应的反方" items={seed.counterArguments} />
            </>
          )}

          <div className="action-row" style={{ marginTop: 16 }}>
            {!blueprintEditMode && (
              <button
                className="btn ghost"
                onClick={() => {
                  setBlueprintEditText(blueprintText);
                  setBlueprintEditMode(true);
                }}
                type="button"
              >
                编辑蓝图
              </button>
            )}
            <button
              className="btn ghost"
              disabled={blueprintRegenerating}
              onClick={() => {
                if (!session.backendSessionId || KANSHAN_BACKEND_MODE !== "gateway") {
                  showToast("重新生成仅在 gateway 模式下可用");
                  return;
                }
                setShowBlueprintRegenDialog(true);
              }}
              type="button"
            >
              {blueprintRegenerating ? "生成中..." : "重新生成"}
            </button>
            <button
              className="btn primary"
              onClick={async () => {
                if (session.backendSessionId && KANSHAN_BACKEND_MODE === "gateway") {
                  try {
                    showToast("正在确认蓝图并生成大纲...");
                    const confirmed = await confirmBlueprintBackend(session.backendSessionId);
                    const outlineResult = await generateOutlineBackend(session.backendSessionId);
                    const outlineConfirmed = await confirmOutlineBackend(session.backendSessionId);
                    updateSession({
                      confirmed: confirmed.confirmed ?? session.confirmed,
                      draftStatus: outlineConfirmed.draftStatus,
                      blueprint: outlineResult.session.blueprint ?? session.blueprint,
                    });
                    showToast("蓝图已确认，大纲已就绪，可进入初稿");
                  } catch (err) {
                    console.error("Backend blueprint confirm/outline failed", err);
                    showToast("确认蓝图失败，请检查后端服务后重试");
                  }
                } else {
                  updateSession({ draftStatus: "draft_ready" });
                  showToast("论证蓝图已确认，可进入初稿");
                }
              }}
              type="button"
            >
              确认蓝图
            </button>
          </div>
        </div>
        {showBlueprintRegenDialog && (
          <InstructionDialog
              title="重新生成论证蓝图"
              tagLabel="重新生成"
              tagColor="orange"
              description="可以指定调整方向，也可以直接重新生成。"
              placeholder="例如：加强反方回应、增加实战案例角度、调整论证顺序..."
              confirmLabel="重新生成"
              allowEmpty
              presets={[
                { label: "加强反方回应", value: "请加强反方观点的回应策略" },
                { label: "增加案例角度", value: "请增加实战案例和真实场景的角度" },
                { label: "调整论证顺序", value: "请调整论证的逻辑顺序，先讲案例再讲理论" },
                { label: "精简结构", value: "请精简蓝图结构，去掉不关键的部分" },
              ]}
              onClose={() => setShowBlueprintRegenDialog(false)}
              onConfirm={async (instruction) => {
                setShowBlueprintRegenDialog(false);
                if (!session.backendSessionId) return;
                setBlueprintRegenerating(true);
                try {
                  const result = await regenerateBlueprintBackend(session.backendSessionId, instruction || undefined);
                  updateSession({ blueprint: result.blueprint });
                  showToast("蓝图已重新生成");
                } catch (err) {
                  console.error("Blueprint regeneration failed", err);
                  showToast("重新生成失败");
                } finally {
                  setBlueprintRegenerating(false);
                }
              }}
            />
          )}
      </>
    );
  }

  if (step === 4) {

    if (draftLoading) {
      return (
        <>
          <h2 className="stage-title">生成表达初稿</h2>
          <p className="stage-desc">Agent 正在生成初稿...</p>
          <div className="draft-box" style={{ textAlign: "center", padding: "48px" }}>
            <Loader2 className="spin" size={32} />
            <p style={{ marginTop: 12, color: "var(--muted)" }}>正在调用草稿编辑 Agent...</p>
          </div>
        </>
      );
    }

    if (backendDraft) {
      return (
        <>
          <h2 className="stage-title">生成表达初稿</h2>
          <p className="stage-desc">由 Agent 生成的初稿，可编辑后进入圆桌审稿。</p>
          <div className="draft-box">
            <div className="tag-row">
              <span className="tag blue">Agent 生成</span>
              <span className="tag orange">请人工检查</span>
            </div>
            <h2>{backendDraft.title}</h2>
            <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.8, marginTop: 12 }}>{backendDraft.body}</div>
          </div>
        </>
      );
    }

    // No backend draft yet - show generate button or client-side fallback
    if (session.backendSessionId && KANSHAN_BACKEND_MODE === "gateway") {
      return (
        <>
          <h2 className="stage-title">生成表达初稿</h2>
          <p className="stage-desc">点击按钮调用 Agent 生成初稿，基于观点种子和浇水材料。</p>
          <div className="draft-box" style={{ textAlign: "center", padding: "48px" }}>
            <p style={{ marginBottom: 16, color: "var(--muted)" }}>蓝图已确认，大纲已就绪，可以生成初稿了。</p>
            <button
              className="btn primary"
              disabled={draftLoading}
              onClick={async () => {
                setDraftLoading(true);
                try {
                  await confirmBlueprintBackend(session.backendSessionId!).catch(() => undefined);
                  await generateOutlineBackend(session.backendSessionId!).catch(() => undefined);
                  await confirmOutlineBackend(session.backendSessionId!).catch(() => undefined);
                  const result = await generateDraftBackend(session.backendSessionId!);
                  updateSession({ draft: result.draft, draftStatus: result.session.draftStatus });
                  showToast("初稿已生成");
                } catch (err) {
                  console.error("Backend draft generation failed", err);
                  showToast("初稿生成失败");
                } finally {
                  setDraftLoading(false);
                }
              }}
              type="button"
            >
              生成初稿
            </button>
          </div>
        </>
      );
    }

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
        <p className="stage-desc">逻辑压测和人味检查合并为圆桌会议，由不同 Agent 从不同视角评判讨论。点击 Agent 头像可选择发言人。</p>
        <RoundtableDiscussion
          backendSessionId={session.backendSessionId}
          onSessionPatch={(patch) => updateSession(patch)}
          onComplete={(adopted) => {
            updateSession({ draftStatus: "finalized", adoptedSuggestions: adopted });
            setStep(6);
          }}
          showToast={showToast}
        />
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
            <button className={`btn primary ${session.draftStatus === "finalized" ? "selected" : ""}`} disabled={finalizing} onClick={async () => {
              if (session.draftStatus === "finalized" || session.draftStatus === "published") {
                showToast("定稿已确认");
                return;
              }
              if (session.backendSessionId && KANSHAN_BACKEND_MODE === "gateway") {
                setFinalizing(true);
                try {
                  const result = await finalizeWritingBackend(session.backendSessionId);
                  updateSession({ draftStatus: result.session.draftStatus });
                  showToast("已确认定稿");
                  return;
                } catch (err) {
                  console.error("Backend finalize failed", err);
                  showToast("确认定稿失败，请稍后重试");
                  return;
                } finally {
                  setFinalizing(false);
                }
              }
              updateSession({ draftStatus: "finalized" });
              showToast("已确认定稿");
            }} type="button">
              {finalizing ? "确认中..." : "确认定稿"}
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
  analyzeFeedbackHandler,
  generateSecondArticle,
  openComments,
}: {
  articles: FeedbackArticle[];
  syncFeedback: () => void;
  analyzeFeedbackHandler: (articleId: string) => void;
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
            <RefreshCw size={14} />
            同步反馈
          </button>
        </div>
        <div className="panel-body grid-1">
          {articles.map((article) => {
            const analysis = article.latestAnalysis;
            return (
              <article className="card history-card" key={article.id}>
                <div>
                  <div className="tag-row">
                    <span className="tag blue">{article.publishMode === "mock" ? "Demo 发布" : "已发布"}</span>
                    <span className={`tag ${article.statusTone}`}>{article.status === "analyzed" ? "已分析" : article.status === "tracking" ? "追踪中" : article.status}</span>
                    {article.latestMetrics?.metricSource === "mock" && <span className="tag orange">Demo 数据</span>}
                  </div>
                  <h3>{article.title}</h3>
                  <InfoBlock title="表现摘要" text={analysis?.performanceSummary || article.performanceSummary} />
                  {analysis ? (
                    <>
                      {analysis.positiveFeedback.length > 0 && <ListBlock title="读者认可点" items={analysis.positiveFeedback} />}
                      {analysis.negativeFeedback.length > 0 && <ListBlock title="主要质疑点" items={analysis.negativeFeedback} />}
                      {analysis.openQuestions.length > 0 && <ListBlock title="未解决问题" items={analysis.openQuestions} />}
                      {analysis.counterArguments.length > 0 && <ListBlock title="反方观点" items={analysis.counterArguments} />}
                      {analysis.secondArticleIdeas.length > 0 && (
                        <ListBlock
                          title="二次创作建议"
                          items={analysis.secondArticleIdeas.map((idea) => `${idea.title}：${idea.reason}`)}
                        />
                      )}
                    </>
                  ) : (
                    <>
                      <ListBlock ordered title="评论反馈提取" items={article.commentInsights} />
                      <InfoBlock title="反哺动作" text={article.memoryAction} />
                    </>
                  )}
                  <div className="action-row">
                    {!analysis && (
                      <button className="btn primary" onClick={() => analyzeFeedbackHandler(article.id)} type="button">
                        <Sparkles size={14} />
                        生成反馈分析
                      </button>
                    )}
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
                  {article.latestMetrics && (
                    <>
                      <div>
                        <div className="field-title">
                          点赞 {article.latestMetrics.likeCount}
                        </div>
                        <div className="mini-bar">
                          <span style={{ width: `${Math.min(100, article.latestMetrics.likeCount)}%` }} />
                        </div>
                      </div>
                      <div>
                        <div className="field-title">
                          评论 {article.latestMetrics.commentCount}
                        </div>
                        <div className="mini-bar">
                          <span style={{ width: `${Math.min(100, article.latestMetrics.commentCount * 3)}%` }} />
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function ProfileSection({
  profile,
  categories,
  onSave,
  onNotify,
  currentUser,
  zhihuBinding,
  onZhihuBindingChange,
}: {
  profile: ProfileData;
  categories: InputCategory[];
  onSave: (profile: ProfileData) => void;
  onNotify: (message: string) => void;
  currentUser?: CurrentUser | null;
  zhihuBinding?: ZhihuBindingViewModel | null;
  onZhihuBindingChange?: (binding: ZhihuBindingViewModel) => void;
}) {
  const [draft, setDraft] = useState(profile);
  const [activePanel, setActivePanel] = useState<ProfilePanelId>("llm");
  const [llmChoice, setLlmChoice] = useState<"platform_free" | "user_provider">("platform_free");
  const [llmDisplayName, setLlmDisplayName] = useState("");
  const [llmBaseUrl, setLlmBaseUrl] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [llmApiKey, setLlmApiKey] = useState("");
  const [llmQuota, setLlmQuota] = useState<Record<string, { used: number; limit: number; remaining: number }> | null>(null);
  const [memoryUpdateRequests, setMemoryUpdateRequests] = useState<MemoryUpdateRequest[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);

  // Listen for Zhihu binding success from popup window
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.data?.type === "zhihu-login-ticket" && event.origin === window.location.origin) {
        getZhihuBinding(currentUser?.userId).then((updated) => {
          if (onZhihuBindingChange) onZhihuBindingChange(updated);
          onNotify("知乎账号关联成功");
        }).catch(() => {});
      }
    }
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [currentUser?.userId, onZhihuBindingChange, onNotify]);
  const [styleScores, setStyleScores] = useState<Record<string, number>>({
    logic: 3,
    stance: 4,
    experience: 5,
    counter: 5,
  });

  const interestCategories = categories.filter((category) => category.kind === "interest");
  const zhihuBound = zhihuBinding?.bindingStatus === "bound";

  // Load memory update requests from API
  useEffect(() => {
    let mounted = true;

    async function loadMemoryUpdateRequests() {
      if (KANSHAN_BACKEND_MODE !== "gateway") return;

      setLoadingRequests(true);
      try {
        const requests = await getMemoryUpdateRequests();
        if (mounted) {
          setMemoryUpdateRequests(requests as unknown as MemoryUpdateRequest[]);
        }
      } catch (error) {
        console.error("Failed to load memory update requests:", error);
      } finally {
        if (mounted) {
          setLoadingRequests(false);
        }
      }
    }

    loadMemoryUpdateRequests();

    return () => {
      mounted = false;
    };
  }, [activePanel]);

  // Fetch LLM quota when LLM panel is active
  useEffect(() => {
    if (activePanel !== "llm") return;
    let mounted = true;
    async function loadLlmPanel() {
      try {
        const [config, quota] = await Promise.all([getLLMConfig(), getLLMQuota()]);
        if (!mounted) return;
        setLlmQuota(quota);
        if (config.activeProvider === "user_provider") {
          setLlmChoice("user_provider");
          setLlmDisplayName(String(config.displayName || ""));
          setLlmBaseUrl(String(config.baseUrl || ""));
          setLlmModel(String(config.model || ""));
        } else {
          setLlmChoice("platform_free");
        }
      } catch (err) {
        console.error("Failed to load LLM config:", err);
      }
    }
    loadLlmPanel();
    return () => {
      mounted = false;
    };
  }, []);

  function toggleInterest(interest: string) {
    const interests = draft.interests.includes(interest)
      ? draft.interests.filter((item) => item !== interest)
      : [...draft.interests, interest];
    setDraft({ ...draft, interests });
  }

  async function saveDraft(message = "用户管理信息已保存") {
    try {
      if (KANSHAN_BACKEND_MODE === "gateway") {
        const selectedInterestIds = interestCategories
          .filter((category) => draft.interests.includes(category.name))
          .map((category) => category.id);

        const updatedProfile = await updateInterests(
          selectedInterestIds.map((interestId) => ({
            interestId,
            selected: true,
            selfRatedLevel: "intermediate",
            intent: "both",
          })),
        );

        await updateBasicProfile({
          nickname: draft.nickname,
          role: draft.role,
          avoidances: draft.avoidances,
        });

        setDraft(updatedProfile);
        onSave(updatedProfile);
        onNotify(message + "（已同步到服务器）");
      } else {
        onSave(draft);
        onNotify(message + "（本地 mock）");
      }
    } catch (err) {
      console.error("Save draft failed:", err);
      onNotify("保存失败，请检查网络连接");
    }
  }

  function mockAction(message: string) {
    onNotify(message);
  }

  async function saveLlmConfig() {
    try {
      if (llmChoice === "user_provider") {
        if (!llmBaseUrl.trim() || !llmModel.trim() || !llmApiKey.trim()) {
          onNotify("请填写 Base URL、模型和 API Key 后再保存");
          return;
        }
        await updateLLMConfig({
          activeProvider: "user_provider",
          status: "user_configured",
          provider: "openai_compat",
          displayName: llmDisplayName || "自有 LLM",
          baseUrl: llmBaseUrl,
          model: llmModel,
          apiKey: llmApiKey,
        });
        setLlmApiKey("");
        onNotify("LLM 配置已保存，涉及个人写作的任务会优先使用你的模型");
        return;
      }
      await updateLLMConfig({ activeProvider: "platform_free", status: "platform_free" });
      onNotify("已切换为平台免费额度");
    } catch (error) {
      console.error("Failed to save LLM config:", error);
      onNotify("LLM 配置保存失败，请检查后端服务");
    }
  }

  async function applyMemoryRequest(requestId: string) {
    try {
      await applyMemoryUpdate(requestId);
      // Remove the applied request from the list
      setMemoryUpdateRequests((prev) => prev.filter((r) => r.id !== requestId));
      onNotify("Memory 更新请求已确认");
    } catch (error) {
      console.error("Failed to apply memory update request:", error);
      onNotify("确认失败，请重试");
    }
  }

  async function rejectMemoryRequest(requestId: string) {
    try {
      await rejectMemoryUpdate(requestId);
      // Remove the rejected request from the list
      setMemoryUpdateRequests((prev) => prev.filter((r) => r.id !== requestId));
      onNotify("Memory 更新请求已拒绝");
    } catch (error) {
      console.error("Failed to reject memory update request:", error);
      onNotify("拒绝失败，请重试");
    }
  }

  function setScore(key: string, value: number) {
    setStyleScores((current) => ({ ...current, [key]: value }));
    onNotify("写作风格问卷已更新到本地状态");
  }

  return (
    <section className="section active">
      <div className="profile-tabbar" role="tablist" aria-label="用户管理">
        {profilePanels.map((panel) => (
          <button
            className={`profile-tab ${activePanel === panel.id ? "active" : ""}`}
            key={panel.id}
            onClick={() => setActivePanel(panel.id)}
            type="button"
          >
            {panel.label}
          </button>
        ))}
      </div>

      {activePanel === "llm" ? (
        <section className="profile-panel-section active">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">LLM 配置</h2>
                <p className="panel-subtitle">系统使用一个 LLM 处理画像生成、摘要、问答和写作任务。</p>
              </div>
            </div>
            <div className="panel-body">
              <div className="llm-choice-grid">
                <button className={`llm-choice ${llmChoice === "platform_free" ? "selected" : ""}`} onClick={() => setLlmChoice("platform_free")} type="button">
                  <strong>平台免费额度</strong>
                  <span>零配置，适合试用。受每日额度限制。</span>
                </button>
                <button className={`llm-choice ${llmChoice === "user_provider" ? "selected" : ""}`} onClick={() => setLlmChoice("user_provider")} type="button">
                  <strong>配置自己的 LLM</strong>
                  <span>API Key 只提交给后端，前端不保存明文。</span>
                </button>
              </div>

              {llmChoice === "platform_free" ? (
                <div className="profile-spaced">
                  <div className="panel">
                    <div className="panel-header">
                      <div>
                        <h2 className="panel-title">每日额度使用情况</h2>
                        <p className="panel-subtitle">每日零点重置。命中缓存的任务不消耗额度。</p>
                      </div>
                    </div>
                    <div className="panel-body form-grid">
                      {llmQuota ? (
                        <div className="quota-board">
                          {Object.entries(llmQuota).map(([taskType, { used, limit, remaining }]) => (
                            <div className="quota-row" key={taskType}>
                              <span>{LLM_TASK_LABELS[taskType] || taskType}</span>
                              <strong>{used}/{limit}</strong>
                              <div className="quota-bar"><i style={{ width: `${limit > 0 ? (used / limit) * 100 : 0}%` }} /></div>
                              <span className="field-text">{remaining} 次剩余</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="card no-hover">
                          <p className="field-text">加载额度数据中...</p>
                        </div>
                      )}
                      <div className="action-row">
                        <button className="btn primary" onClick={saveLlmConfig} type="button">
                          使用平台免费额度
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {llmChoice === "user_provider" ? (
                <div className="profile-spaced">
                  <div className="panel">
                    <div className="panel-header">
                      <div>
                        <h2 className="panel-title">自有模型配置</h2>
                        <p className="panel-subtitle">API Key 只提交到服务端加密保存，前端不读明文。</p>
                      </div>
                    </div>
                    <div className="panel-body form-grid">
                      <div className="field">
                        <label>显示名称</label>
                        <input className="input" value={llmDisplayName} onChange={(e) => setLlmDisplayName(e.target.value)} placeholder="例如 DeepSeek V3 / GPT-4.1" />
                      </div>
                      <div className="field">
                        <label>模型</label>
                        <input className="input" value={llmModel} onChange={(e) => setLlmModel(e.target.value)} placeholder="例如 gpt-4o-mini" />
                      </div>
                      <div className="field">
                        <label>Base URL</label>
                        <input className="input" value={llmBaseUrl} onChange={(e) => setLlmBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" />
                      </div>
                      <div className="field">
                        <label>API Key</label>
                        <input className="input" type="password" value={llmApiKey} onChange={(e) => setLlmApiKey(e.target.value)} placeholder="只提交一次，服务端加密保存" />
                      </div>
                      <div className="action-row">
                        <button className="btn primary" onClick={() => onNotify("正在测试连接（mock）")} type="button">
                          测试连接
                        </button>
                        <button className="btn ghost" onClick={saveLlmConfig} type="button">
                          保存配置
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </section>
      ) : null}

      {activePanel === "interests" ? (
        <section className="profile-panel-section active">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">兴趣画像管理</h2>
                <p className="panel-subtitle">兴趣是长期 Memory 的主分类。关注流和偶遇输入是来源，不进入长期兴趣主类。</p>
              </div>
              <button className="btn primary" onClick={() => saveDraft("兴趣画像已保存")} type="button">
                保存兴趣
              </button>
            </div>
            <div className="panel-body">
              <div className="preference-section-head">
                <div>
                  <strong>选择长期兴趣 Memory 主分类</strong>
                  <span>关注流和偶遇输入是内容来源，不放入长期兴趣主分类。</span>
                </div>
                <em>{draft.interests.length} 个已选</em>
              </div>
              <div className="interest-grid onboarding-interest-grid">
                {profileInterestOptions.map((interest) => (
                  <div className={`interest-card-wrap ${draft.interests.includes(interest.name) ? "selected" : ""}`} key={interest.id}>
                    <button className="interest-card" onClick={() => toggleInterest(interest.name)} type="button">
                      <span className="interest-name">{interest.name}</span>
                      <span className="interest-desc">{interest.desc}</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="panel profile-spaced">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">按兴趣绑定的局部画像</h2>
                <p className="panel-subtitle">同一个用户在不同领域下需要不同视角、证据偏好和写作提醒。</p>
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
                    value={memory.writingReminder}
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
        </section>
      ) : null}

      {activePanel === "memory" ? (
        <section className="profile-panel-section active">
          <div className="profile-layout">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">全局 Memory</h2>
                  <p className="panel-subtitle">跨兴趣通用的用户背景、表达偏好和系统边界。</p>
                </div>
                <button className="btn primary" onClick={() => saveDraft("Memory 已保存")} type="button">
                  保存 Memory
                </button>
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

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Memory 更新请求</h2>
                  <p className="panel-subtitle">系统推断必须经过用户确认。</p>
                </div>
              </div>
              <div className="panel-body form-grid">
                {loadingRequests ? (
                  <div className="card no-hover">
                    <div className="field-text">加载中...</div>
                  </div>
                ) : memoryUpdateRequests.length === 0 ? (
                  <div className="card no-hover">
                    <div className="field-text">暂无待确认的 Memory 更新请求</div>
                  </div>
                ) : (
                  memoryUpdateRequests.map((request) => (
                    <div className="card no-hover" key={request.id}>
                      <div className="tag-row">
                        <span className={`tag ${request.scope === "global" ? "blue" : "green"}`}>
                          {request.scope === "global" ? "全局" : "兴趣"}
                        </span>
                        <span className="tag orange">待确认</span>
                      </div>
                      <h3>{request.targetField}</h3>
                      <p className="field-text">{request.reason}</p>
                      <div className="field-text" style={{ fontSize: "0.85em", marginTop: "4px" }}>
                        建议值: {typeof request.suggestedValue === "string" ? request.suggestedValue.substring(0, 100) : JSON.stringify(request.suggestedValue).substring(0, 100)}...
                      </div>
                      <div className="action-row">
                        <button className="btn primary" onClick={() => applyMemoryRequest(request.id)} type="button">
                          确认
                        </button>
                        <button className="btn ghost" onClick={() => mockAction("已进入编辑 Memory 更新请求")} type="button">
                          编辑
                        </button>
                        <button className="btn danger" onClick={() => rejectMemoryRequest(request.id)} type="button">
                          拒绝
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {activePanel === "style" ? (
        <section className="profile-panel-section active">
          <div className="grid-2">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">结构化写作风格</h2>
                  <p className="panel-subtitle">替代零散问卷结果，便于后端保存和 Prompt 注入。</p>
                </div>
                <button className="btn primary" onClick={() => saveDraft("写作风格已保存")} type="button">
                  保存
                </button>
              </div>
              <div className="panel-body form-grid">
                <div className="field">
                  <label>逻辑深度</label>
                  <select className="select" defaultValue="3 - 平衡" onChange={() => mockAction("逻辑深度已更新 mock")}>
                    <option>3 - 平衡</option>
                    <option>4 - 较强</option>
                    <option>5 - 非常强</option>
                  </select>
                </div>
                <div className="field">
                  <label>立场锋利度</label>
                  <select className="select" defaultValue="4 - 鲜明" onChange={() => mockAction("立场锋利度已更新 mock")}>
                    <option>2 - 克制</option>
                    <option>3 - 平衡</option>
                    <option>4 - 鲜明</option>
                  </select>
                </div>
                <div className="field">
                  <label>证据偏好</label>
                  <select className="select" defaultValue="个人经验 + 案例" onChange={() => mockAction("证据偏好已更新 mock")}>
                    <option>个人经验 + 案例</option>
                    <option>资料优先</option>
                    <option>判断优先</option>
                    <option>论文 / 数据优先</option>
                  </select>
                </div>
                <div className="field">
                  <label>AI 辅助边界</label>
                  <select className="select" defaultValue="草稿级，需要我修改后发布" onChange={() => mockAction("AI 辅助边界已更新 mock")}>
                    <option>草稿级，需要我修改后发布</option>
                    <option>只给大纲</option>
                    <option>只做润色</option>
                    <option>发布前检查</option>
                  </select>
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
                  <h2 className="panel-title">写作风格问答</h2>
                  <p className="panel-subtitle">保留问答式采集，用于补充结构化表单无法覆盖的偏好。</p>
                </div>
              </div>
              <div className="panel-body grid-2">
                {[
                  ["logic", "你希望文章逻辑严密到什么程度？"],
                  ["stance", "你愿意表达鲜明立场吗？"],
                  ["experience", "你喜欢加入个人经历吗？"],
                  ["counter", "是否需要主动反方质疑？"],
                ].map(([key, question]) => (
                  <div className="question-card" key={key}>
                    <h4>{question}</h4>
                    <div className="scale">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button className={styleScores[key] === value ? "selected" : ""} key={value} onClick={() => setScore(key, value)} type="button">
                          {value}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}
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
        <span className="tag green">真实来源</span>
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

function ConfirmDialog({
  title,
  message,
  tagLabel,
  tagColor,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  tagLabel?: string;
  tagColor?: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="overlay">
      <section className="modal">
        <div className="modal-header">
          <div>
            {tagLabel && <span className={`tag ${tagColor || "blue"}`}>{tagLabel}</span>}
            <h2>{title}</h2>
          </div>
          <button className="icon-btn" onClick={onCancel} type="button" aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body form-grid">
          <p style={{ color: "var(--text)", fontSize: 14, lineHeight: 1.6 }}>{message}</p>
          <div className="action-row">
            <button className="btn primary" onClick={onConfirm} type="button">
              {confirmLabel || "确认"}
            </button>
            <button className="btn ghost" onClick={onCancel} type="button">
              取消
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function InstructionDialog({
  title,
  tagLabel,
  tagColor,
  description,
  placeholder,
  presets,
  currentContext,
  confirmLabel,
  onClose,
  onConfirm,
  allowEmpty,
}: {
  title: string;
  tagLabel: string;
  tagColor?: string;
  description?: string;
  placeholder?: string;
  presets?: { label: string; value: string }[];
  currentContext?: string;
  confirmLabel?: string;
  onClose: () => void;
  onConfirm: (instruction: string) => void;
  allowEmpty?: boolean;
}) {
  const [instruction, setInstruction] = useState("");

  return (
    <div className="overlay">
      <section className="modal">
        <div className="modal-header">
          <div>
            <span className={`tag ${tagColor || "blue"}`}>{tagLabel}</span>
            <h2>{title}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} type="button" aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body form-grid">
          {currentContext && (
            <div className="check-item">
              <h4><span className="tag purple">当前内容</span></h4>
              <p>{currentContext}</p>
            </div>
          )}
          {description && <p style={{ color: "var(--muted)", fontSize: 13 }}>{description}</p>}
          <div className="field">
            <label>指令</label>
            <textarea
              className="textarea"
              style={{ minHeight: 80 }}
              placeholder={placeholder || "输入你的指令..."}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              autoFocus
            />
          </div>
          {presets && presets.length > 0 && (
            <div className="field">
              <label>快速选择</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {presets.map((p) => (
                  <button
                    key={p.label}
                    className="btn ghost compact"
                    onClick={() => setInstruction(p.value)}
                    type="button"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="action-row">
            <button className="btn primary" disabled={!allowEmpty && !instruction.trim()} onClick={() => onConfirm(instruction.trim())} type="button">
              {confirmLabel || "确认"}
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

function QuestionDialog({
  card,
  onClose,
  onAnswer,
  onMark,
}: {
  card: WorthReadingCard;
  onClose: () => void;
  onAnswer: (question: string) => Promise<{ seedId: string; questionId: string; question: string; agentAnswer: string; citedSourceIds: string[] }>;
  onMark: (seedId: string, questionId: string, status: SeedQuestion["status"]) => Promise<void>;
}) {
  const [question, setQuestion] = useState(`这个判断的反方证据是什么？`);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [answerThread, setAnswerThread] = useState<
    { seedId: string; questionId: string; question: string; agentAnswer: string; citedSourceIds: string[] }[]
  >([]);
  const [markedStatuses, setMarkedStatuses] = useState<Record<string, SeedQuestion["status"]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const latestAnswer = answerThread[answerThread.length - 1];
  const latestStatus = latestAnswer ? markedStatuses[latestAnswer.questionId] : "";
  const flowResolved = latestStatus === "resolved";

  async function submitQuestion() {
    const nextQuestion = latestAnswer ? followUpQuestion.trim() : question.trim();
    if (!nextQuestion || flowResolved || isLoading) return;
    setIsLoading(true);
    try {
      const nextAnswer = await onAnswer(nextQuestion);
      setAnswerThread((current) => [...current, nextAnswer]);
      setMarkedStatuses((current) => {
        const next = { ...current };
        delete next[nextAnswer.questionId];
        return next;
      });
      setFollowUpQuestion("");
    } finally {
      setIsLoading(false);
    }
  }

  async function markAnswer(
    answer: { seedId: string; questionId: string; question: string; agentAnswer: string; citedSourceIds: string[] },
    status: SeedQuestion['status'],
  ) {
    await onMark(answer.seedId, answer.questionId, status);
    setMarkedStatuses((current) => ({ ...current, [answer.questionId]: status }));
    if (status === 'needs_material') {
      setFollowUpQuestion(`请继续补充"${answer.question}"背后的事实证据、反方材料和可引用来源。`);
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
              disabled={isLoading || flowResolved || (latestAnswer ? !followUpQuestion.trim() : !question.trim())}
            >
              {isLoading ? <Loader2 size={14} className="spin" /> : <MessageCircleQuestion size={14} />}
              {isLoading ? "Agent 思考中..." : latestAnswer ? "继续追问并记录" : "让 Agent 回答并记录"}
            </button>
            <button className="btn ghost" onClick={onClose} type="button" disabled={isLoading}>
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
  const [interestId, setInterestId] = useState(interestCategories[0]?.id ?? "shuma");
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
  onResolve: (seedId: string, material: WateringMaterial) => Promise<void>;
  onAgentSupplement: (type: Extract<WateringMaterialType, "evidence" | "counterargument">) => Promise<void>;
}) {
  const [drafts, setDrafts] = useState<Record<WateringMaterialType, string>>({
    evidence: "",
    counterargument: "",
    personal_experience: "",
    open_question: "",
  });
  const [agentLoading, setAgentLoading] = useState<Extract<WateringMaterialType, "evidence" | "counterargument"> | null>(null);
  const [resolveLoading, setResolveLoading] = useState<string | null>(null);

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
                    <button
                      className="btn ghost compact"
                      onClick={async () => {
                        setAgentLoading(type);
                        try {
                          await onAgentSupplement(type);
                        } finally {
                          setAgentLoading(null);
                        }
                      }}
                      type="button"
                      disabled={agentLoading !== null}
                    >
                      {agentLoading === type ? (
                        <>
                          <Loader2 size={14} className="spin" /> Agent 思考中...
                        </>
                      ) : type === "evidence" ? (
                        "Agent 补证据"
                      ) : (
                        "Agent 找反方"
                      )}
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
  onResolve?: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(material.content);
  const [resolveLoading, setResolveLoading] = useState(false);

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
          <button
            className="btn ghost compact"
            onClick={async () => {
              setResolveLoading(true);
              try {
                await onResolve();
              } finally {
                setResolveLoading(false);
              }
            }}
            type="button"
            disabled={resolveLoading}
          >
            {resolveLoading ? (
              <>
                <Loader2 size={14} className="spin" /> Agent 思考中...
              </>
            ) : (
              '问 Agent'
            )}
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
  const analysis = article.latestAnalysis;
  return (
    <div className="overlay">
      <section className="modal">
        <div className="modal-header">
          <div>
            <span className="tag blue">{analysis ? "反馈分析" : "评论摘要"}</span>
            <h2>{article.title}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} type="button" aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          {analysis ? (
            <>
              <InfoBlock title="表现摘要" text={analysis.performanceSummary} />
              {analysis.positiveFeedback.length > 0 && <ListBlock title="读者认可点" items={analysis.positiveFeedback} />}
              {analysis.negativeFeedback.length > 0 && <ListBlock title="主要质疑点" items={analysis.negativeFeedback} />}
              {analysis.openQuestions.length > 0 && <ListBlock title="未解决问题" items={analysis.openQuestions} />}
              {analysis.counterArguments.length > 0 && <ListBlock title="反方观点" items={analysis.counterArguments} />}
              {analysis.missingMaterials.length > 0 && <ListBlock title="材料缺口" items={analysis.missingMaterials} />}
              {analysis.articlePortrait && (
                <>
                  <InfoBlock title="最强观点" text={analysis.articlePortrait.strongestPoint} />
                  <InfoBlock title="最弱环节" text={analysis.articlePortrait.weakestPoint} />
                  <InfoBlock title="读者类型" text={analysis.articlePortrait.readerProfile} />
                  <InfoBlock title="表达风格反馈" text={analysis.articlePortrait.styleFeedback} />
                  <InfoBlock title="下一篇优先改进点" text={analysis.articlePortrait.nextImprovement} />
                </>
              )}
              {analysis.secondArticleIdeas.length > 0 && (
                <ListBlock
                  title="二次创作建议"
                  items={analysis.secondArticleIdeas.map((idea) => `${idea.title}：${idea.reason}`)}
                />
              )}
              {analysis.seedCandidates.length > 0 && (
                <ListBlock
                  title="可转种子的评论"
                  items={analysis.seedCandidates.map((c) => `${c.title}：${c.reason}`)}
                />
              )}
              {analysis.memoryUpdateCandidates.length > 0 && (
                <ListBlock
                  title="Memory 更新建议"
                  items={analysis.memoryUpdateCandidates.map((c) => `${c.targetField}：${c.reason}`)}
                />
              )}
            </>
          ) : (
            <>
              <ListBlock ordered title="评论反馈提取" items={article.commentInsights} />
              <InfoBlock title="Memory 候选更新" text={article.memoryAction} />
            </>
          )}
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
  onWriteBack,
}: {
  baseMemory: MemorySummary;
  memory: MemorySummary;
  onChange: (memory: MemorySummary) => void;
  onReset: () => void;
  onWriteBack?: () => void;
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
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn ghost compact" onClick={onReset} type="button" disabled={JSON.stringify(baseMemory) === JSON.stringify(memory)}>
            恢复画像默认
          </button>
          {onWriteBack ? (
            <button className="btn primary compact" onClick={onWriteBack} type="button" disabled={JSON.stringify(baseMemory) === JSON.stringify(memory)}>
              写入 Memory
            </button>
          ) : null}
        </div>
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

function WateringAnimation() {
  const [currentFrame, setCurrentFrame] = useState(0);
  const [playing, setPlaying] = useState(true);
  const totalFrames = 4;

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      setCurrentFrame((prev) => (prev + 1) % totalFrames);
    }, 2500);
    return () => clearInterval(interval);
  }, [playing]);

  return (
    <div style={{ textAlign: "center", minWidth: "200px" }}>
      <div style={{ position: "relative", width: "200px", height: "160px", margin: "0 auto", borderRadius: "var(--radius-xl)", overflow: "hidden", boxShadow: "0 8px 24px rgba(22, 119, 255, 0.12)", background: "var(--surface-strong)" }}>
        {[1, 2, 3, 4].map((frame, i) => (
          <img
            key={frame}
            src="/images/watering/frame1.jpg"
            alt={`浇水 ${frame}`}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              position: "absolute",
              top: 0,
              left: 0,
              opacity: i === currentFrame ? 1 : 0,
              zIndex: i === currentFrame ? 2 : 1,
              transition: "opacity 1.5s ease-in-out",
            }}
          />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: "5px", marginTop: "10px" }}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} style={{ width: "6px", height: "6px", borderRadius: "50%", background: i === currentFrame ? "var(--primary)" : "var(--border)", transition: "background 0.3s" }} />
        ))}
      </div>
      <button className="btn compact" style={{ marginTop: "8px" }} onClick={() => setPlaying(!playing)} type="button">
        {playing ? "暂停" : "继续"}
      </button>
    </div>
  );
}

const ROUNDTABLE_ROLE_MAP: Record<string, { name: string; avatar: string }> = {
  logic_reviewer: { name: "逻辑审稿 Agent", avatar: "/images/roundtable/agent-logic_transparent.png" },
  human_editor: { name: "人味编辑 Agent", avatar: "/images/roundtable/agent-human_transparent.png" },
  opponent_reader: { name: "反方读者 Agent", avatar: "/images/roundtable/agent-devil_transparent.png" },
  community_editor: { name: "社区传播 Agent", avatar: "/images/roundtable/agent-spread_transparent.png" },
  author: { name: "主持人（你）", avatar: "/images/roundtable/host_transparent.png" },
  system: { name: "系统", avatar: "/images/roundtable/host_transparent.png" },
};

const ROUNDTABLE_BACKEND_ROLE_BY_UI: Record<string, string> = {
  logic: "logic_reviewer",
  human: "human_editor",
  devil: "opponent_reader",
  spread: "community_editor",
};

function collectRoundtableAdoptedSuggestions(state: RoundtableState | null | undefined, currentSuggestions: RoundtableSuggestion[] = []) {
  const adopted = [
    ...(state?.adoptedSuggestions ?? []),
    ...currentSuggestions.filter((item) => item.adopted).map((item) => item.content),
  ];
  return Array.from(new Set(adopted.map((item) => item.trim()).filter(Boolean)));
}

function RoundtableDiscussion({
  backendSessionId,
  onSessionPatch,
  onComplete,
  showToast,
}: {
  backendSessionId?: string;
  onSessionPatch?: (patch: Partial<WritingSession>) => void;
  onComplete: (adoptedSuggestions: string[]) => void;
  showToast: (msg: string) => void;
}) {
  const useBackend = !!backendSessionId && KANSHAN_BACKEND_MODE === "gateway";

  // Hardcoded fallback data
  const speakers = [
    { id: "logic", name: "逻辑审稿 Agent", avatar: "/images/roundtable/agent-logic_transparent.png", messages: ['我仔细审阅了这篇文章的论证逻辑。主要问题在于"能力同质化"到"工作流壁垒"之间的推导不够清晰。', "建议在第三段增加一个过渡论证：先说明为什么同质化会导致价格战，再引出工作流壁垒作为差异化竞争的必要条件。"] },
    { id: "human", name: "人味编辑 Agent", avatar: "/images/roundtable/agent-human_transparent.png", messages: ["从内容角度来说，这篇文章的技术分析很扎实，但缺少个人视角和真实案例。", '建议在开头或中间插入一个亲身经历的项目场景，比如"去年我参与的一个项目中，团队遇到了类似的问题..."'] },
    { id: "devil", name: "反方读者 Agent", avatar: "/images/roundtable/agent-devil_transparent.png", messages: ['我要提出一个关键质疑：文章认为"上下文是核心壁垒"，但未来长上下文模型可能会改变这个假设。', "如果 AI 能够一次性理解整个代码库，那么上下文管理的技术壁垒是否还成立？"] },
    { id: "spread", name: "社区传播 Agent", avatar: "/images/roundtable/agent-spread_transparent.png", messages: ['从传播角度来看，当前标题"AI Agent 的技术壁垒"比较平淡，建议改成更有冲击力的表达。', '开头建议从一个具体的工程场景切入，比如"上周我花了3天时间调试一个 Agent 的记忆系统..."'] },
  ];

  const [currentTurn, setCurrentTurn] = useState(-1);
  const [messageIndex, setMessageIndex] = useState<Record<string, number>>({});
  const [messages, setMessages] = useState<Array<{ speaker: string; avatar: string; text: string; isHost: boolean }>>([]);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [hostInput, setHostInput] = useState("");
  const [started, setStarted] = useState(false);
  const [backendState, setBackendState] = useState<RoundtableState | null>(null);
  const [backendFailed, setBackendFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<RoundtableSuggestion[]>([]);

  const effectiveUseBackend = useBackend && !backendFailed;
  const canInteractWithRoundtable = started && !loading;

  function addMessage(speaker: string, avatar: string, text: string, isHost = false) {
    setMessages((prev) => [...prev, { speaker, avatar, text, isHost }]);
  }

  // Map backend turns to display messages
  function syncBackendTurnsToMessages(state: RoundtableState) {
    const newMessages: Array<{ speaker: string; avatar: string; text: string; isHost: boolean }> = [];
    for (const turn of state.turns) {
      const role = ROUNDTABLE_ROLE_MAP[turn.role] || { name: turn.role, avatar: "/images/roundtable/host_transparent.png" };
      newMessages.push({
        speaker: role.name,
        avatar: role.avatar,
        text: turn.content,
        isHost: turn.role === "author",
      });
    }
    setMessages(newMessages);
    setSuggestions((state.suggestions || []).filter((item) => !item.adopted));
  }

  function patchFromBackend(result: { session: WritingSession; roundtable: RoundtableState }) {
    onSessionPatch?.({
      draftStatus: result.session.draftStatus,
      roundtable: result.roundtable,
      adoptedSuggestions: collectRoundtableAdoptedSuggestions(result.roundtable, result.roundtable.suggestions || []),
    });
  }

  // --- Backend handlers ---
  async function handleBackendStart() {
    if (!backendSessionId) {
      handleHardcodedStart();
      return;
    }
    setLoading(true);
    try {
      const result = await startRoundtableBackend(backendSessionId);
      setBackendState(result.roundtable);
      syncBackendTurnsToMessages(result.roundtable);
      patchFromBackend(result);
      setStarted(true);
      setSpeakingId(null);
    } catch (err) {
      console.error("Backend roundtable failed, falling back to hardcoded", err);
      setBackendFailed(true);
      handleHardcodedStart();
    } finally {
      setLoading(false);
    }
  }

  async function handleBackendContinue(role?: string) {
    if (!backendSessionId) return;
    setLoading(true);
    try {
      const result = await continueRoundtableBackend(backendSessionId, {
        role,
        conversation: messages,
      });
      setBackendState(result.roundtable);
      syncBackendTurnsToMessages(result.roundtable);
      patchFromBackend(result);
    } catch (err) {
      console.error("Backend roundtable continue failed", err);
      showToast("Agent 发言失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  async function handleBackendAgentSpeak(uiAgentId: string) {
    if (!started) {
      showToast("请先点击开始讨论");
      return;
    }
    if (loading) return;
    const role = ROUNDTABLE_BACKEND_ROLE_BY_UI[uiAgentId] ?? uiAgentId;
    setSpeakingId(uiAgentId);
    await handleBackendContinue(role);
  }

  async function handleBackendSendHost() {
    if (!hostInput.trim() || !backendSessionId) return;
    const content = hostInput.trim();
    setHostInput("");
    setLoading(true);
    try {
      const result = await roundtableAuthorMessageBackend(backendSessionId, content);
      setBackendState(result.roundtable);
      syncBackendTurnsToMessages(result.roundtable);
      patchFromBackend(result);
    } catch (err) {
      console.error("Backend roundtable message failed", err);
      // Still show the message locally
      addMessage("主持人", "/images/roundtable/host_transparent.png", content, true);
    } finally {
      setLoading(false);
    }
  }

  async function handleBackendAdopt(suggestionId: string) {
    if (!backendSessionId) return;
    try {
      const result = await adoptSuggestionBackend(backendSessionId, suggestionId);
      setBackendState(result.roundtable);
      setSuggestions((result.roundtable.suggestions || []).filter((item) => !item.adopted));
      patchFromBackend(result);
      showToast("已采纳建议");
    } catch (err) {
      console.error("Backend adopt suggestion failed", err);
    }
  }

  function handleBackendEnd() {
    const adopted = collectRoundtableAdoptedSuggestions(backendState, suggestions);
    addMessage("系统", "/images/roundtable/host_transparent.png", "讨论结束，进入定稿阶段。");
    setSpeakingId(null);
    onComplete(adopted);
    showToast("圆桌讨论完成，已进入定稿草案");
  }

  // --- Hardcoded fallback handlers ---
  function handleHardcodedStart() {
    setStarted(true);
    setCurrentTurn(0);
    addMessage("系统", "/images/roundtable/host_transparent.png", "圆桌审稿会开始，请各位 Agent 依次发表意见。");
    showNextMessage(0);
  }

  function showNextMessage(speakerIdx: number) {
    if (speakerIdx >= speakers.length) {
      addMessage("系统", "/images/roundtable/host_transparent.png", "所有 Agent 已发言完毕，主持人可以输入回应或结束讨论。");
      return;
    }
    const speaker = speakers[speakerIdx];
    const idx = messageIndex[speaker.id] || 0;
    if (idx < speaker.messages.length) {
      addMessage(speaker.name, speaker.avatar, speaker.messages[idx]);
      setSpeakingId(speaker.id);
      setMessageIndex((prev) => ({ ...prev, [speaker.id]: idx + 1 }));
    }
  }

  function handleNext() {
    const speaker = speakers[currentTurn];
    const idx = messageIndex[speaker.id] || 0;
    if (idx < speaker.messages.length) {
      showNextMessage(currentTurn);
    } else {
      const next = currentTurn + 1;
      setCurrentTurn(next);
      showNextMessage(next);
    }
  }

  function handleSelectAgent(agentId: string) {
    const idx = speakers.findIndex((s) => s.id === agentId);
    if (idx !== -1) {
      setCurrentTurn(idx);
      setSpeakingId(agentId);
      showNextMessage(idx);
    }
  }

  function handleSendHost() {
    if (!hostInput.trim()) return;
    addMessage("主持人", "/images/roundtable/host_transparent.png", hostInput.trim(), true);
    setSpeakingId("host");
    setHostInput("");
  }

  function handleEnd() {
    addMessage("系统", "/images/roundtable/host_transparent.png", "讨论结束，进入定稿阶段。");
    setSpeakingId(null);
    onComplete([]);
    showToast("圆桌讨论完成，已进入定稿草案");
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(300px, 1.2fr)", gap: "20px", minHeight: "500px" }}>
      <div style={{ background: "linear-gradient(180deg, var(--surface-soft) 0%, var(--surface-strong) 100%)", borderRadius: "var(--radius-xl)", padding: "20px", display: "flex", flexDirection: "column", alignItems: "center", gap: "20px", overflow: "hidden" }}>
        <div style={{ display: "flex", justifyContent: "center", alignItems: "flex-end", gap: "clamp(24px, 8vw, 80px)", width: "100%", flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", cursor: started ? "pointer" : "default", opacity: loading ? 0.72 : 1 }} onClick={() => started && !loading && setSpeakingId("host")}>
            <div style={{ position: "relative", width: "clamp(60px, 12vw, 100px)", height: "clamp(60px, 12vw, 100px)" }}>
              <img src="/images/roundtable/host_transparent.png" alt="主持人" style={{ width: "100%", height: "100%", objectFit: "contain", filter: speakingId === "host" ? "drop-shadow(0 6px 20px rgba(22, 119, 255, 0.4))" : "drop-shadow(0 4px 12px rgba(0,0,0,0.1))", transition: "filter 0.3s" }} />
              {speakingId === "host" && <span style={{ position: "absolute", top: "-6px", right: "-10px", fontSize: "16px" }}>💬</span>}
            </div>
            <span style={{ marginTop: "6px", padding: "4px 12px", background: "var(--primary)", color: "#fff", borderRadius: "999px", fontSize: "12px", fontWeight: 700 }}>主持人（你）</span>
          </div>
          <div
            style={{ display: "flex", flexDirection: "column", alignItems: "center", cursor: canInteractWithRoundtable ? "pointer" : "not-allowed", opacity: canInteractWithRoundtable ? 1 : 0.55 }}
            onClick={() => effectiveUseBackend ? handleBackendAgentSpeak("spread") : (canInteractWithRoundtable ? handleSelectAgent("spread") : showToast("请先点击开始讨论"))}
          >
            <div style={{ position: "relative", width: "clamp(50px, 10vw, 90px)", height: "clamp(50px, 10vw, 90px)" }}>
              <img src="/images/roundtable/agent-spread_transparent.png" alt="社区传播" style={{ width: "100%", height: "100%", objectFit: "contain", filter: speakingId === "spread" ? "drop-shadow(0 6px 20px rgba(22, 119, 255, 0.4))" : "drop-shadow(0 4px 12px rgba(0,0,0,0.1))", transition: "filter 0.3s" }} />
              {speakingId === "spread" && <span style={{ position: "absolute", top: "-6px", right: "-10px", fontSize: "16px" }}>💬</span>}
            </div>
            <span style={{ marginTop: "6px", padding: "4px 10px", background: "rgba(255,255,255,0.95)", borderRadius: "999px", fontSize: "11px", fontWeight: 700, boxShadow: "0 2px 6px rgba(0,0,0,0.06)" }}>社区传播</span>
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "center", alignItems: "flex-end", gap: "clamp(16px, 4vw, 32px)", width: "100%", flexWrap: "wrap" }}>
          {["logic", "human", "devil"].map((id) => {
            const agent = speakers.find((s) => s.id === id)!;
            const labels: Record<string, string> = { logic: "逻辑审稿", human: "人味编辑", devil: "反方读者" };
            return (
              <div
                key={id}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", cursor: canInteractWithRoundtable ? "pointer" : "not-allowed", opacity: canInteractWithRoundtable ? 1 : 0.55 }}
                onClick={() => effectiveUseBackend ? handleBackendAgentSpeak(id) : (canInteractWithRoundtable ? handleSelectAgent(id) : showToast("请先点击开始讨论"))}
              >
                <div style={{ position: "relative", width: "clamp(50px, 10vw, 90px)", height: "clamp(50px, 10vw, 90px)" }}>
                  <img src={agent.avatar} alt={labels[id]} style={{ width: "100%", height: "100%", objectFit: "contain", filter: speakingId === id ? "drop-shadow(0 6px 20px rgba(22, 119, 255, 0.4))" : "drop-shadow(0 4px 12px rgba(0,0,0,0.1))", transition: "filter 0.3s" }} />
                  {speakingId === id && <span style={{ position: "absolute", top: "-6px", right: "-10px", fontSize: "16px" }}>💬</span>}
                </div>
                <span style={{ marginTop: "6px", padding: "4px 10px", background: "rgba(255,255,255,0.95)", borderRadius: "999px", fontSize: "11px", fontWeight: 700, boxShadow: "0 2px 6px rgba(0,0,0,0.06)" }}>{labels[id]}</span>
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", background: "#fff", border: "1px solid var(--line)", borderRadius: "var(--radius-xl)", overflow: "hidden" }}>
        <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--line)", background: "var(--surface-soft)" }}>
          <strong style={{ fontSize: "16px" }}>讨论记录</strong>
          <p style={{ color: "var(--muted)", fontSize: "13px", marginTop: "2px" }}>{started ? "点击 Agent 头像选择发言人" : "点击「开始讨论」启动圆桌审稿"}</p>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "14px", display: "flex", flexDirection: "column", gap: "12px", maxHeight: "400px" }}>
          {messages.map((msg, i) => (
            <div key={i} style={{ display: "flex", gap: "10px", flexDirection: msg.isHost ? "row-reverse" : "row" }}>
              <div style={{ flex: "0 0 36px", height: "36px", borderRadius: "8px", overflow: "hidden", border: msg.isHost ? "2px solid var(--primary)" : "2px solid var(--line)", background: "var(--surface-soft)" }}>
                <img src={msg.avatar} alt={msg.speaker} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
              <div style={{ flex: 1, minWidth: 0, textAlign: msg.isHost ? "right" : "left" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--primary)", marginBottom: "2px" }}>{msg.speaker}</div>
                <div style={{ background: msg.isHost ? "var(--primary-soft)" : "var(--surface-soft)", padding: "10px 14px", borderRadius: msg.isHost ? "12px 0 12px 12px" : "0 12px 12px 12px", fontSize: "13px", lineHeight: 1.6, color: "var(--text)", wordBreak: "break-word" }}>{msg.text}</div>
              </div>
            </div>
          ))}
        </div>
        {/* Suggestions panel for backend roundtable */}
        {effectiveUseBackend && suggestions.length > 0 && (
          <div style={{ padding: "12px 14px", borderTop: "1px solid var(--line)", background: "#fffbf0", maxHeight: 200, overflowY: "auto" }}>
            <strong style={{ fontSize: "13px", marginBottom: 8, display: "block" }}>本轮 Agent 建议（点击采纳）</strong>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {suggestions.map((s) => (
                <div
                  key={s.id}
                  style={{
                    display: "flex", gap: 8, alignItems: "center", padding: "6px 10px",
                    background: s.adopted ? "var(--primary-soft)" : "#fff",
                    border: `1px solid ${s.adopted ? "var(--primary)" : "var(--line)"}`,
                    borderRadius: 6, cursor: s.adopted ? "default" : "pointer", fontSize: 12,
                  }}
                  onClick={() => !s.adopted && handleBackendAdopt(s.id)}
                >
                  <span className={`tag ${s.severity === "high" ? "orange" : s.severity === "medium" ? "blue" : "green"}`} style={{ fontSize: 10, padding: "2px 6px" }}>
                    {ROUNDTABLE_ROLE_MAP[s.fromRole]?.name?.replace(" Agent", "") || s.fromRole}
                  </span>
                  <span style={{ flex: 1 }}>{s.content}</span>
                  {s.adopted && <span className="tag green" style={{ fontSize: 10 }}>已采纳</span>}
                </div>
              ))}
            </div>
          </div>
        )}
        <div style={{ padding: "12px 14px", borderTop: "1px solid var(--line)", background: "var(--surface-soft)", display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
          {loading && <Loader2 className="spin" size={16} />}
          {!started ? (
            <button className="btn primary" onClick={effectiveUseBackend ? handleBackendStart : handleHardcodedStart} type="button" disabled={loading}>
              {loading ? "正在启动..." : "开始讨论"}
            </button>
          ) : (
            <>
              {effectiveUseBackend ? (
                <button className="btn ghost compact" type="button" disabled>
                  点击 Agent 头像发言
                </button>
              ) : (
                <button className="btn ghost compact" onClick={handleNext} type="button">下一位发言</button>
              )}
              <div style={{ flex: 1, display: "flex", gap: "6px", minWidth: "180px" }}>
                <input type="text" className="input" style={{ height: "34px", fontSize: "13px" }} value={hostInput} onChange={(e) => setHostInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && canInteractWithRoundtable && (effectiveUseBackend ? handleBackendSendHost() : handleSendHost())} placeholder="输入你的回应..." disabled={!canInteractWithRoundtable} />
                <button className="btn primary compact" onClick={effectiveUseBackend ? handleBackendSendHost : handleSendHost} type="button" disabled={!canInteractWithRoundtable}>发送</button>
              </div>
              <button className="btn primary compact" onClick={effectiveUseBackend ? handleBackendEnd : handleEnd} type="button" disabled={loading}>完成讨论</button>
</>
          )}
        </div>
      </div>
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

function deriveReactionsFromSeeds(seeds: IdeaSeed[]): Record<string, SeedReaction> {
  const reactions: Record<string, SeedReaction> = {};
  for (const seed of seeds) {
    if (seed.createdFromCardId && seed.userReaction) {
      reactions[seed.createdFromCardId] = seed.userReaction;
    }
  }
  return reactions;
}

function ensureTargetCategories(
  filteredContent: { categories: InputCategory[]; cards: WorthReadingCard[] },
  allCategories: InputCategory[],
  targetCategoryIds: string[],
): { categories: InputCategory[]; cards: WorthReadingCard[] } {
  const targetSet = new Set(targetCategoryIds.filter(Boolean));
  if (!targetSet.size) return filteredContent;

  const byId = new Map(allCategories.map((category) => [category.id, category]));
  const targetCategories = targetCategoryIds
    .map((id) => byId.get(id))
    .filter((category): category is InputCategory => Boolean(category));

  return { categories: targetCategories, cards: filteredContent.cards };
}

function normalizeContentPayload(
  content: { categories: InputCategory[]; cards: WorthReadingCard[] },
): { categories: InputCategory[]; cards: WorthReadingCard[] } {
  return {
    categories: content.categories,
    cards: normalizeCards(content.cards),
  };
}

function normalizeCards(cards: WorthReadingCard[]): WorthReadingCard[] {
  return cards.map(normalizeCard);
}

function normalizeCard(card: WorthReadingCard): WorthReadingCard {
  return {
    ...card,
    tags: (card.tags ?? []).map(normalizeTag),
    recommendationReason: card.recommendationReason || "来自知乎真实内容，适合继续阅读和沉淀观点。",
    contentSummary: card.contentSummary || card.originalSources?.[0]?.rawExcerpt || card.title,
    controversies: card.controversies?.length
      ? card.controversies
      : [`围绕"${card.title}"最需要先区分事实、判断和立场。`],
    writingAngles: card.writingAngles?.length
      ? card.writingAngles
      : [`我对"${card.title}"的核心判断`],
    originalSources: (card.originalSources ?? []).map((source) => ({
      ...source,
      meta: Array.isArray(source.meta) ? source.meta : [],
      rawExcerpt: source.rawExcerpt || source.fullContent || source.title,
      fullContent: source.fullContent || source.rawExcerpt || source.title,
      contribution: source.contribution || "提供真实来源内容",
    })),
  };
}

function normalizeTag(tag: { label: string; tone: Tone } | string): { label: string; tone: Tone } {
  if (typeof tag === "string") return { label: tag, tone: "blue" };
  return {
    label: tag.label || "真实来源",
    tone: tag.tone || "blue",
  };
}

function filterContentByTargetCategoryIds(
  content: { categories: InputCategory[]; cards: WorthReadingCard[] },
  targetCategoryIds: string[],
): { categories: InputCategory[]; cards: WorthReadingCard[] } {
  const targetSet = new Set(targetCategoryIds.filter(Boolean));
  if (!targetSet.size) return content;

  const categories = content.categories.filter((category) => targetSet.has(category.id));
  const allowedCategoryIds = new Set(categories.map((category) => category.id));
  const cards = content.cards.filter((card) => allowedCategoryIds.has(card.categoryId));

  return { categories, cards };
}

function readStoredState(initialState: DemoState): DemoState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialState;
    const stored = JSON.parse(raw) as Partial<DemoState>;
    // In gateway mode the backend is the source of truth for seeds and the
    // derived reactions map; keep only UI-level preferences from localStorage.
    const seeds = KANSHAN_BACKEND_MODE === "gateway"
      ? ensureUniqueMaterialIds(initialState.seeds)
      : ensureUniqueMaterialIds(stored.seeds?.length ? stored.seeds : initialState.seeds);
    const reactions = KANSHAN_BACKEND_MODE === "gateway"
      ? deriveReactionsFromSeeds(seeds)
      : (stored.reactions ?? {});
    // Validate selectedCategoryId: must exist in current categories
    const validCategoryIds = new Set(initialState.categories.map((c) => c.id));
    const restoredCategoryId = stored.selectedCategoryId ?? initialState.selectedCategoryId;
    const selectedCategoryId = validCategoryIds.has(restoredCategoryId)
      ? restoredCategoryId
      : (initialState.categories.find((c) => c.kind === "interest")?.id ?? initialState.selectedCategoryId);

    return {
      ...initialState,
      ...stored,
      hasEntered: stored.hasEntered ?? false,
      activeTab: stored.activeTab ?? initialState.activeTab,
      selectedCategoryId,
      selectedSeedId: stored.selectedSeedId ?? initialState.selectedSeedId,
      profile: stored.profile ?? initialState.profile,
      categories: initialState.categories,
      cards: initialState.cards,
      seeds,
      sproutOpportunities: stored.sproutOpportunities?.length ? stored.sproutOpportunities : initialState.sproutOpportunities,
      feedbackArticles: stored.feedbackArticles?.length ? stored.feedbackArticles : initialState.feedbackArticles,
      reactions,
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
    source: card.tags.map((tag) => tag.label || '').filter(Boolean).join(" / "),
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
    return `针对"${question}"，Agent 基于 ${sourceNames} 的初步判断是：这个问题不能直接下结论。正方材料支持"${card.writingAngles[0]}"，但仍需回应"${counter}"。建议把它沉淀为反方回应材料，并在写作前补一个真实案例。`;
  }
  if (turnIndex % 2 === 1) {
    return `第 ${turnIndex + 1} 轮继续求证：我会优先从"${evidence.sourceType}"补材料。当前可引用的方向是"${evidence.rawExcerpt}"。它能帮助回答"${question}"，但仍需要把来源中的具体场景和你的个人经验连接起来，否则文章容易停留在概念判断。`;
  }
  return `第 ${turnIndex + 1} 轮继续求证：围绕"${question}"，更值得补的是反方边界。可以把"${counter}"作为文章中必须回应的问题，再用"${evidence.contribution}"说明为什么你的主张不是绝对结论，而是有适用条件的判断。`;
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
    active: "可发芽",
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

function compactSourceDigest(source: ContentSource) {
  const text = source.rawExcerpt || source.contribution || source.fullContent || source.title;
  return text.length > 88 ? `${text.slice(0, 88)}...` : text;
}

function cardsForCategory(cards: WorthReadingCard[], categoryId: string, refreshState?: DemoState["categoryRefreshState"][string]) {
  const categoryCards = cards.filter((card) => card.categoryId === categoryId);
  if (!refreshState?.visibleCardIds?.length) return categoryCards;
  return [...categoryCards].sort(
    (a, b) => orderIndex(refreshState.visibleCardIds, a.id) - orderIndex(refreshState.visibleCardIds, b.id),
  );
}

function orderIndex(ids: string[], id: string) {
  const index = ids.indexOf(id);
  return index === -1 ? ids.length : index;
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

function getMaxAllowedWritingStep(session: Pick<WritingSession, "confirmed" | "draftStatus"> & { blueprint?: WritingBlueprint; draft?: WritingDraft }) {
  let maxStep = 1;
  if (session.confirmed || session.draftStatus !== "claim_confirming") maxStep = 2;
  if (session.confirmed) maxStep = Math.max(maxStep, 3);
  if (["outline_confirmed", "draft_ready", "reviewing", "finalized", "published"].includes(session.draftStatus)) {
    maxStep = Math.max(maxStep, 4);
  }
  if (session.draft || ["draft_ready", "reviewing", "finalized", "published"].includes(session.draftStatus)) {
    maxStep = Math.max(maxStep, 5);
  }
  if (["finalized", "published"].includes(session.draftStatus)) {
    maxStep = Math.max(maxStep, 6);
  }
  if (session.draftStatus === "published") {
    maxStep = Math.max(maxStep, 7);
  }
  return Math.min(maxStep, writingSteps.length - 1);
}

function writingStepBlockedMessage(step: number, session: Pick<WritingSession, "confirmed" | "draftStatus">) {
  if (step <= 1) return "可以进入当前步骤";
  if (!session.confirmed && step >= 2) return "请先在“确认核心观点”中确认你的核心观点";
  if (step >= 4 && !["outline_confirmed", "draft_ready", "reviewing", "finalized", "published"].includes(session.draftStatus)) {
    return "请先在“生成论证蓝图”中点击确认蓝图，完成大纲生成";
  }
  if (step >= 5 && !["draft_ready", "reviewing", "finalized", "published"].includes(session.draftStatus)) {
    return "请先生成表达初稿";
  }
  if (step >= 6 && !["finalized", "published"].includes(session.draftStatus)) {
    return "请先完成圆桌审稿会";
  }
  if (step >= 7 && session.draftStatus !== "published") {
    return "请先确认定稿";
  }
  return "请先完成前置步骤";
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

function clientBlueprintToStructuredBlueprint(
  coreClaim: string,
  items: Array<{ title: string; items: string[] }>,
): WritingBlueprint {
  const [first, ...rest] = items;
  return {
    centralClaim: coreClaim,
    mainThread: first?.items?.[0] ?? `围绕"${coreClaim}"展开论证。`,
    argumentSteps: rest.map((item, index) => ({
      id: `arg-client-${index + 1}`,
      title: item.title,
      purpose: "展开论证",
      keyPoints: item.items,
    })),
    counterArguments: [],
    responseStrategy: "先承认反方边界，再说明自己的判断适用范围。",
    personalExperienceNeeded: [],
    riskNotes: ["发布前需要人工检查事实、立场和 AI 辅助声明。"],
  };
}

function formatBlueprintForEditing(blueprint: WritingBlueprint): string {
  const lines = [
    `核心观点：${blueprint.centralClaim}`,
    `主线：${blueprint.mainThread}`,
    "",
    "论证步骤：",
  ];
  blueprint.argumentSteps.forEach((step, index) => {
    lines.push(`${index + 1}. ${step.title}`);
    lines.push(`目的：${step.purpose}`);
    step.keyPoints.forEach((point) => lines.push(`- ${point}`));
    lines.push("");
  });
  lines.push("反方质疑：");
  (blueprint.counterArguments.length ? blueprint.counterArguments : [""]).forEach((item) => {
    if (item) lines.push(`- ${item}`);
  });
  lines.push("", `回应策略：${blueprint.responseStrategy}`, "", "需要个人经验：");
  blueprint.personalExperienceNeeded.forEach((item) => lines.push(`- ${item}`));
  lines.push("", "风险提醒：");
  blueprint.riskNotes.forEach((item) => lines.push(`- ${item}`));
  return lines.join("\n");
}

function parseBlueprintEditText(text: string, fallback: WritingBlueprint): WritingBlueprint {
  const lines = text.split(/\r?\n/).map((line) => line.trim());
  const next: WritingBlueprint = {
    centralClaim: fallback.centralClaim,
    mainThread: fallback.mainThread,
    argumentSteps: [],
    counterArguments: [],
    responseStrategy: fallback.responseStrategy,
    personalExperienceNeeded: [],
    riskNotes: [],
  };
  let mode: "steps" | "counter" | "experience" | "risk" | null = null;
  let currentStep: WritingBlueprint["argumentSteps"][number] | null = null;

  function commitStep() {
    if (currentStep) {
      next.argumentSteps.push({
        ...currentStep,
        keyPoints: currentStep.keyPoints.length ? currentStep.keyPoints : ["补充这一节的关键论据"],
      });
      currentStep = null;
    }
  }

  for (const line of lines) {
    if (!line) continue;
    if (line.startsWith("核心观点：") || line.startsWith("核心观点:")) {
      next.centralClaim = line.replace(/^核心观点[：:]/, "").trim() || next.centralClaim;
      continue;
    }
    if (line.startsWith("主线：") || line.startsWith("主线:")) {
      next.mainThread = line.replace(/^主线[：:]/, "").trim() || next.mainThread;
      continue;
    }
    if (line === "论证步骤：") {
      commitStep();
      mode = "steps";
      continue;
    }
    if (line === "反方质疑：") {
      commitStep();
      mode = "counter";
      continue;
    }
    if (line.startsWith("回应策略：") || line.startsWith("回应策略:")) {
      commitStep();
      mode = null;
      next.responseStrategy = line.replace(/^回应策略[：:]/, "").trim() || next.responseStrategy;
      continue;
    }
    if (line === "需要个人经验：") {
      commitStep();
      mode = "experience";
      continue;
    }
    if (line === "风险提醒：") {
      commitStep();
      mode = "risk";
      continue;
    }
    const stepMatch = line.match(/^\d+[.、]\s*(.+)$/);
    if (mode === "steps" && stepMatch) {
      commitStep();
      currentStep = {
        id: createId("arg", stepMatch[1]),
        title: stepMatch[1].trim(),
        purpose: "展开论证",
        keyPoints: [],
      };
      continue;
    }
    if (mode === "steps" && currentStep && (line.startsWith("目的：") || line.startsWith("目的:"))) {
      currentStep.purpose = line.replace(/^目的[：:]/, "").trim() || currentStep.purpose;
      continue;
    }
    if (line.startsWith("- ")) {
      const value = line.slice(2).trim();
      if (!value) continue;
      if (mode === "steps" && currentStep) currentStep.keyPoints.push(value);
      if (mode === "counter") next.counterArguments.push(value);
      if (mode === "experience") next.personalExperienceNeeded.push(value);
      if (mode === "risk") next.riskNotes.push(value);
    }
  }
  commitStep();
  if (!next.argumentSteps.length) next.argumentSteps = fallback.argumentSteps;
  if (!next.counterArguments.length) next.counterArguments = fallback.counterArguments;
  if (!next.personalExperienceNeeded.length) next.personalExperienceNeeded = fallback.personalExperienceNeeded;
  if (!next.riskNotes.length) next.riskNotes = fallback.riskNotes;
  return next;
}

function materialLines(materials: WateringMaterial[], fallback: string[]) {
  const lines = materials.slice(0, 2).map((item) => `${item.title}：${compactText(item.content, 42)}`);
  return lines.length ? lines : fallback;
}

function compactText(text: string, maxLength: number) {
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function normalizeAdjustedClaim(rawAnswer: unknown, currentClaim: string, tone: WritingSession["tone"]) {
  const raw = String(rawAnswer ?? "").trim();
  const cleaned = raw
    .split(/\r?\n/)
    .map((line) => line.trim().replace(/^[-*•\d.、\s]+/, ""))
    .filter(Boolean)
    .find((line) => line.length > 0)
    ?.replace(/^(核心观点|改写后的观点|观点|答案|调整后)[：:]\s*/, "")
    .replace(/^["“”]+|["“”]+$/g, "")
    .trim();

  const looksLikeGenericAnswer =
    !cleaned ||
    cleaned.includes("请根据以下指令") ||
    cleaned.includes("原始观点") ||
    cleaned.includes("这个问题可以先拆成") ||
    cleaned.includes("当前回答是") ||
    cleaned.includes("需要补一条") ||
    cleaned.length > 180;

  if (!looksLikeGenericAnswer) return cleaned;
  if (tone === "sharp") {
    return `真正需要警惕的不是表面的争论，而是：${currentClaim}`;
  }
  if (tone === "steady") {
    return `在限定场景下，我倾向于认为：${currentClaim}`;
  }
  return currentClaim;
}

function draftLead(seed: IdeaSeed, session: Pick<WritingSession, "coreClaim" | "tone">, memory: MemorySummary) {
  const perspective = memory.preferredPerspective[0] ?? seed.interestName;
  const counter = seed.counterArguments[0] ?? "这个判断是否过度概括";
  const personal = seed.wateringMaterials.find((item) => item.type === "personal_experience" && item.adopted);
  const experienceLine = personal ? `我会把"${compactText(personal.content, 36)}"作为文章里最具体的一段经验。` : "这篇还需要补一个真实经验，否则容易停留在资料复述。";

  return `讨论「${seed.sourceTitle}」时，我不想只停在热点本身，而是把它拉回到${perspective}这个具体场景里。我的核心判断是：${session.coreClaim} 这个判断需要同时回应"${counter}"这样的反方问题。${experienceLine}`;
}

function finalDraftText(seed: IdeaSeed, session: Pick<WritingSession, "coreClaim" | "tone">, memory?: MemorySummary) {
  const perspective = memory?.preferredPerspective[0] ?? seed.interestName;
  const counter = seed.counterArguments[0] ?? "相反意见";
  const evidenceCount = seed.wateringMaterials.filter((item) => item.type === "evidence" && item.adopted).length;
  const personal = seed.wateringMaterials.find((item) => item.type === "personal_experience" && item.adopted);

  return `很多人讨论「${seed.sourceTitle}」时，容易先站队。但我更想把问题拆回到${perspective}：${session.coreClaim} 这不是一句结论，而是一条需要证据支撑的判断。当前已有 ${evidenceCount} 条事实证据，仍要回应"${counter}"这样的反方质疑。${personal ? `我会补入自己的观察：${compactText(personal.content, 48)}` : "如果要发布，还需要补一个真实项目或阅读场景。"} 只有观点、反方和个人经验都成立，这篇文章才像作者自己的判断，而不是一篇顺滑的 AI 文。`;
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
