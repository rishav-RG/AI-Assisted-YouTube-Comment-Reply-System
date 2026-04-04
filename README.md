# AI-Assisted YouTube Comment Reply System

This project is a FastAPI-based web application designed to help YouTube creators manage and reply to comments using the power of AI. It connects to the YouTube Data API, syncs channel content, and uses a Retrieval-Augmented Generation (RAG) pipeline to generate context-aware replies.

## Features & TODO Checklist

### ✅ Core Infrastructure

- **FastAPI Backend**: Core web server and application structure.
- **YouTube OAuth 2.0**: Secure user authentication for YouTube channel data access.
- **Database Setup**: PostgreSQL with SQLModel for robust data storage.
- **Comprehensive Data Sync**: Syncs channel info, video metadata, transcripts, and comments.

### 🚀 RAG Pipeline & AI Integration

- [ ] **Aggregate Data for RAG**: Combine video title, description, transcript, and comments into a single context.
- [ ] **Integrate Vector Database**: Set up a vector DB (e.g., ChromaDB, FAISS) to store text embeddings.
- [ ] **Generate Embeddings**: Create a pipeline to generate and store embeddings for the aggregated data.
- [ ] **Build AI Reply Endpoint**:
  - Design an API endpoint to receive new comments.
  - Implement RAG retrieval to find relevant context from the vector DB.
  - Integrate an LLM to generate a context-aware reply.
- [ ] **Develop Reply Management UI**:
  - Store AI-generated replies with a `pending` status.
  - Create a UI to review, approve, edit, or reject replies.
  - Post approved replies back to YouTube.
- [ ] **Implement Background Processing**: Use a task queue (e.g., Celery) for non-blocking data sync and AI tasks.
