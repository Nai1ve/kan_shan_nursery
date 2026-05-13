"use client";

import { ChevronLeft, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { saveOnboarding } from "@/lib/auth/auth-client";
import type { OnboardingPayload, OnboardingResponse, SelectedInterest, WritingStyleSurvey } from "@/lib/types";

const INTEREST_OPTIONS = [
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

const scaleQuestions: { key: keyof WritingStyleSurvey; question: string; low: string; high: string }[] = [
  { key: "logicDepth", question: "你希望文章逻辑严密到什么程度？", low: "轻量表达", high: "严密推演" },
  { key: "stanceSharpness", question: "你愿意在文章中表达鲜明立场吗？", low: "保守克制", high: "明确锋利" },
  { key: "personalExperienceWillingness", question: "你喜欢加入个人经历和踩坑案例吗？", low: "少讲自己", high: "多讲经历" },
  { key: "expressionSharpness", question: "你能接受比较犀利的表达吗？", low: "平和", high: "犀利" },
  { key: "uncertaintyTolerance", question: "你是否愿意暴露自己的不确定和纠结？", low: "少暴露", high: "愿意展开" },
];

const choiceGroups = [
  {
    key: "preferredFormat" as const,
    label: "文章形态",
    options: [
      ["zhihu_answer", "知乎回答"],
      ["balanced", "均衡"],
      ["long_article", "长文"],
      ["column", "专栏"],
      ["draft", "草稿"],
    ],
  },
  {
    key: "evidenceVsJudgment" as const,
    label: "证据 vs 判断",
    options: [["evidence_first", "证据优先"], ["balanced", "均衡"], ["judgment_first", "判断优先"]],
  },
  {
    key: "openingStyle" as const,
    label: "开头风格",
    options: [["direct", "直接"], ["balanced", "均衡"], ["story", "故事感"]],
  },
  {
    key: "titleStyle" as const,
    label: "标题风格",
    options: [["restrained", "克制"], ["balanced", "均衡"], ["spreadable", "传播性"]],
  },
  {
    key: "emotionalTemperature" as const,
    label: "情绪温度",
    options: [["cold", "冷静"], ["balanced", "均衡"], ["emotional", "有情绪"]],
  },
  {
    key: "aiAssistanceBoundary" as const,
    label: "AI 辅助边界",
    options: [["outline", "只给大纲"], ["paragraph", "段落建议"], ["draft", "生成初稿"], ["polish", "润色"], ["publish_ready", "接近定稿"]],
  },
];

interface PreferenceOnboardingPanelProps {
  nickname: string;
  onComplete: (response: OnboardingResponse) => void;
  onStepChange?: (step: "interests" | "style") => void;
}

const defaultStyle: WritingStyleSurvey = {
  logicDepth: 4,
  stanceSharpness: 3,
  personalExperienceWillingness: 4,
  expressionSharpness: 3,
  preferredFormat: "balanced",
  evidenceVsJudgment: "balanced",
  wantsCounterArguments: true,
  openingStyle: "balanced",
  titleStyle: "balanced",
  uncertaintyTolerance: 3,
  emotionalTemperature: "balanced",
  aiAssistanceBoundary: "draft",
};

export function PreferenceOnboardingPanel({ nickname, onComplete, onStepChange }: PreferenceOnboardingPanelProps) {
  const [step, setStep] = useState<"interests" | "style">("interests");
  const [selectedInterests, setSelectedInterests] = useState<SelectedInterest[]>([]);
  const [writingStyle, setWritingStyle] = useState<WritingStyleSurvey>(defaultStyle);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    onStepChange?.(step);
  }, [onStepChange, step]);

  function toggleInterest(interestId: string) {
    setSelectedInterests((prev) => {
      const existing = prev.find((item) => item.interestId === interestId);
      if (existing) return prev.filter((item) => item.interestId !== interestId);
      return [...prev, { interestId, selected: true, selfRatedLevel: "intermediate", intent: "both" }];
    });
  }

  function updateInterest(interestId: string, patch: Partial<SelectedInterest>) {
    setSelectedInterests((prev) => prev.map((item) => (item.interestId === interestId ? { ...item, ...patch } : item)));
  }

  async function handleSubmit() {
    setLoading(true);
    setError("");
    try {
      const payload: OnboardingPayload = { nickname, selectedInterests, writingStyle };
      const response = await saveOnboarding(payload);
      onComplete(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败，请重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-panel preference-panel">
      <div className="auth-card-head">
        <div className="auth-icon-badge"><Sparkles size={18} /></div>
        <div>
          <h3>兴趣领域与写作风格</h3>
          <p>这里生成的是临时画像，后续 OAuth 增强画像会作为草稿交给你确认。</p>
        </div>
      </div>

      {step === "interests" ? (
        <div className="preference-step">
          <div className="preference-section-head">
            <div>
              <strong>选择长期兴趣 Memory 主分类</strong>
              <span>关注流和偶遇输入是内容来源，不放入长期兴趣主分类。</span>
            </div>
            <em>{selectedInterests.length} 个已选</em>
          </div>

          <div className="interest-grid onboarding-interest-grid">
            {INTEREST_OPTIONS.map((interest) => {
              const selected = selectedInterests.find((item) => item.interestId === interest.id);
              return (
                <div className={`interest-card-wrap ${selected ? "selected" : ""}`} key={interest.id}>
                  <button className="interest-card" onClick={() => toggleInterest(interest.id)} type="button">
                    <span className="interest-name">{interest.name}</span>
                    <span className="interest-desc">{interest.desc}</span>
                  </button>
                  {selected ? (
                    <div className="interest-meta-controls">
                      <select value={selected.selfRatedLevel} onChange={(e) => updateInterest(interest.id, { selfRatedLevel: e.target.value as SelectedInterest["selfRatedLevel"] })}>
                        <option value="beginner">入门</option>
                        <option value="intermediate">中级</option>
                        <option value="advanced">进阶</option>
                      </select>
                      <select value={selected.intent} onChange={(e) => updateInterest(interest.id, { intent: e.target.value as SelectedInterest["intent"] })}>
                        <option value="read">主要阅读</option>
                        <option value="write">主要写作</option>
                        <option value="both">读写兼顾</option>
                      </select>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>

          <button className="auth-button primary" onClick={() => setStep("style")} disabled={selectedInterests.length === 0} type="button">
            下一步：设置写作风格
          </button>
        </div>
      ) : null}

      {step === "style" ? (
        <div className="preference-step">
          <div className="preference-section-head">
            <div>
              <strong>写作风格问卷</strong>
              <span>这些结构化答案会写入全局 Memory 和后续写作提示。</span>
            </div>
          </div>

          <div className="style-question-grid">
            {scaleQuestions.map((q) => (
              <div className="style-question" key={q.key}>
                <div className="style-question-head">
                  <strong>{q.question}</strong>
                  <span>{writingStyle[q.key] as number}/5</span>
                </div>
                <div className="scale-label-row"><span>{q.low}</span><span>{q.high}</span></div>
                <div className="style-options">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button
                      key={value}
                      className={`style-option ${writingStyle[q.key] === value ? "selected" : ""}`}
                      onClick={() => setWritingStyle((prev) => ({ ...prev, [q.key]: value }))}
                      type="button"
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="choice-question-grid">
            {choiceGroups.map((group) => (
              <div className="choice-question" key={group.key}>
                <strong>{group.label}</strong>
                <div className="segmented-row">
                  {group.options.map(([value, label]) => (
                    <button
                      key={value}
                      className={writingStyle[group.key] === value ? "selected" : ""}
                      onClick={() => setWritingStyle((prev) => ({ ...prev, [group.key]: value }))}
                      type="button"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <div className="choice-question full">
              <strong>是否主动提出反方质疑</strong>
              <div className="segmented-row">
                <button className={writingStyle.wantsCounterArguments ? "selected" : ""} onClick={() => setWritingStyle((prev) => ({ ...prev, wantsCounterArguments: true }))} type="button">需要</button>
                <button className={!writingStyle.wantsCounterArguments ? "selected" : ""} onClick={() => setWritingStyle((prev) => ({ ...prev, wantsCounterArguments: false }))} type="button">暂不需要</button>
              </div>
            </div>
          </div>

          {error ? <div className="auth-error">{error}</div> : null}

          <div className="style-actions">
            <button className="auth-button secondary" onClick={() => setStep("interests")} type="button">
              <ChevronLeft size={16} /> 上一步
            </button>
            <button className="auth-button primary" onClick={handleSubmit} disabled={loading} type="button">
              {loading ? "生成中..." : "生成临时画像"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
