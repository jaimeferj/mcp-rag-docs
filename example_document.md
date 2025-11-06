# Example Document for RAG Testing

This is an example document that you can use to test the RAG system.

## About RAG (Retrieval-Augmented Generation)

Retrieval-Augmented Generation (RAG) is a technique that enhances large language models by providing them with relevant context from a knowledge base. Instead of relying solely on the model's training data, RAG systems retrieve relevant information from a vector database and include it in the prompt.

## How This System Works

This RAG system uses several components:

1. **Document Processing**: Text and Markdown files are processed and split into manageable chunks
2. **Embeddings**: Each chunk is converted into a vector using Google AI Studio's text-embedding-004 model
3. **Vector Storage**: Vectors are stored in Qdrant, a high-performance vector database
4. **Retrieval**: When a query is made, similar chunks are retrieved based on vector similarity
5. **Generation**: The retrieved context is provided to Google's Gemini 1.5 Flash model to generate an answer

## Features

### Document Support
The system supports two file formats:
- Plain text (.txt) files
- Markdown (.md) files

### Intelligent Chunking
Documents are split into overlapping chunks to ensure context is preserved across chunk boundaries. The default chunk size is 1000 characters with 200 characters of overlap.

### Google AI Integration
This system uses Google AI Studio's free tier for both embeddings and text generation. The models used are:
- **Embeddings**: text-embedding-004
- **LLM**: gemini-1.5-flash

## Use Cases

RAG systems are useful for:
- Question answering over private documents
- Building chatbots with domain-specific knowledge
- Document search and summarization
- Knowledge base querying

## Getting Started

1. Upload this document using the API or MCP server
2. Ask questions like "What is RAG?" or "What file formats are supported?"
3. The system will retrieve relevant chunks and generate an answer
