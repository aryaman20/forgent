import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

export interface Agent {
	id: string;
	name: string;
	description: string;
	model_provider: string;
	model_name: string;
	has_knowledge_base: boolean;
	is_active: boolean;
	created_at: string;
}

export interface Message {
	id: string;
	role: "user" | "assistant";
	content: string;
	sources: unknown[];
	isStreaming: boolean;
	created_at: string;
}

export interface Conversation {
	id: string;
	agent_id: string;
	title: string;
	messages: Message[];
}

interface AgentStoreState {
	agents: Agent[];
	selectedAgent: Agent | null;
	conversations: Conversation[];
	activeConversation: Conversation | null;
	isStreaming: boolean;
	streamingContent: string;
	setAgents: (agents: Agent[]) => void;
	addAgent: (agent: Agent) => void;
	updateAgent: (id: string, updates: Partial<Agent>) => void;
	removeAgent: (id: string) => void;
	setSelectedAgent: (agent: Agent | null) => void;
	setConversations: (conversations: Conversation[]) => void;
	setActiveConversation: (conversation: Conversation | null) => void;
	addUserMessage: (content: string) => void;
	startStreaming: () => void;
	appendStreamToken: (token: string) => void;
	finishStreaming: (messageId: string, sources: unknown[], usage: unknown) => void;
	setStreamError: (error: string) => void;
}

const useAgentStore = create<AgentStoreState>()(
	immer((set) => ({
		agents: [],
		selectedAgent: null,
		conversations: [],
		activeConversation: null,
		isStreaming: false,
		streamingContent: "",

		setAgents: (agents) =>
			set((state) => {
				state.agents = agents;
			}),

		addAgent: (agent) =>
			set((state) => {
				state.agents.unshift(agent);
			}),

		updateAgent: (id, updates) =>
			set((state) => {
				const index = state.agents.findIndex((agent) => agent.id === id);
				if (index !== -1) {
					state.agents[index] = { ...state.agents[index], ...updates };
				}

				if (state.selectedAgent?.id === id) {
					state.selectedAgent = { ...state.selectedAgent, ...updates };
				}
			}),

		removeAgent: (id) =>
			set((state) => {
				state.agents = state.agents.filter((agent) => agent.id !== id);
				if (state.selectedAgent?.id === id) {
					state.selectedAgent = null;
				}
			}),

		setSelectedAgent: (agent) =>
			set((state) => {
				state.selectedAgent = agent;
			}),

		setConversations: (conversations) =>
			set((state) => {
				state.conversations = conversations;
			}),

		setActiveConversation: (conversation) =>
			set((state) => {
				state.activeConversation = conversation;
			}),

		addUserMessage: (content) =>
			set((state) => {
				if (!state.activeConversation) {
					if (!state.selectedAgent) {
						return;
					}

					const draftConversation: Conversation = {
						id: `temp-${crypto.randomUUID()}`,
						agent_id: state.selectedAgent.id,
						title: "New conversation",
						messages: [],
					};

					state.activeConversation = draftConversation;
					state.conversations.unshift(draftConversation);
				}

				const userMessage: Message = {
					id: crypto.randomUUID(),
					role: "user",
					content,
					sources: [],
					isStreaming: false,
					created_at: new Date().toISOString(),
				};

				state.activeConversation.messages.push(userMessage);

				const conversationIndex = state.conversations.findIndex(
					(conversation) => conversation.id === state.activeConversation?.id,
				);
				if (conversationIndex !== -1) {
					state.conversations[conversationIndex].messages = [
						...state.activeConversation.messages,
					];
				}
			}),

		startStreaming: () =>
			set((state) => {
				state.isStreaming = true;
				state.streamingContent = "";

				if (!state.activeConversation) {
					if (!state.selectedAgent) {
						return;
					}

					const draftConversation: Conversation = {
						id: `temp-${crypto.randomUUID()}`,
						agent_id: state.selectedAgent.id,
						title: "New conversation",
						messages: [],
					};

					state.activeConversation = draftConversation;
					state.conversations.unshift(draftConversation);
				}

				const assistantMessage: Message = {
					id: crypto.randomUUID(),
					role: "assistant",
					content: "",
					sources: [],
					isStreaming: true,
					created_at: new Date().toISOString(),
				};

				state.activeConversation.messages.push(assistantMessage);

				const conversationIndex = state.conversations.findIndex(
					(conversation) => conversation.id === state.activeConversation?.id,
				);
				if (conversationIndex !== -1) {
					state.conversations[conversationIndex].messages = [
						...state.activeConversation.messages,
					];
				}
			}),

		appendStreamToken: (token) =>
			set((state) => {
				if (!state.isStreaming || !state.activeConversation) {
					return;
				}

				state.streamingContent += token;

				const lastMessage =
					state.activeConversation.messages[state.activeConversation.messages.length - 1];
				if (lastMessage && lastMessage.role === "assistant" && lastMessage.isStreaming) {
					lastMessage.content += token;
				}

				const conversationIndex = state.conversations.findIndex(
					(conversation) => conversation.id === state.activeConversation?.id,
				);
				if (conversationIndex !== -1) {
					state.conversations[conversationIndex].messages = [
						...state.activeConversation.messages,
					];
				}
			}),

		finishStreaming: (messageId, sources, usage) =>
			set((state) => {
				if (!state.activeConversation) {
					state.isStreaming = false;
					state.streamingContent = "";
					return;
				}

				const target = state.activeConversation.messages.find(
					(message) => message.id === messageId,
				);

				if (target) {
					target.isStreaming = false;
					target.sources = sources;
				} else {
					const fallback =
						state.activeConversation.messages[state.activeConversation.messages.length - 1];
					if (fallback && fallback.role === "assistant") {
						fallback.isStreaming = false;
						fallback.sources = sources;
					}
				}

				const conversationIndex = state.conversations.findIndex(
					(conversation) => conversation.id === state.activeConversation?.id,
				);
				if (conversationIndex !== -1) {
					state.conversations[conversationIndex].messages = [
						...state.activeConversation.messages,
					];
				}

				void usage;
				state.isStreaming = false;
				state.streamingContent = "";
			}),

		setStreamError: (error) =>
			set((state) => {
				if (state.activeConversation) {
					const lastMessage =
						state.activeConversation.messages[state.activeConversation.messages.length - 1];
					if (lastMessage && lastMessage.role === "assistant" && lastMessage.isStreaming) {
						lastMessage.isStreaming = false;
						lastMessage.content = lastMessage.content || `Error: ${error}`;
					}

					const conversationIndex = state.conversations.findIndex(
						(conversation) => conversation.id === state.activeConversation?.id,
					);
					if (conversationIndex !== -1) {
						state.conversations[conversationIndex].messages = [
							...state.activeConversation.messages,
						];
					}
				}

				state.isStreaming = false;
				state.streamingContent = "";
			}),
	})),
);

export default useAgentStore;
