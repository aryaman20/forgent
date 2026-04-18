"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { SignInButton, UserButton, useAuth } from "@clerk/nextjs";

import ChatWindow from "@/components/chat/ChatWindow";
import { createAgent, getAgents, getConversation, getConversations } from "@/lib/api";
import useAgentStore, { type Agent, type Conversation, type Message } from "@/lib/store";

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord => {
  return typeof value === "object" && value !== null;
};

const asArray = (value: unknown): unknown[] => {
  if (Array.isArray(value)) {
    return value;
  }
  if (isRecord(value) && Array.isArray(value.items)) {
    return value.items;
  }
  if (isRecord(value) && Array.isArray(value.data)) {
    return value.data;
  }
  return [];
};

const parseAgent = (raw: unknown): Agent | null => {
  if (!isRecord(raw)) {
    return null;
  }

  if (typeof raw.id !== "string" || typeof raw.name !== "string") {
    return null;
  }

  return {
    id: raw.id,
    name: raw.name,
    description: typeof raw.description === "string" ? raw.description : "",
    model_provider: typeof raw.model_provider === "string" ? raw.model_provider : "",
    model_name: typeof raw.model_name === "string" ? raw.model_name : "",
    has_knowledge_base: Boolean(raw.has_knowledge_base),
    is_active: raw.is_active !== false,
    created_at: typeof raw.created_at === "string" ? raw.created_at : new Date().toISOString(),
  };
};

const parseMessage = (raw: unknown): Message | null => {
  if (!isRecord(raw)) {
    return null;
  }

  const role = raw.role === "assistant" ? "assistant" : raw.role === "user" ? "user" : null;
  if (!role) {
    return null;
  }

  return {
    id: typeof raw.id === "string" ? raw.id : crypto.randomUUID(),
    role,
    content: typeof raw.content === "string" ? raw.content : "",
    sources: Array.isArray(raw.sources) ? raw.sources : [],
    isStreaming: false,
    created_at: typeof raw.created_at === "string" ? raw.created_at : new Date().toISOString(),
  };
};

const parseConversation = (raw: unknown): Conversation | null => {
  if (!isRecord(raw)) {
    return null;
  }

  if (typeof raw.id !== "string" || typeof raw.agent_id !== "string") {
    return null;
  }

  return {
    id: raw.id,
    agent_id: raw.agent_id,
    title: typeof raw.title === "string" ? raw.title : "New conversation",
    messages: asArray(raw.messages)
      .map(parseMessage)
      .filter((value): value is Message => value !== null),
  };
};

export default function ChatDashboardPage() {
  const { isLoaded, isSignedIn } = useAuth();
  const [isBootstrapping, setIsBootstrapping] = useState<boolean>(true);
  const [isLoadingConversations, setIsLoadingConversations] = useState<boolean>(false);
  const [isCreatingAgent, setIsCreatingAgent] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const {
    agents,
    selectedAgent,
    conversations,
    activeConversation,
    setAgents,
    setSelectedAgent,
    setConversations,
    setActiveConversation,
  } = useAgentStore();

  const activeAgentId = selectedAgent?.id ?? "";

  const boot = useCallback(async () => {
    if (!isSignedIn) {
      setIsBootstrapping(false);
      setAgents([]);
      setSelectedAgent(null);
      setConversations([]);
      setActiveConversation(null);
      return;
    }

    setIsBootstrapping(true);
    setError("");

    try {
      const response = await getAgents(1, 50);
      const parsedAgents = asArray(response)
        .map(parseAgent)
        .filter((value): value is Agent => value !== null);

      setAgents(parsedAgents);

      if (!parsedAgents.length) {
        setSelectedAgent(null);
        setConversations([]);
        setActiveConversation(null);
        return;
      }

      const nextAgent = parsedAgents[0];
      setSelectedAgent(nextAgent);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load agents";
      setError(message);
    } finally {
      setIsBootstrapping(false);
    }
  }, [isSignedIn, setActiveConversation, setAgents, setConversations, setSelectedAgent]);

  const loadConversations = useCallback(
    async (agentId: string) => {
      if (!agentId) {
        return;
      }
      if (!isSignedIn) {
        setConversations([]);
        setActiveConversation(null);
        return;
      }

      setIsLoadingConversations(true);
      setError("");

      try {
        const response = await getConversations(agentId);
        const parsedConversations = asArray(response)
          .map(parseConversation)
          .filter((value): value is Conversation => value !== null);

        setConversations(parsedConversations);

        if (!parsedConversations.length) {
          setActiveConversation(null);
          return;
        }

        const existing = activeConversation;
        const sameAgent = existing?.agent_id === agentId;
        if (sameAgent) {
          const updated = parsedConversations.find((conversation) => conversation.id === existing.id);
          setActiveConversation(updated ?? parsedConversations[0]);
        } else {
          setActiveConversation(parsedConversations[0]);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load conversations";
        setError(message);
      } finally {
        setIsLoadingConversations(false);
      }
    },
    [activeConversation, isSignedIn, setActiveConversation, setConversations],
  );

  useEffect(() => {
    void boot();
  }, [boot]);

  useEffect(() => {
    if (!selectedAgent?.id) {
      return;
    }
    void loadConversations(selectedAgent.id);
  }, [loadConversations, selectedAgent?.id]);

  const selectConversation = async (conversation: Conversation) => {
    setActiveConversation(conversation);

    if (conversation.messages.length > 0) {
      return;
    }

    try {
      const response = await getConversation(conversation.agent_id, conversation.id);
      const fullConversation = parseConversation(response);
      if (!fullConversation) {
        return;
      }

      setActiveConversation(fullConversation);
      setConversations(
        conversations.map((item) => (item.id === fullConversation.id ? fullConversation : item)),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load conversation details";
      setError(message);
    }
  };

  const startNewConversation = () => {
    setActiveConversation(null);
  };

  const createFirstAgent = async () => {
    setError("");
    setIsCreatingAgent(true);

    try {
      const response = await createAgent({
        name: "My First Agent",
        description: "Auto-created starter agent",
        system_prompt: "You are a helpful assistant for my documents and chats.",
        model_provider: "openai",
        model_name: "gpt-4o",
        temperature: 0.7,
        max_tokens: 2048,
        tools_config: [],
        retrieval_config: {
          top_k: 5,
          strategy: "hybrid",
          rerank: true,
          score_threshold: 0.5,
        },
      });

      const parsed = parseAgent(response);
      if (!parsed) {
        throw new Error("Agent created but response was invalid");
      }

      const nextAgents = [parsed, ...agents];
      setAgents(nextAgents);
      setSelectedAgent(parsed);
      setConversations([]);
      setActiveConversation(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create agent";
      setError(message);
    } finally {
      setIsCreatingAgent(false);
    }
  };

  const header = useMemo(() => {
    if (!selectedAgent) {
      return "No agent selected";
    }
    return selectedAgent.name;
  }, [selectedAgent]);

  return (
    <div className="flex h-screen min-h-0 bg-zinc-950 text-zinc-100">
      <aside className="flex w-[320px] shrink-0 flex-col border-r border-zinc-800 bg-zinc-900/70">
        <div className="border-b border-zinc-800 p-4">
          <h1 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Live Chat</h1>
          <p className="mt-1 truncate text-lg font-semibold text-zinc-100">{header}</p>
        </div>

        <div className="space-y-3 p-4">
          <label htmlFor="agent-select" className="text-xs font-medium text-zinc-400">
            Agent
          </label>
          <select
            id="agent-select"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
            value={selectedAgent?.id ?? ""}
            onChange={(event) => {
              const agent = agents.find((item) => item.id === event.target.value) ?? null;
              setSelectedAgent(agent);
              setActiveConversation(null);
            }}
          >
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={startNewConversation}
            disabled={!selectedAgent}
            className="w-full rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            New Chat
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
          {isLoadingConversations ? (
            <p className="px-2 py-3 text-sm text-zinc-400">Loading conversations...</p>
          ) : conversations.length === 0 ? (
            <p className="px-2 py-3 text-sm text-zinc-500">No conversations yet.</p>
          ) : (
            conversations.map((conversation) => {
              const isActive = activeConversation?.id === conversation.id;
              return (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => {
                    void selectConversation(conversation);
                  }}
                  className={[
                    "mb-2 w-full rounded-lg px-3 py-3 text-left transition",
                    isActive
                      ? "border border-violet-500/60 bg-violet-500/10"
                      : "border border-zinc-800 bg-zinc-900 hover:border-zinc-700",
                  ].join(" ")}
                >
                  <p className="truncate text-sm font-medium text-zinc-100">
                    {conversation.title || "Untitled conversation"}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">{conversation.messages.length} messages</p>
                </button>
              );
            })
          )}
        </div>
      </aside>

      <main className="min-h-0 flex-1">
        {!isLoaded ? (
          <div className="flex h-full items-center justify-center text-zinc-400">Loading auth...</div>
        ) : !isSignedIn ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
            <p className="text-zinc-300">Sign in to access your agents and chats.</p>
            <SignInButton mode="modal">
              <button
                type="button"
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
              >
                Sign in with Clerk
              </button>
            </SignInButton>
          </div>
        ) : isBootstrapping ? (
          <div className="flex h-full items-center justify-center text-zinc-400">Loading chat workspace...</div>
        ) : !selectedAgent ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
            <p className="text-zinc-300">No agents found. Create an agent first to start chatting.</p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  void createFirstAgent();
                }}
                disabled={isCreatingAgent}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreatingAgent ? "Creating..." : "Create Agent"}
              </button>
              <button
                type="button"
                onClick={() => {
                  void boot();
                }}
                className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
              >
                Retry
              </button>
            </div>
          </div>
        ) : (
          <ChatWindow agentId={activeAgentId} />
        )}
      </main>

      {!!error && (
        <div className="pointer-events-none fixed bottom-4 right-4 max-w-sm rounded-lg border border-red-500/30 bg-red-950/90 px-4 py-3 text-sm text-red-200 shadow-xl">
          {error}
        </div>
      )}

      <div className="fixed right-4 top-4 z-20 rounded-full border border-zinc-700 bg-zinc-900/90 p-1">
        {isSignedIn ? (
          <UserButton afterSignOutUrl="/" />
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
