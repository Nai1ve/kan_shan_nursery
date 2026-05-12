"use client";

import { CheckCircle2, KeyRound, ShieldCheck, Zap } from "lucide-react";
import { useMemo, useState } from "react";
import type { LlmConfigViewModel } from "@/lib/types";

interface LlmConfigPanelProps {
  onComplete: (config: LlmConfigViewModel) => void;
}

type LlmChoice = "platform_free" | "user_provider" | "not_configured";

const quotaRows = [
  ["画像生成", 1, 3],
  ["内容摘要", 12, 50],
  ["疑问回答", 4, 20],
  ["写作草稿", 0, 5],
];

function maskKey(key: string) {
  if (!key) return undefined;
  if (key.length <= 8) return "****";
  return `${key.slice(0, 4)}...${key.slice(-4)}`;
}

export function LlmConfigPanel({ onComplete }: LlmConfigPanelProps) {
  const [choice, setChoice] = useState<LlmChoice>("platform_free");
  const [displayName, setDisplayName] = useState("OpenAI Compatible");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [model, setModel] = useState("gpt-4o-mini");
  const [apiKey, setApiKey] = useState("");
  const [tested, setTested] = useState(false);
  const [error, setError] = useState("");

  const platformQuota = useMemo(
    () => ({
      profileSignalSummarize: { used: 1, limit: 3, remaining: 2 },
      profileMemorySynthesize: { used: 1, limit: 3, remaining: 2 },
      profileRiskReview: { used: 0, limit: 3, remaining: 3 },
      summarizeContent: { used: 12, limit: 50, remaining: 38 },
      answerSeedQuestion: { used: 4, limit: 20, remaining: 16 },
      supplementMaterial: { used: 0, limit: 15, remaining: 15 },
      argumentBlueprint: { used: 0, limit: 8, remaining: 8 },
      draft: { used: 0, limit: 5, remaining: 5 },
      roundtableReview: { used: 0, limit: 5, remaining: 5 },
    }),
    [],
  );

  function testUserProvider() {
    setError("");
    if (!baseUrl.trim() || !model.trim() || !apiKey.trim()) {
      setError("请填写 Base URL、模型名和 API Key 后再测试连接");
      return;
    }
    setTested(true);
  }

  function submit() {
    setError("");
    if (choice === "user_provider" && !tested) {
      setError("请先测试连接，或选择平台免费额度 / 稍后配置");
      return;
    }

    if (choice === "platform_free") {
      onComplete({
        status: "platform_free",
        activeProvider: "platform_free",
        displayName: "平台免费额度",
        model: "知乎直答 / 平台托管模型",
        quota: platformQuota,
      });
      return;
    }

    if (choice === "user_provider") {
      onComplete({
        status: "user_configured",
        activeProvider: "user_provider",
        displayName,
        maskedKey: maskKey(apiKey),
        model,
      });
      return;
    }

    onComplete({ status: "not_configured", activeProvider: "none", displayName: "稍后配置" });
  }

  return (
    <div className="auth-panel llm-panel">
      <div className="auth-card-head">
        <div className="auth-icon-badge"><KeyRound size={18} /></div>
        <div>
          <h3>选择 LLM 使用方式</h3>
          <p>系统可以使用平台免费额度，但额度有限；也可以接入你自己的 OpenAI-compatible 服务。</p>
        </div>
      </div>

      <div className="llm-choice-grid">
        <button className={`llm-choice ${choice === "platform_free" ? "selected" : ""}`} onClick={() => setChoice("platform_free")} type="button">
          <Zap size={18} />
          <strong>平台免费额度</strong>
          <span>零配置，适合试用和黑客松演示。</span>
        </button>
        <button className={`llm-choice ${choice === "user_provider" ? "selected" : ""}`} onClick={() => setChoice("user_provider")} type="button">
          <ShieldCheck size={18} />
          <strong>配置自己的 LLM</strong>
          <span>API Key 只提交给后端，前端不保存明文。</span>
        </button>
        <button className={`llm-choice ${choice === "not_configured" ? "selected" : ""}`} onClick={() => setChoice("not_configured")} type="button">
          <KeyRound size={18} />
          <strong>稍后配置</strong>
          <span>先完成画像，使用非 LLM 或 mock 能力。</span>
        </button>
      </div>

      {choice === "platform_free" ? (
        <div className="quota-board">
          {quotaRows.map(([label, used, limit]) => (
            <div className="quota-row" key={label}>
              <span>{label}</span>
              <strong>{used}/{limit}</strong>
              <div className="quota-bar"><i style={{ width: `${(Number(used) / Number(limit)) * 100}%` }} /></div>
            </div>
          ))}
        </div>
      ) : null}

      {choice === "user_provider" ? (
        <div className="llm-config-form">
          <div className="auth-form-grid">
            <div className="form-group">
              <label>显示名称</label>
              <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="例如 OpenAI / DeepSeek" />
            </div>
            <div className="form-group">
              <label>模型</label>
              <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="例如 gpt-4o-mini" />
            </div>
          </div>
          <div className="form-group">
            <label>Base URL</label>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" />
          </div>
          <div className="form-group">
            <label>API Key</label>
            <input type="password" value={apiKey} onChange={(e) => { setApiKey(e.target.value); setTested(false); }} placeholder="只用于提交给后端，前端不写入 localStorage" />
          </div>
          <button className="auth-button secondary" onClick={testUserProvider} type="button">
            测试连接
          </button>
          {tested ? <div className="auth-success"><CheckCircle2 size={15} /> mock 测试通过，实际联调时由后端验证。</div> : null}
        </div>
      ) : null}

      {choice === "not_configured" ? (
        <div className="auth-explain-card orange">
          <KeyRound size={18} />
          <div>
            <strong>稍后配置的影响</strong>
            <span>需要 LLM 的摘要、问答、发芽和写作功能会提示补配置或使用平台免费额度。</span>
          </div>
        </div>
      ) : null}

      {error ? <div className="auth-error">{error}</div> : null}

      <div className="auth-action-grid single">
        <button className="auth-button primary" onClick={submit} type="button">保存 LLM 设置，继续画像采集</button>
      </div>
    </div>
  );
}
