import hashlib
import json
from typing import Any, Dict, List, Optional

from langchain_cohere import ChatCohere, CohereEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from pinecone import Pinecone, ServerlessSpec
from sqlalchemy import desc
from sqlmodel import Session, select

from config import (
    COHERE_API_KEY,
    COHERE_CHAT_MODEL,
    COHERE_EMBED_MODEL,
    PINECONE_API_KEY,
    PINECONE_CLOUD,
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE_PREFIX,
    PINECONE_REGION,
    RAG_TOP_K,
)
from app.db.models import Comment, RAGChunk, Reply, ReplyStatus, Video
from app.services.context_aggregator import get_aggregated_context
from app.services.rag_cache import RAGCache
from app.services.rag_chunking import build_documents, chunk_documents


class RAGReplyService:
    def __init__(self) -> None:
        self.cache = RAGCache()
        self._pinecone_client: Optional[Pinecone] = None

    @staticmethod
    def _namespace(user_id: int, video_id: int) -> str:
        return f"{PINECONE_NAMESPACE_PREFIX}:u{user_id}:v{video_id}"

    @staticmethod
    def _hash_chunk(text: str, source_type: str, source_ref: str, idx: int) -> str:
        payload = f"{source_type}|{source_ref}|{idx}|{text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _get_embeddings(self) -> CohereEmbeddings:
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY is not configured")
        return CohereEmbeddings(model=COHERE_EMBED_MODEL, cohere_api_key=COHERE_API_KEY)

    def _get_chat_model(self) -> ChatCohere:
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY is not configured")
        return ChatCohere(model=COHERE_CHAT_MODEL, cohere_api_key=COHERE_API_KEY)

    def _get_pinecone_index(self):
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is not configured")
        if not self._pinecone_client:
            self._pinecone_client = Pinecone(api_key=PINECONE_API_KEY)

        existing_indexes = set(self._pinecone_client.list_indexes().names())
        if PINECONE_INDEX_NAME not in existing_indexes:
            dimension = len(self._get_embeddings().embed_query("dimension-probe"))
            self._pinecone_client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
            )

        return self._pinecone_client.Index(PINECONE_INDEX_NAME)

    def _upsert_reply(
        self,
        session: Session,
        comment: Comment,
        generated_reply: str,
        source_chunk_ids: List[str],
        prompt_hash: str,
    ) -> Reply:
        existing = session.exec(
            select(Reply)
            .where(Reply.comment_id == comment.id, Reply.user_id == comment.user_id)
            .order_by(desc(Reply.created_at))
        ).first()

        if existing:
            existing.generated_reply = generated_reply
            existing.model_name = COHERE_CHAT_MODEL
            existing.prompt_hash = prompt_hash
            existing.source_chunk_ids = json.dumps(source_chunk_ids, ensure_ascii=True)
            existing.status = ReplyStatus.pending
            session.add(existing)
            session.flush()
            return existing

        reply = Reply(
            user_id=comment.user_id,
            comment_id=comment.id,
            generated_reply=generated_reply,
            status=ReplyStatus.pending,
            model_name=COHERE_CHAT_MODEL,
            prompt_hash=prompt_hash,
            source_chunk_ids=json.dumps(source_chunk_ids, ensure_ascii=True),
        )
        session.add(reply)
        session.flush()
        return reply

    def index_video_context(self, session: Session, user_id: int, video_id: int) -> Dict[str, Any]:
        aggregated_context = get_aggregated_context(session, video_id)
        if not aggregated_context:
            raise ValueError("Video context not found")

        context_hash = self.cache.stable_hash(aggregated_context)
        aggregate_cache_key = f"{user_id}:{video_id}"
        aggregate_cached = self.cache.get_json("aggregate", aggregate_cache_key)
        if aggregate_cached and aggregate_cached.get("context_hash") == context_hash:
            return {
                "indexed": 0,
                "skipped": aggregate_cached.get("chunk_count", 0),
                "context_hash": context_hash,
            }

        docs = chunk_documents(build_documents(aggregated_context))
        existing_chunks = session.exec(
            select(RAGChunk).where(RAGChunk.user_id == user_id, RAGChunk.video_id == video_id)
        ).all()
        by_hash = {chunk.chunk_hash: chunk for chunk in existing_chunks}

        to_index_docs: List[Document] = []
        to_index_ids: List[str] = []
        new_hashes = set()

        for idx, doc in enumerate(docs):
            source_type = str(doc.metadata.get("source_type", "unknown"))
            source_ref = str(doc.metadata.get("thread_index", ""))
            chunk_hash = self._hash_chunk(doc.page_content, source_type, source_ref, idx)
            new_hashes.add(chunk_hash)

            if chunk_hash in by_hash:
                by_hash[chunk_hash].is_stale = False
                session.add(by_hash[chunk_hash])
                continue

            metadata = {
                **doc.metadata,
                "user_id": user_id,
                "video_id": video_id,
                "chunk_hash": chunk_hash,
                "text": doc.page_content,
            }
            to_index_docs.append(Document(page_content=doc.page_content, metadata=metadata))
            to_index_ids.append(chunk_hash)

            session.add(
                RAGChunk(
                    user_id=user_id,
                    video_id=video_id,
                    chunk_hash=chunk_hash,
                    chunk_index=idx,
                    source_type=source_type,
                    source_ref=source_ref,
                    text=doc.page_content,
                    metadata_json=json.dumps(metadata, ensure_ascii=True),
                    is_stale=False,
                )
            )

        for old in existing_chunks:
            if old.chunk_hash not in new_hashes:
                old.is_stale = True
                session.add(old)

        if to_index_docs:
            embeddings = self._get_embeddings().embed_documents([d.page_content for d in to_index_docs])
            vectors = []
            for idx, vector in enumerate(embeddings):
                vectors.append(
                    {
                        "id": to_index_ids[idx],
                        "values": vector,
                        "metadata": to_index_docs[idx].metadata,
                    }
                )

            index = self._get_pinecone_index()
            index.upsert(vectors=vectors, namespace=self._namespace(user_id, video_id))

        session.commit()
        self.cache.set_json(
            "aggregate",
            aggregate_cache_key,
            {"context_hash": context_hash, "chunk_count": len(docs)},
        )

        return {
            "indexed": len(to_index_docs),
            "skipped": len(docs) - len(to_index_docs),
            "context_hash": context_hash,
        }

    def _retrieve_context(
        self, user_id: int, video_id: int, comment: Comment, top_k: int
    ) -> List[Dict[str, Any]]:
        key_payload = {
            "user_id": user_id,
            "video_id": video_id,
            "comment_id": comment.id,
            "comment_text": comment.comment_text,
            "top_k": top_k,
        }
        cache_key = self.cache.stable_hash(key_payload)
        scoped_cache_key = f"{user_id}:{video_id}:{cache_key}"
        cached = self.cache.get_json("retrieval", scoped_cache_key)
        if cached:
            return cached.get("docs", [])

        query_vector = self._get_embeddings().embed_query(comment.comment_text)
        index = self._get_pinecone_index()
        query_result = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            namespace=self._namespace(user_id, video_id),
            filter={"user_id": user_id, "video_id": video_id},
        )

        payload = []
        for match in query_result.get("matches", []):
            metadata = match.get("metadata", {})
            payload.append(
                {
                    "content": metadata.get("text") or "",
                    "metadata": metadata,
                }
            )
        self.cache.set_json("retrieval", scoped_cache_key, {"docs": payload})
        return payload

    def _build_prompt(self, context: dict, comment_text: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        persona = context.get("channel_context", {}).get("persona") or "Default persona"
        tone = context.get("channel_context", {}).get("tone") or "Helpful and calm"

        context_blob = "\n\n".join(d.get("content", "") for d in retrieved_docs)

        prompt = ChatPromptTemplate.from_template(
            """
You are generating a short reply for a YouTube creator.

Channel persona: {persona}
Preferred tone: {tone}

Policy:
- Keep reply concise and human.
- Be polite and de-escalate if the comment is abusive.
- Never mirror insults.
- If user asks for help/info, provide practical direction.
- Output only the reply text.

Comment to reply:
{comment_text}

Retrieved context:
{context_blob}
""".strip()
        )

        return prompt.invoke(
            {
                "persona": persona,
                "tone": tone,
                "comment_text": comment_text,
                "context_blob": context_blob or "No additional context.",
            }
        ).to_string()

    def generate_for_comment(
        self,
        session: Session,
        user_id: int,
        comment_id: int,
        force_regenerate: bool = False,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        comment = session.get(Comment, comment_id)
        if not comment or comment.user_id != user_id:
            raise ValueError("Comment not found")

        if comment.is_creator:
            return {"status": "skipped", "reason": "creator_comment"}

        existing_reply = session.exec(
            select(Reply)
            .where(Reply.comment_id == comment.id, Reply.user_id == user_id)
            .order_by(desc(Reply.created_at))
        ).first()

        if existing_reply and not force_regenerate:
            comment.is_processed = True
            session.add(comment)
            session.commit()
            return {"status": "skipped", "reason": "existing_reply"}

        if not comment.video_id:
            raise ValueError("Comment has no linked video")

        self.index_video_context(session, user_id, comment.video_id)
        context = get_aggregated_context(session, comment.video_id)

        retrieved_docs = self._retrieve_context(
            user_id=user_id,
            video_id=comment.video_id,
            comment=comment,
            top_k=top_k or RAG_TOP_K,
        )

        prompt_text = self._build_prompt(context, comment.comment_text, retrieved_docs)
        prompt_hash = self.cache.stable_hash(
            {
                "prompt": prompt_text,
                "model": COHERE_CHAT_MODEL,
                "comment_id": comment.id,
            }
        )

        reply_cache_key = self.cache.stable_hash({"prompt_hash": prompt_hash, "comment_id": comment.id})
        cached_reply = self.cache.get_json("reply", reply_cache_key)

        if cached_reply and not force_regenerate:
            generated_text = cached_reply.get("generated_reply", "")
        else:
            chat_model = self._get_chat_model()
            generated_text = chat_model.invoke(prompt_text).content.strip()
            self.cache.set_json(
                "reply",
                reply_cache_key,
                {"generated_reply": generated_text},
            )

        source_chunk_ids = [
            d.get("metadata", {}).get("chunk_hash")
            for d in retrieved_docs
            if d.get("metadata", {}).get("chunk_hash")
        ]

        reply_row = self._upsert_reply(
            session=session,
            comment=comment,
            generated_reply=generated_text,
            source_chunk_ids=source_chunk_ids,
            prompt_hash=prompt_hash,
        )

        comment.is_processed = True
        session.add(comment)
        session.commit()

        return {
            "status": "generated",
            "comment_id": comment.id,
            "reply_id": reply_row.id,
            "source_chunks": source_chunk_ids,
        }

    def generate_for_video(
        self,
        session: Session,
        user_id: int,
        video_id: int,
        force_regenerate: bool = False,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        video = session.get(Video, video_id)
        if not video or video.user_id != user_id:
            raise ValueError("Video not found")

        index_stats = self.index_video_context(session, user_id, video_id)

        stmt = select(Comment).where(
            Comment.user_id == user_id,
            Comment.video_id == video_id,
            Comment.is_creator == False,
        )
        if not force_regenerate:
            stmt = stmt.where(Comment.is_processed == False)

        comments = session.exec(stmt).all()

        generated = 0
        skipped_existing = 0
        skipped_creator = 0
        failed = 0

        for comment in comments:
            result = self.generate_for_comment(
                session=session,
                user_id=user_id,
                comment_id=comment.id,
                force_regenerate=force_regenerate,
                top_k=top_k,
            )
            status = result.get("status")
            reason = result.get("reason")

            if status == "generated":
                generated += 1
            elif reason == "existing_reply":
                skipped_existing += 1
            elif reason == "creator_comment":
                skipped_creator += 1
            else:
                failed += 1

        return {
            "video_id": video_id,
            "index": index_stats,
            "generated": generated,
            "skipped_existing_reply": skipped_existing,
            "skipped_creator": skipped_creator,
            "failed": failed,
            "scanned": len(comments),
        }
