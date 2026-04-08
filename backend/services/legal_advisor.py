from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

try:
    from groq import Groq
except ImportError:
    Groq = None


BASE_DIR = Path(__file__).resolve().parent.parent
KB_PATH = BASE_DIR / "data" / "knowledge_base"


@dataclass
class KnowledgeDocument:
    name: str
    text: str


@dataclass
class KnowledgeChunk:
    document: str
    chunk_id: int
    text: str


class LegalAdvisor:
    CACHE_TTL_MINUTES = 10
    CHUNK_SIZE = 1100
    CHUNK_OVERLAP = 180
    VECTOR_TOP_K = 4

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = Groq(api_key=self.api_key) if self.api_key and Groq else None
        self._cache: Dict[str, tuple[dict, datetime]] = {}

        self.documents = self._load_documents()
        self.knowledge_base_text = self._render_full_context(self.documents)
        self._chunks: List[KnowledgeChunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._chunk_matrix = None

        if self.model:
            print("[ok] Groq (TradeGPT Legal Advisor) initialized")
        else:
            print("[warn] No GROQ_API_KEY found. TradeGPT answer generation is unavailable.")

    def _load_documents(self) -> List[KnowledgeDocument]:
        print("[info] Loading regulatory knowledge base into RAM...")
        documents: List[KnowledgeDocument] = []

        if KB_PATH.exists():
            for file_path in sorted(KB_PATH.iterdir()):
                if file_path.suffix.lower() not in {".txt", ".md"}:
                    continue
                text = file_path.read_text(encoding="utf-8")
                documents.append(KnowledgeDocument(name=file_path.name, text=text))
            print(f"[ok] Loaded {len(documents)} regulatory documents into context memory.")
        else:
            print(f"[warn] Knowledge base path not found: {KB_PATH}")

        return documents

    def _render_full_context(self, documents: List[KnowledgeDocument]) -> str:
        if not documents:
            return "No local regulations found. The corpus is empty."

        return "\n\n".join(
            f"--- Document: {document.name} ---\n{document.text}"
            for document in documents
        )

    def _chunk_document(self, text: str) -> List[str]:
        normalized = re.sub(r"\n{3,}", "\n\n", text.strip())
        if not normalized:
            return []

        chunks: List[str] = []
        start = 0
        length = len(normalized)
        while start < length:
            end = min(length, start + self.CHUNK_SIZE)
            if end < length:
                paragraph_break = normalized.rfind("\n\n", start + 400, end)
                if paragraph_break > start:
                    end = paragraph_break
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= length:
                break
            start = max(end - self.CHUNK_OVERLAP, start + 1)

        return chunks

    def _ensure_vector_index(self) -> None:
        if self._vectorizer is not None and self._chunk_matrix is not None:
            return

        self._chunks = []
        for document in self.documents:
            for chunk_id, chunk_text in enumerate(self._chunk_document(document.text), start=1):
                self._chunks.append(
                    KnowledgeChunk(
                        document=document.name,
                        chunk_id=chunk_id,
                        text=chunk_text,
                    )
                )

        texts = [chunk.text for chunk in self._chunks]
        if not texts:
            self._vectorizer = TfidfVectorizer()
            self._chunk_matrix = self._vectorizer.fit_transform(["empty corpus"])
            return

        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._chunk_matrix = self._vectorizer.fit_transform(texts)

    def _retrieve_vector_chunks(self, user_query: str) -> List[Dict]:
        self._ensure_vector_index()
        if not self._chunks or self._vectorizer is None or self._chunk_matrix is None:
            return []

        query_vector = self._vectorizer.transform([user_query])
        scores = linear_kernel(query_vector, self._chunk_matrix).flatten()
        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True,
        )

        retrieved = []
        for index, score in ranked[: self.VECTOR_TOP_K]:
            chunk = self._chunks[index]
            retrieved.append(
                {
                    "document": chunk.document,
                    "chunk_id": chunk.chunk_id,
                    "score": round(float(score), 4),
                    "text": chunk.text,
                }
            )

        return retrieved

    def _get_query_hash(self, mode: str, query: str) -> str:
        return hashlib.md5(f"{mode}:{query.lower().strip()}".encode()).hexdigest()

    def _is_cache_valid(self, query_hash: str) -> bool:
        if query_hash not in self._cache:
            return False
        _, timestamp = self._cache[query_hash]
        return datetime.now() - timestamp < timedelta(minutes=self.CACHE_TTL_MINUTES)

    def _build_citations(self, answer_text: str, retrieved_chunks: List[Dict] | None = None) -> List[str]:
        citations: List[str] = []

        if "CBAM" in answer_text:
            citations.append("EU CBAM Regulation 2023/956")
        if "WTO" in answer_text or "GATT" in answer_text:
            citations.append("WTO/GATT Rules Reference")
        if "FTP" in answer_text or "Foreign Trade Policy" in answer_text or "DGFT" in answer_text:
            citations.append("India Foreign Trade Policy 2023")
        if "Customs" in answer_text or "export regulation" in answer_text.lower():
            citations.append("India Export Regulations")

        for chunk in retrieved_chunks or []:
            label = f"{chunk['document']} chunk {chunk['chunk_id']}"
            if label not in citations:
                citations.append(label)

        if not citations:
            citations.append("CarbonShip Knowledge Base")

        return citations

    def _serialize_retrieval(self, retrieved_chunks: List[Dict]) -> List[Dict]:
        return [
            {
                "document": chunk["document"],
                "chunk_id": chunk["chunk_id"],
                "score": chunk["score"],
                "preview": chunk["text"][:220],
            }
            for chunk in retrieved_chunks
        ]

    async def ask_question(self, user_query: str) -> dict:
        query_hash = self._get_query_hash("full_context", user_query)
        if self._is_cache_valid(query_hash):
            result, _ = self._cache[query_hash]
            return {**result, "cached": True}

        if not self.model:
            result = {
                "answer": (
                    "TradeGPT loaded the regulatory corpus, but answer generation is unavailable "
                    "because GROQ_API_KEY is not configured."
                ),
                "citations": [document.name for document in self.documents],
                "confidence": "Unavailable (LLM missing)",
                "source": "TradeGPT Full-Context Engine",
                "retrieval_method": "full_context",
                "corpus_documents": [document.name for document in self.documents],
            }
            self._cache[query_hash] = (result, datetime.now())
            return result

        system_prompt = f"""Answer the user query strictly from the provided regulatory corpus.
If the corpus does not contain the answer, say that clearly.
Do not use outside knowledge.

You are TradeGPT, an expert legal analyst for CBAM, Indian trade policy, and WTO text.
Requirements:
1. Cite specific Articles or Sections when present.
2. Connect provisions across documents when relevant.
3. Prefer concise, structured bullet points.

=== FULL REGULATORY CORPUS ===
{self.knowledge_base_text}
"""

        try:
            completion = self.model.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.1,
                max_completion_tokens=2048,
            )
            answer_text = completion.choices[0].message.content
            result = {
                "answer": answer_text,
                "citations": self._build_citations(answer_text),
                "confidence": "High (Full corpus in context)",
                "source": "TradeGPT · LLaMA 3.3 70B (Full-Context RAG)",
                "retrieval_method": "full_context",
                "corpus_documents": [document.name for document in self.documents],
            }
        except Exception as exc:  # noqa: BLE001
            result = {
                "answer": f"TradeGPT full-context request failed: {exc}",
                "citations": [document.name for document in self.documents],
                "confidence": "Error",
                "source": "TradeGPT Full-Context Engine",
                "retrieval_method": "full_context",
                "corpus_documents": [document.name for document in self.documents],
            }
        self._cache[query_hash] = (result, datetime.now())
        return result

    async def ask_legal_question(self, user_query: str) -> dict:
        return await self.ask_question(user_query)

    async def ask_vector_question(self, user_query: str) -> dict:
        retrieved_chunks = self._retrieve_vector_chunks(user_query)
        retrieval_meta = self._serialize_retrieval(retrieved_chunks)
        citations = self._build_citations("", retrieved_chunks)

        query_hash = self._get_query_hash("vector", user_query)
        if self._is_cache_valid(query_hash):
            result, _ = self._cache[query_hash]
            return {**result, "cached": True}

        if not self.model:
            result = {
                "answer": (
                    "Vector retrieval completed against the local regulatory corpus, but answer "
                    "generation is unavailable because GROQ_API_KEY is not configured."
                ),
                "citations": citations,
                "confidence": "Retrieval only (LLM missing)",
                "source": "TradeGPT · Local TF-IDF Vector Index",
                "retrieval_method": "tfidf_vector_index",
                "retrieved_chunks": retrieval_meta,
            }
            self._cache[query_hash] = (result, datetime.now())
            return result

        context = "\n\n---\n\n".join(
            f"[{chunk['document']} chunk {chunk['chunk_id']} | score={chunk['score']}]\n{chunk['text']}"
            for chunk in retrieved_chunks
        )

        system_prompt = f"""Answer the user query strictly from the retrieved chunks below.
If the retrieved chunks are insufficient, say so clearly.
Do not use outside knowledge.

You are TradeGPT operating in chunked vector-retrieval mode.
Call out when cross-references are missing because only partial chunks were retrieved.

=== RETRIEVED CHUNKS ===
{context}
"""

        try:
            completion = self.model.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.1,
                max_completion_tokens=1024,
            )

            answer_text = completion.choices[0].message.content
            result = {
                "answer": answer_text,
                "citations": self._build_citations(answer_text, retrieved_chunks),
                "confidence": "Medium (Chunked TF-IDF vector retrieval)",
                "source": "TradeGPT · LLaMA 3.3 70B (TF-IDF Vector RAG)",
                "retrieval_method": "tfidf_vector_index",
                "retrieved_chunks": retrieval_meta,
            }
        except Exception as exc:  # noqa: BLE001
            result = {
                "answer": f"TradeGPT vector request failed: {exc}",
                "citations": citations,
                "confidence": "Error",
                "source": "TradeGPT · Local TF-IDF Vector Index",
                "retrieval_method": "tfidf_vector_index",
                "retrieved_chunks": retrieval_meta,
            }
        self._cache[query_hash] = (result, datetime.now())
        return result


legal_advisor = LegalAdvisor()
