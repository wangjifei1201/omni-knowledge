"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Upload,
  Search,
  FileText,
  File,
  FileSpreadsheet,
  Image as ImageIcon,
  Trash2,
  Eye,
  Download,
  Grid,
  List,
  MoreHorizontal,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  X,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Document } from "@/types";
import { DocumentViewer } from "@/components/chat/document-viewer";

const fileTypeIcons: Record<string, React.ElementType> = {
  pdf: FileText,
  doc: FileText,
  docx: FileText,
  xls: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  png: ImageIcon,
  jpg: ImageIcon,
  jpeg: ImageIcon,
};

const statusConfig: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  pending: { label: "待处理", color: "bg-yellow-100 text-yellow-700", icon: Clock },
  processing: { label: "处理中", color: "bg-blue-100 text-blue-700", icon: RefreshCw },
  completed: { label: "已完成", color: "bg-green-100 text-green-700", icon: CheckCircle },
  failed: { label: "失败", color: "bg-red-100 text-red-700", icon: AlertCircle },
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [department, setDepartment] = useState("");
  const [category, setCategory] = useState("");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);

  // Batch selection state
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [batchTrainOpen, setBatchTrainOpen] = useState(false);
  const [batchTrainTaskId, setBatchTrainTaskId] = useState<string | null>(null);
  const [batchTrainStatus, setBatchTrainStatus] = useState<any>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getDocuments({
        keyword,
        department,
        category,
        page,
        page_size: pageSize,
      });
      setDocuments(res.items || []);
      setTotal(res.total || 0);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [keyword, department, category, page, pageSize]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Poll batch train status
  useEffect(() => {
    if (!batchTrainTaskId) return;

    const pollStatus = async () => {
      try {
        const status = await api.getBatchTrainStatus(batchTrainTaskId);
        setBatchTrainStatus(status);

        if (status.status === "completed") {
          // Stop polling when completed
          setBatchTrainTaskId(null);
          loadDocuments();
        }
      } catch (err) {
        console.error("获取训练状态失败:", err);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 2000);
    return () => clearInterval(interval);
  }, [batchTrainTaskId, loadDocuments]);

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个文档吗？")) return;
    try {
      await api.deleteDocument(id);
      loadDocuments();
      setSelectedIds((prev) => prev.filter((i) => i !== id));
    } catch {}
  };

  const handleDownload = async (doc: Document) => {
    try {
      await api.downloadDocument(doc.id, `${doc.doc_name}.${doc.file_type}`);
    } catch (err) {
      console.error("下载失败:", err);
    }
  };

  const handlePreview = (doc: Document) => {
    setPreviewDoc(doc);
  };

  const handleReparse = async (doc: Document) => {
    try {
      await api.reparseDocument(doc.id);
      loadDocuments();
    } catch (err) {
      console.error("重新解析失败:", err);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(documents.map((d) => d.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (docId: string, checked: boolean) => {
    if (checked) {
      setSelectedIds((prev) => [...prev, docId]);
    } else {
      setSelectedIds((prev) => prev.filter((id) => id !== docId));
    }
  };

  const handleBatchTrain = async () => {
    if (selectedIds.length === 0) return;

    try {
      const result = await api.batchTrainDocuments(selectedIds);
      setBatchTrainTaskId(result.task_id);
      setBatchTrainStatus({
        status: "pending",
        total: result.total,
        completed: 0,
        failed: 0,
        results: [],
      });
      setBatchTrainOpen(true);
    } catch (err: any) {
      alert(err.message || "启动批量训练失败");
    }
  };

  const totalPages = Math.ceil(total / pageSize);
  const isAllSelected = documents.length > 0 && selectedIds.length === documents.length;
  const isSomeSelected = selectedIds.length > 0 && selectedIds.length < documents.length;

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="h-full flex flex-col p-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">文档管理</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            管理知识库中的所有文档，支持上传、检索和分类
          </p>
        </div>
        <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Upload className="w-4 h-4" />
              上传文档
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>上传文档</DialogTitle>
              <DialogDescription>
                支持一次上传最多10个文档，系统将自动提取文档属性
              </DialogDescription>
            </DialogHeader>
            <MultiUploadForm
              onSuccess={() => {
                setUploadOpen(false);
                loadDocuments();
              }}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* 批量操作工具栏 */}
      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 p-3 bg-primary/5 rounded-lg border border-primary/20">
          <span className="text-sm font-medium">已选择 {selectedIds.length} 个文档</span>
          <Separator orientation="vertical" className="h-5" />
          <Button size="sm" variant="default" className="gap-1.5" onClick={handleBatchTrain}>
            <Zap className="w-4 h-4" />
            批量训练
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])}>
            取消选择
          </Button>
        </div>
      )}

      {/* 筛选栏 */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="搜索文档名称..."
            className="pl-9 bg-white/60"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
        </div>
        <Select value={department} onValueChange={setDepartment}>
          <SelectTrigger className="w-[140px] bg-white/60">
            <SelectValue placeholder="全部部门" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">全部部门</SelectItem>
            <SelectItem value="安全部">安全部</SelectItem>
            <SelectItem value="人事部">人事部</SelectItem>
            <SelectItem value="技术部">技术部</SelectItem>
          </SelectContent>
        </Select>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-[140px] bg-white/60">
            <SelectValue placeholder="全部类别" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">全部类别</SelectItem>
            <SelectItem value="应急预案">应急预案</SelectItem>
            <SelectItem value="管理制度">管理制度</SelectItem>
            <SelectItem value="操作规程">操作规程</SelectItem>
          </SelectContent>
        </Select>
        <Separator orientation="vertical" className="h-6" />
        <div className="flex items-center border rounded-lg overflow-hidden bg-white/60">
          <Button
            variant={viewMode === "table" ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0 rounded-none"
            onClick={() => setViewMode("table")}
          >
            <List className="w-4 h-4" />
          </Button>
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0 rounded-none"
            onClick={() => setViewMode("grid")}
          >
            <Grid className="w-4 h-4" />
          </Button>
        </div>
        <Button variant="ghost" size="sm" onClick={loadDocuments}>
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
        </Button>
      </div>

      {/* 文档列表 */}
      <div className="flex-1 overflow-auto">
        {viewMode === "table" ? (
          <div className="bg-white/60 rounded-xl border border-black/5 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-[40px]">
                    <Checkbox
                      checked={isAllSelected}
                      onCheckedChange={handleSelectAll}
                      aria-label="全选"
                      className={isSomeSelected ? "data-[state=checked]:bg-primary/50" : ""}
                    />
                  </TableHead>
                  <TableHead className="w-[35%]">文档名称</TableHead>
                  <TableHead>部门</TableHead>
                  <TableHead>类别</TableHead>
                  <TableHead>大小</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>上传时间</TableHead>
                  <TableHead className="w-[80px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                      {loading ? "加载中..." : "暂无文档，点击上方按钮上传"}
                    </TableCell>
                  </TableRow>
                ) : (
                  documents.map((doc) => {
                    const IconComp = fileTypeIcons[doc.file_type] || File;
                    const status = statusConfig[doc.status] || statusConfig.pending;
                    const StatusIcon = status.icon;
                    const isSelected = selectedIds.includes(doc.id);
                    return (
                      <TableRow key={doc.id} className={isSelected ? "bg-primary/5" : ""}>
                        <TableCell>
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={(checked) => handleSelectOne(doc.id, !!checked)}
                            aria-label={`选择 ${doc.doc_name}`}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-lg bg-primary/5 flex items-center justify-center">
                              <IconComp className="w-4 h-4 text-primary" />
                            </div>
                            <div>
                              <p
                                className="text-sm font-medium truncate max-w-[280px] cursor-pointer hover:text-primary hover:underline"
                                onClick={() => window.location.href = `/documents/${doc.id}`}
                              >
                                {doc.doc_name}
                              </p>
                              <p className="text-[11px] text-muted-foreground">
                                {doc.file_type.toUpperCase()} · {doc.page_count} 页
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">{doc.department || "-"}</TableCell>
                        <TableCell className="text-sm">{doc.category || "-"}</TableCell>
                        <TableCell className="text-sm">{formatFileSize(doc.file_size)}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={cn("text-[11px] gap-1", status.color)}>
                            <StatusIcon className="w-3 h-3" />
                            {status.label}
                          </Badge>
                          {doc.status === "processing" && (
                            <Progress value={doc.parse_progress * 100} className="h-1 mt-1 w-16" />
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(doc.created_at).toLocaleDateString("zh-CN")}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                                <MoreHorizontal className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                className="gap-2"
                                onClick={() => handlePreview(doc)}
                              >
                                <Eye className="w-4 h-4" /> 查看详情
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="gap-2"
                                onClick={() => handleDownload(doc)}
                              >
                                <Download className="w-4 h-4" /> 下载文件
                              </DropdownMenuItem>
                              {(doc.status === "failed" || doc.status === "completed") && (
                                <DropdownMenuItem
                                  className="gap-2"
                                  onClick={() => handleReparse(doc)}
                                >
                                  <RefreshCw className="w-4 h-4" /> 重新训练
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuItem
                                className="gap-2 text-destructive"
                                onClick={() => handleDelete(doc.id)}
                              >
                                <Trash2 className="w-4 h-4" /> 删除文档
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {documents.map((doc) => {
              const IconComp = fileTypeIcons[doc.file_type] || File;
              const status = statusConfig[doc.status] || statusConfig.pending;
              const isSelected = selectedIds.includes(doc.id);
              return (
                <Card
                  key={doc.id}
                  className={cn(
                    "bg-white/60 hover:bg-white/80 border-black/5 transition-colors cursor-pointer relative",
                    isSelected && "ring-2 ring-primary"
                  )}
                  onClick={() => handleSelectOne(doc.id, !isSelected)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/5 flex items-center justify-center">
                        <IconComp className="w-5 h-5 text-primary" />
                      </div>
                      <Badge variant="secondary" className={cn("text-[10px]", status.color)}>
                        {status.label}
                      </Badge>
                    </div>
                    <p
                      className="text-sm font-medium truncate cursor-pointer hover:text-primary hover:underline"
                      onClick={(e) => { e.stopPropagation(); window.location.href = `/documents/${doc.id}`; }}
                    >
                      {doc.doc_name}
                    </p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      {doc.department || "未分类"} · {formatFileSize(doc.file_size)}
                    </p>
                    {doc.tags && doc.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {doc.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} variant="outline" className="text-[10px] h-5 px-1.5">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                    {isSelected && (
                      <div className="absolute top-2 right-2">
                        <CheckCircle className="w-5 h-5 text-primary" />
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-black/5">
          <p className="text-sm text-muted-foreground">共 {total} 个文档</p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* 文档预览弹窗 */}
      <Dialog open={!!previewDoc} onOpenChange={(open) => { if (!open) setPreviewDoc(null); }}>
        <DialogContent className="sm:max-w-[900px] h-[80vh] p-0 gap-0 overflow-hidden">
          <DialogHeader className="sr-only">
            <DialogTitle>{previewDoc?.doc_name || "文档预览"}</DialogTitle>
          </DialogHeader>
          {previewDoc && (
            <DocumentViewer
              docId={previewDoc.id}
              docName={`${previewDoc.doc_name}.${previewDoc.file_type}`}
              onClose={() => setPreviewDoc(null)}
              mode="dialog"
            />
          )}
        </DialogContent>
      </Dialog>

      {/* 批量训练进度弹窗 */}
      <Dialog open={batchTrainOpen} onOpenChange={(open) => {
        if (!open && batchTrainStatus?.status === "completed") {
          setBatchTrainOpen(false);
          setBatchTrainStatus(null);
          setSelectedIds([]);
        }
      }}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>批量训练进度</DialogTitle>
          </DialogHeader>
          {batchTrainStatus && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <span>
                  总进度：{batchTrainStatus.completed + batchTrainStatus.failed} / {batchTrainStatus.total}
                </span>
                <Badge variant={batchTrainStatus.status === "completed" ? "default" : "secondary"}>
                  {batchTrainStatus.status === "running" ? "进行中" :
                   batchTrainStatus.status === "completed" ? "已完成" : "等待中"}
                </Badge>
              </div>
              <Progress
                value={((batchTrainStatus.completed + batchTrainStatus.failed) / batchTrainStatus.total) * 100}
                className="h-2"
              />
              <div className="max-h-[300px] overflow-y-auto space-y-2">
                {batchTrainStatus.results?.map((r: any) => (
                  <div
                    key={r.doc_id}
                    className="flex items-center justify-between p-2 bg-muted/50 rounded-lg text-sm"
                  >
                    <span className="truncate max-w-[280px]">{r.doc_name}</span>
                    <Badge
                      variant="secondary"
                      className={cn(
                        "text-[10px]",
                        r.status === "completed" && "bg-green-100 text-green-700",
                        r.status === "failed" && "bg-red-100 text-red-700",
                        r.status === "processing" && "bg-blue-100 text-blue-700"
                      )}
                    >
                      {r.status === "completed" ? "完成" :
                       r.status === "failed" ? "失败" :
                       r.status === "processing" ? "处理中" : "等待"}
                    </Badge>
                  </div>
                ))}
              </div>
              {batchTrainStatus.status === "completed" && (
                <DialogFooter>
                  <Button onClick={() => {
                    setBatchTrainOpen(false);
                    setBatchTrainStatus(null);
                    setSelectedIds([]);
                  }}>
                    完成
                  </Button>
                </DialogFooter>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// File upload item type
interface UploadFileItem {
  id: string;
  file: File;
  status: "pending" | "extracting" | "uploading" | "success" | "failed";
  metadata?: {
    doc_name: string;
    department: string;
    category: string;
    security_level: string;
    tags: string[];
    description: string;
  };
  error?: string;
}

function MultiUploadForm({ onSuccess }: { onSuccess: () => void }) {
  const [files, setFiles] = useState<UploadFileItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFilesSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length === 0) return;

    // Check max limit
    if (files.length + selectedFiles.length > 10) {
      setError("一次最多上传10个文件");
      return;
    }

    // Add files to list
    const newFiles: UploadFileItem[] = selectedFiles.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: "pending" as const,
    }));

    setFiles((prev) => [...prev, ...newFiles]);
    setError("");

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError("请选择要上传的文件");
      return;
    }

    setUploading(true);
    setError("");

    try {
      // Step 1: Extract metadata using LLM
      setFiles((prev) => prev.map((f) => ({ ...f, status: "extracting" as const })));

      const formData = new FormData();
      files.forEach((f) => formData.append("files", f.file));

      let metadataResults: any[] = [];
      try {
        const res = await api.extractDocumentMetadata(formData);
        metadataResults = res.results || [];
      } catch (err) {
        console.error("元数据提取失败，使用默认值:", err);
        // Use default metadata if extraction fails
        metadataResults = files.map((f, i) => ({
          file_index: i,
          filename: f.file.name,
          doc_name: f.file.name.replace(/\.[^.]+$/, ""),
          department: "",
          category: "",
          security_level: "内部",
          tags: [],
          description: "",
        }));
      }

      // Update files with extracted metadata
      setFiles((prev) =>
        prev.map((f, i) => {
          const meta = metadataResults.find((m) => m.file_index === i) || metadataResults[i];
          return {
            ...f,
            status: "uploading" as const,
            metadata: meta
              ? {
                  doc_name: meta.doc_name || f.file.name.replace(/\.[^.]+$/, ""),
                  department: meta.department || "",
                  category: meta.category || "",
                  security_level: meta.security_level || "内部",
                  tags: meta.tags || [],
                  description: meta.description || "",
                }
              : {
                  doc_name: f.file.name.replace(/\.[^.]+$/, ""),
                  department: "",
                  category: "",
                  security_level: "内部",
                  tags: [],
                  description: "",
                },
          };
        })
      );

      // Step 2: Upload files one by one
      for (let i = 0; i < files.length; i++) {
        const fileItem = files[i];
        const meta = metadataResults.find((m) => m.file_index === i) || metadataResults[i];

        try {
          const uploadData = new FormData();
          uploadData.append("file", fileItem.file);
          uploadData.append("doc_name", meta?.doc_name || fileItem.file.name.replace(/\.[^.]+$/, ""));
          uploadData.append("department", meta?.department || "");
          uploadData.append("category", meta?.category || "");
          uploadData.append("security_level", meta?.security_level || "内部");
          uploadData.append("tags", (meta?.tags || []).join(","));
          uploadData.append("description", meta?.description || "");

          await api.uploadDocument(uploadData);

          setFiles((prev) =>
            prev.map((f) => (f.id === fileItem.id ? { ...f, status: "success" as const } : f))
          );
        } catch (err: any) {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileItem.id
                ? { ...f, status: "failed" as const, error: err.message || "上传失败" }
                : f
            )
          );
        }
      }

      // Call success after a short delay to show final status
      setTimeout(() => {
        onSuccess();
      }, 1000);
    } catch (err: any) {
      setError(err.message || "上传失败");
    } finally {
      setUploading(false);
    }
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase() || "";
    const IconComp = fileTypeIcons[ext] || File;
    return <IconComp className="w-4 h-4 text-primary" />;
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      {/* File select area */}
      <div>
        <Label>选择文件（最多10个）</Label>
        <div className="mt-1.5 border-2 border-dashed border-black/10 rounded-xl p-6 text-center hover:border-primary/30 transition-colors">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            id="multi-file-upload"
            multiple
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.csv,.png,.jpg,.jpeg,.gif"
            onChange={handleFilesSelect}
          />
          <label htmlFor="multi-file-upload" className="cursor-pointer">
            <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              点击选择或拖拽文件到此处
            </p>
            <p className="text-[11px] text-muted-foreground mt-1">
              支持 PDF/Word/Excel/PPT/图片/文本，单次最多10个
            </p>
          </label>
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2 max-h-[240px] overflow-y-auto">
          {files.map((item) => (
            <div
              key={item.id}
              className={cn(
                "flex items-center gap-3 p-2.5 rounded-lg border",
                item.status === "success" && "bg-green-50 border-green-200",
                item.status === "failed" && "bg-red-50 border-red-200",
                (item.status === "pending" || item.status === "extracting" || item.status === "uploading") &&
                  "bg-white border-black/10"
              )}
            >
              <div className="w-8 h-8 rounded-lg bg-primary/5 flex items-center justify-center flex-shrink-0">
                {getFileIcon(item.file.name)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{item.file.name}</p>
                <p className="text-[11px] text-muted-foreground">
                  {formatSize(item.file.size)}
                  {item.metadata?.doc_name && item.metadata.doc_name !== item.file.name.replace(/\.[^.]+$/, "") && (
                    <span className="ml-2 text-primary">
                      → {item.metadata.doc_name}
                    </span>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {item.status === "pending" && (
                  <Badge variant="secondary" className="text-[10px]">
                    待上传
                  </Badge>
                )}
                {item.status === "extracting" && (
                  <Badge variant="secondary" className="text-[10px] bg-blue-100 text-blue-700">
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    提取中
                  </Badge>
                )}
                {item.status === "uploading" && (
                  <Badge variant="secondary" className="text-[10px] bg-blue-100 text-blue-700">
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    上传中
                  </Badge>
                )}
                {item.status === "success" && (
                  <Badge variant="secondary" className="text-[10px] bg-green-100 text-green-700">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    成功
                  </Badge>
                )}
                {item.status === "failed" && (
                  <Badge variant="secondary" className="text-[10px] bg-red-100 text-red-700">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    失败
                  </Badge>
                )}
                {!uploading && item.status !== "success" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => removeFile(item.id)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <DialogFooter>
        <Button
          onClick={handleUpload}
          disabled={uploading || files.length === 0}
          className="gap-2"
        >
          {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
          {uploading ? "上传中..." : `上传 ${files.length} 个文件`}
        </Button>
      </DialogFooter>
    </div>
  );
}
