"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import { getConversation, streamChat } from "@/lib/api";
import useAgentStore, { type Conversation, type Message } from "@/lib/store";

interface ChatWindowProps {
  agentId: string;
}

export default function ChatWindow({ agentId }: ChatWindowProps) {
  const [inputMessage, setInputMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const {
    conversations,
    activeConversation,
    isStreaming,
    streamingContent,
    addUserMessage,
    startStreaming,
    appendStreamToken,
    finishStreaming,
    setStreamError,
    setConversations,
    setActiveConversation,
  } = useAgentStore();

  const toConversation = (raw: unknown): Conversation | null => {
    if (!raw || typeof raw !== "object") {
      return null;
    }

    const src = raw as Record<string, unknown>;
    if (typeof src.id !== "string" || typeof src.agent_id !== "string") {
      return null;
    }

    const rawMessages = Array.isArray(src.messages) ? src.messages : [];
    const messages: Message[] = rawMessages
      .map((item): Message | null => {
        if (!item || typeof item !== "object") {
          return null;
        }

        const msg = item as Record<string, unknown>;
        const role = msg.role === "assistant" ? "assistant" : msg.role === "user" ? "user" : null;
        if (!role) {
          return null;
        }

        return {
          id: String(msg.id ?? crypto.randomUUID()),
          role,
          content: String(msg.content ?? ""),
          sources: Array.isArray(msg.sources) ? msg.sources : [],
          isStreaming: false,
          created_at: String(msg.created_at ?? new Date().toISOString()),
        };
      })
      .filter((value): value is Message => value !== null);

    return {
      id: src.id,
      agent_id: src.agent_id,
      title: typeof src.title === "string" ? src.title : "New conversation",
      messages,
    };
  };

  const messages = useMemo(() => activeConversation?.messages ?? [], [activeConversation]);
  const tokenCount = useMemo(() => {
    const text = isStreaming ? streamingContent : messages.map((m) => m.content).join(" ");
    const trimmed = text.trim();
    return trimmed ? trimmed.split(/\s+/).length : 0;
  }, [isStreaming, messages, streamingContent]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 220)}px`;
  }, [inputMessage]);

  const handleSend = async () => {
    if (!inputMessage.trim() || isStreaming) {
      return;
    }

    const message = inputMessage.trim();
    setInputMessage("");
    addUserMessage(message);
    startStreaming();

    setIsLoading(true);
    try {
      await streamChat(
        agentId,
        message,
        activeConversation?.id ?? null,
        (chunk) => {
          appendStreamToken(chunk.content ?? "");
        },
        async (done) => {
          finishStreaming(done.message_id ?? "", done.sources ?? [], done.usage ?? {});

          if (!done.conversation_id) {
            return;
          }

          try {
            const conversationResponse = await getConversation(agentId, done.conversation_id);
            const serverConversation = toConversation(conversationResponse);
            if (!serverConversation) {
              return;
            }

            const activeId = activeConversation?.id;
            const nextConversations = [...conversations];
            const existingIndex = nextConversations.findIndex(
              (conversation) =>
                conversation.id === serverConversation.id ||
                (activeId?.startsWith("temp-") && conversation.id === activeId),
            );

            if (existingIndex >= 0) {
              nextConversations[existingIndex] = serverConversation;
            } else {
              nextConversations.unshift(serverConversation);
            }

            setConversations(nextConversations);
            setActiveConversation(serverConversation);
          } catch {
            // Keep optimistic local state if conversation sync fails.
          }
        },
        (err) => {
          setStreamError(err);
        },
      );
    } catch (error) {
      const errMessage = error instanceof Error ? error.message : "Chat stream failed";
      setStreamError(errMessage);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-zinc-950 text-zinc-100">
      <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-3">
          {messages.map((message) => {
            const isUser = message.role === "user";
            return (
              <div
                key={message.id}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={[
                    "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
                    isUser
                      ? "bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white"
                      : "bg-zinc-800 text-zinc-100",
                  ].join(" ")}
                >
                  <div className="prose prose-invert max-w-none break-words prose-p:my-2 prose-pre:rounded-lg prose-pre:bg-black/30">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                  {!!message.sources?.length && (
                    <p className="mt-2 text-xs text-zinc-300">
                      Sources: {message.sources.length} documents
                    </p>
                  )}
                </div>
              </div>
            );
          })}

          {isStreaming && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl bg-zinc-800 px-4 py-3 text-sm text-zinc-100 shadow-sm">
                <div className="prose prose-invert max-w-none break-words prose-p:my-2">
                  <ReactMarkdown>{streamingContent || "Thinking..."}</ReactMarkdown>
                </div>
                <span className="ml-1 inline-block h-4 w-2 animate-pulse rounded-sm bg-violet-400 align-middle" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t border-zinc-800 bg-zinc-900/80 px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto flex w-full max-w-4xl items-end gap-3 rounded-2xl border border-zinc-700 bg-zinc-900 p-3">
          <textarea
            ref={inputRef}
            rows={1}
            value={inputMessage}
            onChange={(event) => setInputMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void handleSend();
              }
            }}
            placeholder="Ask anything..."
            className="max-h-[220px] min-h-[42px] flex-1 resize-none bg-transparent px-1 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-500"
          />

          <button
            type="button"
            onClick={() => {
              void handleSend();
            }}
            disabled={isStreaming || isLoading}
            className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>

        <div className="mx-auto mt-2 flex w-full max-w-4xl justify-end text-xs text-zinc-400">
          {isStreaming ? "Thinking..." : `${tokenCount} tokens`}
        </div>
      </div>
    </div>
  );
}
