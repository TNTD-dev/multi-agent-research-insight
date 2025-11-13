"""
RAG Agent - handles vector store creation and retrieval.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from src.agents.state import ResearchSource, ResearchState
from src.config import ResearchConfig
from src.utils.logger import default_logger as logger


class RAGAgent:
    """Agent responsible for preparing and querying the RAG vector store."""

    def __init__(self, llm, config: ResearchConfig):
        self.llm = llm
        self.config = config
        self.embeddings = HuggingFaceEmbeddings(model_name=config.rag.embedding_model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap,
        )

    def create_vector_store(
        self, sources: List[ResearchSource], query: str
    ) -> Tuple[Chroma, str]:
        """Create a Chroma vector store from validated sources."""

        if not sources:
            raise ValueError("No sources provided to create vector store.")

        documents: List[Document] = []
        for source in sources:
            content = (
                f"Title: {source.get('title', '')}\n"
                f"Authors: {', '.join(source.get('authors', [])[:3])}\n"
                f"Summary: {source.get('full_text', source.get('summary', ''))}\n"
                f"Published: {source.get('published', 'Unknown')}\n"
                f"Source: {source.get('source_type', 'unknown')}"
            )
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source_id": source.get("id", ""),
                        "title": source.get("title", ""),
                        "url": source.get("url", ""),
                        "source_type": source.get("source_type", ""),
                        "citation_count": source.get("citation_count", 0),
                    },
                )
            )

        split_docs = self.text_splitter.split_documents(documents)
        logger.info("RAG: Prepared %d chunks from %d sources", len(split_docs), len(sources))

        collection_name = f"research_{hashlib.md5(query.encode()).hexdigest()[:8]}"
        vector_store = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=self.config.rag.chroma_persist_directory,
        )

        logger.info("RAG: Vector store created %s", collection_name)
        return vector_store, collection_name

    def query_rag(self, vector_store: Chroma, query: str, k: int | None = None) -> List[Dict[str, object]]:
        """Retrieve relevant chunks from the vector store."""

        k = k or self.config.rag.similarity_top_k
        results = vector_store.similarity_search(query, k=k)
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]

    def integrate(self, state: ResearchState) -> Dict[str, object]:
        """Create embeddings and persist the vector store."""

        validated_sources = state.validated_sources
        if not validated_sources:
            logger.warning("RAG: No validated sources provided.")
            return {
                "embeddings_created": False,
                "rag_ready": False,
                "vector_store_id": "",
            }

        vector_store, collection_id = self.create_vector_store(validated_sources, state.query)
        retrieved = self.query_rag(vector_store, state.query, k=3)
        logger.info("RAG: Retrieved %d chunks during sanity check", len(retrieved))

        return {
            "embeddings_created": True,
            "rag_ready": True,
            "vector_store_id": collection_id,
        }
