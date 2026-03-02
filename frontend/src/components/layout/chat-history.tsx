"use client";

import { useEffect, useState } from "react";
import { Plus, MessageSquare, Trash2, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { useChatStore } from "@/store";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Conversation } from "@/types";

export function ChatHistory() {
  const {
    conversations,
    activeConversationId,
    setConversations,
    setActiveConversation,
    setMessages,
    reset,
  } = useChatStore();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const res = await api.getConversations();
      setConversations(res.items || []);
    } catch {
      // 接口不可用，使用空列表
      setConversations([]);
    }
  };

  const handleNewChat = () => {
    reset();
  };

  const handleSelectConversation = async (conv: Conversation) => {
    setActiveConversation(conv.id);
    try {
      const messages = await api.getConversationMessages(conv.id);
      setMessages(messages || []);
    } catch {
      setMessages([]);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      setConversations(conversations.filter((c) => c.id !== id));
      if (activeConversationId === id) reset();
    } catch {}
  };

  const handleRename = async (id: string) => {
    if (!editTitle.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await api.renameConversation(id, editTitle.trim());
      setConversations(
        conversations.map((c) =>
          c.id === id ? { ...c, title: editTitle.trim() } : c
        )
      );
    } catch {}
    setEditingId(null);
  };

  // 按日期分组对话
  const grouped = groupByDate(conversations);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2 text-sm bg-white/50 hover:bg-white/80 border-black/5"
          onClick={handleNewChat}
        >
          <Plus className="w-4 h-4" />
          新建会话
        </Button>
      </div>
      <ScrollArea className="flex-1 px-3 scrollbar-thin">
        {Object.entries(grouped).map(([label, convs]) => (
          <div key={label} className="mb-3">
            <p className="text-[11px] font-medium text-muted-foreground px-2 mb-1">
              {label}
            </p>
            {convs.map((conv) => (
              <div
                key={conv.id}
                className={cn(
                  "group flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer",
                  "transition-colors duration-150 text-sm",
                  activeConversationId === conv.id
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-black/5 hover:text-foreground"
                )}
                onClick={() => handleSelectConversation(conv)}
              >
                <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                {editingId === conv.id ? (
                  <Input
                    className="h-6 text-xs px-1"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => handleRename(conv.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRename(conv.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span className="truncate flex-1 text-xs">
                    {conv.title}
                  </span>
                )}
                <div className="hidden group-hover:flex items-center gap-0.5 shrink-0">
                  <button
                    className="p-0.5 rounded hover:bg-black/10"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(conv.id);
                      setEditTitle(conv.title);
                    }}
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    className="p-0.5 rounded hover:bg-destructive/10 hover:text-destructive"
                    onClick={(e) => handleDelete(conv.id, e)}
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ))}
      </ScrollArea>
    </div>
  );
}

function groupByDate(
  conversations: Conversation[]
): Record<string, Conversation[]> {
  const groups: Record<string, Conversation[]> = {};
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  for (const conv of conversations) {
    const date = new Date(conv.updated_at);
    let label: string;
    if (date >= today) {
      label = "今天";
    } else if (date >= yesterday) {
      label = "昨天";
    } else if (date >= weekAgo) {
      label = "本周";
    } else {
      label = "更早";
    }
    if (!groups[label]) groups[label] = [];
    groups[label].push(conv);
  }
  return groups;
}
