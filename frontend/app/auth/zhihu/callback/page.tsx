"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { handleZhihuCallback } from "@/lib/auth/auth-client";

export default function ZhihuCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState("处理中...");

  useEffect(() => {
    const code = searchParams.get("code");
    const error = searchParams.get("error");

    if (error) {
      setStatus(`授权失败: ${error}`);
      return;
    }

    if (!code) {
      setStatus("缺少授权码");
      return;
    }

    handleZhihuCallback(code)
      .then(() => {
        setStatus("授权成功！正在跳转...");
        setTimeout(() => router.push("/"), 2000);
      })
      .catch((err) => {
        setStatus(`授权失败: ${err.message}`);
      });
  }, [searchParams, router]);

  return (
    <div style={{ padding: "48px", textAlign: "center", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>知乎授权</h1>
      <p style={{ fontSize: "16px", color: "#666" }}>{status}</p>
      {status.includes("失败") && (
        <button
          onClick={() => router.push("/")}
          style={{
            marginTop: "24px",
            padding: "8px 16px",
            fontSize: "14px",
            cursor: "pointer",
            border: "1px solid #ccc",
            borderRadius: "4px",
            background: "#fff",
          }}
        >
          返回首页
        </button>
      )}
    </div>
  );
}
