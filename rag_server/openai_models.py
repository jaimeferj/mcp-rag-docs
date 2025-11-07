"""OpenAI-compatible API models for web UI integration."""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


# Request models
class ChatMessage(BaseModel):
    """A single chat message."""

    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = Field(default="rag-smart", description="Model to use (rag-smart, rag-standard, rag-enhanced)")
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, ge=1, le=1, description="Number of completions (only 1 supported)")
    stream: Optional[bool] = Field(default=False)
    max_tokens: Optional[int] = Field(default=None)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    user: Optional[str] = None

    # Custom RAG parameters
    expand_detail: Optional[bool] = Field(default=False, description="Get full implementation details")
    repo_filter: Optional[str] = Field(default=None, description="Filter by repository")
    top_k: Optional[int] = Field(default=5, description="Number of chunks to retrieve")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")


# Response models
class ChatCompletionUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""

    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length", "content_filter", "null"]


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str
    object: Literal["chat.completion"]
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage

    # Custom fields
    rag_metadata: Optional[Dict[str, Any]] = Field(default=None, description="RAG-specific metadata")


# Streaming models
class ChatCompletionChunkDelta(BaseModel):
    """Delta content in a streaming chunk."""

    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionChunkChoice(BaseModel):
    """A single streaming choice."""

    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[Literal["stop", "length", "content_filter", "null"]] = None


class ChatCompletionChunk(BaseModel):
    """Streaming chat completion chunk."""

    id: str
    object: Literal["chat.completion.chunk"]
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]


# Models list
class ModelInfo(BaseModel):
    """Information about an available model."""

    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "rag-system"
    permission: List[Dict[str, Any]] = []
    root: str
    parent: Optional[str] = None


class ModelsListResponse(BaseModel):
    """List of available models."""

    object: Literal["list"] = "list"
    data: List[ModelInfo]


# Error models
class ErrorDetail(BaseModel):
    """Error detail information."""

    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: ErrorDetail
