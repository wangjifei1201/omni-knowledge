"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { useAuthStore, useSidebarStore } from "@/store";
import { cn } from "@/lib/utils";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loadFromStorage } = useAuthStore();
  const { collapsed } = useSidebarStore();
  const router = useRouter();

  useEffect(() => {
    loadFromStorage();
  }, []);

  useEffect(() => {
    // 从存储中加载认证信息后检查
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
    }
  }, [user]);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <Sidebar />
      <main
        className={cn(
          "pt-[var(--header-height)] transition-all duration-300",
          collapsed ? "pl-[60px]" : "pl-[var(--sidebar-width)]"
        )}
      >
        <div className="h-[calc(100vh-var(--header-height))]">{children}</div>
      </main>
    </div>
  );
}
