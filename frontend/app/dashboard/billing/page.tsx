"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

import { axiosInstance } from "@/lib/api";

type BillingInfo = {
  plan: string;
  status: string;
  current_period_end: string | null;
  agent_count: number;
  agent_limit: number;
  message_count_today: number;
  message_limit_daily: number;
};

const planBadgeClasses: Record<string, string> = {
  free: "bg-zinc-700 text-zinc-200 border-zinc-600",
  pro: "bg-violet-500/20 text-violet-200 border-violet-400/40",
  team: "bg-emerald-500/20 text-emerald-200 border-emerald-400/40",
};

function clampPercent(value: number): number {
  if (Number.isNaN(value) || !Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, value));
}

export default function BillingPage() {
  const { isSignedIn } = useAuth();
  const [billingInfo, setBillingInfo] = useState<BillingInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [upgrading, setUpgrading] = useState<boolean>(false);

  useEffect(() => {
    const fetchBillingInfo = async () => {
      setLoading(true);
      try {
        const response = await axiosInstance.get<BillingInfo>("/api/v1/analytics/billing-info");
        setBillingInfo(response.data);
      } catch {
        setBillingInfo(null);
      } finally {
        setLoading(false);
      }
    };

    if (isSignedIn) {
      void fetchBillingInfo();
    } else {
      setLoading(false);
    }
  }, [isSignedIn]);

  const handleUpgrade = async (plan: "pro" | "team") => {
    setUpgrading(true);
    try {
      const response = await axiosInstance.post<{ checkout_url: string }>("/api/v1/billing/checkout", {
        plan,
        success_url: `${window.location.origin}/dashboard/billing?success=true`,
        cancel_url: `${window.location.origin}/dashboard/billing`,
      });

      window.location.href = response.data.checkout_url;
    } finally {
      setUpgrading(false);
    }
  };

  const handleManageBilling = async () => {
    const response = await axiosInstance.post<{ portal_url: string }>("/api/v1/billing/portal");
    window.location.href = response.data.portal_url;
  };

  const normalizedPlan = (billingInfo?.plan || "free").toLowerCase();
  const agentUsagePercent = clampPercent(
    ((billingInfo?.agent_count || 0) / Math.max(1, billingInfo?.agent_limit || 1)) * 100,
  );
  const messageUsagePercent = clampPercent(
    ((billingInfo?.message_count_today || 0) / Math.max(1, billingInfo?.message_limit_daily || 1)) * 100,
  );

  return (
    <div className="min-h-screen bg-zinc-950 px-6 py-8 text-zinc-100 md:px-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight">Billing &amp; Plans</h1>
          {upgrading && (
            <div className="inline-flex items-center gap-2 rounded-lg border border-violet-500/40 bg-violet-500/10 px-3 py-2 text-sm text-violet-200">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet-300 border-t-transparent" />
              Redirecting to checkout...
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6">
          {loading ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-6 w-40 rounded bg-zinc-800" />
              <div className="h-3 w-full rounded bg-zinc-800" />
              <div className="h-3 w-full rounded bg-zinc-800" />
            </div>
          ) : !billingInfo ? (
            <p className="text-zinc-400">Unable to load billing info.</p>
          ) : (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-zinc-400">Current Plan</p>
                  <span
                    className={[
                      "mt-2 inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase",
                      planBadgeClasses[normalizedPlan] || planBadgeClasses.free,
                    ].join(" ")}
                  >
                    {normalizedPlan}
                  </span>
                </div>

                {normalizedPlan !== "free" && (
                  <button
                    type="button"
                    onClick={() => {
                      void handleManageBilling();
                    }}
                    className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200 transition hover:bg-zinc-800"
                  >
                    Manage Billing
                  </button>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <div className="mb-1 flex items-center justify-between text-sm text-zinc-300">
                    <span>Agents</span>
                    <span>
                      {billingInfo.agent_count} / {billingInfo.agent_limit} used
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-zinc-800">
                    <div
                      className="h-2 rounded-full bg-violet-500"
                      style={{ width: `${agentUsagePercent}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-1 flex items-center justify-between text-sm text-zinc-300">
                    <span>Messages today</span>
                    <span>
                      {billingInfo.message_count_today} / {billingInfo.message_limit_daily}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-zinc-800">
                    <div
                      className="h-2 rounded-full bg-sky-500"
                      style={{ width: `${messageUsagePercent}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6">
            <p className="text-xs uppercase tracking-wider text-zinc-400">Free</p>
            <p className="mt-2 text-3xl font-semibold">$0<span className="text-base text-zinc-400">/month</span></p>
            <ul className="mt-5 space-y-2 text-sm text-zinc-300">
              <li>3 agents</li>
              <li>100 messages/day</li>
              <li>1 knowledge base</li>
            </ul>
            <button
              type="button"
              disabled={normalizedPlan === "free"}
              className="mt-6 w-full rounded-lg bg-zinc-700 px-4 py-2 text-sm text-zinc-200 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {normalizedPlan === "free" ? "Current Plan" : "Downgrade to Free"}
            </button>
          </div>

          <div className="relative rounded-2xl border border-violet-500/60 bg-zinc-900/80 p-6 shadow-[0_0_0_1px_rgba(139,92,246,0.2)]">
            <span className="absolute -top-3 right-4 rounded-full bg-violet-600 px-3 py-1 text-xs font-semibold text-white">
              Most Popular
            </span>
            <p className="text-xs uppercase tracking-wider text-violet-300">Pro</p>
            <p className="mt-2 text-3xl font-semibold">$29<span className="text-base text-zinc-400">/month</span></p>
            <ul className="mt-5 space-y-2 text-sm text-zinc-300">
              <li>Unlimited agents</li>
              <li>10,000 messages/day</li>
              <li>All LLM providers</li>
              <li>Priority support</li>
            </ul>
            <button
              type="button"
              disabled={upgrading || normalizedPlan === "pro"}
              onClick={() => {
                void handleUpgrade("pro");
              }}
              className="mt-6 w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {normalizedPlan === "pro" ? "Current Plan" : "Upgrade to Pro"}
            </button>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6">
            <p className="text-xs uppercase tracking-wider text-zinc-400">Team</p>
            <p className="mt-2 text-3xl font-semibold">$99<span className="text-base text-zinc-400">/month</span></p>
            <ul className="mt-5 space-y-2 text-sm text-zinc-300">
              <li>Everything in Pro</li>
              <li>100,000 messages/day</li>
              <li>Team management</li>
              <li>Analytics export</li>
              <li>SLA</li>
            </ul>
            <button
              type="button"
              disabled={upgrading || normalizedPlan === "team"}
              onClick={() => {
                void handleUpgrade("team");
              }}
              className="mt-6 w-full rounded-lg border border-zinc-600 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-100 transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {normalizedPlan === "team" ? "Current Plan" : "Upgrade to Team"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
