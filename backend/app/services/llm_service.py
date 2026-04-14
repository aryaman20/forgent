import litellm
import structlog
from litellm import acompletion, completion_cost

from app.core.config import settings

logger = structlog.get_logger()

# Configure LiteLLM with provider keys.
litellm.openai_key = settings.OPENAI_API_KEY
litellm.anthropic_key = settings.ANTHROPIC_API_KEY
litellm.gemini_key = settings.GOOGLE_API_KEY

# Send successful traces to LangSmith via LiteLLM callbacks.
litellm.success_callback = ["langsmith"]


class LLMService:
    """Unified interface for all LLM providers using LiteLLM."""

    def _build_model_string(self, provider: str, model_name: str) -> str:
        if provider == "openai":
            return model_name
        if provider == "ollama":
            return f"ollama/{model_name}"
        return f"{provider}/{model_name}"

    async def chat(
        self,
        messages: list[dict],
        provider: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ):
        model_string = self._build_model_string(provider, model_name)

        logger.info(
            "LLM call",
            model=model_string,
            stream=stream,
            message_count=len(messages),
        )

        response = await acompletion(
            model=model_string,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )
        return response

    def calculate_cost(self, response) -> float:
        try:
            return completion_cost(completion_response=response)
        except Exception:
            return 0.0

    def extract_text(self, response) -> str:
        return response.choices[0].message.content

    def extract_usage(self, response) -> dict:
        usage = response.usage
        return {
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }


llm_service = LLMService()
