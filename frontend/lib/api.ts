import axios, { type AxiosInstance, type AxiosResponse } from "axios";

type Dict = Record<string, unknown>;

export interface PaginatedParams {
	page?: number;
	pageSize?: number;
}

export interface StreamChunk {
	type: "token" | "done" | "error" | string;
	content?: string;
	conversation_id?: string;
	message_id?: string;
	usage?: Dict;
	sources?: Dict[];
}

export interface ClerkWindow extends Window {
	Clerk?: {
		session?: {
			getToken: () => Promise<string | null>;
		};
	};
}

const axiosInstance: AxiosInstance = axios.create({
	baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});

axiosInstance.interceptors.request.use(async (config) => {
	const token = await (window as ClerkWindow).Clerk?.session?.getToken?.();

	if (token) {
		if (config.headers && typeof (config.headers as { set?: unknown }).set === "function") {
			(config.headers as { set: (name: string, value: string) => void }).set(
				"Authorization",
				`Bearer ${token}`,
			);
		} else {
			config.headers = {
				...(config.headers || {}),
				Authorization: `Bearer ${token}`,
			} as typeof config.headers;
		}
	}

	return config;
});

export async function getAgents(
	page: number = 1,
	pageSize: number = 20,
): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.get("/api/v1/agents", {
		params: { page, page_size: pageSize },
	});
	return response.data;
}

export async function createAgent(data: Dict): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.post("/api/v1/agents", data);
	return response.data;
}

export async function getAgent(agentId: string): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.get(`/api/v1/agents/${agentId}`);
	return response.data;
}

export async function updateAgent(agentId: string, data: Dict): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.put(
		`/api/v1/agents/${agentId}`,
		data,
	);
	return response.data;
}

export async function deleteAgent(agentId: string): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.delete(`/api/v1/agents/${agentId}`);
	return response.data;
}

export async function uploadDocument(agentId: string, file: File): Promise<Dict> {
	const formData = new FormData();
	formData.append("file", file);

	const response: AxiosResponse<Dict> = await axiosInstance.post(
		`/api/v1/knowledge/${agentId}/upload`,
		formData,
		{
			headers: {
				"Content-Type": "multipart/form-data",
			},
		},
	);

	return response.data;
}

export async function getDocuments(agentId: string): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.get(`/api/v1/knowledge/${agentId}`);
	return response.data;
}

export async function deleteDocument(agentId: string, docId: string): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.delete(
		`/api/v1/knowledge/${agentId}/documents/${docId}`,
	);
	return response.data;
}

export async function getConversations(agentId: string): Promise<Dict[]> {
	const response: AxiosResponse<Dict[]> = await axiosInstance.get(
		`/api/v1/chat/${agentId}/conversations`,
	);
	return response.data;
}

export async function getConversation(
	agentId: string,
	conversationId: string,
): Promise<Dict> {
	const response: AxiosResponse<Dict> = await axiosInstance.get(
		`/api/v1/chat/${agentId}/conversations/${conversationId}`,
	);
	return response.data;
}

export async function streamChat(
	agentId: string,
	message: string,
	conversationId: string | null,
	onChunk: (chunk: StreamChunk) => void,
	onDone: (chunk: StreamChunk) => void,
	onError: (error: string) => void,
): Promise<void> {
	const token = await (window as ClerkWindow).Clerk?.session?.getToken?.();

	const response = await fetch(
		`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat/${agentId}/stream`,
		{
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				...(token ? { Authorization: `Bearer ${token}` } : {}),
			},
			body: JSON.stringify({
				message,
				conversation_id: conversationId,
			}),
		},
	);

	if (!response.ok || !response.body) {
		onError(`Request failed with status ${response.status}`);
		return;
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";
	let sawDone = false;
	let sawError = false;

	while (true) {
		const { done, value } = await reader.read();
		if (done) {
			break;
		}

		buffer += decoder.decode(value, { stream: true });
		const parts = buffer.split("data: ");
		buffer = parts.pop() ?? "";

		for (const part of parts) {
			const raw = part.trim();
			if (!raw) {
				continue;
			}

			const lines = raw.split("\n");
			for (const line of lines) {
				const payload = line.trim();
				if (!payload) {
					continue;
				}

				try {
					const parsed: StreamChunk = JSON.parse(payload);
					if (parsed.type === "token") {
						onChunk(parsed);
					} else if (parsed.type === "done") {
						sawDone = true;
						onDone(parsed);
					} else if (parsed.type === "error") {
						sawError = true;
						onError(parsed.content || "Unknown stream error");
					}
				} catch {
					// Ignore malformed partial chunks and continue.
				}
			}
		}
	}

	const trailing = buffer.trim();
	if (trailing.startsWith("data: ")) {
		const payload = trailing.slice(6).trim();
		if (payload) {
			try {
				const parsed: StreamChunk = JSON.parse(payload);
				if (parsed.type === "token") {
					onChunk(parsed);
				} else if (parsed.type === "done") {
					sawDone = true;
					onDone(parsed);
				} else if (parsed.type === "error") {
					sawError = true;
					onError(parsed.content || "Unknown stream error");
				}
			} catch {
				// Ignore malformed trailing payload.
			}
		}
	}

	if (!sawDone && !sawError) {
		onError("Chat stream ended unexpectedly. Check backend model/API key configuration.");
	}
}

export { axiosInstance };
