"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { ZhihuLoginTicketMessage } from "@/lib/types";

function createNonce(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

const OAUTH_TICKET_BRIDGE_KEY = "kanshan:oauth:zhihu:ticket:v1";
const LOCAL_FALLBACK_ORIGIN = "http://127.0.0.1:3000";

function isLocalOrigin(origin: string): boolean {
  return origin.startsWith("http://127.0.0.1:") || origin.startsWith("http://localhost:");
}

function ZhihuOauthSuccessContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("正在通知主页面...");
  const [countdown, setCountdown] = useState<number | null>(null);
  const nonceRef = useRef(createNonce());

  const ticket = searchParams.get("ticket");
  const error = searchParams.get("error");
  const openerOriginParam = searchParams.get("opener_origin");
  const localFallbackDone = searchParams.get("local_fallback") === "1";
  const message = useMemo<ZhihuLoginTicketMessage | null>(() => {
    if (!ticket) return null;
    return {
      type: "zhihu-login-ticket",
      ticket,
      nonce: nonceRef.current,
      ts: Date.now(),
    };
  }, [ticket]);

  useEffect(() => {
    if (error) {
      setStatus(`授权失败: ${error}`);
      return;
    }
    if (!message) {
      setStatus("授权失败: 缺少登录票据");
      return;
    }

    const currentOrigin = window.location.origin;
    if (!isLocalOrigin(currentOrigin) && !localFallbackDone) {
      const next = new URL(`${LOCAL_FALLBACK_ORIGIN}/oauth/zhihu/success`);
      next.searchParams.set("ticket", message.ticket);
      next.searchParams.set("opener_origin", LOCAL_FALLBACK_ORIGIN);
      next.searchParams.set("local_fallback", "1");
      console.info("[oauth][success] redirecting to local fallback", {
        from: currentOrigin,
        to: next.toString(),
      });
      window.location.replace(next.toString());
      return;
    }

    if (window.opener && !window.opener.closed) {
      const targetOrigin = openerOriginParam || window.location.origin;
      console.info("[oauth][success] postMessage start", {
        senderOrigin: window.location.origin,
        targetOrigin,
        hasOpener: true,
        ticketLength: message.ticket.length,
      });
      try {
        for (let i = 0; i < 3; i += 1) {
          window.opener.postMessage(message, targetOrigin);
        }
        localStorage.setItem(OAUTH_TICKET_BRIDGE_KEY, JSON.stringify(message));
        setStatus("授权成功，主页面正在登录。你可以返回主页面或等待自动关闭。");
        setCountdown(12);
        const timer = window.setInterval(() => {
          setCountdown((prev) => {
            if (prev === null) return prev;
            if (prev <= 1) {
              window.clearInterval(timer);
              window.close();
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      } catch {
        setStatus("通知主页面失败，请手动返回主页重试");
      }
      return;
    }

    localStorage.setItem(OAUTH_TICKET_BRIDGE_KEY, JSON.stringify(message));
    console.warn("[oauth][success] opener missing", { origin: window.location.origin });
    setStatus("未检测到主页面窗口，已写入本地票据，请返回主页继续");
  }, [error, message]);

  return (
    <div style={{ padding: "48px", textAlign: "center", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>知乎授权结果</h1>
      <p style={{ fontSize: "16px", color: "#666" }}>{status}</p>
      {countdown !== null ? <p style={{ fontSize: "14px", color: "#999" }}>{countdown} 秒后返回主页</p> : null}
    </div>
  );
}

export default function ZhihuOauthSuccessPage() {
  return (
    <Suspense fallback={<div style={{ padding: "48px", textAlign: "center" }}>加载中...</div>}>
      <ZhihuOauthSuccessContent />
    </Suspense>
  );
}
