"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Clock3, DollarSign, MessageSquare, Zap } from "lucide-react";

import { axiosInstance } from "@/lib/api";

type AnalyticsSummary = {
  period_days: number;
  total_messages: number;
  total_tokens_input: number;
  total_tokens_output: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  daily_stats: DailyUsageStat[];
  agent_stats: AgentUsageStat[];
  top_model: string | null;
};

type DailyUsageStat = {
  date: string;
  total_messages: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
};

type AgentUsageStat = {
  agent_id: string;
  agent_name: string;
  total_messages: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms?: number;
};

const PERIODS = [7, 30, 90] as const;
const PIE_COLORS = ["#8b5cf6", "#a78bfa", "#c4b5fd", "#ddd6fe"];

const formatNumber = (value: number): string => {
  return new Intl.NumberFormat("en-US").format(value);
};

const formatCurrency = (value: number): string => {
  return `$${value.toFixed(2)}`;
};

function StatCardSkeleton() {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5 animate-pulse">
      <div className="mb-4 h-9 w-9 rounded-lg bg-zinc-800" />
      <div className="mb-2 h-8 w-24 rounded bg-zinc-800" />
      <div className="h-4 w-20 rounded bg-zinc-800" />
    </div>
  );
}

function ChartSkeleton() {
  return <div className="h-[320px] w-full animate-pulse rounded-2xl bg-zinc-900/80 border border-zinc-800" />;
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyUsageStat[]>([]);
  const [agentStats, setAgentStats] = useState<AgentUsageStat[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [days, setDays] = useState<number>(30);

  useEffect(() => {
    const fetchSummary = async () => {
      setLoading(true);

      try {
        const response = await axiosInstance.get<AnalyticsSummary>(`/api/v1/analytics/summary?days=${days}`);
        const data = response.data;
        setSummary(data);
        setDailyStats(data.daily_stats || []);
        setAgentStats(data.agent_stats || []);
      } catch {
        setSummary(null);
        setDailyStats([]);
        setAgentStats([]);
      } finally {
        setLoading(false);
      }
    };

    void fetchSummary();
  }, [days]);

  const totalTokens = (summary?.total_tokens_input || 0) + (summary?.total_tokens_output || 0);
  const sortedAgents = [...agentStats].sort((a, b) => b.total_messages - a.total_messages);

  return (
    <div className="min-h-screen bg-zinc-950 px-6 py-8 text-zinc-100 md:px-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight">Analytics Dashboard</h1>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-1">
            {PERIODS.map((period) => (
              <button
                key={period}
                type="button"
                onClick={() => setDays(period)}
                className={[
                  "rounded-lg px-4 py-2 text-sm transition",
                  days === period
                    ? "bg-violet-600 text-white"
                    : "text-zinc-300 hover:bg-zinc-800",
                ].join(" ")}
              >
                {period}D
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {loading ? (
            <>
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
            </>
          ) : (
            <>
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <div className="mb-3 inline-flex rounded-lg bg-sky-500/20 p-2 text-sky-300">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <p className="text-3xl font-semibold">{formatNumber(summary?.total_messages || 0)}</p>
                <p className="mt-1 text-sm text-zinc-400">Total Messages</p>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <div className="mb-3 inline-flex rounded-lg bg-violet-500/20 p-2 text-violet-300">
                  <Zap className="h-5 w-5" />
                </div>
                <p className="text-3xl font-semibold">{formatNumber(totalTokens)}</p>
                <p className="mt-1 text-sm text-zinc-400">Total Tokens</p>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <div className="mb-3 inline-flex rounded-lg bg-emerald-500/20 p-2 text-emerald-300">
                  <DollarSign className="h-5 w-5" />
                </div>
                <p className="text-3xl font-semibold">{formatCurrency(summary?.total_cost_usd || 0)}</p>
                <p className="mt-1 text-sm text-zinc-400">Total Cost</p>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <div className="mb-3 inline-flex rounded-lg bg-amber-500/20 p-2 text-amber-300">
                  <Clock3 className="h-5 w-5" />
                </div>
                <p className="text-3xl font-semibold">{Math.round(summary?.avg_latency_ms || 0)}ms</p>
                <p className="mt-1 text-sm text-zinc-400">Avg Latency</p>
              </div>
            </>
          )}
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
          <div className="xl:col-span-3 rounded-2xl border border-zinc-800 bg-zinc-900/80 p-4">
            <h2 className="mb-3 text-sm font-medium text-zinc-300">Daily Messages</h2>
            {loading ? (
              <ChartSkeleton />
            ) : (
              <div className="h-[320px] w-full">
                <ResponsiveContainer>
                  <LineChart data={dailyStats}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                    <XAxis dataKey="date" stroke="#a1a1aa" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#a1a1aa" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        border: "1px solid #3f3f46",
                        borderRadius: "12px",
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="total_messages"
                      name="Messages"
                      stroke="#8b5cf6"
                      strokeWidth={3}
                      dot={{ r: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="xl:col-span-2 rounded-2xl border border-zinc-800 bg-zinc-900/80 p-4">
            <h2 className="mb-3 text-sm font-medium text-zinc-300">Cost Per Day</h2>
            {loading ? (
              <ChartSkeleton />
            ) : (
              <div className="h-[320px] w-full">
                <ResponsiveContainer>
                  <BarChart data={dailyStats}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                    <XAxis dataKey="date" stroke="#a1a1aa" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#a1a1aa" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        border: "1px solid #3f3f46",
                        borderRadius: "12px",
                      }}
                    />
                    <Legend />
                    <Bar dataKey="total_cost_usd" name="Cost (USD)" fill="#a855f7" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
          <div className="xl:col-span-3 rounded-2xl border border-zinc-800 bg-zinc-900/80 p-4">
            <h2 className="mb-3 text-sm font-medium text-zinc-300">Agent Leaderboard</h2>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, idx) => (
                  <div key={idx} className="h-11 animate-pulse rounded bg-zinc-800" />
                ))}
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-zinc-800">
                <table className="w-full text-sm">
                  <thead className="bg-zinc-900">
                    <tr className="text-left text-zinc-400">
                      <th className="px-4 py-3 font-medium">Agent Name</th>
                      <th className="px-4 py-3 font-medium">Messages</th>
                      <th className="px-4 py-3 font-medium">Tokens</th>
                      <th className="px-4 py-3 font-medium">Cost</th>
                      <th className="px-4 py-3 font-medium">Avg Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedAgents.map((agent) => (
                      <tr key={agent.agent_id} className="border-t border-zinc-800 hover:bg-zinc-800/40">
                        <td className="px-4 py-3 font-semibold text-zinc-100">{agent.agent_name}</td>
                        <td className="px-4 py-3 text-zinc-300">{formatNumber(agent.total_messages)}</td>
                        <td className="px-4 py-3 text-zinc-300">{formatNumber(agent.total_tokens)}</td>
                        <td className="px-4 py-3 text-zinc-300">{formatCurrency(agent.total_cost_usd)}</td>
                        <td className="px-4 py-3 text-zinc-300">
                          {typeof agent.avg_latency_ms === "number"
                            ? `${Math.round(agent.avg_latency_ms)}ms`
                            : "--"}
                        </td>
                      </tr>
                    ))}
                    {sortedAgents.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-4 py-6 text-center text-zinc-500">
                          No usage data yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="xl:col-span-2 rounded-2xl border border-zinc-800 bg-zinc-900/80 p-4">
            <h2 className="mb-3 text-sm font-medium text-zinc-300">Messages Share</h2>
            {loading ? (
              <ChartSkeleton />
            ) : (
              <div className="h-[320px] w-full">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={sortedAgents.slice(0, 4)}
                      dataKey="total_messages"
                      nameKey="agent_name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label
                    >
                      {sortedAgents.slice(0, 4).map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        border: "1px solid #3f3f46",
                        borderRadius: "12px",
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
