import operator
from typing import Annotated, Sequence, TypedDict

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agents.tools.registry import get_tools_for_agent
from app.core.config import settings

logger = structlog.get_logger()

_ = (HumanMessage, AIMessage)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


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
):
    tools = get_tools_for_agent(tools_config)
    llm = get_llm(provider, model_name, temperature, tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", create_agent_node(llm, system_prompt))
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
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
