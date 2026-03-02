"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  FileText,
  BarChart3,
  Users,
  Settings,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuthStore, useSidebarStore } from "@/store";
import { cn } from "@/lib/utils";
import { ChatHistory } from "./chat-history";

const navItems = [
  { href: "/chat", label: "智能问答", icon: MessageSquare },
  { href: "/documents", label: "文档管理", icon: FileText },
  { href: "/statistics", label: "使用统计", icon: BarChart3 },
];

const adminItems = [
  { href: "/users", label: "用户管理", icon: Users },
  { href: "/settings", label: "系统设置", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const { collapsed, toggle } = useSidebarStore();
  const isAdmin = user?.role === "admin";

  return (
    <aside
      className={cn(
        "fixed left-0 top-[var(--header-height)] bottom-0 z-30",
        "sidebar-glass border-r border-white/20",
        "transition-all duration-300 ease-in-out",
        collapsed ? "w-[60px]" : "w-[var(--sidebar-width)]"
      )}
    >
      <div className="flex flex-col h-full">
        {/* 导航菜单 */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href}>
                <div
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium",
                    "transition-all duration-200",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-black/5 hover:text-foreground"
                  )}
                >
                  <item.icon className="w-[18px] h-[18px] shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </div>
              </Link>
            );
          })}

          {isAdmin && (
            <>
              <Separator className="my-2 bg-black/5" />
              {adminItems.map((item) => {
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link key={item.href} href={item.href}>
                    <div
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium",
                        "transition-all duration-200",
                        isActive
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-black/5 hover:text-foreground"
                      )}
                    >
                      <item.icon className="w-[18px] h-[18px] shrink-0" />
                      {!collapsed && <span>{item.label}</span>}
                    </div>
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* 对话历史 - 仅在对话页面且侧栏展开时显示 */}
        {!collapsed && pathname.startsWith("/chat") && (
          <>
            <Separator className="bg-black/5" />
            <div className="flex-1 overflow-hidden">
              <ChatHistory />
            </div>
          </>
        )}

        {/* 折叠切换 */}
        <div className="p-3 border-t border-white/10">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggle}
            className="w-full justify-center text-muted-foreground hover:text-foreground"
          >
            {collapsed ? (
              <PanelLeft className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </aside>
  );
}
