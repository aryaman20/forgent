import asyncio
import json
import time
from typing import AsyncGenerator
from uuid import UUID

import structlog
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_agent_graph
from app.models.conversation import MessageRole
from app.rag.pipeline import rag_pipeline
from app.rag.qdrant_manager import qdrant_manager
from app.rag.retriever import RetrievalConfig
from app.schemas.chat import StreamChunk
from app.services.agent_service import agent_service
from app.services.conversation_service import conversation_service

logger = structlog.get_logger()


class ChatService:
    async def stream_chat(
        self,
        db: AsyncSession,
        agent_id: UUID,
        user_id: UUID,
        org_id: UUID,
        message: str,
        conversation_id: UUID = None,
    ) -> AsyncGenerator[str, None]:
        _ = (json, asyncio, build_agent_graph)

        # Step 1 - setup
        agent = await agent_service.get_agent(db, agent_id, org_id)
        conversation = await conversation_service.get_or_create_conversation(
            db,
            agent_id,
            user_id,
            conversation_id,
        )
        await conversation_service.save_message(
            db,
            conversation.id,
            MessageRole.USER,
            message,
        )

        # Step 2 - RAG
        if agent.has_knowledge_base:
            collection_name = await qdrant_manager.get_collection_name(
                str(org_id),
                str(agent_id),
            )
            config = RetrievalConfig(**(agent.retrieval_config or {}))
            sources = await rag_pipeline.query(message, collection_name, config)
            context = await rag_pipeline.build_context(sources)
        else:
            sources = []
            context = ""

        # Step 3 - build message history for LLM
        history = await conversation_service.get_conversation_history(db, conversation.id)
        llm_messages = conversation_service.build_messages_for_llm(history)
        if context:
            llm_messages = [{"role": "system", "content": f"Context:\n{context}"}] + llm_messages

        is_first_message = len(history) <= 1

        # Step 4 - stream from LangGraph
        graph = agent_service.get_agent_graph(agent)

        full_response = ""
        tokens_input = 0
        tokens_output = 0
        start_time = time.time()

        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=message)]},
                version="v2",
            ):
                event_type = event.get("event")

                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    chunk_content = getattr(chunk, "content", None) if chunk else None
                    if chunk_content:
                        full_response += chunk_content
                        tokens_output += 1

                        stream_chunk = StreamChunk(type="token", content=chunk_content)
                        yield f"data: {stream_chunk.model_dump_json()}\n\n"

                elif event_type == "on_chat_model_end":
                    output = event.get("data", {}).get("output", {})

                    usage_metadata = getattr(output, "usage_metadata", None) or {}
                    if isinstance(output, dict) and not usage_metadata:
                        usage_metadata = output.get("usage_metadata") or output.get("token_usage") or {}

                    if usage_metadata:
                        tokens_input = int(
                            usage_metadata.get("input_tokens", usage_metadata.get("prompt_tokens", tokens_input))
                            or tokens_input
                        )
                        tokens_output = int(
                            usage_metadata.get(
                                "output_tokens",
                                usage_metadata.get("completion_tokens", tokens_output),
                            )
                            or tokens_output
                        )

            # Step 5 - after streaming done
            latency_ms = int((time.time() - start_time) * 1000)

            saved_message = await conversation_service.save_message(
                db,
                conversation.id,
                MessageRole.ASSISTANT,
                full_response,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                sources=sources,
                model_used=f"{agent.model_provider}/{agent.model_name}",
            )

            if sources:
                sources_chunk = StreamChunk(type="sources", sources=sources)
                yield f"data: {sources_chunk.model_dump_json()}\n\n"

            done_chunk = StreamChunk(
                type="done",
                conversation_id=str(conversation.id),
                message_id=str(saved_message.id),
                usage={"tokens_input": tokens_input, "tokens_output": tokens_output},
            )
            yield f"data: {done_chunk.model_dump_json()}\n\n"

            if is_first_message:
                await conversation_service.update_conversation_title(
                    db,
                    conversation.id,
                    message,
                )

        except Exception as exc:
            logger.exception(
                "Streaming chat failed",
                agent_id=str(agent_id),
                conversation_id=str(conversation.id),
                error=str(exc),
            )
            error_chunk = StreamChunk(type="error", content=str(exc))
            yield f"data: {error_chunk.model_dump_json()}\n\n"


chat_service = ChatService()
