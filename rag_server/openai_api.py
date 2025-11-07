"""OpenAI-compatible API endpoints for web UI integration."""

import time
import uuid
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from rag_server.openai_models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    ChatMessage,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ModelsListResponse,
    ModelInfo,
    ErrorResponse,
    ErrorDetail,
)
from rag_server.rag_system import RAGSystem


# Create router
router = APIRouter(prefix="/v1", tags=["OpenAI Compatible API"])


# Available models
AVAILABLE_MODELS = {
    "rag-smart": {
        "id": "rag-smart",
        "description": "Smart query with automatic routing and classification",
        "method": "smart_query",
    },
    "rag-standard": {
        "id": "rag-standard",
        "description": "Standard RAG query with documentation search",
        "method": "query",
    },
    "rag-enhanced": {
        "id": "rag-enhanced",
        "description": "Enhanced RAG with automatic reference following",
        "method": "query_enhanced",
    },
}


def get_rag_system(request: Request) -> RAGSystem:
    """Get RAG system from app state."""
    return request.app.state.rag_system


def extract_user_query(messages: list[ChatMessage]) -> tuple[str, str]:
    """
    Extract user query and system context from messages.

    Returns:
        (user_query, system_context)
    """
    system_context = ""
    user_query = ""

    for message in messages:
        if message.role == "system":
            system_context += message.content + "\n"
        elif message.role == "user":
            user_query = message.content  # Use last user message
        # Note: assistant messages are ignored for now (no conversation history)

    return user_query.strip(), system_context.strip()


def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters)."""
    return len(text) // 4


async def generate_streaming_response(
    rag_result: dict,
    request_id: str,
    model: str,
    created: int,
) -> AsyncGenerator[str, None]:
    """Generate SSE-formatted streaming chunks."""

    # Send initial chunk with role
    chunk = ChatCompletionChunk(
        id=request_id,
        object="chat.completion.chunk",
        created=created,
        model=model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=ChatCompletionChunkDelta(role="assistant"),
                finish_reason=None,
            )
        ],
    )
    yield f"data: {chunk.model_dump_json()}\n\n"

    # Stream the answer content
    answer = rag_result.get("answer", "")

    # Split into words for streaming effect
    words = answer.split()
    for i, word in enumerate(words):
        content = word + (" " if i < len(words) - 1 else "")
        chunk = ChatCompletionChunk(
            id=request_id,
            object="chat.completion.chunk",
            created=created,
            model=model,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatCompletionChunkDelta(content=content),
                    finish_reason=None,
                )
            ],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"

    # Send final chunk with finish_reason
    chunk = ChatCompletionChunk(
        id=request_id,
        object="chat.completion.chunk",
        created=created,
        model=model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=ChatCompletionChunkDelta(),
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {chunk.model_dump_json()}\n\n"

    # Send [DONE] marker
    yield "data: [DONE]\n\n"


@router.post("/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    req: Request,
):
    """
    Create a chat completion (OpenAI-compatible).

    Supports both streaming and non-streaming responses.
    """
    try:
        rag_system = get_rag_system(req)

        # Validate model
        if request.model not in AVAILABLE_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model}' not found. Available: {list(AVAILABLE_MODELS.keys())}",
            )

        # Extract query from messages
        user_query, system_context = extract_user_query(request.messages)

        if not user_query:
            raise HTTPException(
                status_code=400,
                detail="No user message found in request",
            )

        # Add system context to query if present
        if system_context:
            user_query = f"{system_context}\n\n{user_query}"

        # Route to appropriate RAG method
        model_config = AVAILABLE_MODELS[request.model]
        method = model_config["method"]

        if method == "smart_query":
            rag_result = rag_system.smart_query(
                question=user_query,
                expand_detail=request.expand_detail,
                repo_filter=request.repo_filter,
            )
        elif method == "query_enhanced":
            rag_result = rag_system.query_enhanced(
                question=user_query,
                top_k=request.top_k,
                max_followups=3,
                tags=request.tags,
            )
        else:  # query
            rag_result = rag_system.query(
                question=user_query,
                top_k=request.top_k,
                tags=request.tags,
            )

        answer = rag_result.get("answer", "No answer generated")

        # Generate unique IDs
        request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        created = int(time.time())

        # Handle streaming
        if request.stream:
            return StreamingResponse(
                generate_streaming_response(rag_result, request_id, request.model, created),
                media_type="text/event-stream",
            )

        # Non-streaming response
        prompt_tokens = estimate_tokens(user_query)
        completion_tokens = estimate_tokens(answer)

        response = ChatCompletionResponse(
            id=request_id,
            object="chat.completion",
            created=created,
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=answer,
                    ),
                    finish_reason="stop",
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            rag_metadata={
                "sources": rag_result.get("sources", []),
                "confidence": rag_result.get("confidence"),
                "classification": rag_result.get("classification"),
            } if method == "smart_query" else None,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}",
        )


@router.get("/models")
async def list_models() -> ModelsListResponse:
    """List available models."""
    created = int(time.time())

    models = [
        ModelInfo(
            id=model_id,
            created=created,
            root=model_id,
        )
        for model_id in AVAILABLE_MODELS.keys()
    ]

    return ModelsListResponse(data=models)


@router.get("/models/{model_id}")
async def get_model(model_id: str) -> ModelInfo:
    """Get information about a specific model."""
    if model_id not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_id}' not found",
        )

    return ModelInfo(
        id=model_id,
        created=int(time.time()),
        root=model_id,
    )
