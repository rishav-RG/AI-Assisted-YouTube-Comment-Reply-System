from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE, RAG_MAX_COMMENTS_CONTEXT


def build_documents(aggregated_context: dict) -> List[Document]:
    docs: List[Document] = []

    channel_context = aggregated_context.get("channel_context", {})
    video_context = aggregated_context.get("video_context", {})
    comments_context = aggregated_context.get("comments_context", [])

    title = video_context.get("title") or ""
    description = video_context.get("description") or ""
    transcript = video_context.get("transcript") or ""

    docs.append(
        Document(
            page_content=f"Video title: {title}\n\nVideo description:\n{description}",
            metadata={"source_type": "video_meta"},
        )
    )

    if transcript.strip():
        docs.append(
            Document(
                page_content=f"Video transcript:\n{transcript}",
                metadata={"source_type": "transcript"},
            )
        )

    persona = channel_context.get("persona") or "Default persona"
    tone = channel_context.get("tone") or "Default tone"
    docs.append(
        Document(
            page_content=f"Channel persona: {persona}\nChannel tone: {tone}",
            metadata={"source_type": "channel_context"},
        )
    )

    for idx, thread in enumerate(comments_context[:RAG_MAX_COMMENTS_CONTEXT]):
        comment = thread.get("comment", {})
        replies = thread.get("replies", [])

        lines = [f"Parent comment: {comment.get('text', '')}"]
        for reply in replies:
            lines.append(f"Reply: {reply.get('text', '')}")

        docs.append(
            Document(
                page_content="\n".join(lines),
                metadata={"source_type": "comment_thread", "thread_index": idx},
            )
        )

    return docs


def chunk_documents(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)
