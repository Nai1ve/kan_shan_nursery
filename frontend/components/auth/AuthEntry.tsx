"use client";

import {
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { exchangeZhihuTicket, getMe, getZhihuBinding, setSession } from "@/lib/auth/auth-client";

const OAUTH_TICKET_BRIDGE_KEY = "kanshan:oauth:zhihu:ticket:v1";
import type {
  AuthResponse,
  AuthStatus,
  LlmConfigViewModel,
  OnboardingResponse,
  ProfileData,
  UserSetupState,
  ZhihuLoginTicketMessage,
} from "@/lib/types";
import { ZhihuLinkPanel } from "./ZhihuLinkPanel";
import { LlmConfigPanel } from "./LlmConfigPanel";
import { PreferenceOnboardingPanel } from "./PreferenceOnboardingPanel";
import { ProfileGenerationPanel } from "./ProfileGenerationPanel";

type AuthStep = "loading" | "zhihu" | "llm" | "preferences" | "generating";
type ProgressStepId = "zhihu" | "llm" | "interest" | "style" | "generation";

interface AuthEntryProps {
  onComplete: (profile?: ProfileData) => void;
  onShowDemo?: () => void;
}

const setupSteps: { id: ProgressStepId; label: string; desc: string }[] = [
  { id: "zhihu", label: "知乎授权", desc: "OAuth 绑定身份" },
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
        const binding = await getZhihuBinding(me.user.userId).catch(() => null);
        if (binding?.bindingStatus === "bound") {
          if (me.setupState === "ready" || me.setupState === "provisional_ready") {
            onComplete();
            return;
          }
          setSetupState(me.setupState || "llm_pending");
          navigateToStep(me.setupState || "llm_pending");
          return;
        }
        setSetupState("zhihu_pending");
        setStep("zhihu");
        return;
      }
    } catch {
      // ignore
    }

    setAuthStatus("guest");
    setStep("zhihu");
  }, [navigateToStep, onComplete]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void checkAuthStatus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [checkAuthStatus]);

  useEffect(() => {
    const consumed = new Set<string>();
    const consumePayload = (payload: Partial<ZhihuLoginTicketMessage> | undefined, source: "message" | "storage") => {
      if (payload?.type !== "zhihu-login-ticket") return;
      const ticket = payload.ticket;
      const nonce = payload.nonce;
      const ts = payload.ts;
      if (!ticket || !nonce || typeof ts !== "number") {
        console.warn(`[oauth][auth-entry] reject ${source}: payload invalid`, payload);
        return;
      }
      if (Date.now() - ts > 5 * 60 * 1000) {
        console.warn(`[oauth][auth-entry] reject ${source}: expired`, { ageMs: Date.now() - ts });
        return;
      }
      const dedupeKey = `${nonce}:${ticket}`;
      if (consumed.has(dedupeKey)) return;
      consumed.add(dedupeKey);

      void (async () => {
        try {
          const exchanged = await exchangeZhihuTicket(ticket);
          setSession(exchanged.session.sessionId);
          localStorage.removeItem(OAUTH_TICKET_BRIDGE_KEY);
          setUser(exchanged.user);
          setAuthStatus("authenticated");
          const nextState = exchanged.setupState || "llm_pending";
          setSetupState(nextState);
          if (nextState === "ready" || nextState === "provisional_ready") {
            onComplete();
          } else {
            navigateToStep(nextState);
          }
          console.info(`[oauth][auth-entry] exchange success via ${source}, setupState=${nextState}`);
        } catch (error) {
          console.error(`[oauth][auth-entry] exchange failed via ${source}`, error);
        }
      })();
    };

    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) {
        console.warn("[oauth][auth-entry] reject message: origin mismatch", {
          eventOrigin: event.origin,
          currentOrigin: window.location.origin,
        });
        return;
      }
      consumePayload(event.data as Partial<ZhihuLoginTicketMessage> | undefined, "message");
    };

    const onStorageTick = () => {
      const raw = localStorage.getItem(OAUTH_TICKET_BRIDGE_KEY);
      if (!raw) return;
      try {
        const parsed = JSON.parse(raw) as Partial<ZhihuLoginTicketMessage>;
        consumePayload(parsed, "storage");
      } catch {
        localStorage.removeItem(OAUTH_TICKET_BRIDGE_KEY);
      }
    };

    const storageTimer = window.setInterval(onStorageTick, 600);
    onStorageTick();
    window.addEventListener("message", onMessage);
    return () => {
      window.clearInterval(storageTimer);
      window.removeEventListener("message", onMessage);
    };
  }, [checkAuthStatus, navigateToStep, onComplete]);


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
            : "zhihu";
  const activeIndex = Math.max(0, setupSteps.findIndex((item) => item.id === progressStep));
  const stepTitle =
    progressStep === "zhihu"
      ? "知乎 OAuth 授权"
      : progressStep === "llm"
        ? "配置 LLM 使用方式"
          : progressStep === "interest"
            ? "选择兴趣领域"
            : progressStep === "style"
              ? "建立创作画像"
              : "临时画像已生成";
  const stepDesc =
    progressStep === "zhihu"
      ? "系统将直接使用知乎 OAuth 返回的用户信息作为本地身份。"
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
            {step === "zhihu" ? (
              <section className="auth-step-panel active">
                <ZhihuLinkPanel userId={user?.userId} onComplete={handleZhihuComplete} onSkip={handleZhihuSkip} />
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
