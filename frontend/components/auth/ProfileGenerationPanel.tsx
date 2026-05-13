"use client";

import { ArrowRight, CheckCircle2, Clock3, KeyRound, Link2, Loader2, Sprout, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { EnrichmentJob, LlmConfigViewModel, OnboardingResponse } from "@/lib/types";
import { getLatestEnrichmentJob } from "@/lib/api-client";

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

  const [enrichmentJob, setEnrichmentJob] = useState<EnrichmentJob | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // Poll enrichment job status
  const pollEnrichmentJob = useCallback(async () => {
    try {
      const job = await getLatestEnrichmentJob();
      setEnrichmentJob(job);

      // Stop polling if job is completed, failed, or fallback
      if (job.status === "completed" || job.status === "failed" || job.status === "fallback" || job.status === "not_started") {
        setIsPolling(false);
        return false;
      }
      return true; // Continue polling
    } catch (error) {
      console.error("Failed to fetch enrichment job:", error);
      return false;
    }
  }, []);

  // Start polling when component mounts
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    let mounted = true;

    const startPolling = async () => {
      if (!mounted) return;

      const shouldContinue = await pollEnrichmentJob();
      if (shouldContinue && mounted) {
        timeoutId = setTimeout(startPolling, 3000); // Poll every 3 seconds
      }
    };

    // Start polling if we have an enrichment job
    if (response.enrichmentJob) {
      setIsPolling(true);
      startPolling();
    }

    return () => {
      mounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [response.enrichmentJob, pollEnrichmentJob]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 size={16} />;
      case "failed":
        return <XCircle size={16} />;
      case "running":
      case "queued":
        return <Loader2 size={16} className="animate-spin" />;
      default:
        return <Clock3 size={16} />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "completed":
        return "OAuth 增强画像已完成";
      case "failed":
        return "OAuth 增强画像生成失败";
      case "fallback":
        return "OAuth 增强画像使用回退方案";
      case "running":
        return "OAuth 增强画像生成中...";
      case "queued":
        return "OAuth 增强画像排队中";
      default:
        return "OAuth 增强画像后台生成中";
    }
  };

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
          <div className={`generation-status ${enrichmentJob?.status === "completed" ? "done" : enrichmentJob?.status === "failed" ? "error" : "pending"}`}>
            {getStatusIcon(enrichmentJob?.status || "not_started")}
            <span>{getStatusLabel(enrichmentJob?.status || "not_started")}</span>
          </div>
        </div>

        <div className="profile-preview-card">
          <div className="tag-row">
            <span className="tag blue">临时画像</span>
            <span className="tag green">可进入工作台</span>
            {enrichmentJob?.status === "completed" && <span className="tag purple">增强画像待确认</span>}
          </div>
          <h4>{profile.nickname}</h4>
          <p>{profile.globalMemory.longTermBackground}</p>
          <div className="mini-profile-row"><strong>兴趣</strong><span>{profile.interests.join(" / ")}</span></div>
          <div className="mini-profile-row"><strong>风格</strong><span>{profile.globalMemory.writingStyle}</span></div>
          <div className="mini-profile-row"><strong>LLM</strong><span>{llmLabel}</span></div>
          {enrichmentJob?.signalCounts && Object.keys(enrichmentJob.signalCounts).length > 0 && (
            <div className="mini-profile-row">
              <strong>信号</strong>
              <span>
                {Object.entries(enrichmentJob.signalCounts)
                  .map(([key, count]) => `${key}: ${count}`)
                  .join(" / ")}
              </span>
            </div>
          )}
          {enrichmentJob?.memoryUpdateRequestIds && enrichmentJob.memoryUpdateRequestIds.length > 0 && (
            <div className="mini-profile-row">
              <strong>待确认</strong>
              <span>{enrichmentJob.memoryUpdateRequestIds.length} 条记忆更新建议</span>
            </div>
          )}
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
