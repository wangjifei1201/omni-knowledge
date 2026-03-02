"use client";

import { useState, useEffect } from "react";
import {
  Server,
  Database,
  Brain,
  Shield,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/store";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Message {
  text: string;
  type: "success" | "error" | "";
}

interface SystemConfig {
  llm: { api_base: string; model_name: string };
  embedding: { api_base: string; model_name: string; dimension: number };
  reranker: { api_base: string; model_name: string };
  database: { type: string; host: string; port: number; name: string };
  vector_store: { type: string; index_path: string };
  storage: { type: string; path: string };
}

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const [saving, setSaving] = useState(false);

  const [profile, setProfile] = useState({
    display_name: user?.display_name || "",
    email: user?.email || "",
    department: user?.department || "",
  });
  const [passwordForm, setPasswordForm] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [profileMsg, setProfileMsg] = useState<Message>({ text: "", type: "" });
  const [passwordMsg, setPasswordMsg] = useState<Message>({ text: "", type: "" });

  // System config state
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setProfile({
        display_name: user.display_name || "",
        email: user.email || "",
        department: user.department || "",
      });
    }
  }, [user]);

  // Fetch system config for admin users
  useEffect(() => {
    if (user?.role === "admin" && !systemConfig) {
      setConfigLoading(true);
      api
        .getSystemConfig()
        .then(setSystemConfig)
        .catch(() => {})
        .finally(() => setConfigLoading(false));
    }
  }, [user, systemConfig]);

  const handleSaveProfile = async () => {
    setSaving(true);
    setProfileMsg({ text: "", type: "" });
    try {
      const updatedUser = await api.updateMe(profile);
      updateUser(updatedUser);
      setProfileMsg({ text: "个人信息已更新", type: "success" });
    } catch (err: any) {
      setProfileMsg({ text: err.message || "保存失败", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordMsg({ text: "两次输入的密码不一致", type: "error" });
      return;
    }
    if (passwordForm.new_password.length < 6) {
      setPasswordMsg({ text: "新密码长度至少为6位", type: "error" });
      return;
    }
    setSaving(true);
    setPasswordMsg({ text: "", type: "" });
    try {
      await api.changePassword({
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password,
      });
      setPasswordMsg({ text: "密码修改成功", type: "success" });
      setPasswordForm({ old_password: "", new_password: "", confirm_password: "" });
    } catch (err: any) {
      setPasswordMsg({ text: err.message || "密码修改失败", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const MessageDisplay = ({ msg }: { msg: Message }) => {
    if (!msg.text) return null;
    return (
      <div
        className={cn(
          "flex items-center gap-2 text-sm",
          msg.type === "success" ? "text-green-600" : "text-red-600"
        )}
      >
        {msg.type === "success" ? (
          <CheckCircle2 className="w-4 h-4" />
        ) : (
          <AlertCircle className="w-4 h-4" />
        )}
        {msg.text}
      </div>
    );
  };

  return (
    <div className="h-full overflow-y-auto p-6 scrollbar-thin">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-semibold">系统设置</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            管理个人信息与系统配置
          </p>
        </div>

        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="bg-white/60">
            <TabsTrigger value="profile">个人信息</TabsTrigger>
            <TabsTrigger value="security">安全设置</TabsTrigger>
            {user?.role === "admin" && (
              <TabsTrigger value="system">系统配置</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="profile">
            <Card className="bg-white/60 border-black/5">
              <CardHeader>
                <CardTitle className="text-base">个人信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>用户名</Label>
                    <Input className="mt-1.5" value={user?.username || ""} disabled />
                  </div>
                  <div>
                    <Label>显示名称</Label>
                    <Input
                      className="mt-1.5"
                      value={profile.display_name}
                      onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
                    />
                  </div>
                </div>
                <div>
                  <Label>邮箱</Label>
                  <Input
                    className="mt-1.5"
                    value={profile.email}
                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  />
                </div>
                <div>
                  <Label>部门</Label>
                  <Input
                    className="mt-1.5"
                    value={profile.department}
                    onChange={(e) => setProfile({ ...profile, department: e.target.value })}
                  />
                </div>
                <MessageDisplay msg={profileMsg} />
                <Button onClick={handleSaveProfile} disabled={saving} className="gap-2">
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                  保存
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security">
            <Card className="bg-white/60 border-black/5">
              <CardHeader>
                <CardTitle className="text-base">修改密码</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 max-w-md">
                <div>
                  <Label>当前密码</Label>
                  <Input
                    className="mt-1.5"
                    type="password"
                    value={passwordForm.old_password}
                    onChange={(e) => setPasswordForm({ ...passwordForm, old_password: e.target.value })}
                  />
                </div>
                <div>
                  <Label>新密码</Label>
                  <Input
                    className="mt-1.5"
                    type="password"
                    value={passwordForm.new_password}
                    onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  />
                </div>
                <div>
                  <Label>确认新密码</Label>
                  <Input
                    className="mt-1.5"
                    type="password"
                    value={passwordForm.confirm_password}
                    onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  />
                </div>
                <MessageDisplay msg={passwordMsg} />
                <Button onClick={handleChangePassword} disabled={saving} className="gap-2">
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Shield className="w-4 h-4" />
                  )}
                  修改密码
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {user?.role === "admin" && (
            <TabsContent value="system">
              <div className="space-y-6">
                {configLoading ? (
                  <Card className="bg-white/60 border-black/5">
                    <CardHeader>
                      <Skeleton className="h-5 w-32" />
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <Skeleton className="h-10 w-full" />
                      <Skeleton className="h-10 w-full" />
                      <Skeleton className="h-10 w-3/4" />
                    </CardContent>
                  </Card>
                ) : systemConfig ? (
                  <>
                    <Card className="bg-white/60 border-black/5">
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Brain className="w-4 h-4" />
                          AI 模型配置
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-muted-foreground">LLM API 地址</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.llm.api_base}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">LLM 模型名称</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.llm.model_name}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">Embedding API 地址</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.embedding.api_base}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">Embedding 模型名称</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.embedding.model_name}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">向量维度</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.embedding.dimension}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">Reranker 模型</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.reranker.model_name}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-white/60 border-black/5">
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Database className="w-4 h-4" />
                          数据存储
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-muted-foreground">关系数据库</Label>
                            <div className="mt-1.5 flex items-center gap-2">
                              <Badge variant="secondary" className="uppercase">
                                {systemConfig.database.type}
                              </Badge>
                              <span className="text-sm font-medium">
                                {systemConfig.database.host}:{systemConfig.database.port}
                              </span>
                            </div>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">数据库名称</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.database.name}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">向量数据库</Label>
                            <div className="mt-1.5 flex items-center gap-2">
                              <Badge variant="secondary" className="uppercase">
                                {systemConfig.vector_store.type}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                {systemConfig.vector_store.index_path}
                              </span>
                            </div>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">文件存储</Label>
                            <div className="mt-1.5 flex items-center gap-2">
                              <Badge variant="secondary" className="uppercase">
                                {systemConfig.storage.type}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                {systemConfig.storage.path}
                              </span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-white/60 border-black/5">
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Server className="w-4 h-4" />
                          服务信息
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-muted-foreground">Reranker API 地址</Label>
                            <p className="mt-1.5 text-sm font-medium">{systemConfig.reranker.api_base}</p>
                          </div>
                        </div>
                        <p className="mt-4 text-xs text-muted-foreground">
                          系统配置为只读模式，如需修改请编辑后端 .env 配置文件并重启服务。
                        </p>
                      </CardContent>
                    </Card>
                  </>
                ) : (
                  <Card className="bg-white/60 border-black/5">
                    <CardContent className="py-8 text-center text-muted-foreground">
                      无法加载系统配置
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </div>
  );
}
