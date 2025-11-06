"""Pydantic models for API request and response validation."""

from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for querying the RAG system."""

    question: str = Field(..., description="The question to ask")
    top_k: Optional[int] = Field(None, description="Number of chunks to retrieve")
    tags: Optional[List[str]] = Field(None, description="Tags to filter documents by")
    section_path: Optional[str] = Field(None, description="Section path to filter by")


class Source(BaseModel):
    """Source information for a retrieved chunk."""

    filename: str
    chunk_index: int
    score: float
    section_path: str = "Document"


class QueryResponse(BaseModel):
    """Response model for RAG queries."""

    answer: str
    sources: List[Source]
    context_used: List[str]


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    doc_id: str
    filename: str
    file_type: str
    tags: List[str] = []
    num_chunks: int
    message: str = "Document uploaded successfully"


class DocumentInfo(BaseModel):
    """Information about a stored document."""

    doc_id: str
    filename: str
    file_type: str
    tags: List[str] = []


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""

    documents: List[DocumentInfo]
    total: int


class DeleteResponse(BaseModel):
    """Response model for document deletion."""

    doc_id: str
    chunks_deleted: int
    message: str = "Document deleted successfully"


class StatsResponse(BaseModel):
    """Response model for system statistics."""

    total_documents: int
    total_chunks: int
    collection_name: str


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    message: str


class TagsResponse(BaseModel):
    """Response model for tags listing."""

    tags: List[str]
    total: int


class SectionInfo(BaseModel):
    """Information about a document section."""

    section_path: str
    section_level: int
    chunk_count: int


class SectionsResponse(BaseModel):
    """Response model for document sections."""

    doc_id: str
    sections: List[SectionInfo]
    total: int
