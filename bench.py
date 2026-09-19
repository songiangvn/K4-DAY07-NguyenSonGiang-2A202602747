"""bench.py — công cụ đo retrieval cho Lab 07 (K4-L3A, nhóm G26).

Luồng: file .md -> tách frontmatter -> chunk phần thân -> mỗi chunk là một
Document -> nạp vào EmbeddingStore -> chạy 5 benchmark query -> in top-3.

Chunking xảy ra Ở ĐÂY, ngoài store: store coi 1 Document = 1 record.

Cách dùng:
    python bench.py                        # chiến lược mặc định (xem STRATEGY)
    python bench.py --strategy heading     # đổi chiến lược không cần sửa file
    python bench.py --llm                  # gọi LLM thật để chấm grounding
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from src import (
    Document,
    EmbeddingStore,
    FixedSizeChunker,
    GeminiEmbedder,
    KnowledgeBaseAgent,
    LocalEmbedder,
    OpenAIEmbedder,
    RecursiveChunker,
    SentenceChunker,
    _mock_embed,
)

DATA_DIR = Path("data/hoc-bong-hoc-phi")
OUTPUT_PATH = Path("ket_qua_benchmark.txt")
CACHE_PATH = Path(".embedding_cache.json")

# =============================================================================
# DÒNG DUY NHẤT MỖI THÀNH VIÊN ĐỔI — chiến lược chunking của riêng bạn.
# Mọi thứ khác giữ nguyên để so sánh giữa các thành viên mới công bằng.
# =============================================================================
STRATEGY = "recursive"


class HeadingChunker:
    """Chia theo tiêu đề/mục của văn bản quy định.

    Lý do thiết kế: văn bản quy định được người soạn chia sẵn theo mục
    (`## Mức học bổng theo hoàn cảnh`, `## Hồ sơ đăng ký`), nên mỗi mục vốn
    đã là một đơn vị ngữ nghĩa trọn vẹn. Mục nào dài quá ngưỡng thì hạ xuống
    RecursiveChunker, và tiêu đề được GẮN LẠI vào từng mảnh con — thiếu bước
    này thì mảnh thứ hai trở đi mất ngữ cảnh "đây là mục nói về cái gì".
    """

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        chunks: list[str] = []
        for section in re.split(r"(?m)^(?=#{1,6}\s)", text):
            section = section.strip()
            if not section:
                continue
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            heading = (
                section.split("\n", 1)[0].strip() if section.startswith("#") else ""
            )
            for piece in self._fallback.chunk(section):
                if heading and not piece.lstrip().startswith(heading):
                    piece = f"{heading}\n{piece}"
                chunks.append(piece)
        return chunks


CHUNKERS = {
    "fixed": lambda: FixedSizeChunker(chunk_size=500, overlap=50),
    "sentence": lambda: SentenceChunker(max_sentences_per_chunk=3),
    "recursive": lambda: RecursiveChunker(chunk_size=500),
    "heading": lambda: HeadingChunker(chunk_size=500),
}


# =============================================================================
# 5 BENCHMARK QUERY + GOLD ANSWER — cả nhóm dùng chung bộ này.
#
# must_contain: chuỗi đặc trưng PHẢI xuất hiện trong ngữ cảnh truy xuất được.
# Chấm theo doc_id thôi là chưa đủ: một chiến lược có thể chiếm trọn top-3
# bằng đúng tài liệu gold mà không chunk nào chứa câu trả lời.
# =============================================================================
BENCHMARK = [
    {
        "id": 1,
        "kind": "tra số liệu",
        "question": "Sinh viên thuộc hộ nghèo được cấp học bổng hỗ trợ học tập trị giá bao nhiêu phần trăm học phí?",
        "gold_answer": (
            "Toàn phần, trị giá 100% học phí (so với chương trình đào tạo chuẩn). "
            "Hộ cận nghèo và hộ đặc biệt khó khăn được bán phần 50% học phí."
        ),
        "gold_doc_id": "tieu-chi-xet-hoc-bong-ho-tro-hoc-tap",
        "must_contain": ["100% học phí"],
        "metadata_filter": None,
    },
    {
        "id": 2,
        "kind": "hỏi điều kiện",
        "question": "Điều kiện GPA và điểm rèn luyện để được học bổng khuyến khích học tập loại A là bao nhiêu?",
        "gold_answer": "Loại A: GPA từ 3.6 và điểm rèn luyện từ 90. Mức học bổng loại A tương đương 150% học phí.",
        "gold_doc_id": "ho-tro-tai-chinh-tan-sinh-vien",
        "must_contain": ["3.6", "90"],
        "metadata_filter": None,
    },
    {
        "id": 3,
        "kind": "hỏi quy trình — CẦN METADATA FILTER",
        "question": "Hồ sơ đăng ký học bổng hỗ trợ học tập nộp ở đâu?",
        "gold_answer": (
            "Với sinh viên đang học: gửi về Phòng Tuyển sinh, Phòng 202, Nhà D7, "
            "Trường Đại học Bách khoa Hà Nội, số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội."
        ),
        "gold_doc_id": "tieu-chi-xet-hoc-bong-ho-tro-hoc-tap",
        "must_contain": ["Phòng 202", "D7"],
        "metadata_filter": {"audience": "student"},
        # Câu này cố tình KHÔNG nêu người hỏi là ai. Corpus có hai tài liệu cùng
        # nói về "học bổng hỗ trợ học tập" nhưng khác audience và khác đáp án:
        #   audience=student   -> nộp Phòng 202, Nhà D7 (Phòng Tuyển sinh)
        #   audience=applicant -> nộp online, bản cứng ở Phòng 103 nhà C1 (Phòng CTSV)
        # Không lọc thì retrieval lẫn hai tài liệu và agent trả lời sai đối tượng.
    },
    {
        "id": 4,
        "kind": "tra học phí",
        "question": "Học phí chương trình ELITECH năm học 2022-2023 là bao nhiêu một năm?",
        "gold_answer": (
            "35 đến 40 triệu đồng/năm học; riêng Khoa học dữ liệu và Trí tuệ nhân tạo (IT-E10) "
            "và Logistics và Quản lý chuỗi cung ứng (EM-E14) khoảng 60 triệu đồng/năm học."
        ),
        "gold_doc_id": "hoc-phi-dai-hoc-2022",
        "must_contain": ["35", "40 triệu"],
        "metadata_filter": None,
    },
    {
        "id": 5,
        "kind": "liệt kê",
        "question": "Những chương trình vi mạch bán dẫn nào được nhận học bổng mức 4.200.000 đồng/tháng?",
        "gold_answer": (
            "Hai chương trình đại học và một chương trình kỹ sư chuyên sâu: Kỹ thuật Điện tử - Viễn thông (ET1), "
            "Hệ thống nhúng thông minh và IoT (tăng cường tiếng Nhật) (ET-E9), và Kỹ sư chuyên sâu Thiết kế vi mạch."
        ),
        "gold_doc_id": "nghi-dinh-55-nhan-hoc-bong",
        "must_contain": ["ET1", "ET-E9"],
        "metadata_filter": None,
    },
]


class CachedEmbedder:
    """Cache embedding theo hash nội dung để chạy lại không tốn thêm tiền API."""

    def __init__(self, inner, model_tag: str, path: Path = CACHE_PATH) -> None:
        self._inner = inner
        self._model_tag = model_tag
        self._path = path
        self._backend_name = getattr(inner, "_backend_name", type(inner).__name__)
        self.hits = 0
        self.misses = 0
        try:
            self._cache = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self._cache = {}

    def __call__(self, text: str) -> list[float]:
        key = hashlib.md5(f"{self._model_tag}\x00{text}".encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached

        vector = self._inner(text)
        self._cache[key] = vector
        self.misses += 1
        return vector

    def save(self) -> None:
        self._path.write_text(json.dumps(self._cache), encoding="utf-8")


def build_embedder():
    """Chọn backend theo .env, tự lùi về mock nếu thiếu thư viện hoặc key."""
    load_dotenv(override=False)
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()

    try:
        if provider == "openai":
            model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            return CachedEmbedder(OpenAIEmbedder(model_name=model), model), provider
        if provider == "local":
            inner = LocalEmbedder()
            return CachedEmbedder(inner, inner.model_name), provider
        if provider == "gemini":
            model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
            return CachedEmbedder(GeminiEmbedder(model_name=model), model), provider
    except Exception as exc:  # thiếu key hoặc thư viện -> không làm sập benchmark
        print(f"[!] Không khởi tạo được backend '{provider}' ({exc}); quay về mock.")

    return CachedEmbedder(_mock_embed, "mock"), "mock"


def parse_markdown(path: Path) -> tuple[dict, str]:
    """Tách frontmatter YAML thành metadata và phần còn lại thành content."""
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}, raw.strip()

    parts = raw.split("---")
    frontmatter = dict(re.findall(r"^(\w+):\s*(.+)$", parts[1], re.M))
    return {k: v.strip() for k, v in frontmatter.items()}, "---".join(parts[2:]).strip()


def load_chunked_documents(chunker) -> list[Document]:
    """Mỗi chunk là một Document; metadata frontmatter trải vào MỌI chunk."""
    documents: list[Document] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        frontmatter, body = parse_markdown(path)
        for index, chunk in enumerate(chunker.chunk(body)):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    # doc_id trỏ về FILE GỐC, không phải id của chunk.
                    metadata={**frontmatter, "doc_id": path.stem, "chunk_index": index},
                )
            )
    return documents


def build_llm_fn(use_real_llm: bool):
    if not use_real_llm:

        def demo_llm(_prompt: str) -> str:
            return "[DEMO LLM — chạy với --llm để gọi model thật]"

        return demo_llm

    from openai import OpenAI

    client = OpenAI()
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    def openai_llm(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content.strip()

    return openai_llm


def rank_of(results: list[dict], doc_id: str) -> int | None:
    for position, result in enumerate(results, start=1):
        if result["metadata"].get("doc_id") == doc_id:
            return position
    return None


def score_case(results: list[dict], case: dict) -> tuple[int, int, bool, int | None]:
    """Chấm hai mức: theo doc_id (ngây thơ) và theo nội dung (thật)."""
    rank = rank_of(results, case["gold_doc_id"])
    context = "\n".join(r["content"] for r in results)
    context_ok = all(needle in context for needle in case["must_contain"])

    naive = 2 if rank == 1 else 1 if rank in (2, 3) else 0
    strict = naive if context_ok else 0
    return naive, strict, context_ok, rank


def format_results(results: list[dict]) -> list[str]:
    lines = []
    for position, result in enumerate(results, start=1):
        preview = " ".join(result["content"].split())[:110]
        lines.append(
            f"      {position}. score={result['score']:+.4f}  {result['metadata'].get('doc_id')}"
            f"  [{result['metadata'].get('audience')}]  #{result['metadata'].get('chunk_index')}"
        )
        lines.append(f"         {preview}...")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark retrieval cho Lab 07")
    parser.add_argument("--strategy", choices=sorted(CHUNKERS), default=STRATEGY)
    parser.add_argument(
        "--llm", action="store_true", help="gọi LLM thật để chấm grounding"
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--out", type=Path, default=OUTPUT_PATH, help="file kết quả")
    args = parser.parse_args()

    out: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        out.append(line)

    chunker = CHUNKERS[args.strategy]()
    embedder, provider = build_embedder()

    documents = load_chunked_documents(chunker)
    store = EmbeddingStore(collection_name="g26_hoc_bong", embedding_fn=embedder)
    store.add_documents(documents)

    files = sorted(DATA_DIR.glob("*.md"))
    lengths = [len(d.content) for d in documents]

    emit("=" * 78)
    emit("BENCHMARK RETRIEVAL — Lab 07 · Nhóm G26 · chủ đề học bổng & học phí HUST")
    emit("=" * 78)
    emit(f"Chiến lược chunking : {args.strategy}")
    emit(f"Embedding backend   : {embedder._backend_name} (provider={provider})")
    emit(f"Tài liệu nạp        : {len(files)} file .md")
    emit(f"Chunk đã nạp        : {store.get_collection_size()} chunks")
    emit(
        f"Độ dài chunk        : min={min(lengths)}  max={max(lengths)}  avg={sum(lengths)/len(lengths):.1f}"
    )
    if provider == "mock":
        emit("")
        emit("[!] CẢNH BÁO: MockEmbedder băm MD5, KHÔNG mã hoá ngữ nghĩa.")
        emit(
            "    Mọi điểm số dưới đây là nhiễu — không dùng để kết luận chất lượng retrieval."
        )

    agent = KnowledgeBaseAgent(store=store, llm_fn=build_llm_fn(args.llm))

    total_naive = 0
    total_strict = 0

    for case in BENCHMARK:
        emit("")
        emit("-" * 78)
        emit(f"[Q{case['id']}] ({case['kind']}) {case['question']}")
        emit(f"      Gold answer : {case['gold_answer']}")
        emit(f"      Gold doc_id : {case['gold_doc_id']}")
        emit(f"      Phải chứa   : {case['must_contain']}")
        emit("")

        results = store.search_with_filter(
            case["question"], top_k=args.top_k, metadata_filter=case["metadata_filter"]
        )
        emit(f"   Top-{args.top_k} (metadata_filter={case['metadata_filter']}):")
        for line in format_results(results):
            emit(line)

        naive, strict, context_ok, rank = score_case(results, case)
        total_naive += naive
        total_strict += strict
        emit("")
        emit(f"   Hạng của tài liệu gold : {rank if rank else 'KHÔNG CÓ trong top-3'}")
        emit(f"   Ngữ cảnh chứa đáp án   : {'CÓ' if context_ok else 'KHÔNG'}")
        emit(f"   Điểm theo doc_id       : {naive}/2   <- cách chấm ngây thơ")
        emit(f"   Điểm theo nội dung     : {strict}/2   <- cách chấm thật (SCORING.md)")

        # A/B bắt buộc cho câu cần filter.
        if case["metadata_filter"]:
            emit("")
            emit("   === A/B: CÙNG CÂU HỎI, BỎ METADATA FILTER ===")
            without = store.search_with_filter(
                case["question"], top_k=args.top_k, metadata_filter=None
            )
            for line in format_results(without):
                emit(line)
            _, s2, ok2, r2 = score_case(without, case)
            emit("")
            emit(
                f"   Không lọc -> hạng gold={r2}, ngữ cảnh chứa đáp án={'CÓ' if ok2 else 'KHÔNG'}, điểm thật={s2}/2"
            )
            changed = [r["metadata"].get("doc_id") for r in without] != [
                r["metadata"].get("doc_id") for r in results
            ]
            emit(
                f"   Filter có đổi kết quả không: {'CÓ' if changed else 'KHÔNG — câu hỏi chưa thực sự cần filter'}"
            )

        emit("")
        emit("   Câu trả lời của agent:")
        answer = agent.answer(case["question"], top_k=args.top_k)
        for line in answer.splitlines() or [""]:
            emit(f"      {line}")

    emit("")
    emit("=" * 78)
    emit(f"TỔNG ĐIỂM — chấm theo doc_id   : {total_naive}/10")
    emit(f"TỔNG ĐIỂM — chấm theo nội dung : {total_strict}/10")
    emit(f"Chênh lệch giữa hai cách chấm  : {total_naive - total_strict} điểm")
    emit("=" * 78)

    embedder.save()
    print(f"\n[cache] hits={embedder.hits} misses={embedder.misses} -> {CACHE_PATH}")

    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[out]   Đã ghi {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
