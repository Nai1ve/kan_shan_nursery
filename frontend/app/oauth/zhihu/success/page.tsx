"use client";

import { Suspense, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import type { ZhihuLoginTicketMessage } from "@/lib/types";

function createNonce(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

const OAUTH_TICKET_BRIDGE_KEY = "kanshan:oauth:zhihu:ticket:v1";

function ZhihuOauthSuccessContent() {
  const searchParams = useSearchParams();
  const nonceRef = useRef(createNonce());
  const statusRef = useRef<HTMLParagraphElement | null>(null);

  const ticket = searchParams.get("ticket");
  const error = searchParams.get("error");
  const openerOriginParam = searchParams.get("opener_origin");

  useEffect(() => {
    function setStatus(text: string) {
      if (statusRef.current) statusRef.current.textContent = text;
    }

    if (error) {
      setStatus(`授权失败: ${error}`);
      return;
    }
    if (!ticket) {
      setStatus("授权失败: 缺少登录票据");
      return;
    }

    const message: ZhihuLoginTicketMessage = {
      type: "zhihu-login-ticket",
      ticket,
      nonce: nonceRef.current,
      ts: Date.now(),
    };

    if (window.opener && !window.opener.closed) {
      const targetOrigin = openerOriginParam || window.location.origin;
      console.info("[oauth][success] postMessage start", {
        senderOrigin: window.location.origin,
        targetOrigin,
        hasOpener: true,
        ticketLength: message.ticket.length,
      });
      try {
        const sendToOpener = () => {
          if (!window.opener || window.opener.closed) return;
          window.opener.postMessage(message, targetOrigin);
        };

        sendToOpener();
        const messageTimer = window.setInterval(sendToOpener, 120);
        setStatus("授权成功，正在返回主页面...");
        const closeTimer = window.setTimeout(() => {
          window.clearInterval(messageTimer);
          window.close();
        }, 480);

        return () => {
          window.clearInterval(messageTimer);
          window.clearTimeout(closeTimer);
        };
      } catch {
        setStatus("通知主页面失败，请手动返回主页重试");
      }
      return;
    }

    localStorage.setItem(OAUTH_TICKET_BRIDGE_KEY, JSON.stringify(message));
    console.warn("[oauth][success] opener missing", { origin: window.location.origin });
    setStatus("未检测到主页面窗口。若主页面与本页同源，可返回主页继续；不同源时请重新从主页面发起授权。");
  }, [error, openerOriginParam, ticket]);

  return (
    <div style={{ padding: "48px", textAlign: "center", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>知乎授权结果</h1>
      <p ref={statusRef} style={{ fontSize: "16px", color: "#666" }}>正在通知主页面...</p>
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
