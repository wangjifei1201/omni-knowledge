"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Document, DocumentChunk, ChunkingStrategyDef } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  FileText,
  Download,
  RefreshCw,
  Save,
  ChevronDown,
  ChevronUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Hash,
  Settings2,
  Layers,
} from "lucide-react";

const statusConfig: Record<string, { label: string; color: string; icon: any }> = {
  pending: { label: "待处理", color: "bg-yellow-100 text-yellow-800", icon: Clock },
  processing: { label: "处理中", color: "bg-blue-100 text-blue-800", icon: RefreshCw },
  completed: { label: "已完成", color: "bg-green-100 text-green-800", icon: CheckCircle },
  failed: { label: "失败", color: "bg-red-100 text-red-800", icon: AlertCircle },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params.id as string;

  // Document state
  const [doc, setDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);

  // Chunking strategies
  const [strategies, setStrategies] = useState<ChunkingStrategyDef[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState("paragraph");
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({});
  const [configDirty, setConfigDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [retraining, setRetraining] = useState(false);

  // Chunks state
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunksTotal, setChunksTotal] = useState(0);
  const [chunksPage, setChunksPage] = useState(1);
  const [chunksLoading, setChunksLoading] = useState(false);
  const chunksPageSize = 20;

  // Expanded chunks
  const [expandedChunks, setExpandedChunks] = useState<Set<number>>(new Set());

  // Load document
  const loadDocument = useCallback(async () => {
    try {
      const data = await api.getDocument(docId);
      setDoc(data);
      setSelectedStrategy(data.chunking_strategy || "paragraph");
      setStrategyParams(data.chunking_params || {});
      setConfigDirty(false);
    } catch (err: any) {
      console.error("Failed to load document:", err);
    } finally {
      setLoading(false);
    }
  }, [docId]);

  // Load strategies
  const loadStrategies = useCallback(async () => {
    try {
      const data = await api.getChunkingStrategies();
      setStrategies(data.strategies);
    } catch (err: any) {
      console.error("Failed to load strategies:", err);
    }
  }, []);

  // Load chunks
  const loadChunks = useCallback(async (page: number) => {
    setChunksLoading(true);
    try {
      const data = await api.getDocumentChunks(docId, page, chunksPageSize);
      setChunks(data.items);
      setChunksTotal(data.total);
      setChunksPage(page);
    } catch (err: any) {
      console.error("Failed to load chunks:", err);
    } finally {
      setChunksLoading(false);
    }
  }, [docId]);

  useEffect(() => {
    loadDocument();
    loadStrategies();
    loadChunks(1);
  }, [loadDocument, loadStrategies, loadChunks]);

  // Poll for status changes during processing
  useEffect(() => {
    if (!doc || doc.status !== "processing") return;
    const interval = setInterval(async () => {
      try {
        const data = await api.getDocument(docId);
        setDoc(data);
        if (data.status !== "processing") {
          setRetraining(false);
          loadChunks(1);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [doc?.status, docId, loadChunks]);

  // Get current strategy definition
  const currentStrategyDef = strategies.find((s) => s.name === selectedStrategy);

  // Get effective param value
  const getParamValue = (key: string, defaultVal: number) => {
    return strategyParams[key] ?? defaultVal;
  };

  // Handle param change
  const handleParamChange = (key: string, value: number) => {
    setStrategyParams((prev) => ({ ...prev, [key]: value }));
    setConfigDirty(true);
  };

  // Handle strategy change
  const handleStrategyChange = (strategy: string) => {
    setSelectedStrategy(strategy);
    // Reset params to defaults for the new strategy
    const def = strategies.find((s) => s.name === strategy);
    if (def) {
      const defaults: Record<string, any> = {};
      def.params.forEach((p) => {
        defaults[p.key] = p.default;
      });
      setStrategyParams(defaults);
    }
    setConfigDirty(true);
  };

  // Save config
  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await api.updateChunkingConfig(docId, {
        chunking_strategy: selectedStrategy,
        chunking_params: strategyParams,
      });
      setConfigDirty(false);
      await loadDocument();
    } catch (err: any) {
      alert("保存失败: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  // Retrain
  const handleRetrain = async () => {
    if (!confirm("重新训练将重新解析文档并生成向量，确定继续？")) return;
    setRetraining(true);
    try {
      await api.retrainDocument(docId, {
        chunking_strategy: selectedStrategy,
        chunking_params: strategyParams,
      });
      setConfigDirty(false);
      // Reload doc to get processing status
      const data = await api.getDocument(docId);
      setDoc(data);
    } catch (err: any) {
      alert("训练失败: " + err.message);
      setRetraining(false);
    }
  };

  // Toggle chunk expand
  const toggleChunk = (idx: number) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  // Download
  const handleDownload = () => {
    if (doc) {
      api.downloadDocument(docId, `${doc.doc_name}.${doc.file_type}`);
    }
  };

  const totalChunkPages = Math.ceil(chunksTotal / chunksPageSize);
  const isProcessing = doc?.status === "processing" || retraining;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-muted-foreground">文档不存在</p>
        <Button variant="outline" onClick={() => router.push("/documents")}>
          返回文档列表
        </Button>
      </div>
    );
  }

  const StatusIcon = statusConfig[doc.status]?.icon || Clock;

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button
          onClick={() => router.push("/documents")}
          className="hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          文档管理
        </button>
        <span>/</span>
        <span className="text-foreground truncate max-w-xs">{doc.doc_name}</span>
      </div>

      {/* Document info */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <FileText className="h-8 w-8 text-muted-foreground" />
              <div>
                <CardTitle className="text-lg">{doc.doc_name}</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {doc.file_type.toUpperCase()} &middot; {formatFileSize(doc.file_size)} &middot; {doc.page_count} 页 &middot; {doc.chunk_count} 个分段
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={statusConfig[doc.status]?.color || ""}>
                <StatusIcon className="h-3 w-3 mr-1" />
                {statusConfig[doc.status]?.label || doc.status}
              </Badge>
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download className="h-4 w-4 mr-1" />
                下载
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">部门</span>
              <p>{doc.department || "-"}</p>
            </div>
            <div>
              <span className="text-muted-foreground">分类</span>
              <p>{doc.category || "-"}</p>
            </div>
            <div>
              <span className="text-muted-foreground">安全级别</span>
              <p>{doc.security_level || "-"}</p>
            </div>
            <div>
              <span className="text-muted-foreground">上传时间</span>
              <p>{new Date(doc.created_at).toLocaleString("zh-CN")}</p>
            </div>
          </div>
          {doc.tags && doc.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {doc.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
          {doc.description && (
            <p className="text-sm text-muted-foreground mt-3">{doc.description}</p>
          )}
        </CardContent>
      </Card>

      {/* Chunking strategy config */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            分段策略配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>分段策略</Label>
              <Select
                value={selectedStrategy}
                onValueChange={handleStrategyChange}
                disabled={isProcessing}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((s) => (
                    <SelectItem key={s.name} value={s.name}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {currentStrategyDef && (
                <p className="text-xs text-muted-foreground">
                  {currentStrategyDef.description}
                </p>
              )}
            </div>

            {currentStrategyDef?.params.map((p) => (
              <div key={p.key} className="space-y-2">
                <Label>{p.label}</Label>
                <Input
                  type="number"
                  min={p.min}
                  max={p.max}
                  value={getParamValue(p.key, p.default)}
                  onChange={(e) => handleParamChange(p.key, Number(e.target.value))}
                  disabled={isProcessing}
                />
                <p className="text-xs text-muted-foreground">
                  范围: {p.min} - {p.max}
                </p>
              </div>
            ))}
          </div>

          <Separator />

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSaveConfig}
              disabled={!configDirty || saving || isProcessing}
            >
              {saving ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-1" />
              )}
              保存配置
            </Button>
            <Button
              size="sm"
              onClick={handleRetrain}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
              {isProcessing ? "训练中..." : "重新训练"}
            </Button>
            {configDirty && (
              <span className="text-xs text-orange-500">配置已修改，请保存或重新训练</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Chunks list */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Layers className="h-5 w-5" />
              分段结果
              <Badge variant="secondary" className="ml-1">{chunksTotal} 个分段</Badge>
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => loadChunks(chunksPage)}
              disabled={chunksLoading}
            >
              <RefreshCw className={`h-4 w-4 ${chunksLoading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isProcessing ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              文档正在处理中，请稍候...
            </div>
          ) : chunks.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              暂无分段数据
            </div>
          ) : (
            <div className="space-y-2">
              {chunks.map((chunk) => {
                const isExpanded = expandedChunks.has(chunk.chunk_index);
                const preview = chunk.content.length > 200 && !isExpanded
                  ? chunk.content.slice(0, 200) + "..."
                  : chunk.content;

                return (
                  <div
                    key={chunk.id}
                    className="border rounded-lg p-3 hover:bg-muted/30 transition-colors"
                  >
                    <div
                      className="flex items-center justify-between cursor-pointer"
                      onClick={() => toggleChunk(chunk.chunk_index)}
                    >
                      <div className="flex items-center gap-2 text-sm">
                        <Badge variant="outline" className="font-mono text-xs">
                          <Hash className="h-3 w-3 mr-0.5" />
                          {chunk.chunk_index + 1}
                        </Badge>
                        <span className="text-muted-foreground text-xs">
                          {chunk.token_count} 字符
                        </span>
                      </div>
                      {chunk.content.length > 200 && (
                        isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )
                      )}
                    </div>
                    <p className="text-sm mt-2 whitespace-pre-wrap break-words leading-relaxed">
                      {preview}
                    </p>
                  </div>
                );
              })}

              {/* Pagination */}
              {totalChunkPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={chunksPage <= 1 || chunksLoading}
                    onClick={() => loadChunks(chunksPage - 1)}
                  >
                    上一页
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {chunksPage} / {totalChunkPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={chunksPage >= totalChunkPages || chunksLoading}
                    onClick={() => loadChunks(chunksPage + 1)}
                  >
                    下一页
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
