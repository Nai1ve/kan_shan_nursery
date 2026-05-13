"use client";

import { UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { register } from "@/lib/auth/auth-client";
import type { AuthResponse } from "@/lib/types";

interface RegisterPanelProps {
  onSuccess: (response: AuthResponse) => void;
  onSwitchToLogin: () => void;
}

export function RegisterPanel({ onSuccess, onSwitchToLogin }: RegisterPanelProps) {
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!nickname.trim()) {
      setError("请输入昵称");
      return;
    }
    if (!email.trim()) {
      setError("请输入邮箱，后续登录使用");
      return;
    }
    if (!password || password.length < 6) {
      setError("密码至少需要 6 个字符");
      return;
    }
    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }

    setLoading(true);
    try {
      const response = await register({
        nickname: nickname.trim(),
        email: email.trim(),
        password,
      });
      onSuccess(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败，请重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-panel">
      <div className="auth-card-head">
        <div className="auth-icon-badge"><UserPlus size={18} /></div>
        <div>
          <h3>创建看山账号</h3>
          <p>先建立本地用户，再把知乎授权、LLM 配置和画像绑定到这个用户。</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="auth-form-grid">
          <div className="form-group">
            <label htmlFor="nickname">昵称 *</label>
            <input
              id="nickname"
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="例如 看山编辑"
              disabled={loading}
              autoComplete="name"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">邮箱 *</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com，登录使用"
              disabled={loading}
              autoComplete="email"
            />
          </div>
        </div>

        <div className="auth-form-grid">
          <div className="form-group">
            <label htmlFor="password">密码 *</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 6 个字符"
              disabled={loading}
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">确认密码 *</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="再次输入密码"
              disabled={loading}
              autoComplete="new-password"
            />
          </div>
        </div>

        {error ? <div className="auth-error">{error}</div> : null}

        <button type="submit" className="auth-button primary" disabled={loading}>
          {loading ? "创建中..." : "创建账号，继续关联知乎"}
        </button>
      </form>

      <div className="auth-footer">
        已有账号？<button onClick={onSwitchToLogin} type="button">登录</button>
      </div>
    </div>
  );
}
