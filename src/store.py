from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        # In-memory only, deliberately. The skeleton probed for chromadb and set
        # this flag before any client existed, so merely having chromadb installed
        # would route every method into an unimplemented branch.
        self._use_chroma = False

    def _make_record(self, doc: Document) -> dict[str, Any]:
        """Normalize one Document into the dict shape kept in the store."""
        # Copy: the caller keeps ownership of its own metadata dict.
        metadata = dict(doc.metadata or {})
        # delete_document() matches on this key, so every record must carry one.
        # At chunk level the caller sets it to the SOURCE file, not the chunk id.
        metadata.setdefault("doc_id", doc.id)

        record = {
            "index": self._next_index,
            "id": doc.id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._embedding_fn(doc.content),
        }
        self._next_index += 1
        return record

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """Rank an arbitrary candidate set against query.

        Both search() and search_with_filter() funnel through here so they can
        never disagree; they differ only in which candidates they pass in.
        """
        if not records or top_k <= 0:
            return []

        query_embedding = self._embedding_fn(query)
        results = []
        for record in records:
            # Embeddings are unit-normalized, so dot product == cosine similarity.
            result = {key: value for key, value in record.items() if key != "embedding"}
            result["score"] = _dot(query_embedding, record["embedding"])
            results.append(result)

        results.sort(key=lambda result: result["score"], reverse=True)
        return results[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store

        One Document becomes one record; chunking happens in the caller.
        """
        for doc in docs:
            self._store.append(self._make_record(doc))

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        # Pre-filter, never post-filter: taking top_k first and discarding
        # mismatches afterwards can return nothing while valid documents remain,
        # because the k slots were already spent on the wrong audience.
        if not metadata_filter:
            candidates = self._store
        else:
            candidates = [
                record
                for record in self._store
                if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
            ]

        return self._search_records(query, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        remaining = [record for record in self._store if record["metadata"].get("doc_id") != doc_id]
        if len(remaining) == len(self._store):
            return False

        self._store = remaining
        return True
