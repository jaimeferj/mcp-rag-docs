"""FastAPI server for the RAG system."""

import tempfile
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from config.settings import settings
from rag_server.models import (
    DeleteResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SectionsResponse,
    StatsResponse,
    TagsResponse,
)
from rag_server.rag_system import RAGSystem


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Initialize RAG system
    app.state.rag_system = RAGSystem()
    yield
    # Shutdown: cleanup if needed
    app.state.rag_system = None


# Initialize FastAPI app
app = FastAPI(
    title="RAG Server",
    description="Retrieval-Augmented Generation server with Google AI Studio integration",
    version="0.1.0",
    lifespan=lifespan,
)


def get_rag_system() -> RAGSystem:
    """Get the RAG system instance."""
    return app.state.rag_system


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint."""
    return HealthResponse(
        status="ok",
        message="RAG Server is running. Visit /docs for API documentation.",
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", message="RAG server is operational")


@app.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    tags: str = Form(""),
):
    """
    Upload a document to the RAG system.

    Supports .txt and .md files.
    Tags can be provided as comma-separated values.
    """
    rag_system = get_rag_system()
    try:
        # Parse tags from comma-separated string
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Check file extension
        file_path = Path(file.filename)
        if not rag_system.document_processor.is_supported(file_path):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: .txt, .md",
            )

        # Read file content
        content = await file.read()
        text_content = content.decode("utf-8")

        # Save to temporary file for processing
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=file_path.suffix, delete=False
        ) as temp_file:
            temp_file.write(text_content)
            temp_path = Path(temp_file.name)

        try:
            # Add document to RAG system with tags
            result = await rag_system.add_document(temp_path, text_content, tags=tags_list)

            return DocumentUploadResponse(**result)
        finally:
            # Clean up temporary file
            temp_path.unlink(missing_ok=True)

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="File must be valid UTF-8 encoded text"
        )
    except Exception as e:
        # Log full traceback for debugging
        tb = traceback.format_exc()
        print(f"Error processing document:\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {e}")


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system with a question.

    The system will retrieve relevant context and generate an answer using Google AI Studio.
    Optionally filter by tags and/or section path.
    """
    rag_system = get_rag_system()
    try:
        result = rag_system.query(
            request.question,
            request.top_k,
            tags=request.tags,
            section_path=request.section_path,
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(tags: str = Query("", description="Comma-separated tags to filter by")):
    """List all documents in the RAG system, optionally filtered by tags."""
    rag_system = get_rag_system()
    try:
        # Parse tags from comma-separated string
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None

        documents = rag_system.list_documents(tags=tags_list)
        return DocumentListResponse(documents=documents, total=len(documents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {e}")


@app.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(doc_id: str):
    """Delete a document from the RAG system."""
    rag_system = get_rag_system()
    try:
        chunks_deleted = rag_system.delete_document(doc_id)

        if chunks_deleted == 0:
            raise HTTPException(status_code=404, detail="Document not found")

        return DeleteResponse(doc_id=doc_id, chunks_deleted=chunks_deleted)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {e}")


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get statistics about the RAG system."""
    rag_system = get_rag_system()
    try:
        stats = rag_system.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {e}")


@app.get("/tags", response_model=TagsResponse)
async def get_tags():
    """Get all unique tags across all documents."""
    rag_system = get_rag_system()
    try:
        tags = rag_system.get_tags()
        return TagsResponse(tags=tags, total=len(tags))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tags: {e}")


@app.get("/documents/{doc_id}/sections", response_model=SectionsResponse)
async def get_document_sections(doc_id: str):
    """Get the section structure of a document."""
    rag_system = get_rag_system()
    try:
        sections = rag_system.get_document_sections(doc_id)
        return SectionsResponse(doc_id=doc_id, sections=sections, total=len(sections))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting document sections: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "rag_server.server:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=True,
    )
