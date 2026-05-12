"use client";

import {
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getMe } from "@/lib/auth/auth-client";
import type {
  AuthResponse,
  AuthStatus,
  LlmConfigViewModel,
  OnboardingResponse,
  ProfileData,
  UserSetupState,
} from "@/lib/types";
import { LoginPanel } from "./LoginPanel";
import { RegisterPanel } from "./RegisterPanel";
import { ZhihuLinkPanel } from "./ZhihuLinkPanel";
import { LlmConfigPanel } from "./LlmConfigPanel";
import { PreferenceOnboardingPanel } from "./PreferenceOnboardingPanel";
import { ProfileGenerationPanel } from "./ProfileGenerationPanel";

type AuthStep = "loading" | "login" | "register" | "zhihu" | "llm" | "preferences" | "generating";
type ProgressStepId = "auth" | "zhihu" | "llm" | "interest" | "style" | "generation";

interface AuthEntryProps {
  onComplete: (profile?: ProfileData) => void;
  onShowDemo?: () => void;
}

const setupSteps: { id: ProgressStepId; label: string; desc: string }[] = [
  { id: "auth", label: "注册", desc: "绑定本地用户身份" },
  { id: "zhihu", label: "知乎关联", desc: "授权或跳过" },
  { id: "llm", label: "LLM 配置", desc: "免费额度或自有模型" },
  { id: "interest", label: "兴趣领域", desc: "选择长期 Memory 主类" },
  { id: "style", label: "创作画像", desc: "资料 + 风格问卷" },
  { id: "generation", label: "完成", desc: "进入工作台" },
];

export function AuthEntry({ onComplete, onShowDemo }: AuthEntryProps) {
  const [step, setStep] = useState<AuthStep>("loading");
  const [preferenceStep, setPreferenceStep] = useState<"interests" | "style">("interests");
  const [authStatus, setAuthStatus] = useState<AuthStatus>("guest");
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const [setupState, setSetupState] = useState<UserSetupState>("zhihu_pending");
  const [zhihuSkipped, setZhihuSkipped] = useState(false);
  const [llmConfig, setLlmConfig] = useState<LlmConfigViewModel | null>(null);
  const [onboardingResult, setOnboardingResult] = useState<OnboardingResponse | null>(null);

  const navigateToStep = useCallback((state: UserSetupState) => {
    switch (state) {
      case "zhihu_pending":
        setStep("zhihu");
        break;
      case "llm_pending":
        setStep("llm");
        break;
      case "preferences_pending":
        setStep("preferences");
        break;
      case "provisional_ready":
      case "ready":
        onComplete();
        break;
      default:
        setStep("zhihu");
    }
  }, [onComplete]);

  const checkAuthStatus = useCallback(async () => {
    try {
      const me = await getMe();
      if (me.authenticated && me.user) {
        setUser(me.user);
        setAuthStatus("authenticated");
        setSetupState(me.setupState || "zhihu_pending");
        navigateToStep(me.setupState || "zhihu_pending");
      } else {
        setAuthStatus("guest");
        setStep("login");
      }
    } catch {
      setAuthStatus("guest");
      setStep("login");
    }
  }, [navigateToStep]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void checkAuthStatus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [checkAuthStatus]);

  function handleRegisterSuccess(response: AuthResponse) {
    setUser(response.user);
    setSetupState(response.setupState);
    setAuthStatus("authenticated");
    setZhihuSkipped(false);
    setStep("zhihu");
  }

  function handleLoginSuccess(response: AuthResponse) {
    setUser(response.user);
    setSetupState(response.setupState);
    setAuthStatus("authenticated");
    // 登录直接进入工作台，不走引导流程
    onComplete();
  }

  function handleZhihuComplete() {
    setSetupState("llm_pending");
    setZhihuSkipped(false);
    setStep("llm");
  }

  function handleZhihuSkip() {
    setSetupState("llm_pending");
    setZhihuSkipped(true);
    setStep("llm");
  }

  function handleLlmComplete(config: LlmConfigViewModel) {
    setLlmConfig(config);
    setSetupState("preferences_pending");
    setPreferenceStep("interests");
    setStep("preferences");
  }

  function handlePreferencesComplete(response: OnboardingResponse) {
    setOnboardingResult(response);
    setSetupState("provisional_ready");
    setStep("generating");
  }

  const progressStep: ProgressStepId =
    step === "zhihu"
      ? "zhihu"
      : step === "llm"
        ? "llm"
        : step === "preferences"
          ? preferenceStep === "style"
            ? "style"
            : "interest"
          : step === "generating"
            ? "generation"
            : "auth";
  const activeIndex = Math.max(0, setupSteps.findIndex((item) => item.id === progressStep));
  const stepTitle =
    progressStep === "auth"
      ? "登录 / 注册"
      : progressStep === "zhihu"
        ? "关联知乎账号"
        : progressStep === "llm"
          ? "配置 LLM 使用方式"
          : progressStep === "interest"
            ? "选择兴趣领域"
            : progressStep === "style"
              ? "建立创作画像"
              : "临时画像已生成";
  const stepDesc =
    progressStep === "auth"
      ? "用户必须先拥有本地账号，后续 OAuth、LLM 配置和画像才能绑定到用户。"
      : progressStep === "zhihu"
        ? "OAuth 暂未开放时可以跳过，系统会先根据显式填写内容生成临时画像。"
        : progressStep === "llm"
          ? "可使用平台免费额度，也可配置自己的 OpenAI-compatible 模型。"
          : progressStep === "interest"
            ? "兴趣是长期 Memory 的主分类，关注流和偶遇输入只是内容来源。"
            : progressStep === "style"
              ? "写作风格会写入全局 Memory，用于后续写作和审稿。"
              : "进入工作台前，系统会展示临时画像摘要和后续可增强项。";

  if (step === "loading") {
    return (
      <main className="auth-entry-shell auth-entry-loading">
        <div className="auth-loading-card">
          <Loader2 className="spin" size={26} />
          <span>正在检查登录状态...</span>
        </div>
      </main>
    );
  }

  // 登录页面 - 简洁布局
  if (step === "login") {
    return (
      <main className="login-shell">
        <div className="login-container">
          {/* 左侧：登录表单 */}
          <div className="login-left">
            <div className="login-brand">
              <div className="login-logo">苗</div>
              <div>
                <h1>看山小苗圃</h1>
                <p>知乎读写一体创作 Agent</p>
              </div>
            </div>

            <div className="login-form-container">
              <h2>登录</h2>
              <p className="login-subtitle">登录你的账号继续使用</p>

              <LoginPanel
                onSuccess={handleLoginSuccess}
                onSwitchToRegister={() => setStep("register")}
              />

              <div className="login-divider">
                <span>或</span>
              </div>

              <button
                className="btn ghost login-demo-btn"
                onClick={onShowDemo}
                type="button"
              >
                进入演示模式
              </button>
            </div>
          </div>

          {/* 右侧：刘看山图片区域 */}
          <div className="login-right">
            <div className="login-image-placeholder">
              <div className="login-mascot">
                <div className="mascot-character">刘</div>
                <div className="mascot-name">看山</div>
              </div>
              <p className="login-tagline">看到好内容，形成好观点，写出好文章</p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // 注册页面 - 左侧表单，右侧图片
  if (step === "register") {
    return (
      <main className="login-shell">
        <div className="login-container">
          {/* 左侧：注册表单 */}
          <div className="login-left">
            <div className="login-brand">
              <div className="login-logo">苗</div>
              <div>
                <h1>看山小苗圃</h1>
                <p>知乎读写一体创作 Agent</p>
              </div>
            </div>

            <div className="login-form-container">
              <h2>注册</h2>
              <p className="login-subtitle">创建账号开始你的创作之旅</p>

              <RegisterPanel
                onSuccess={handleRegisterSuccess}
                onSwitchToLogin={() => setStep("login")}
              />

              <div className="login-divider">
                <span>或</span>
              </div>

              <button
                className="btn ghost login-demo-btn"
                onClick={onShowDemo}
                type="button"
              >
                进入演示模式
              </button>
            </div>
          </div>

          {/* 右侧：刘看山图片区域 */}
          <div className="login-right">
            <div className="login-image-placeholder">
              <div className="login-mascot">
                <div className="mascot-character">刘</div>
                <div className="mascot-name">看山</div>
              </div>
              <p className="login-tagline">看到好内容，形成好观点，写出好文章</p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // 后续步骤（知乎关联、LLM配置、兴趣选择、画像生成）
  return (
    <main className="auth-entry-shell">
      <div className="auth-entry-topbar">
        <div className="auth-brand">
          <div className="login-logo auth-logo">苗</div>
          <div className="auth-title-block">
            <h1>{stepTitle}</h1>
            <p>{stepDesc}</p>
          </div>
        </div>
        <div className="auth-status-pill" role="status">
          <div className="avatar">{user?.nickname?.slice(0, 1) || "访"}</div>
          <div>
            <div className="auth-pill-name">{user?.nickname || "Guest"}</div>
            <div className="auth-pill-desc">
              {authStatus === "authenticated" ? `已登录 · ${setupState}` : "未登录 · 未建画像"}
            </div>
          </div>
        </div>
      </div>

      <div className="auth-progress" aria-label="设置进度">
        {setupSteps.map((item, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex;
          return (
            <div className={`auth-progress-step ${active || done ? "active" : ""} ${done ? "done" : ""}`} key={item.id}>
              <div className="auth-step-num">{done ? <CheckCircle2 size={15} /> : index + 1}</div>
              <strong>{item.label}</strong>
              <span>{item.desc}</span>
            </div>
          );
        })}
      </div>

      <div className="auth-main-grid">
        <article className="panel auth-wizard-panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">{stepTitle}</h2>
              <p className="panel-subtitle">{stepDesc}</p>
            </div>
          </div>

          <div className="panel-body">
            {step === "zhihu" && user ? (
              <section className="auth-step-panel active">
                <ZhihuLinkPanel userId={user.userId} onComplete={handleZhihuComplete} onSkip={handleZhihuSkip} />
              </section>
            ) : null}

            {step === "llm" ? (
              <section className="auth-step-panel active">
                <LlmConfigPanel onComplete={handleLlmComplete} />
              </section>
            ) : null}

            {step === "preferences" && user ? (
              <section className="auth-step-panel active">
                <PreferenceOnboardingPanel
                  nickname={user.nickname}
                  onComplete={handlePreferencesComplete}
                  onStepChange={setPreferenceStep}
                />
              </section>
            ) : null}

            {step === "generating" && onboardingResult ? (
              <section className="auth-step-panel active">
                <ProfileGenerationPanel
                  response={onboardingResult}
                  zhihuSkipped={zhihuSkipped}
                  llmConfig={llmConfig}
                  onEnterWorkspace={() => onComplete(onboardingResult.profile)}
                  onBackToZhihu={() => setStep("zhihu")}
                  onBackToLlm={() => setStep("llm")}
                />
              </section>
            ) : null}
          </div>
        </article>
      </div>
    </main>
  );
}
