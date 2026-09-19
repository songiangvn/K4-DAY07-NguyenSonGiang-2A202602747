from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    NO_CONTEXT_MESSAGE = (
        "Không tìm thấy tài liệu liên quan trong cơ sở tri thức để trả lời câu hỏi này."
    )

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)

        # Empty store or no candidates: say so instead of burning an LLM call
        # on a prompt with no context to ground the answer in.
        if not results:
            return self.NO_CONTEXT_MESSAGE

        prompt = self._build_prompt(question, results)
        return self.llm_fn(prompt)

    def _build_prompt(self, question: str, results: list[dict]) -> str:
        """Build a grounded prompt whose answer can be traced back to a chunk."""
        blocks = []
        for number, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = metadata.get("source_url") or metadata.get("source") or metadata.get("doc_id", "unknown")
            title = metadata.get("title", result.get("id", ""))
            blocks.append(f"[{number}] {title} (nguồn: {source})\n{result['content']}")

        context = "\n\n".join(blocks)

        # Numbering the chunks and demanding citations is what makes the answer
        # traceable to a specific chunk and file (Source Traceability in
        # docs/EVALUATION.md) — for a corpus of regulations that is not optional.
        return (
            "Bạn là trợ lý tra cứu quy định và dịch vụ đại học.\n"
            "Chỉ được trả lời dựa trên các đoạn ngữ cảnh được đánh số bên dưới.\n"
            "Nếu ngữ cảnh không chứa thông tin cần thiết, hãy nói rõ là không tìm thấy "
            "trong tài liệu — tuyệt đối không suy đoán quy định.\n"
            "Mỗi ý trong câu trả lời phải trích dẫn số đoạn đã dùng, ví dụ [1] hoặc [2].\n"
            "Trả lời bằng cùng ngôn ngữ với câu hỏi.\n\n"
            f"=== NGỮ CẢNH ===\n{context}\n\n"
            f"=== CÂU HỎI ===\n{question}\n\n"
            "=== TRẢ LỜI ==="
        )
