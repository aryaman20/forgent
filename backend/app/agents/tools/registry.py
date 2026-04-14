from app.agents.tools.web_search import web_search
from app.agents.tools.calculator import calculator

# Registry pattern: central map from tool names to callable tool objects.
ALL_TOOLS = {
    "web_search": web_search,
    "calculator": calculator,
}


def get_tools_for_agent(tools_config: list[dict]) -> list:
    """
    Given an agent's tools_config from the database,
    return the actual LangChain tool objects.
    """
    tools: list = []
    for tool_cfg in tools_config:
        if tool_cfg.get("enabled", True):
            tool_name = tool_cfg.get("name")
            if tool_name in ALL_TOOLS:
                tools.append(ALL_TOOLS[tool_name])
    return tools
