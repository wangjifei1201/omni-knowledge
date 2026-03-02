"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import type { editor as MonacoEditor } from "monaco-editor";
import {
  FileText,
  Save,
  X,
  ChevronLeft,
  ChevronRight,
  File,
  Maximize2,
  Minimize2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// 动态导入 Monaco 编辑器，避免 SSR 问题
const Editor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full bg-slate-50">
        <div className="text-sm text-muted-foreground">编辑器加载中...</div>
      </div>
    ),
  }
);

interface DocumentViewerProps {
  docId?: string;
  docName?: string;
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  /** 需要在文档中高亮显示的文本 */
  highlightText?: string;
  /** 是否为弹窗模式（隐藏折叠按钮） */
  mode?: "panel" | "dialog";
}

export function DocumentViewer({
  docId,
  docName,
  onClose,
  collapsed = false,
  onToggleCollapse,
  highlightText,
  mode = "panel",
}: DocumentViewerProps) {
  const [content, setContent] = useState<string>("");
  const [originalContent, setOriginalContent] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isModified, setIsModified] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const decorationsRef = useRef<MonacoEditor.IEditorDecorationsCollection | null>(null);

  // 根据文件扩展名检测语法高亮语言
  const getLanguage = useCallback((fileName: string): string => {
    const ext = fileName?.split(".").pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      txt: "plaintext",
      md: "markdown",
      json: "json",
      js: "javascript",
      ts: "typescript",
      py: "python",
      html: "html",
      css: "css",
      xml: "xml",
      yaml: "yaml",
      yml: "yaml",
      csv: "plaintext",
      doc: "plaintext",
      docx: "plaintext",
    };
    return langMap[ext || ""] || "plaintext";
  }, []);

  // 高亮文本并滚动到对应位置
  const applyHighlight = useCallback((editor: MonacoEditor.IStandaloneCodeEditor, text: string) => {
    if (!text || !editor) return;

    const model = editor.getModel();
    if (!model) return;

    const fullText = model.getValue();
    const index = fullText.indexOf(text);
    if (index === -1) return;

    const startPos = model.getPositionAt(index);
    const endPos = model.getPositionAt(index + text.length);

    // 清除旧的高亮装饰
    if (decorationsRef.current) {
      decorationsRef.current.clear();
    }

    // 添加新的高亮装饰
    decorationsRef.current = editor.createDecorationsCollection([
      {
        range: {
          startLineNumber: startPos.lineNumber,
          startColumn: startPos.column,
          endLineNumber: endPos.lineNumber,
          endColumn: endPos.column,
        },
        options: {
          className: "highlight-citation-text",
          isWholeLine: false,
          overviewRuler: {
            color: "#fbbf24",
            position: 1,
          },
        },
      },
    ]);

    // 滚动到高亮位置
    editor.revealLineInCenter(startPos.lineNumber);
  }, []);

  // 编辑器挂载回调
  const handleEditorDidMount = useCallback(
    (editor: MonacoEditor.IStandaloneCodeEditor) => {
      editorRef.current = editor;
      if (highlightText && content) {
        applyHighlight(editor, highlightText);
      }
    },
    [highlightText, content, applyHighlight]
  );

  // 当高亮文本变化时重新应用高亮
  useEffect(() => {
    if (editorRef.current && highlightText && content) {
      applyHighlight(editorRef.current, highlightText);
    }
  }, [highlightText, content, applyHighlight]);

  // 加载文档内容
  useEffect(() => {
    if (!docId) {
      setContent("");
      setOriginalContent("");
      setError(null);
      return;
    }

    const loadContent = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const text = await api.previewDocument(docId);
        setContent(text);
        setOriginalContent(text);
        setIsModified(false);
      } catch (err: any) {
        setError(err.message || "文档加载失败");
        setContent("");
      } finally {
        setIsLoading(false);
      }
    };

    loadContent();
  }, [docId]);

  const handleContentChange = (value: string | undefined) => {
    if (value !== undefined) {
      setContent(value);
      setIsModified(value !== originalContent);
    }
  };

  const handleSave = async () => {
    if (!docId || !isModified) return;

    setIsSaving(true);
    try {
      // TODO: 后端实现保存接口后启用
      // await api.saveDocument(docId, content);
      setOriginalContent(content);
      setIsModified(false);
    } catch (err: any) {
      setError(err.message || "保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  const handleRefresh = async () => {
    if (!docId) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const text = await api.previewDocument(docId);
      setContent(text);
      setOriginalContent(text);
      setIsModified(false);
    } catch (err: any) {
      setError(err.message || "文档加载失败");
    } finally {
      setIsLoading(false);
    }
  };

  if (collapsed && mode === "panel") {
    return (
      <div className="h-full flex flex-col items-center py-4 bg-white/50 backdrop-blur-sm border-l border-black/5">
        <Button
          variant="ghost"
          size="sm"
          className="w-8 h-8 p-0"
          onClick={onToggleCollapse}
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
        <div className="mt-4 [writing-mode:vertical-rl] text-xs text-muted-foreground">
          文档查看器
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "h-full flex flex-col bg-white/50 backdrop-blur-sm",
        mode === "panel" && "border-l border-black/5",
        isFullscreen && "fixed inset-0 z-50 bg-white"
      )}
    >
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between p-3 border-b border-black/5">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {mode === "panel" && (
            <Button
              variant="ghost"
              size="sm"
              className="w-7 h-7 p-0 shrink-0"
              onClick={onToggleCollapse}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
          )}
          <FileText className="w-4 h-4 text-primary shrink-0" />
          <span className="text-sm font-medium truncate">
            {docName || "未选择文档"}
          </span>
          {isModified && (
            <Badge variant="secondary" className="text-[10px] h-5 shrink-0">
              已修改
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="w-7 h-7 p-0"
            onClick={handleRefresh}
            disabled={!docId || isLoading}
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
          </Button>
          {isModified && (
            <Button
              variant="ghost"
              size="sm"
              className="w-7 h-7 p-0 text-primary"
              onClick={handleSave}
              disabled={isSaving}
            >
              <Save className="w-3.5 h-3.5" />
            </Button>
          )}
          {mode === "panel" && (
            <Button
              variant="ghost"
              size="sm"
              className="w-7 h-7 p-0"
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              {isFullscreen ? (
                <Minimize2 className="w-3.5 h-3.5" />
              ) : (
                <Maximize2 className="w-3.5 h-3.5" />
              )}
            </Button>
          )}
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              className="w-7 h-7 p-0"
              onClick={onClose}
            >
              <X className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* 高亮样式注入 */}
      <style jsx global>{`
        .highlight-citation-text {
          background-color: rgba(251, 191, 36, 0.35);
          border: 1px solid rgba(245, 158, 11, 0.5);
          border-radius: 2px;
        }
      `}</style>

      {/* 编辑器内容区 */}
      <div className="flex-1 overflow-hidden">
        {!docId ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <File className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-sm">点击引用中的「在文档中查看」</p>
            <p className="text-xs mt-1">即可预览文档内容</p>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <p className="text-sm text-destructive">{error}</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={handleRefresh}
            >
              重试
            </Button>
          </div>
        ) : (
          <Editor
            height="100%"
            language={getLanguage(docName || "")}
            value={content}
            onChange={handleContentChange}
            onMount={handleEditorDidMount}
            theme="vs-light"
            options={{
              readOnly: false,
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: "on",
              wordWrap: "on",
              scrollBeyondLastLine: false,
              automaticLayout: true,
              padding: { top: 12, bottom: 12 },
              renderLineHighlight: "gutter",
              scrollbar: {
                verticalScrollbarSize: 8,
                horizontalScrollbarSize: 8,
              },
            }}
          />
        )}
      </div>
    </div>
  );
}
