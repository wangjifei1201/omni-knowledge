"use client";

import { useState, useRef, useEffect, useCallback, ReactNode } from "react";
import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Send,
  ThumbsUp,
  ThumbsDown,
  FileText,
  Copy,
  Search,
  SlidersHorizontal,
  Sparkles,
  ExternalLink,
  PanelRight,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatStore, useAuthStore } from "@/store";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatMessage, Citation } from "@/types";
import { DocumentViewer } from "@/components/chat/document-viewer";

/**
 * Creates a custom ReactMarkdown components config that makes [引用N] markers clickable
 */
function createCitationComponents(
  citations: Citation[] | undefined | null,
  onCitationClick: (c: Citation) => void
): Components {
  return {
    // Override paragraph to handle inline citations
    p: ({ children }) => {
      return <p>{processChildren(children, citations, onCitationClick)}</p>;
    },
    // Override list items
    li: ({ children }) => {
      return <li>{processChildren(children, citations, onCitationClick)}</li>;
    },
  };
}

/**
 * Process children nodes, replacing [引用N] text with clickable buttons
 */
function processChildren(
  children: ReactNode,
  citations: Citation[] | undefined | null,
  onCitationClick: (c: Citation) => void
): ReactNode {
  if (!citations || citations.length === 0) return children;

  // Convert children to array for processing
  const childArray = Array.isArray(children) ? children : [children];

  return childArray.map((child, idx) => {
    if (typeof child === "string") {
      return processTextWithCitations(child, citations, onCitationClick, idx);
    }
    return child;
  });
}

/**
 * Process a text string, replacing [引用N] patterns with clickable buttons
 */
function processTextWithCitations(
  text: string,
  citations: Citation[],
  onCitationClick: (c: Citation) => void,
  keyPrefix: number
): ReactNode {
  const pattern = /(\[引用(\d+)\])/g;
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    // Add clickable citation button
    const citationNum = parseInt(match[2], 10);
    const citationIndex = citationNum - 1; // Convert to 0-based index
    const citation = citations[citationIndex];

    if (citation) {
      parts.push(
        <button
          key={`${keyPrefix}-cite-${citationNum}`}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onCitationClick(citation);
          }}
          className="inline-flex items-center text-primary hover:bg-primary/10 px-0.5 rounded cursor-pointer underline underline-offset-2 decoration-primary/50 hover:decoration-primary font-medium"
          title={`查看引用 ${citationNum}: ${citation.doc_name}`}
        >
          {match[1]}
        </button>
      );
    } else {
      // Citation index out of range, render as plain text
      parts.push(match[1]);
    }

    lastIndex = pattern.lastIndex;
  }

  // Add remaining text after last match
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  // If no matches found, return original text
  if (parts.length === 0) {
    return text;
  }

  return parts;
}

export default function ChatPage() {
  const {
    activeConversationId,
    messages,
    isLoading,
    setActiveConversation,
    addMessage,
    setLoading,
    setConversations,
  } = useChatStore();
  const { user } = useAuthStore();
  const [input, setInput] = useState("");
  const [searchMode, setSearchMode] = useState<"hybrid" | "semantic" | "keyword">("hybrid");
  const [detailLevel, setDetailLevel] = useState<"brief" | "normal" | "detailed">("normal");
  const [showSettings, setShowSettings] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 右侧面板状态
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(true);
  const [rightPanelWidth, setRightPanelWidth] = useState(380);
  const [isDraggingRight, setIsDraggingRight] = useState(false);

  // 文档查看器弹出框状态
  const [docViewerOpen, setDocViewerOpen] = useState(false);
  const [viewingDoc, setViewingDoc] = useState<{ id: string; name: string } | null>(null);
  const [viewingHighlightText, setViewingHighlightText] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  // 右侧面板拖拽调整大小
  useEffect(() => {
    if (!isDraggingRight) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX;
      setRightPanelWidth(Math.max(280, Math.min(600, newWidth)));
    };

    const handleMouseUp = () => setIsDraggingRight(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDraggingRight]);

  const handleViewInDocument = useCallback((citation: Citation) => {
    if (!citation.doc_id) return;
    setViewingDoc({
      id: citation.doc_id,
      name: citation.doc_name,
    });
    setViewingHighlightText(citation.original_text);
    setDocViewerOpen(true);
  }, []);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput("");
    setLoading(true);
    setStreamingContent("");
    setStreamingCitations([]);

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: question,
      confidence: 0,
      feedback: null,
      created_at: new Date().toISOString(),
    };
    addMessage(userMsg);

    let fullContent = "";
    let citations: Citation[] = [];

    try {
      await api.sendMessageStream(
        {
          conversation_id: activeConversationId || undefined,
          question,
          search_mode: searchMode,
          doc_scope: [],
          detail_level: detailLevel,
        },
        {
          onStatus: (status) => {
            setStreamingContent(status + "\n\n");
          },
          onToken: (token) => {
            fullContent += token;
            setStreamingContent(fullContent);
          },
          onCitations: (cits) => {
            citations = cits.map((c: any) => ({
              doc_id: c.doc_id || "",
              doc_name: c.doc_name || "",
              chapter: c.chapter || "",
              section: c.section || "",
              page: c.page || 0,
              original_text: c.original_text || "",
              confidence: c.confidence || 0,
              chunk_id: c.chunk_id || "",
            }));
            setStreamingCitations(citations);
          },
          onDone: async (data) => {
            if (!activeConversationId && data.conversation_id) {
              setActiveConversation(data.conversation_id);
              try {
                const convRes = await api.getConversations();
                setConversations(convRes.items || []);
              } catch {}
            }

            const assistantMsg: ChatMessage = {
              id: `msg-${Date.now()}`,
              role: "assistant",
              content: fullContent,
              citations: citations,
              confidence: 0.85,
              feedback: null,
              created_at: new Date().toISOString(),
            };
            addMessage(assistantMsg);
            setStreamingContent("");
            setStreamingCitations([]);
            setLoading(false);
          },
          onError: (error) => {
            addMessage({
              id: `error-${Date.now()}`,
              role: "assistant",
              content: `抱歉，发生了错误：${error}`,
              confidence: 0,
              feedback: null,
              created_at: new Date().toISOString(),
            });
            setStreamingContent("");
            setLoading(false);
          },
        }
      );
    } catch (err: any) {
      addMessage({
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `抱歉，发生了错误：${err.message}`,
        confidence: 0,
        feedback: null,
        created_at: new Date().toISOString(),
      });
      setStreamingContent("");
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFeedback = async (messageId: string, feedback: "like" | "dislike") => {
    try {
      await api.submitFeedback(messageId, feedback);
    } catch {}
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="flex h-full overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100/50">
      {/* 左侧栏 - 固定窄边栏 */}
      <div className="flex-shrink-0 w-10 bg-white/50 border-r border-black/5 flex flex-col items-center py-3">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-primary" />
        </div>
        <div className="mt-3 [writing-mode:vertical-rl] text-[10px] text-muted-foreground">
          知识问答
        </div>
      </div>

      {/* 中部 - 对话区 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 消息列表 */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
          {messages.length === 0 ? (
            <WelcomeScreen onSuggestionClick={(q) => setInput(q)} />
          ) : (
            <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  user={user}
                  onFeedback={handleFeedback}
                  onCopy={copyToClipboard}
                  onCitationClick={(c) => {
                    setSelectedCitation(c);
                    setRightPanelCollapsed(false);
                  }}
                  onViewInDocument={handleViewInDocument}
                />
              ))}
              {/* 流式消息 */}
              {isLoading && streamingContent && (
                <div className="flex gap-3 animate-fade-in">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Sparkles className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 max-w-[80%]">
                    <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed bg-white/80 border border-black/5 rounded-tl-md shadow-sm">
                      <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-p:my-2 prose-ul:my-2 prose-ol:my-2">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={createCitationComponents(streamingCitations, (c) => {
                            setSelectedCitation(c);
                            setRightPanelCollapsed(false);
                          })}
                        >
                          {streamingContent}
                        </ReactMarkdown>
                      </div>
                      <span className="inline-block w-2 h-4 bg-primary/60 animate-pulse ml-0.5" />
                    </div>
                    {streamingCitations.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <p className="text-[11px] text-muted-foreground font-medium">参考来源</p>
                        <div className="flex flex-wrap gap-1.5">
                          {streamingCitations.map((c, i) => (
                            <button
                              key={i}
                              onClick={() => {
                                setSelectedCitation(c);
                                setRightPanelCollapsed(false);
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-primary/5 hover:bg-primary/10 border border-primary/10 text-xs text-primary transition-colors"
                            >
                              <FileText className="w-3 h-3" />
                              {c.doc_name}
                              <Badge variant="secondary" className="text-[9px] h-4 px-1 ml-1">
                                {(c.confidence * 100).toFixed(0)}%
                              </Badge>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {isLoading && !streamingContent && (
                <div className="flex gap-3 animate-fade-in">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Sparkles className="w-4 h-4 text-primary" />
                  </div>
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="border-t border-black/5 bg-white/40 backdrop-blur-sm p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center gap-2 mb-2">
              <Popover open={showSettings} onOpenChange={setShowSettings}>
                <PopoverTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-muted-foreground"
                  >
                    <SlidersHorizontal className="w-3.5 h-3.5 mr-1" />
                    高级选项
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-64" align="start">
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-medium mb-1 block">搜索模式</label>
                      <Select value={searchMode} onValueChange={(v: any) => setSearchMode(v)}>
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="hybrid">混合搜索</SelectItem>
                          <SelectItem value="semantic">语义搜索</SelectItem>
                          <SelectItem value="keyword">关键词搜索</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <label className="text-xs font-medium mb-1 block">详细程度</label>
                      <Select value={detailLevel} onValueChange={(v: any) => setDetailLevel(v)}>
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="brief">简要</SelectItem>
                          <SelectItem value="normal">普通</SelectItem>
                          <SelectItem value="detailed">详细</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
              <Badge variant="secondary" className="text-[10px] h-5">
                {searchMode === "hybrid" ? "混合" : searchMode === "semantic" ? "语义" : "关键词"}
              </Badge>
            </div>
            <div className="flex items-end gap-2 bg-white/70 rounded-xl border border-black/10 p-2 shadow-sm focus-within:border-primary/30 focus-within:ring-2 focus-within:ring-primary/10 transition-all">
              <Textarea
                ref={inputRef}
                placeholder="输入问题...（Shift+Enter 换行）"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="min-h-[40px] max-h-[160px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-sm p-1"
                rows={1}
              />
              <Button
                size="icon"
                className="shrink-0 h-9 w-9 rounded-lg"
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧拖拽手柄 */}
      {!rightPanelCollapsed && (
        <div
          className={cn(
            "w-1 cursor-col-resize hover:bg-primary/30 transition-colors flex-shrink-0",
            isDraggingRight && "bg-primary/50"
          )}
          onMouseDown={() => setIsDraggingRight(true)}
        />
      )}

      {/* 右侧面板 - 引用详情 */}
      {!rightPanelCollapsed && selectedCitation && (
        <div
          className="flex-shrink-0 bg-white/80 backdrop-blur-sm animate-slide-in"
          style={{ width: rightPanelWidth }}
        >
          <div className="h-full flex flex-col">
            <div className="p-4 border-b border-black/5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">引用详情</h3>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => setRightPanelCollapsed(true)}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">来源文档</p>
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium">{selectedCitation.doc_name}</span>
                  </div>
                </div>
                <Separator />
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-muted-foreground">章节</p>
                    <p className="text-sm">{selectedCitation.chapter || "-"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">小节</p>
                    <p className="text-sm">{selectedCitation.section || "-"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">页码</p>
                    <p className="text-sm">{selectedCitation.page > 0 ? `第 ${selectedCitation.page} 页` : "-"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">置信度</p>
                    <p className="text-sm">{(selectedCitation.confidence * 100).toFixed(0)}%</p>
                  </div>
                </div>
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground mb-2">原文内容</p>
                  <div className="bg-primary/5 border border-primary/10 rounded-lg p-3">
                    <p className="text-sm leading-relaxed">{selectedCitation.original_text}</p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full gap-2"
                  onClick={() => handleViewInDocument(selectedCitation)}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  在文档中查看
                </Button>
              </div>
            </ScrollArea>
          </div>
        </div>
      )}

      {/* 右侧折叠面板切换 */}
      {rightPanelCollapsed && (
        <div className="flex-shrink-0 w-10 bg-white/50 border-l border-black/5 flex flex-col items-center py-3">
          <Button
            variant="ghost"
            size="sm"
            className="w-8 h-8 p-0"
            onClick={() => setRightPanelCollapsed(false)}
            disabled={!selectedCitation}
          >
            <PanelRight className="w-4 h-4" />
          </Button>
          <div className="mt-3 [writing-mode:vertical-lr] rotate-180 text-[10px] text-muted-foreground">
            引用
          </div>
        </div>
      )}

      {/* 文档查看弹出框 */}
      <Dialog open={docViewerOpen} onOpenChange={setDocViewerOpen}>
        <DialogContent className="max-w-4xl w-[90vw] h-[80vh] p-0 gap-0 overflow-hidden [&>button:last-child]:hidden">
          <DialogTitle className="sr-only">
            {viewingDoc?.name || "文档预览"}
          </DialogTitle>
          <DocumentViewer
            docId={viewingDoc?.id}
            docName={viewingDoc?.name}
            highlightText={viewingHighlightText}
            onClose={() => setDocViewerOpen(false)}
            mode="dialog"
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}

function WelcomeScreen({ onSuggestionClick }: { onSuggestionClick: (q: string) => void }) {
  const suggestions = [
    "火灾应急处置流程是什么？",
    "公司安全管理制度有哪些？",
    "迟到的考勤政策是什么？",
    "公司有多少应急预案？",
  ];
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-md animate-fade-in">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
          <Sparkles className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-xl font-semibold mb-2">知识库智能问答</h2>
        <p className="text-sm text-muted-foreground mb-6">
          AI 驱动的文档检索与引用追踪
        </p>
        <div className="space-y-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSuggestionClick(s)}
              className="w-full text-left px-4 py-3 rounded-xl bg-white/60 hover:bg-white/90 border border-black/5 text-sm transition-colors"
            >
              <Search className="w-3.5 h-3.5 inline mr-2 text-muted-foreground" />
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  user,
  onFeedback,
  onCopy,
  onCitationClick,
  onViewInDocument: _onViewInDocument,
}: {
  message: ChatMessage;
  user: any;
  onFeedback: (id: string, fb: "like" | "dislike") => void;
  onCopy: (text: string) => void;
  onCitationClick: (c: Citation) => void;
  onViewInDocument: (c: Citation) => void;
}) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3 animate-fade-in", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-medium",
          isUser ? "bg-primary text-white" : "bg-primary/10 text-primary"
        )}
      >
        {isUser ? (
          user?.display_name?.slice(0, 1) || "U"
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
      </div>

      <div className={cn("flex-1 max-w-[80%]", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-white rounded-tr-md"
              : "bg-white/80 border border-black/5 rounded-tl-md shadow-sm"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-headings:text-foreground prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-code:bg-black/5 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-pre:bg-slate-900 prose-pre:text-slate-100">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={createCitationComponents(message.citations, onCitationClick)}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-[11px] text-muted-foreground font-medium">参考来源</p>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((c, i) => (
                <button
                  key={i}
                  onClick={() => onCitationClick(c)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-primary/5 hover:bg-primary/10 border border-primary/10 text-xs text-primary transition-colors"
                >
                  <FileText className="w-3 h-3" />
                  {c.doc_name}
                  {c.page > 0 && <span className="text-primary/60">P{c.page}</span>}
                  <Badge variant="secondary" className="text-[9px] h-4 px-1 ml-1">
                    {(c.confidence * 100).toFixed(0)}%
                  </Badge>
                </button>
              ))}
            </div>
          </div>
        )}

        {!isUser && (
          <div className="flex items-center gap-1 mt-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
              onClick={() => onCopy(message.content)}
            >
              <Copy className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "h-7 w-7 p-0",
                message.feedback === "like"
                  ? "text-green-500"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => onFeedback(message.id, "like")}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "h-7 w-7 p-0",
                message.feedback === "dislike"
                  ? "text-red-500"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => onFeedback(message.id, "dislike")}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
