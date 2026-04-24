import Sidebar from "@/components/ui/Sidebar";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default async function DashboardLayout({ children }: DashboardLayoutProps) {
  const { userId } = await auth();

  if (!userId) {
    redirect("/sign-in");
  }

  return (
    <div className="flex h-screen bg-[#0b0b14]">
      <Sidebar />
      <main className="ml-[240px] flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
