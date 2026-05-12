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
type AuthMode = "login" | "register" | "demo";
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
  const [authMode, setAuthMode] = useState<AuthMode>("register");
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
        setAuthMode("register");
        setStep("register");
      }
    } catch {
      setAuthStatus("guest");
      setAuthMode("register");
      setStep("register");
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
    navigateToStep(response.setupState);
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

  function setAuthPanel(mode: AuthMode) {
    setAuthMode(mode);
    if (mode === "login") setStep("login");
    if (mode === "register") setStep("register");
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

  return (
    <main className="auth-entry-shell">
      <div className="auth-entry-topbar">
        <div className="auth-brand">
          <div className="login-logo auth-logo">苗</div>
          <div className="auth-title-block">
            <h1>登录 / 注册</h1>
            <p>先建立本地用户身份，再逐步完成知乎授权、LLM 配置、兴趣采集和画像生成。</p>
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
            {(step === "login" || step === "register") ? (
              <section className="auth-step-panel active">
                <div className="grid-2 auth-intro-grid">
                  <div className="card no-hover">
                    <div className="tag-row">
                      <span className="tag blue">欢迎使用</span>
                      <span className="tag green">本地账号</span>
                    </div>
                    <h3>看山小苗圃</h3>
                    <p className="field-text">
                      登录或注册一个本地账号。后续的知乎授权、兴趣选择、写作风格和创作画像都会绑定到这个账号。
                    </p>
                    <div className="field-block">
                      <div className="field-title">你将完成：</div>
                      <ul className="field-list">
                        <li>选择兴趣领域，建立长期 Memory 主类</li>
                        <li>配置平台免费额度或自己的 LLM</li>
                        <li>生成临时画像，等待 OAuth 后增强</li>
                        <li>进入读写一体工作台</li>
                      </ul>
                    </div>
                  </div>

                  <div className="card no-hover">
                    <div className="auth-tabs" role="tablist" aria-label="登录注册入口">
                      <button
                        className={`auth-tab ${authMode === "login" ? "active" : ""}`}
                        onClick={() => setAuthPanel("login")}
                        type="button"
                      >
                        登录
                      </button>
                      <button
                        className={`auth-tab ${authMode === "register" ? "active" : ""}`}
                        onClick={() => setAuthPanel("register")}
                        type="button"
                      >
                        注册
                      </button>
                      <button
                        className={`auth-tab ${authMode === "demo" ? "active" : ""}`}
                        onClick={() => setAuthMode("demo")}
                        type="button"
                      >
                        演示模式
                      </button>
                    </div>

                    {authMode === "login" ? (
                      <div className="auth-mode-panel active">
                        <LoginPanel onSuccess={handleLoginSuccess} onSwitchToRegister={() => setAuthPanel("register")} />
                      </div>
                    ) : null}

                    {authMode === "register" ? (
                      <div className="auth-mode-panel active">
                        <RegisterPanel onSuccess={handleRegisterSuccess} onSwitchToLogin={() => setAuthPanel("login")} />
                      </div>
                    ) : null}

                    {authMode === "demo" ? (
                      <div className="auth-mode-panel active">
                        <div className="auth-panel compact-auth-panel">
                          <div className="tag-row">
                            <span className="tag orange">开发 / 路演入口</span>
                          </div>
                          <h3>演示模式</h3>
                          <p className="field-text">演示模式用于黑客松路演或开发调试，不作为正式用户主路径。</p>
                          {onShowDemo ? (
                            <button className="auth-button primary" onClick={onShowDemo} type="button">
                              进入演示工作台
                            </button>
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </section>
            ) : null}

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
