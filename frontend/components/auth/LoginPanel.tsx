"use client";

import { LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";
import { login } from "@/lib/auth/auth-client";
import type { AuthResponse } from "@/lib/types";

interface LoginPanelProps {
  onSuccess: (response: AuthResponse) => void;
  onSwitchToRegister: () => void;
}

export function LoginPanel({ onSuccess, onSwitchToRegister }: LoginPanelProps) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!identifier.trim()) {
      setError("请输入用户名或邮箱");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }

    setLoading(true);
    try {
      const response = await login({ identifier: identifier.trim(), password });
      onSuccess(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败，请重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-panel">
      <div className="auth-card-head">
        <div className="auth-icon-badge"><LogIn size={18} /></div>
        <div>
          <h3>登录账号</h3>
          <p>继续使用你的画像 Memory、观点种子和写作记录。</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="identifier">用户名或邮箱</label>
          <input
            id="identifier"
            type="text"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="例如 liupeize 或 you@example.com"
            disabled={loading}
            autoComplete="username"
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">密码</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="输入密码"
            disabled={loading}
            autoComplete="current-password"
          />
        </div>

        {error ? <div className="auth-error">{error}</div> : null}

        <button type="submit" className="auth-button primary" disabled={loading}>
          {loading ? "登录中..." : "登录并继续"}
        </button>
      </form>

      <div className="auth-footer">
        还没有账号？<button onClick={onSwitchToRegister} type="button">创建新账号</button>
      </div>
    </div>
  );
}
