"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import {
  BarChart2,
  BookOpen,
  Bot,
  CreditCard,
  MessageSquare,
  Settings,
  Zap,
} from "lucide-react";

const navItems = [
  { href: "/dashboard/agents", icon: Bot, label: "Agents" },
  { href: "/dashboard/chat", icon: MessageSquare, label: "Chat" },
  { href: "/dashboard/knowledge", icon: BookOpen, label: "Knowledge" },
  { href: "/dashboard/analytics", icon: BarChart2, label: "Analytics" },
  { href: "/dashboard/billing", icon: CreditCard, label: "Billing" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-[240px] border-r border-zinc-800 bg-[#0f0f1a] px-4 py-5">
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="rounded-lg bg-violet-500/20 p-1.5 text-violet-400">
          <Zap className="h-5 w-5" />
        </div>
        <span className="text-xl font-bold tracking-tight text-white">Forgent</span>
      </div>

      <nav className="space-y-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                isActive
                  ? "bg-violet-600/30 text-white"
                  : "text-zinc-400 hover:bg-zinc-800/70 hover:text-zinc-200",
              ].join(" ")}
            >
              <Icon className="h-4.5 w-4.5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="absolute bottom-4 left-4 right-4 rounded-xl border border-zinc-800 bg-zinc-900/70 px-3 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <Settings className="h-3.5 w-3.5" />
            <span>Account</span>
          </div>
          <UserButton />
        </div>
      </div>
    </aside>
  );
}
