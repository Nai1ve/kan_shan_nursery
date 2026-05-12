"use client";

import { ArrowRight, CheckCircle2, Clock3, KeyRound, Link2, Sprout } from "lucide-react";
import type { LlmConfigViewModel, OnboardingResponse } from "@/lib/types";

interface ProfileGenerationPanelProps {
  response: OnboardingResponse;
  zhihuSkipped: boolean;
  llmConfig: LlmConfigViewModel | null;
  onEnterWorkspace: () => void;
  onBackToZhihu: () => void;
  onBackToLlm: () => void;
}

export function ProfileGenerationPanel({
  response,
  zhihuSkipped,
  llmConfig,
  onEnterWorkspace,
  onBackToZhihu,
  onBackToLlm,
}: ProfileGenerationPanelProps) {
  const profile = response.profile;
  const llmLabel = llmConfig?.displayName || "未配置";

  return (
    <div className="auth-panel generation-panel">
      <div className="auth-card-head">
        <div className="auth-icon-badge"><Sprout size={18} /></div>
        <div>
          <h3>临时画像已生成</h3>
          <p>你可以先进入工作台。后续如果 OAuth 可用，增强画像会作为草稿等待你确认。</p>
        </div>
      </div>

      <div className="generation-grid">
        <div className="generation-status-list">
          <div className="generation-status done"><CheckCircle2 size={16} /><span>保存兴趣领域</span></div>
          <div className="generation-status done"><CheckCircle2 size={16} /><span>保存写作风格</span></div>
          <div className="generation-status done"><CheckCircle2 size={16} /><span>生成临时画像</span></div>
          <div className={`generation-status ${zhihuSkipped ? "pending" : "done"}`}>
            {zhihuSkipped ? <Clock3 size={16} /> : <CheckCircle2 size={16} />}
            <span>{zhihuSkipped ? "知乎 OAuth 稍后关联" : "知乎授权状态已记录"}</span>
          </div>
          <div className="generation-status pending"><Clock3 size={16} /><span>OAuth 增强画像后台生成中</span></div>
        </div>

        <div className="profile-preview-card">
          <div className="tag-row"><span className="tag blue">临时画像</span><span className="tag green">可进入工作台</span></div>
          <h4>{profile.nickname}</h4>
          <p>{profile.globalMemory.longTermBackground}</p>
          <div className="mini-profile-row"><strong>兴趣</strong><span>{profile.interests.join(" / ")}</span></div>
          <div className="mini-profile-row"><strong>风格</strong><span>{profile.globalMemory.writingStyle}</span></div>
          <div className="mini-profile-row"><strong>LLM</strong><span>{llmLabel}</span></div>
        </div>
      </div>

      <div className="auth-explain-card blue">
        <KeyRound size={18} />
        <div>
          <strong>LLM 状态：{llmLabel}</strong>
          <span>平台免费额度会被限流；如需更稳定的画像增强和写作生成，可以随时切换到自己的 LLM。</span>
        </div>
      </div>

      <div className="auth-action-grid">
        <button className="auth-button primary" onClick={onEnterWorkspace} type="button">
          进入工作台 <ArrowRight size={16} />
        </button>
        <button className="auth-button secondary" onClick={onBackToZhihu} type="button">
          <Link2 size={16} /> 稍后再试知乎关联
        </button>
        <button className="auth-button link" onClick={onBackToLlm} type="button">
          调整 LLM 设置
        </button>
      </div>
    </div>
  );
}
