import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智能知识库 - omni-knowledge",
  description: "企业级智能知识库问答系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
