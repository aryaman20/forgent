"use client";

import { SignInButton, UserButton, useAuth } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import ChatWindow from "@/components/chat/ChatWindow";
import { getAgent, getConversations } from "@/lib/api";
import useAgentStore, { type Agent, type Conversation, type Message } from "@/lib/store";

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord => {
  return typeof value === "object" && value !== null;
};

const asAgent = (value: unknown): Agent | null => {
  if (!isRecord(value)) {
    return null;
  }

  if (typeof value.id !== "string" || typeof value.name !== "string") {
    return null;
  }

  return {
    id: value.id,
    name: value.name,
    description: typeof value.description === "string" ? value.description : "",
    model_provider: typeof value.model_provider === "string" ? value.model_provider : "",
    model_name: typeof value.model_name === "string" ? value.model_name : "",
    has_knowledge_base: Boolean(value.has_knowledge_base),
    is_active: value.is_active !== false,
    created_at: typeof value.created_at === "string" ? value.created_at : new Date().toISOString(),
  };
};

const asConversations = (value: unknown): Conversation[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (!isRecord(item)) {
        return null;
      }

      if (typeof item.id !== "string" || typeof item.agent_id !== "string") {
        return null;
      }

      const messages: Message[] = Array.isArray(item.messages)
        ? item.messages
            .map((msg) => {
              if (!isRecord(msg)) {
                return null;
              }

              const role = msg.role === "assistant" ? "assistant" : msg.role === "user" ? "user" : null;
              if (!role) {
                return null;
              }

              return {
                id: typeof msg.id === "string" ? msg.id : crypto.randomUUID(),
                role,
                content: typeof msg.content === "string" ? msg.content : "",
                sources: Array.isArray(msg.sources) ? msg.sources : [],
                isStreaming: false,
                created_at:
                  typeof msg.created_at === "string" ? msg.created_at : new Date().toISOString(),
              } as Message;
            })
            .filter((msg): msg is Message => msg !== null)
        : [];

      return {
        id: item.id,
        agent_id: item.agent_id,
        title: typeof item.title === "string" ? item.title : "Untitled conversation",
        messages,
      } as Conversation;
    })
    .filter((conversation): conversation is Conversation => conversation !== null);
};

export default function ChatPage() {
  const { isLoaded, isSignedIn } = useAuth();
  const params = useParams();
  const agentId = useMemo(() => {
    const raw = params?.agentId;
    if (Array.isArray(raw)) {
      return raw[0] ?? "";
    }
    return typeof raw === "string" ? raw : "";
  }, [params]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  const {
    selectedAgent,
    conversations,
    activeConversation,
    setSelectedAgent,
    setConversations,
    setActiveConversation,
  } = useAgentStore();

  useEffect(() => {
    if (!agentId) {
      return;
    }
    if (!isSignedIn) {
      setSelectedAgent(null);
      setConversations([]);
      setActiveConversation(null);
      setIsLoading(false);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      setError("");

      try {
        const [agentResponse, conversationResponse] = await Promise.all([
          getAgent(agentId),
          getConversations(agentId),
        ]);

        const parsedAgent = asAgent(agentResponse);
        if (!parsedAgent) {
          throw new Error("Invalid agent response");
        }

        const parsedConversations = asConversations(conversationResponse);

        setSelectedAgent(parsedAgent);
        setConversations(parsedConversations);
        setActiveConversation(parsedConversations[0] ?? null);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load chat data";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, [agentId, isSignedIn, setActiveConversation, setConversations, setSelectedAgent]);

  return (
    <div className="flex h-screen min-h-0 bg-zinc-950 text-zinc-100">
      <aside className="hidden w-72 shrink-0 border-r border-zinc-800 bg-zinc-900/70 md:block">
        <div className="border-b border-zinc-800 px-4 py-3 text-sm font-semibold text-zinc-300">
          Conversations
        </div>
        <div className="max-h-[calc(100vh-56px)] space-y-2 overflow-y-auto px-3 py-3">
          {conversations.map((conversation) => {
            const isActive = activeConversation?.id === conversation.id;
            return (
              <button
                key={conversation.id}
                type="button"
                onClick={() => setActiveConversation(conversation)}
                className={[
                  "w-full rounded-lg border px-3 py-2 text-left text-sm transition",
                  isActive
                    ? "border-violet-500/70 bg-violet-500/10 text-violet-100"
                    : "border-zinc-800 bg-zinc-900 text-zinc-300 hover:border-zinc-700",
                ].join(" ")}
              >
                <p className="truncate font-medium">{conversation.title || "Untitled conversation"}</p>
                <p className="mt-1 text-xs text-zinc-500">{conversation.messages.length} messages</p>
              </button>
            );
          })}
          {!conversations.length && !isLoading && (
            <p className="px-1 py-2 text-sm text-zinc-500">No conversations yet.</p>
          )}
        </div>
      </aside>

      <div className="flex min-h-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-zinc-800 bg-zinc-900/60 px-4 py-3">
          <h1 className="truncate text-base font-semibold text-zinc-100">
            {selectedAgent?.name || "Loading agent..."}
          </h1>
          {selectedAgent?.model_provider && (
            <span className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300">
              {selectedAgent.model_provider}
            </span>
          )}
          <span
            className={[
              "rounded-full border px-2 py-0.5 text-xs",
              selectedAgent?.has_knowledge_base
                ? "border-emerald-600/50 bg-emerald-600/15 text-emerald-300"
                : "border-zinc-700 bg-zinc-800 text-zinc-400",
            ].join(" ")}
          >
            {selectedAgent?.has_knowledge_base ? "Knowledge Base" : "No Knowledge Base"}
          </span>
        </header>

        <main className="min-h-0 flex-1">
          {!isLoaded ? (
            <div className="flex h-full items-center justify-center text-zinc-400">Loading auth...</div>
          ) : !isSignedIn ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
              <p className="text-zinc-300">Sign in to access this agent chat.</p>
              <SignInButton mode="modal">
                <button
                  type="button"
                  className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
                >
                  Sign in with Clerk
                </button>
              </SignInButton>
            </div>
          ) : isLoading ? (
            <div className="flex h-full items-center justify-center text-zinc-400">Loading chat...</div>
          ) : error ? (
            <div className="flex h-full items-center justify-center px-6 text-center text-red-300">
              {error}
            </div>
          ) : (
            <ChatWindow agentId={agentId} />
          )}
        </main>
      </div>

      <div className="fixed right-4 top-4 z-20 rounded-full border border-zinc-700 bg-zinc-900/90 p-1">
        {isSignedIn ? (
          <UserButton />
        ) : (
          <SignInButton mode="modal">
            <button
              type="button"
              className="rounded-full px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Sign in
            </button>
          </SignInButton>
        )}
      </div>
    </div>
  );
}
