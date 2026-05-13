import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "看山小苗圃｜读写一体创作 Agent",
  description: "看到好内容，形成好观点，写出好文章。",
  icons: {
    icon: "/images/favicon/favicon-32.png",
    apple: "/images/favicon/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
