import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Next.js 15+ blocks cross-origin requests to dev resources (HMR, /_next/*)
  // unless the origin is explicitly allowed. dev_up.sh starts the backend on
  // 127.0.0.1 and the frontend on the same host, but the browser still sees
  // 127.0.0.1:3000 vs localhost:3000 as different origins. Allow both so
  // either URL works for the operator.
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "curve-bytes-weed-delivering.trycloudflare.com",
    "leading-compare-yields-grove.trycloudflare.com",
  ],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.KANSHAN_GATEWAY_URL || "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
