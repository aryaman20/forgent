import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0b0b14] p-6 text-white">
      <div className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-900/70 p-8 shadow-2xl">
        <h1 className="text-3xl font-bold tracking-tight">Forgent</h1>
        <p className="mt-3 text-zinc-300">
          Open the dashboard directly or sign in to continue.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/dashboard/chat"
            className="rounded-lg bg-violet-600 px-4 py-2 font-medium text-white transition hover:bg-violet-500"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/sign-in"
            className="rounded-lg border border-zinc-700 px-4 py-2 font-medium text-zinc-100 transition hover:bg-zinc-800"
          >
            Sign In
          </Link>
        </div>
      </div>
    </main>
  );
}
