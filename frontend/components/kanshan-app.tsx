"use client";

import {
  BookOpen,
  Check,
  ChevronRight,
  History,
  Home,
  Leaf,
  Loader2,
  PenLine,
  RefreshCw,
  Sprout,
  UserRound,
} from "lucide-react";
import type { ComponentType, Dispatch, SetStateAction } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  fetchContent,
  fetchFeedbackArticles,
  fetchProfile,
  fetchSeeds,
  fetchSproutOpportunities,
} from "@/lib/api-client";
import type {
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  ProfileData,
  SproutOpportunity,
  TabId,
  WorthReadingCard,
} from "@/lib/types";

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
  today: ["看到好内容，形成好观点。", ""],
  seeds: ["收藏的不是内容，是下一篇文章的种子。", "每一颗种子都包含来源、反应、核心观点、可写方向和补充材料。"],
  sprout: ["旧想法，遇到新热点，就会发芽。", "用今日热榜、搜索结果和关注流激活历史种子，捕捉稍纵即逝的表达时机。"],
  write: ["一步一步，把观点养成文章。", "从观点确认到论证蓝图，再到圆桌审稿、定稿草案和发布反馈。"],
  history: ["历史反馈，不只是数据。", "监控已发布文章，把读者反馈提炼成新种子、写作风险和用户 Memory。"],
  profile: ["你的画像，是系统理解你的方式。", "展示并编辑用户兴趣小类、创作背景、长期 Memory 和写作风格画像。"],
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

const writingAdvice = [
  ["主编建议", "这颗种子适合演示，因为它能串联“看什么、今日发芽、写作苗圃、圆桌审稿、历史反馈”。", "blue"],
  ["立场边界", "建议避免写成“代码生成不重要”。更稳的表达是：代码生成重要，但不是长期壁垒的全部。", "green"],
  ["风格选择", "如果用于知乎，建议选择“深度分析 + 工程复盘”的混合结构，既有判断，也有个人经验。", "purple"],
  ["蓝图检查", "当前结构成立。生成初稿时要避免概念堆叠，优先用具体工程场景解释抽象观点。", "blue"],
  ["初稿提醒", "初稿已经能读，但还缺少你的真实项目经验。下一步圆桌审稿会集中处理逻辑和人味。", "orange"],
  ["圆桌结论", "文章可进入定稿，但必须补足“为什么上下文难迁移”和“个人工程经验”两个点。", "red"],
  ["定稿提醒", "这是最终草稿，不是自动发布稿。用户修改后再发布，才能保留作者主体性。", "green"],
  ["反馈闭环", "发布后应提取评论中的支持、反对和补充材料，反哺下一轮文章和观点种子。", "blue"],
] as const;

const onboardingQuestions = [
  ["你希望文章逻辑严密到什么程度？", "3"],
  ["你愿意在文章中表达鲜明立场吗？", "4"],
  ["你喜欢加入个人经历和踩坑案例吗？", "5"],
  ["你能接受比较犀利的表达吗？", "3"],
  ["你希望文章更像知乎回答还是公众号长文？", "中"],
  ["你希望多引用资料还是多讲自己的判断？", "平"],
  ["你是否希望系统主动提出反方质疑？", "5"],
  ["你希望文章开头更直接还是更有故事感？", "中"],
  ["你希望标题更克制还是更有传播性？", "中"],
  ["你是否愿意暴露自己的不确定和纠结？", "4"],
  ["你希望风格更冷静还是更有情绪？", "2"],
  ["你希望 AI 帮你写到什么程度？", "稿"],
];

interface AppState {
  profile: ProfileData;
  categories: InputCategory[];
  cards: WorthReadingCard[];
  seeds: IdeaSeed[];
  sproutOpportunities: SproutOpportunity[];
  feedbackArticles: FeedbackArticle[];
}

export function KanshanApp() {
  const [entered, setEntered] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("today");
  const [toast, setToast] = useState("");
  const [data, setData] = useState<AppState | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("ai-coding");
  const [selectedSeedId, setSelectedSeedId] = useState("seed-ai-coding-moat");
  const [sproutStarted, setSproutStarted] = useState(false);
  const [writingStep, setWritingStep] = useState(0);

  useEffect(() => {
    let mounted = true;

    async function loadMockData() {
      const [profile, content, seeds, sproutOpportunities, feedbackArticles] =
        await Promise.all([
          fetchProfile(),
          fetchContent(),
          fetchSeeds(),
          fetchSproutOpportunities(),
          fetchFeedbackArticles(),
        ]);

      if (!mounted) return;

      setData({
        profile,
        categories: content.categories,
        cards: content.cards,
        seeds,
        sproutOpportunities,
        feedbackArticles,
      });
    }

    loadMockData().catch(() => {
      showToast("Mock API 加载失败");
    });

    return () => {
      mounted = false;
    };
  }, []);

  function showToast(message: string) {
    setToast(message);
    window.clearTimeout(window.__kanshanToastTimer);
    window.__kanshanToastTimer = window.setTimeout(() => setToast(""), 1800);
  }

  function enterApp(mode: "zhihu" | "onboarding" | "demo") {
    setEntered(true);
    setActiveTab(mode === "onboarding" ? "onboarding" : "today");
    showToast(
      mode === "zhihu"
        ? "已模拟关联知乎账号"
        : mode === "onboarding"
          ? "进入首次画像采集"
          : "进入演示模式",
    );
  }

  function goTab(tab: TabId) {
    setActiveTab(tab);
    if (tab === "write") setWritingStep((current) => current);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const selectedSeed = useMemo(() => {
    if (!data) return null;
    return data.seeds.find((seed) => seed.id === selectedSeedId) ?? data.seeds[0];
  }, [data, selectedSeedId]);

  const selectedCards = useMemo(() => {
    if (!data) return [];
    return data.cards.filter((card) => card.categoryId === selectedCategory);
  }, [data, selectedCategory]);

  const activeHero = heroMap[activeTab];

  if (!entered) {
    return <LoginScreen onEnter={enterApp} />;
  }

  if (!data) {
    return (
      <main className="loading-screen">
        <Loader2 className="spin" size={28} />
        <span>正在加载看山小苗圃 mock 数据...</span>
      </main>
    );
  }

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
              <button
                className={activeTab === tab.id ? "active" : ""}
                key={tab.id}
                onClick={() => goTab(tab.id)}
                type="button"
              >
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
          <p>当前查看 AI Coding；关注流与偶遇输入可在同级入口切换。3 颗观点种子进入“可发芽”状态。</p>
        </div>
        <div className="sidebar-card">
          <div className="eyebrow">产品原则</div>
          <p>看到好内容，形成好观点，写出好文章。</p>
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
              <div className="user-mode">主编模式 · 已建画像</div>
            </div>
          </button>
        </header>

        {activeTab === "onboarding" ? (
          <OnboardingSection profile={data.profile} goProfile={() => goTab("profile")} showToast={showToast} />
        ) : null}
        {activeTab === "today" ? (
          <TodaySection
            categories={data.categories}
            cards={selectedCards}
            selectedCategory={selectedCategory}
            setSelectedCategory={setSelectedCategory}
            showToast={showToast}
            startWriting={() => goTab("write")}
            startSprout={() => {
              setSproutStarted(true);
              goTab("sprout");
            }}
          />
        ) : null}
        {activeTab === "seeds" && selectedSeed ? (
          <SeedsSection
            seeds={data.seeds}
            selectedSeed={selectedSeed}
            setSelectedSeedId={setSelectedSeedId}
            startWriting={() => goTab("write")}
            startSprout={() => {
              setSproutStarted(true);
              goTab("sprout");
            }}
            showToast={showToast}
          />
        ) : null}
        {activeTab === "sprout" ? (
          <SproutSection
            started={sproutStarted}
            opportunities={data.sproutOpportunities}
            onStart={() => {
              setSproutStarted(true);
              showToast("已开始：历史种子 × 今日热点 × 用户画像");
            }}
            openSeeds={() => goTab("seeds")}
            startWriting={() => goTab("write")}
          />
        ) : null}
        {activeTab === "write" ? (
          <WritingSection
            step={writingStep}
            setStep={setWritingStep}
            memory={data.profile.interestMemories[0]}
            goHistory={() => goTab("history")}
            showToast={showToast}
          />
        ) : null}
        {activeTab === "history" ? (
          <HistorySection articles={data.feedbackArticles} showToast={showToast} />
        ) : null}
        {activeTab === "profile" ? <ProfileSection profile={data.profile} showToast={showToast} /> : null}
      </main>

      <div className={`floating-toast ${toast ? "show" : ""}`}>{toast}</div>
    </div>
  );
}

function LoginScreen({
  onEnter,
}: {
  onEnter: (mode: "zhihu" | "onboarding" | "demo") => void;
}) {
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

function LoginOption({
  icon,
  title,
  desc,
  onClick,
}: {
  icon: string;
  title: string;
  desc: string;
  onClick: () => void;
}) {
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

function OnboardingSection({
  profile,
  goProfile,
  showToast,
}: {
  profile: ProfileData;
  goProfile: () => void;
  showToast: (message: string) => void;
}) {
  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">首次登录：建立你的创作画像</h2>
            <p className="panel-subtitle">兴趣不只按大类保存，而是细化到兴趣小类，用于后续“今日看什么”的分组展示。</p>
          </div>
          <button className="btn primary" onClick={goProfile} type="button">
            跳过，进入首页
          </button>
        </div>
        <div className="panel-body profile-layout">
          <div className="form-grid">
            <Field label="你希望系统怎么称呼你？" value={profile.nickname} />
            <div className="field">
              <label>你的身份 / 创作背景</label>
              <select className="select" defaultValue="技术创作者 / 工程师">
                <option>技术创作者 / 工程师</option>
                <option>学生 / 研究者</option>
                <option>产品经理</option>
                <option>职场经验分享者</option>
                <option>泛知识创作者</option>
              </select>
            </div>
            <div className="field">
              <label>兴趣小类</label>
              <div className="tag-row">
                {[...profile.interests, "医疗 AI", "产品设计", "内容创作"].map((item, index) => (
                  <button className={`chip ${index < profile.interests.length ? "selected" : ""}`} key={item} type="button">
                    {item}
                  </button>
                ))}
              </div>
            </div>
            <div className="field">
              <label>你最希望系统帮你避免什么？</label>
              <textarea className="textarea" defaultValue="避免把文章写成正确但无聊的 AI 味长文；保留工程经验、个人判断和反方视角。" />
            </div>
            <button
              className="btn primary"
              onClick={() => {
                showToast("画像已生成，可在个人画像页继续修改");
                goProfile();
              }}
              type="button"
            >
              生成我的画像
            </button>
          </div>
          <div>
            <div className="category-header no-top">
              <div>
                <h3>写作风格问卷</h3>
                <p>用 12 个问题形成你的写作画像。1 表示低，5 表示高。</p>
              </div>
            </div>
            <div className="grid-2">
              {onboardingQuestions.map(([question, selected], index) => (
                <div className="question-card" key={question}>
                  <h4>
                    {index + 1}. {question}
                  </h4>
                  <div className="scale">
                    {scaleValues(index).map((value) => (
                      <button className={value === selected ? "selected" : ""} key={value} type="button">
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
  selectedCategory,
  setSelectedCategory,
  showToast,
  startWriting,
  startSprout,
}: {
  categories: InputCategory[];
  cards: WorthReadingCard[];
  selectedCategory: string;
  setSelectedCategory: (category: string) => void;
  showToast: (message: string) => void;
  startWriting: () => void;
  startSprout: () => void;
}) {
  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">今日看什么</h2>
            <p className="panel-subtitle">选择兴趣小类、关注流或偶遇输入，只展示当前分类下的内容。</p>
          </div>
          <button className="btn primary" onClick={() => showToast("已刷新当前分类输入")} type="button">
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
                onClick={() => {
                  if (!category.available) {
                    showToast("原型暂展开 AI Coding、Agent 工程化、关注流和偶遇输入样例");
                    return;
                  }
                  setSelectedCategory(category.id);
                }}
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
                <h3>{sectionTitle(selectedCategory)}</h3>
                <p>{sectionDescription(selectedCategory)}</p>
              </div>
              <span className="tag blue">当前分类</span>
            </div>
            <div className="grid-2">
              {cards.map((card) => (
                <ContentCard
                  card={card}
                  key={card.id}
                  showToast={showToast}
                  startWriting={startWriting}
                  startSprout={startSprout}
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
  showToast,
  startWriting,
  startSprout,
}: {
  card: WorthReadingCard;
  showToast: (message: string) => void;
  startWriting: () => void;
  startSprout: () => void;
}) {
  return (
    <article className={`card structured-card ${card.featured ? "featured-card" : ""}`}>
      <div className="tag-row">
        {card.tags.map((tag) => (
          <span className={`tag ${tag.tone}`} key={`${card.id}-${tag.label}`}>
            {tag.label}
          </span>
        ))}
      </div>
      <h3>标题：{card.title}</h3>
      <InfoBlock title="推荐理由" text={card.recommendationReason} />
      {card.originalSources?.length ? (
        <div className="field-block">
          <div className="field-title">原始内容来源：</div>
          <div className="source-list">
            {card.originalSources.map((source) => (
              <div className="source-card" key={source.title}>
                <div className="source-meta">
                  <span>{source.sourceType}</span>
                  {source.meta.map((item) => (
                    <span key={item}>{item}</span>
                  ))}
                </div>
                <strong>{source.title}</strong>
                <p>来源要点：{source.rawExcerpt}</p>
                <p>贡献：{source.contribution}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <InfoBlock title="内容摘要" text={card.contentSummary} />
      <ListBlock ordered title="主要争议" items={card.controversies} />
      <ListBlock title="可写角度" items={card.writingAngles} />
      <div className="action-row">
        <button className="btn ghost" onClick={() => showToast("已生成摘要")} type="button">
          总结一下
        </button>
        <button className="btn ghost" onClick={() => showToast("已记录：我认同")} type="button">
          我认同
        </button>
        <button className="btn ghost" onClick={() => showToast("已记录：我反对")} type="button">
          我反对
        </button>
        <button className="btn ghost" onClick={() => showToast("已记录：有疑问")} type="button">
          有疑问
        </button>
        <button
          className="btn primary"
          onClick={() => {
            showToast("已加入种子库");
            if (card.id.includes("moat")) startSprout();
          }}
          type="button"
        >
          加入种子库
        </button>
        <button className="btn ghost" onClick={startWriting} type="button">
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
  startWriting,
  startSprout,
  showToast,
}: {
  seeds: IdeaSeed[];
  selectedSeed: IdeaSeed;
  setSelectedSeedId: (id: string) => void;
  startWriting: () => void;
  startSprout: () => void;
  showToast: (message: string) => void;
}) {
  return (
    <section className="section active">
      <div className="two-column-layout">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">我的种子库</h2>
              <p className="panel-subtitle">种子卡片按完整模板展示，包含来源、反应、核心观点、可写方向和下一步操作。</p>
            </div>
            <button className="btn primary" onClick={() => showToast("新建手动种子")} type="button">
              新建种子
            </button>
          </div>
          <div className="panel-body seed-list">
            {seeds.map((seed) => (
              <button
                className={`card structured-card seed-card ${seed.id === selectedSeed.id ? "selected" : ""}`}
                key={seed.id}
                onClick={() => {
                  setSelectedSeedId(seed.id);
                  showToast("已切换观点种子");
                }}
                type="button"
              >
                <div className="tag-row">
                  <span className={`tag ${seed.statusTone}`}>{seed.statusLabel}</span>
                  <span className="tag blue">{seed.interestName}</span>
                </div>
                <h3>观点种子：{seed.title}</h3>
                <InfoBlock title="来源" text={seed.source} />
                <InfoBlock title="原始内容摘要" text={seed.sourceSummary} />
                <InfoBlock title="我的反应" text={seed.userReaction} />
                <InfoBlock title="核心观点" text={seed.coreClaim} />
                <ListBlock ordered title="可写方向" items={seed.possibleAngles} />
                <ListBlock title="需要补充" items={seed.requiredMaterials} />
              </button>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">种子详情</h2>
              <p className="panel-subtitle">把模糊想法转成可写作结构。</p>
            </div>
          </div>
          <div className="panel-body">
            <div className="card no-hover">
              <div className="tag-row">
                <span className="tag blue">核心观点</span>
              </div>
              <h3>{selectedSeed.coreClaim}</h3>
              <InfoBlock
                title="下一步建议"
                text="这颗种子已经具备热点、论点和个人经验入口，适合直接进入“今日发芽”或“写作苗圃”。"
              />
              <div className="action-row">
                <button className="btn primary" onClick={startWriting} type="button">
                  开始写作
                </button>
                <button className="btn ghost" onClick={startSprout} type="button">
                  今日发芽
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
}: {
  started: boolean;
  opportunities: SproutOpportunity[];
  onStart: () => void;
  openSeeds: () => void;
  startWriting: () => void;
}) {
  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">今日发芽</h2>
            <p className="panel-subtitle">历史种子 × 今日热点 × 用户画像，捕捉最适合动笔的时机。为控制接口和 Token 成本，默认由用户主动触发。</p>
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
            {opportunities.map((opportunity) => (
              <article className="card structured-card sprout-card" key={opportunity.id}>
                <div className="sprout-badge">{opportunity.score}</div>
                <div className="tag-row">
                  {opportunity.tags.map((tag) => (
                    <span className={`tag ${tag.tone}`} key={tag.label}>
                      {tag.label}
                    </span>
                  ))}
                </div>
                <h3>今日发芽机会</h3>
                <InfoBlock title="被激活的种子" text={opportunity.activatedSeed} />
                <InfoBlock title="触发热点" text={opportunity.triggerTopic} />
                <InfoBlock title="为什么值得写" text={opportunity.whyWorthWriting} />
                <InfoBlock title="建议标题" text={opportunity.suggestedTitle} />
                <InfoBlock title="建议角度" text={opportunity.suggestedAngle} />
                <InfoBlock title="建议补充" text={opportunity.suggestedMaterials} />
                <div className="action-row">
                  <button className="btn primary" onClick={startWriting} type="button">
                    开始写作
                  </button>
                  <button className="btn ghost" type="button">
                    补充资料
                  </button>
                  <button className="btn ghost" type="button">
                    换个角度
                  </button>
                  <button className="btn ghost" type="button">
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
  step,
  setStep,
  memory,
  goHistory,
  showToast,
}: {
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  memory: ProfileData["interestMemories"][number];
  goHistory: () => void;
  showToast: (message: string) => void;
}) {
  const [adviceLabel, adviceText, adviceTone] = writingAdvice[step];

  return (
    <section className="section active">
      <div className="wizard-layout">
        <aside className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">写作流程</h2>
              <p className="panel-subtitle">流程写死但可交互，适合直接演示。</p>
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
            <MemoryInjection memory={memory} />
            <WritingStageContent step={step} goHistory={goHistory} showToast={showToast} setStep={setStep} />
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
              <p className="panel-subtitle">不同 Agent 共同评判，用户满意后点击定稿。</p>
            </div>
          </div>
          <div className="panel-body">
            <div className="check-item">
              <h4>
                <span className={`tag ${adviceTone}`}>{adviceLabel}</span>
              </h4>
              <p>{adviceText}</p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}

function WritingStageContent({
  step,
  setStep,
  goHistory,
  showToast,
}: {
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  goHistory: () => void;
  showToast: (message: string) => void;
}) {
  if (step === 0) {
    return (
      <>
        <h2 className="stage-title">选择观点种子</h2>
        <p className="stage-desc">当前演示选择的是“AI 编程工具的护城河可能不在代码生成”。</p>
        <div className="draft-box">
          <div className="tag-row">
            <span className="tag green">可发芽</span>
            <span className="tag blue">AI 编程</span>
          </div>
          <h2>观点种子：AI 编程工具的护城河可能不在代码生成</h2>
          <p>
            <strong>核心观点：</strong>单纯代码生成工具的护城河很浅，真正的壁垒可能在上下文积累、工作流入口、团队协作和企业数据闭环。
          </p>
          <p>
            <strong>触发热点：</strong>AI 编程工具进入企业协作场景。
          </p>
          <p>
            <strong>建议文章类型：</strong>深度分析 / 工程复盘。
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
            单纯代码生成能力很难成为 AI 编程工具的长期护城河。真正有价值的是上下文积累、工程工作流入口、团队协作数据和企业级可控交付。
          </p>
          <p>
            <strong>文章基调：</strong>
            <br />
            不是否定 AI 编程工具的价值，而是讨论它的长期竞争壁垒在哪里。
          </p>
          <p>
            <strong>你想让读者带走的判断：</strong>
            <br />
            AI 编程产品的竞争，将从“谁更会写代码”转向“谁更懂工程现场”。
          </p>
          <div className="action-row">
            <button className="btn primary" onClick={() => showToast("已确认核心观点")} type="button">
              确认
            </button>
            <button className="btn ghost" type="button">
              调整观点
            </button>
            <button className="btn ghost" type="button">
              更犀利一点
            </button>
            <button className="btn ghost" type="button">
              更稳健一点
            </button>
            <button className="btn ghost" type="button">
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
          {[
            ["深度分析", "适合讨论 AI 编程产品的长期壁垒，强调逻辑、推演和资料支撑。", true],
            ["经验复盘", "适合加入 FileSync3、Java 后端等个人项目经验，提高人味和可信度。", false],
            ["知乎回答", "更直接，适合回答“AI 编程工具的护城河是什么？”这类问题。", false],
            ["观点评论", "更贴近热点，强调时效、立场和反差。", false],
          ].map(([title, desc, recommended]) => (
            <div className="card no-hover" key={title as string}>
              {recommended ? (
                <div className="tag-row">
                  <span className="tag blue">推荐</span>
                </div>
              ) : null}
              <h3>{title}</h3>
              <p>{desc}</p>
            </div>
          ))}
        </div>
      </>
    );
  }

  if (step === 3) {
    return (
      <>
        <h2 className="stage-title">论证蓝图</h2>
        <p className="stage-desc">先把文章骨架搭好，再进入正文。</p>
        <div className="draft-box">
          <p>
            <strong>中心观点：</strong>
            <br />
            AI 编程工具的长期护城河，不在代码生成，而在工程上下文和工作流闭环。
          </p>
          <p>
            <strong>背景：</strong>
            <br />
            代码生成能力正在快速普及，单次生成效果的差距会逐渐缩小。
          </p>
          <Blueprint title="分论点一：代码生成能力容易被模型升级追平" items={["基础模型能力会持续提升", "常规代码模式可被大量数据覆盖", "单点生成能力难以形成长期壁垒"]} />
          <Blueprint title="分论点二：工程上下文更难迁移" items={["每个团队的代码规范、业务规则、历史债务不同", "真正影响效率的是上下文理解和持续协作", "工程现场的信息高度碎片化"]} />
          <Blueprint title="分论点三：企业用户真正关心的是可控交付" items={["生成代码只是开始", "代码需要测试、审查、集成、回滚、追责", "工具必须嵌入研发流程"]} />
          <p>
            <strong>反方观点：</strong>
            <br />
            如果模型足够强，是否也能理解上下文？
          </p>
          <p>
            <strong>建议加入的个人经验：</strong>
            <br />
            你过去做 FileSync3 或 Java 后端项目时，可以补充“真正困难的不是写代码，而是数据链路、状态变化、边界条件和客户需求变化”。
          </p>
        </div>
      </>
    );
  }

  if (step === 4) {
    return (
      <>
        <h2 className="stage-title">生成表达初稿</h2>
        <p className="stage-desc">这不是最终发布稿，而是基于观点种子生成的可编辑表达稿。</p>
        <div className="draft-box">
          <h2>AI 编程工具的护城河，可能不在“会写代码”</h2>
          <p>如果只看单次代码生成效果，AI 编程工具之间的差距很容易被模型升级抹平。今天一个工具能生成接口代码，明天另一个工具也可以；今天一个模型能补测试样例，下一轮基础模型更新后，这类能力可能很快变成标配。</p>
          <p>真正值得讨论的是，当“生成代码”这件事逐渐商品化以后，AI 编程产品还能靠什么形成长期壁垒。我的判断是，壁垒不会只来自模型本身，而会更多来自工程上下文、研发工作流入口、团队协作数据，以及企业级可控交付能力。</p>
          <p>很多项目里，写代码不是最难的部分。真正困难的是弄清楚需求边界、兼容历史逻辑、处理状态变化、保证出问题时能定位、回滚和追责。</p>
        </div>
      </>
    );
  }

  if (step === 5) {
    return (
      <>
        <h2 className="stage-title">圆桌审稿会</h2>
        <p className="stage-desc">逻辑压测和人味检查合并为圆桌会议，由不同 Agent 从不同视角评判讨论。</p>
        <div className="roundtable">
          <AgentReview avatar="逻" title="逻辑审稿 Agent" text="第 2 段到第 3 段之间仍有跳跃：你从代码生成同质化推到工程上下文更重要，需要解释上下文为什么难以被模型直接学习。" />
          <AgentReview avatar="人" title="人味编辑 Agent" text="文章目前像行业分析，缺少你的真实项目经验。建议加入 FileSync3 或复杂后端系统中“代码不难，边界很难”的具体场景。" tone="orange" />
          <AgentReview avatar="反" title="反方读者 Agent" text="我会质疑：未来长上下文模型能吸收整个代码库，为什么上下文仍是壁垒？你需要回应上下文长度不等于上下文质量。" tone="purple" />
          <AgentReview avatar="传" title="社区传播 Agent" text="标题有传播性但不标题党。建议开头从工程场景切入，而不是从“随着 AI 技术发展”这类泛化表达切入。" tone="green" />
        </div>
        <div className="action-row">
          <button className="btn ghost" type="button">采纳逻辑建议</button>
          <button className="btn ghost" type="button">补充个人经历</button>
          <button className="btn ghost" type="button">生成反方回应</button>
          <button
            className="btn primary"
            onClick={() => {
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
          <h2>AI 编程工具的护城河，可能不在“会写代码”</h2>
          <p>很多人讨论 AI 编程工具时，容易把注意力放在“谁更会写代码”上。但如果只看单次代码生成效果，这件事很可能会越来越难形成长期差距。模型会升级，常规代码模式会被大量覆盖，今天领先的补全、生成、测试能力，明天就可能变成行业标配。</p>
          <p>我更关心的是另一件事：当代码生成能力逐渐商品化之后，AI 编程产品还能靠什么形成长期壁垒？我的判断是，壁垒不会只来自模型本身，而会更多来自工程上下文、研发工作流入口、团队协作数据，以及企业级可控交付能力。</p>
          <p>这和我过去做复杂后端系统时的感受很接近。很多时候，写出一段代码并不是最难的部分。真正麻烦的是弄清楚需求边界、兼容历史逻辑、处理状态变化、保证出了问题之后能够定位、回滚和追责。AI 可以生成一段看起来正确的代码，但它不天然知道这个字段为什么不能改、这个状态为什么不能丢、这个逻辑为什么必须兼容历史客户。</p>
          <p>所以，AI 编程工具的竞争终点，可能不是谁更会写代码，而是谁更懂工程现场。代码生成是入口，工程上下文才可能成为长期资产。</p>
          <div className="action-row">
            <button className="btn primary" onClick={() => showToast("已定稿：请人工修改后发布")} type="button">确认定稿</button>
            <button className="btn ghost" type="button">继续修改</button>
            <button className="btn ghost" type="button">复制草稿</button>
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
          <li>请补充一个你真实经历中的工程场景，避免文章过于抽象。</li>
          <li>请确认文中观点是你认可的表达，不要直接发布未检查版本。</li>
          <li>建议先发布到圈子收集评论，再发布为长文。</li>
          <li>发布后进入“历史反馈”页面，系统会提取评论中的支持、反对和补充材料。</li>
        </ul>
        <div className="action-row">
          <button
            className="btn primary"
            onClick={() => {
              showToast("已模拟发布，进入历史反馈");
              goHistory();
            }}
            type="button"
          >
            我已修改，模拟发布
          </button>
          <button className="btn ghost" type="button">保存为草稿</button>
          <button className="btn ghost" type="button">复制最终稿</button>
        </div>
      </div>
    </>
  );
}

function HistorySection({
  articles,
  showToast,
}: {
  articles: FeedbackArticle[];
  showToast: (message: string) => void;
}) {
  return (
    <section className="section active">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">历史文章监控反馈</h2>
            <p className="panel-subtitle">监控已发布文章表现，提取反馈信号，反哺用户画像、种子库和下一篇文章。</p>
          </div>
          <button className="btn primary" onClick={() => showToast("已同步最新互动数据")} type="button">
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
                  <button className="btn primary" type="button">生成二次文章</button>
                  <button className="btn ghost" type="button">更新 Memory</button>
                  <button className="btn ghost" type="button">查看评论摘要</button>
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
  showToast,
}: {
  profile: ProfileData;
  showToast: (message: string) => void;
}) {
  return (
    <section className="section active">
      <div className="profile-layout">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">个人信息管理</h2>
              <p className="panel-subtitle">独立部署时，这里用于建立和维护你的本地用户画像 Memory。</p>
            </div>
            <button className="btn primary" onClick={() => showToast("个人画像已保存")} type="button">
              保存画像
            </button>
          </div>
          <div className="panel-body form-grid">
            <Field label="昵称" value={profile.nickname} />
            <Field label="账号状态" value={profile.accountStatus} />
            <Field label="身份标签" value={profile.role} />
            <div className="field">
              <label>兴趣小类</label>
              <div className="tag-row">
                {[...profile.interests, "医疗 AI", "产品设计"].map((interest, index) => (
                  <button className={`chip ${index < profile.interests.length ? "selected" : ""}`} key={interest} type="button">
                    {interest}
                  </button>
                ))}
              </div>
            </div>
            <div className="field">
              <label>不希望系统做什么</label>
              <textarea className="textarea" defaultValue={profile.avoidances} />
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
            <MemoryCard title="长期背景" text={profile.globalMemory.longTermBackground} />
            <MemoryCard title="内容偏好" text={profile.globalMemory.contentPreference} />
            <MemoryCard title="写作风格" text={profile.globalMemory.writingStyle} />
            <MemoryCard title="推荐策略" text={profile.globalMemory.recommendationStrategy} />
            <MemoryCard title="写作风险提醒" text={profile.globalMemory.riskReminder} />
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
            {profile.interestMemories.map((memory) => (
              <div className="memory-card" key={memory.interestName}>
                <strong>{memory.interestName}</strong>
                <p className="field-text">
                  知识水平：{memory.knowledgeLevel}；偏好视角：{memory.preferredPerspective.join("、")}。
                </p>
                <textarea className="textarea" defaultValue={`证据偏好：${memory.evidencePreference}。写作提醒：${memory.writingReminder}`} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="field">
      <label>{label}</label>
      <input className="input" defaultValue={value} />
    </div>
  );
}

function MemoryCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="memory-card">
      <strong>{title}</strong>
      <textarea className="textarea" defaultValue={text} />
    </div>
  );
}

function MemoryInjection({ memory }: { memory: ProfileData["interestMemories"][number] }) {
  return (
    <div className="memory-injection">
      <div className="tag-row">
        <span className="tag blue">已匹配兴趣分类画像：{memory.interestName}</span>
        <span className="tag green">Memory 已注入</span>
      </div>
      <h3>本次写作使用的画像 Memory</h3>
      <p>
        <strong>偏好视角：</strong>
        {memory.preferredPerspective.join("、")}。
        <br />
        <strong>证据偏好：</strong>
        {memory.evidencePreference}，避免只讲工具趋势。
        <br />
        <strong>写作提醒：</strong>
        {memory.writingReminder} 并回应“长上下文模型会不会削弱壁垒”的反方质疑。
      </p>
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

function ListBlock({
  title,
  items,
  ordered,
}: {
  title: string;
  items: string[];
  ordered?: boolean;
}) {
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

function AgentReview({
  avatar,
  title,
  text,
  tone = "blue",
}: {
  avatar: string;
  title: string;
  text: string;
  tone?: "blue" | "orange" | "purple" | "green";
}) {
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

function scaleValues(index: number) {
  if (index === 4) return ["答", "中", "文", "专", "稿"];
  if (index === 5) return ["料", "2", "平", "4", "判"];
  if (index === 7) return ["直", "2", "中", "4", "事"];
  if (index === 8) return ["克", "2", "中", "4", "传"];
  if (index === 10) return ["冷", "2", "中", "4", "情"];
  if (index === 11) return ["纲", "段", "稿", "修", "发"];
  return ["1", "2", "3", "4", "5"];
}

function sectionTitle(category: string) {
  if (category === "following") return "关注流精选";
  if (category === "serendipity") return "偶遇输入";
  if (category === "agent") return "兴趣小类：Agent 工程化";
  return "兴趣小类：AI Coding";
}

function sectionDescription(category: string) {
  if (category === "following") return "来自你关注的人和圈子动态，优先筛选观点密度高、讨论价值高的内容。";
  if (category === "serendipity") return "保留少量远端关联信息，避免推荐只在同温层内自我强化。";
  if (category === "agent") return "系统保留多个兴趣小类，每类可以独立展开 3–5 张卡片。";
  return "基于你的 AI Coding、工程实践、程序员成长标签筛选。";
}

declare global {
  interface Window {
    __kanshanToastTimer: number | undefined;
  }
}
