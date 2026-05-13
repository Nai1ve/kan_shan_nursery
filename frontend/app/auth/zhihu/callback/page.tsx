"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { getSession } from "@/lib/auth/auth-client";

function ZhihuCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState("处理中...");
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const code = searchParams.get("authorization_code") || searchParams.get("code");
    const error = searchParams.get("error");
    const stateSessionId = searchParams.get("state");
    const localSessionId = getSession();
    const sessionId = stateSessionId || localSessionId;

    if (error) {
      router.replace(`/oauth/zhihu/success?error=${encodeURIComponent(error)}`);
      return;
    }

    if (!code) {
      router.replace("/oauth/zhihu/success?error=code_missing");
      return;
    }

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (sessionId) headers["x-session-id"] = sessionId;

    const callbackParams = new URLSearchParams({ code });
    if (sessionId) callbackParams.set("session_id", sessionId);

    const callbackUrl = `/api/v1/auth/zhihu/callback?${callbackParams.toString()}`;
    console.info("[oauth][callback] request", {
      callbackUrl,
      origin: window.location.origin,
      host: window.location.host,
      hasSessionHeader: Boolean(sessionId),
    });

    fetch(callbackUrl, { method: "GET", headers })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}));
        console.info("[oauth][callback] response", {
          status: res.status,
          ok: res.ok,
          hasData: Boolean(body?.data),
          hasTicketInData: Boolean(body?.data?.ticket),
          hasTicketAtRoot: Boolean(body?.ticket),
        });
        if (!res.ok) {
          const message =
            body.error?.detail?.downstreamDetail?.message ||
            body.error?.detail?.message ||
            body.detail?.downstreamDetail?.message ||
            body.detail?.message ||
            body.error?.message ||
            `HTTP ${res.status}`;
          throw new Error(message);
        }
        return body;
      })
      .then((body) => {
        const ticket = body?.data?.ticket;
        if (!ticket || typeof ticket !== "string") {
          throw new Error("missing login ticket in response.data.ticket");
        }
        setStatus("授权成功，正在返回主页面...");
        const openerOrigin = encodeURIComponent(window.location.origin);
        router.replace(`/oauth/zhihu/success?ticket=${encodeURIComponent(ticket)}&opener_origin=${openerOrigin}`);
      })
      .catch((err: Error) => {
        console.error("[oauth][callback] failed", { message: err.message });
        setStatus(`授权失败: ${err.message}`);
        router.replace(`/oauth/zhihu/success?error=${encodeURIComponent(err.message)}`);
      });
  }, [searchParams, router]);

  return (
    <div style={{ padding: "48px", textAlign: "center", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>知乎授权</h1>
      <p style={{ fontSize: "16px", color: "#666" }}>{status}</p>
    </div>
  );
}

export default function ZhihuCallbackPage() {
  return (
    <Suspense fallback={<div style={{ padding: "48px", textAlign: "center" }}>加载中...</div>}>
      <ZhihuCallbackContent />
    </Suspense>
  );
}
