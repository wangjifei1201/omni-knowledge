"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  MessageSquare,
  Users,
  Clock,
  TrendingUp,
  ThumbsUp,
  ThumbsDown,
  BarChart3,
  Search,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import type { StatsOverview } from "@/types";

export default function StatisticsPage() {
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [trends, setTrends] = useState<{ date: string; count: number }[]>([]);
  const [topQueries, setTopQueries] = useState<{ query: string; count: number }[]>([]);
  const [trendDays, setTrendDays] = useState("7");

  useEffect(() => {
    loadStats();
  }, [trendDays]);

  const loadStats = async () => {
    try {
      const [overviewRes, trendsRes, topRes] = await Promise.allSettled([
        api.getStatsOverview(),
        api.getQueryTrends(parseInt(trendDays)),
        api.getTopQueries(),
      ]);
      if (overviewRes.status === "fulfilled") setOverview(overviewRes.value);
      if (trendsRes.status === "fulfilled") setTrends(trendsRes.value.trends || []);
      if (topRes.status === "fulfilled") setTopQueries(topRes.value.top_queries || []);
    } catch {} finally {
    }
  };

  const statCards = [
    {
      label: "文档总数",
      value: overview?.total_documents ?? 0,
      icon: FileText,
      color: "text-blue-600 bg-blue-50",
    },
    {
      label: "问答总数",
      value: overview?.total_queries ?? 0,
      icon: MessageSquare,
      color: "text-green-600 bg-green-50",
    },
    {
      label: "用户数",
      value: overview?.total_users ?? 0,
      icon: Users,
      color: "text-purple-600 bg-purple-50",
    },
    {
      label: "平均响应时间",
      value: `${overview?.avg_response_time_ms ?? 0}ms`,
      icon: Clock,
      color: "text-orange-600 bg-orange-50",
    },
  ];

  const maxTrendCount = Math.max(...trends.map((t) => t.count), 1);

  return (
    <div className="h-full overflow-y-auto p-6 scrollbar-thin">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-semibold">使用统计</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            系统使用情况概览与数据分析
          </p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {statCards.map((s) => (
            <Card key={s.label} className="bg-white/60 border-black/5">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{s.label}</p>
                    <p className="text-2xl font-bold mt-1">{s.value}</p>
                  </div>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${s.color}`}>
                    <s.icon className="w-5 h-5" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* 查询趋势 */}
          <Card className="bg-white/60 border-black/5">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">
                  <TrendingUp className="w-4 h-4 inline mr-1.5" />
                  查询趋势
                </CardTitle>
                <Select value={trendDays} onValueChange={setTrendDays}>
                  <SelectTrigger className="w-[100px] h-7 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">近7天</SelectItem>
                    <SelectItem value="30">近30天</SelectItem>
                    <SelectItem value="90">近90天</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {trends.length > 0 ? (
                <div className="flex items-end gap-1 h-[180px] mt-2">
                  {trends.map((t, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-[10px] text-muted-foreground">
                        {t.count}
                      </span>
                      <div
                        className="w-full bg-primary/20 rounded-t-sm min-h-[4px] transition-all"
                        style={{
                          height: `${(t.count / maxTrendCount) * 140}px`,
                        }}
                      />
                      <span className="text-[9px] text-muted-foreground truncate w-full text-center">
                        {t.date ? new Date(t.date).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" }) : ""}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
                  暂无数据
                </div>
              )}
            </CardContent>
          </Card>

          {/* 反馈统计 */}
          <Card className="bg-white/60 border-black/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">
                <BarChart3 className="w-4 h-4 inline mr-1.5" />
                反馈统计
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6 mt-4">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
                    <ThumbsUp className="w-5 h-5 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span className="text-sm">满意</span>
                      <span className="text-sm font-medium">
                        {overview?.feedback?.likes ?? 0}
                      </span>
                    </div>
                    <Progress
                      value={
                        overview?.feedback
                          ? (overview.feedback.likes /
                              Math.max(overview.feedback.likes + overview.feedback.dislikes, 1)) *
                            100
                          : 0
                      }
                      className="h-2"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
                    <ThumbsDown className="w-5 h-5 text-red-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span className="text-sm">不满意</span>
                      <span className="text-sm font-medium">
                        {overview?.feedback?.dislikes ?? 0}
                      </span>
                    </div>
                    <Progress
                      value={
                        overview?.feedback
                          ? (overview.feedback.dislikes /
                              Math.max(overview.feedback.likes + overview.feedback.dislikes, 1)) *
                            100
                          : 0
                      }
                      className="h-2 [&>div]:bg-red-500"
                    />
                  </div>
                </div>
                <div className="text-center pt-4 border-t border-black/5">
                  <p className="text-sm text-muted-foreground">今日查询</p>
                  <p className="text-3xl font-bold mt-1">
                    {overview?.today_queries ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 热门查询 */}
        <Card className="bg-white/60 border-black/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">
              <Search className="w-4 h-4 inline mr-1.5" />
              热门查询
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topQueries.length > 0 ? (
              <div className="space-y-2 mt-2">
                {topQueries.map((q, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-black/5 transition-colors"
                  >
                    <Badge
                      variant="secondary"
                      className="w-6 h-6 p-0 flex items-center justify-center text-[11px] shrink-0"
                    >
                      {i + 1}
                    </Badge>
                    <span className="text-sm flex-1 truncate">{q.query}</span>
                    <span className="text-sm text-muted-foreground shrink-0">
                      {q.count} 次
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-sm text-muted-foreground">
                暂无查询记录
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
