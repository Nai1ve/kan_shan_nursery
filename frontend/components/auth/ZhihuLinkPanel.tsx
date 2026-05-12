"use client";

import { AlertCircle, CheckCircle2, Database, ExternalLink, Link2 } from "lucide-react";
import { useState } from "react";
import { getZhihuAuthorizeUrl, getZhihuBinding } from "@/lib/auth/auth-client";
import type { ZhihuBindingStatus } from "@/lib/types";

interface ZhihuLinkPanelProps {
  userId: string;
  onComplete: () => void;
  onSkip: () => void;
}

const dataScopes = [
  ["用户信息", "昵称、头像、简介，用于识别你的公开身份和长期背景。"],
  ["关注列表", "分析你主动关注的作者和话题，提取长期兴趣方向。"],
  ["粉丝列表", "理解潜在读者结构，辅助后续写作风格判断。"],
  ["关注动态", "汇总近期阅读偏好，作为今日输入和画像增强信号。"],
];

export function ZhihuLinkPanel({ userId, onComplete, onSkip }: ZhihuLinkPanelProps) {
  const [bindingStatus, setBindingStatus] = useState<ZhihuBindingStatus>("not_started");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [authorizeUrl, setAuthorizeUrl] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  async function checkBindingStatus() {
    const binding = await getZhihuBinding(userId);
    setBindingStatus(binding.bindingStatus);
    if (binding.bindingStatus === "bound") {
      onComplete();
    }
  }

  async function handleAuthorize() {
    setLoading(true);
    setError("");
    setBindingStatus("authorizing");
    try {
      const { url } = await getZhihuAuthorizeUrl();
      setAuthorizeUrl(url);
      if (url.includes("MOCK") || url.includes("client_id=MOCK")) {
        setBindingStatus("unavailable");
        setError("知乎 OAuth 鉴权暂未开放，当前建议先跳过，用填写内容生成临时画像。");
        return;
      }
      window.open(url, "_blank", "width=640,height=760");
      await checkBindingStatus();
    } catch (err) {
      setBindingStatus("failed");
      setError(err instanceof Error ? err.message : "获取知乎授权链接失败");
    } finally {
      setLoading(false);
    }
  }

  function handleSkip() {
    setBindingStatus("skipped");
    onSkip();
  }

  return (
    <div className="auth-panel zhihu-link-panel">
      <div className="auth-card-head">
        <div className="auth-icon-badge"><Link2 size={18} /></div>
        <div>
          <h3>关联知乎账号</h3>
          <p>授权后会把知乎公开输入汇总成画像信号；不可用时也能先用本地问卷生成临时画像。</p>
        </div>
      </div>

      <div className="auth-explain-card blue">
        <Database size={18} />
        <div>
          <strong>为什么要先关联？</strong>
          <span>OAuth 数据会和本地用户绑定，后续推荐、发芽和写作 Memory 才能追溯到真实兴趣来源。</span>
        </div>
      </div>

      <div className="zhihu-scope-list">
        {dataScopes.map(([title, desc]) => (
          <div className="zhihu-scope-item" key={title}>
            <CheckCircle2 size={15} />
            <div>
              <strong>{title}</strong>
              <span>{desc}</span>
            </div>
          </div>
        ))}
      </div>

      {showDetails ? (
        <div className="auth-detail-box">
          <strong>数据使用边界</strong>
          <p>前端不会接触 app_secret、access_secret 或 OAuth access_token。真实授权完成后，后端只保存必要的授权状态和脱敏后的画像信号。</p>
          <p>公开关注和动态只用于生成可见、可编辑的 Memory，不会替用户自动发布内容。</p>
        </div>
      ) : null}

      {error ? (
        <div className="auth-error inline">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      ) : null}

      {bindingStatus === "bound" ? <div className="auth-success">知乎账号已关联，可以继续配置 LLM。</div> : null}
      {authorizeUrl && bindingStatus !== "bound" ? <p className="auth-muted">授权入口：{authorizeUrl}</p> : null}

      <div className="auth-action-grid">
        <button className="auth-button primary" onClick={handleAuthorize} disabled={loading} type="button">
          <ExternalLink size={16} />
          {loading ? "获取授权中..." : "尝试关联知乎账号"}
        </button>
        <button className="auth-button secondary" onClick={handleSkip} disabled={loading} type="button">
          暂时跳过，先建立本地画像
        </button>
        <button className="auth-button link" onClick={() => setShowDetails((value) => !value)} type="button">
          {showDetails ? "收起数据说明" : "查看将使用哪些数据"}
        </button>
      </div>
    </div>
  );
}
