import operator
from typing import Annotated, Optional, Sequence, TypedDict

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agents.tools.registry import get_tools_for_agent
from app.core.config import settings
from app.rag.pipeline import rag_pipeline
from app.rag.retriever import RetrievalConfig

logger = structlog.get_logger()

_ = (HumanMessage, AIMessage)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    collection_name: Optional[str]
    retrieval_config: Optional[dict]
    use_rag: bool


def get_llm(provider: str, model_name: str, temperature: float, tools: list):
    llm_kwargs = {
        "temperature": temperature,
        "streaming": True,
    }

    if provider == "openai":
        llm = ChatOpenAI(model=model_name, api_key=settings.OPENAI_API_KEY, **llm_kwargs)
    elif provider == "anthropic":
        llm = ChatAnthropic(
            model=model_name,
            api_key=settings.ANTHROPIC_API_KEY,
            **llm_kwargs,
        )
    elif provider == "google":
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            **llm_kwargs,
        )
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama

        llm = ChatOllama(model=model_name, **llm_kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    if tools:
        llm = llm.bind_tools(tools)

    return llm


def create_agent_node(llm, system_prompt: str):
    async def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        all_messages = [SystemMessage(content=system_prompt)] + list(messages)
        response = await llm.ainvoke(all_messages)
        return {"messages": [response]}

    return agent_node


def create_rag_node():
    async def rag_node(state: AgentState) -> dict:
        messages = state.get("messages", [])
        last_human_message = None
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                last_human_message = message.content
                break

        if (
            state.get("use_rag")
            and state.get("collection_name")
            and last_human_message
        ):
            config = RetrievalConfig(**(state.get("retrieval_config") or {}))
            results = await rag_pipeline.query(
                last_human_message,
                state["collection_name"],
                config,
            )
            context = await rag_pipeline.build_context(results)
            if context:
                context_message = SystemMessage(
                    content=f"Use this context to answer:\n\n{context}"
                )
                return {"messages": [context_message]}

        return {"messages": []}

    return rag_node


def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END


def build_agent_graph(
    provider: str,
    model_name: str,
    temperature: float,
    system_prompt: str,
    tools_config: list[dict],
    collection_name: str = None,
    retrieval_config: dict = None,
    use_rag: bool = False,
):
    tools = get_tools_for_agent(tools_config)
    llm = get_llm(provider, model_name, temperature, tools)
    rag_node = create_rag_node()

    async def rag_node_with_defaults(state: AgentState) -> dict:
        merged_state = dict(state)
        if "collection_name" not in merged_state:
            merged_state["collection_name"] = collection_name
        if "retrieval_config" not in merged_state:
            merged_state["retrieval_config"] = retrieval_config
        if "use_rag" not in merged_state:
            merged_state["use_rag"] = use_rag
        return await rag_node(merged_state)

    graph = StateGraph(AgentState)
    graph.add_node("rag", rag_node_with_defaults)
    graph.add_node("agent", create_agent_node(llm, system_prompt))
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("rag")
    graph.add_edge("rag", "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )
    graph.add_edge("tools", "agent")

    logger.info("Agent graph built", provider=provider, model=model_name)
    return graph.compile()
