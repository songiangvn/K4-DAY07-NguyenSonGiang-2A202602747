# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Sơn Giang
**Nhóm:** G26 — vai Code (theo dõi tiến độ hoàn thiện `src/`, xác nhận 42/42 test pass)
**Ngày:** 19/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine similarity đo **góc** giữa hai vector embedding, không đo khoảng cách. Điểm gần 1 nghĩa là hai vector gần như cùng hướng trong không gian embedding, tức mô hình đánh giá hai đoạn text nói về cùng một nội dung — kể cả khi chúng không dùng chung một từ nào.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Sinh viên thuộc hộ nghèo được cấp học bổng toàn phần trị giá 100% học phí."
- Câu B: "Người học có gia đình thuộc diện nghèo được miễn toàn bộ tiền học."
- Tại sao tương đồng: Hai câu **gần như không trùng từ vựng** ("học bổng toàn phần" vs "miễn toàn bộ tiền học", "sinh viên" vs "người học"), nhưng diễn đạt đúng một chính sách. Đây mới là phép thử thật của embedding — nếu chọn hai câu chỉ khác nhau vài chữ thì similarity cao cũng không chứng minh được mô hình hiểu nghĩa hay chỉ đang so khớp từ.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Học bổng hỗ trợ học tập trị giá 50% học phí dành cho hộ cận nghèo."
- Câu B: "Thư viện Tạ Quang Bửu mở cửa từ 7h30 đến 21h các ngày trong tuần."
- Tại sao khác: Khác hẳn chủ đề (chính sách tài chính vs giờ giấc dịch vụ), không chung trường ngữ nghĩa nào. Hai vector gần như vuông góc → điểm quanh 0.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Vì cosine **bỏ qua độ dài vector, chỉ giữ lại hướng**. Độ lớn của embedding phản ánh những thứ như độ dài đoạn text chứ không phản ánh nội dung, nên một đoạn 3 câu và một đoạn 30 câu cùng nói về học phí sẽ cách xa nhau theo Euclid dù cùng nghĩa. Cosine còn bị chặn trong `[-1, 1]` nên đặt ngưỡng lọc được một lần và dùng chung cho mọi tài liệu, trong khi ngưỡng Euclid phải chỉnh lại theo từng bộ dữ liệu.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* Mỗi chunk mới chỉ tiến thêm được `step = chunk_size − overlap = 500 − 50 = 450` ký tự, riêng chunk đầu phủ trọn 500. Áp công thức `ceil((độ_dài − overlap) / (chunk_size − overlap))` = `ceil((10000 − 50) / 450)` = `ceil(9950 / 450)` = `ceil(22.11)`.
> *Đáp án:* **23 chunks.** Đã kiểm lại bằng chính code trong repo thay vì tin công thức suông:
> ```bash
> python -c "from src.chunking import FixedSizeChunker; print(len(FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)))"
> # 23
> ```

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Số chunk **tăng lên 25** (`ceil((10000 − 100) / 400)` = `ceil(24.75)` = 25, `FixedSizeChunker` chạy thật cũng ra 25): overlap càng lớn thì step càng nhỏ, cùng một tài liệu phải cắt thành nhiều lát hơn. Lý do đánh đổi lấy chi phí đó là **thông tin nằm vắt ngang ranh giới chunk**: một câu như "sinh viên hộ nghèo được cấp học bổng toàn phần 100% học phí" nếu bị cắt đúng giữa thì không chunk nào chứa trọn vẹn cả điều kiện lẫn mức hưởng, và retrieval sẽ không bao giờ trả về được đáp án đầy đủ dù tài liệu có chứa nó. Overlap cho mỗi đoạn text một cơ hội thứ hai xuất hiện nguyên vẹn trong ít nhất một chunk. Giá phải trả là nhiều chunk hơn (tốn embedding, tốn lưu trữ) và top-k dễ bị chiếm bởi các chunk trùng lặp nội dung.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Regex dùng **lookbehind**: `re.compile(r"(?<=[.!?])\s+")`. Chỗ này tôi cân nhắc kỹ vì cách viết trực giác `[.!?]\s+` sẽ **nuốt mất dấu câu** — regex ăn luôn ký tự kết câu vào phần bị split bỏ, kết quả mọi chunk thành câu cụt. Lookbehind khớp khoảng trắng *đứng sau* dấu câu mà không tiêu thụ chính dấu câu đó, nên `\s+` cũng phủ luôn cả bốn trường hợp docstring yêu cầu (`". "`, `"! "`, `"? "`, `".\n"`). Sau khi tách thì strip từng câu và loại câu rỗng, rồi gom `max_sentences_per_chunk` câu một bằng slice theo bước nhảy.
>
> **Edge case đã xử lý:** text rỗng trả `[]` chứ không crash; chuỗi khoảng trắng thừa giữa các câu bị strip; câu rỗng sinh ra do dấu câu liên tiếp bị lọc bỏ.
>
> **Edge case tôi biết là chưa xử lý được:** regex này coi mọi dấu chấm là hết câu, nên **chữ viết tắt và số thập phân bị cắt sai** — `"TS. Nguyễn Văn A"` tách thành hai câu, `"v.v."` tách thành ba, `"2.5 triệu đồng"` tách giữa con số. Với corpus quy định tiếng Việt thì cả ba dạng đều xuất hiện thật (tài liệu học bổng có "30 triệu đồng", "100% học phí", các mục liệt kê kết thúc bằng "v.v."). Sửa đúng cần một danh sách ngoại lệ viết tắt hoặc chuyển sang thư viện tách câu chuyên dụng, nằm ngoài phạm vi bài lab.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán chạy **hai chiều**, và tôi chú ý đúng chỗ này vì viết thiếu một chiều là code vẫn chạy nhưng kết quả hỏng:
> - *Đệ quy xuống sâu:* thử separator theo thứ tự ưu tiên `["\n\n", "\n", ". ", " ", ""]` — cắt ở ranh giới "to" trước để giữ trọn ngữ nghĩa; mảnh nào vẫn dài hơn `chunk_size` mới gọi lại `_split` với **danh sách separator còn lại**, tức hạ dần xuống ranh giới nhỏ hơn.
> - *Gom lên:* dùng một biến `buffer` nối các mảnh nhỏ liền kề cho tới sát `chunk_size` rồi mới flush. Thiếu bước này thì một file nhiều dòng ngắn sẽ nổ ra hàng trăm chunk vụn 5–10 ký tự và retrieval rất tệ. Tôi test riêng: 200 dòng ngắn với `chunk_size=200` cho ra **9 chunks, ngắn nhất 98 ký tự, dài nhất 200** — không còn mảnh vụn nào.
>
> **Base case — có ba, không phải một:**
> 1. `current_text` rỗng → trả `[]`.
> 2. `len(current_text) <= chunk_size` → trả `[current_text]`, không cắt thêm.
> 3. Hết separator (`remaining_separators == []`) **hoặc** separator hiện tại là chuỗi rỗng `""` → cắt cứng theo `chunk_size`.
>
> Nhánh 3 tôi gộp hai điều kiện có chủ đích. Ngoài việc đỡ cho `separators=[]` truyền thẳng từ test, nó còn chặn một lỗi runtime: `DEFAULT_SEPARATORS` có phần tử cuối là `""`, mà `"abc".split("")` trong Python ném `ValueError: empty separator`. Nếu chỉ kiểm tra danh sách rỗng thì mọi văn bản đệ quy xuống tới separator cuối cùng đều crash.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Tôi làm **hai helper trước, bốn method công khai sau**, vì làm ngược lại sẽ phải viết lặp cùng một logic ở bốn chỗ.
>
> `_make_record` chuẩn hoá một `Document` thành dict `{index, id, content, metadata, embedding}`. Hai chi tiết tôi cân nhắc: (1) **copy metadata** bằng `dict(doc.metadata or {})` chứ không giữ tham chiếu tới dict của người gọi — store không được sửa dữ liệu bên ngoài; (2) luôn bảo đảm có khoá `metadata["doc_id"]`, mặc định lấy `doc.id` nếu caller chưa đặt, vì `delete_document` dựa hoàn toàn vào khoá này.
>
> `add_documents` chỉ lặp và append — **một `Document` = một record**, không tự chunk. Việc chunking nằm ở tầng ngoài (`bench.py`), mỗi chunk được tạo thành một `Document` riêng. `search` uỷ quyền thẳng cho `_search_records` trên toàn bộ store. Độ tương tự tính bằng **dot product** (`_dot`) chứ không gọi `compute_similarity`: các embedder trong repo đều trả vector đã chuẩn hoá `||v|| = 1`, mà với vector đơn vị thì dot product **bằng đúng** cosine, nên bỏ được phép chia cho tích hai norm luôn bằng 1.
>
> Kết quả trả về tôi **loại bỏ khoá `embedding`** — vector 64–384 chiều làm bẩn output khi in ra terminal và không ai dùng tới nó ở tầng trên.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> **Lọc TRƯỚC, rồi mới search.** Đây là điểm tôi thấy dễ sai nhất và hậu quả thì âm thầm: nếu lấy top-k trước rồi mới bỏ những cái không khớp metadata, ta có thể còn lại **0 kết quả dù store vẫn còn tài liệu hợp lệ** — vì k slot đã bị tài liệu sai đối tượng chiếm hết. Tôi dựng một test riêng để chứng minh: store có 6 tài liệu `audience=applicant` và đúng 1 tài liệu `audience=student` cùng nói về học bổng hỗ trợ học tập; gọi `search_with_filter(..., top_k=3, metadata_filter={"audience": "student"})` trả về **đúng 1 kết quả (`s1`)**, trong khi lọc-sau sẽ trả về 0 vì cả 3 slot đã bị applicant chiếm.
>
> Cả `search` và `search_with_filter` đều đi qua **cùng một hàm `_search_records`**, chỉ khác tập ứng viên truyền vào. Nhờ vậy hai đường không thể lệch kết quả, và `metadata_filter=None` hiển nhiên trả về y hệt `search` (kiểm lại: cả hai đều ra 7 kết quả trên cùng store).
>
> `delete_document` lọc giữ lại các record có `metadata["doc_id"] != doc_id`, so sánh độ dài trước/sau để quyết định trả `True` hay `False`. Điểm quan trọng là nó xoá **theo file gốc chứ không theo chunk**: với 4 chunk `hoc-bong#0..3` cùng mang `doc_id="hoc-bong"`, một lệnh `delete_document("hoc-bong")` xoá sạch cả 4, gọi lần hai trả `False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba nhịp: truy xuất top-k → dựng prompt có ngữ cảnh → gọi `llm_fn`.
>
> Phần tôi đầu tư nhất là cách dựng ngữ cảnh. Mỗi chunk được **đánh số `[1] [2] [3]` kèm tiêu đề và nguồn** (ưu tiên `source_url`, lùi dần về `source` rồi `doc_id`), rồi prompt yêu cầu model trích dẫn đúng số đó trong câu trả lời. Nhờ vậy mỗi ý trong câu trả lời **truy vết ngược được** về đúng chunk và đúng file — đây là tiêu chí *Source Traceability* trong `docs/EVALUATION.md`, và với corpus quy định học bổng thì nó không phải tính năng phụ: người đọc phải kiểm chứng được mức 100% hay 50% học phí đến từ văn bản nào.
>
> Hai ràng buộc chống bịa đặt viết thẳng trong prompt: chỉ được dùng ngữ cảnh đã cung cấp, và nếu ngữ cảnh không đủ thì phải nói rõ là không tìm thấy trong tài liệu thay vì suy đoán quy định của trường.
>
> Trường hợp store rỗng được chặn **trước khi** gọi LLM — trả về câu thông báo cố định. Vừa không crash, vừa không tốn một lần gọi LLM cho một prompt không có gì để bám vào. Tôi kiểm bằng cách đếm số lần `llm_fn` được gọi: **0 lần** khi store rỗng.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\LAB_AI_IN_ACTION\Lab07\K4-L3A-Data-Foundations
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.09s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

`main.py` cũng chạy trọn vẹn từ đầu đến cuối:

```
$ python main.py "Chunking là gì?"
Skipping missing file: data\customer_support_playbook.txt
Loaded 5 documents
Embedding backend: mock embeddings fallback
Stored 5 documents in EmbeddingStore
=== EmbeddingStore Search Test ===
1. score=0.150 source=data\rag_system_design.md
2. score=0.027 source=data\python_intro.txt
3. score=0.025 source=data\chunking_experiment_report.md
=== KnowledgeBaseAgent Test ===
Agent answer:
[DEMO LLM] Generated answer from prompt preview: Bạn là trợ lý tra cứu quy định ...
```

Dòng `Skipping missing file` là bình thường — repo không có file `data/customer_support_playbook.txt`.

### Ghi chú về `_use_chroma`

Tôi **bỏ hẳn nhánh ChromaDB** và để `self._use_chroma = False` cố định. Mã khởi tạo sẵn có một cái bẫy: nó `import chromadb` rồi gán `self._use_chroma = True` **trước khi** client hoặc collection nào được tạo. Trên máy tôi không cài `chromadb` nên nhánh đó không bao giờ chạy và test vẫn xanh — nhưng nếu máy chấm bài tình cờ có sẵn `chromadb`, cờ này bật lên và mọi method sẽ rẽ vào nhánh chưa hề được lập trình, làm sập toàn bộ 14 test của `EmbeddingStore`. Không test nào cần Chroma và `requirements.txt` cũng không cài nó, nên in-memory là lựa chọn đúng.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Đo bằng `compute_similarity()` trên vector `text-embedding-3-small`. Dự đoán được **viết ra trước khi chạy** và không sửa lại sau khi thấy kết quả.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Sinh viên thuộc hộ nghèo được cấp học bổng toàn phần trị giá 100% học phí." | "Người học có gia đình thuộc diện nghèo được miễn toàn bộ tiền học." | cao (~0,60) | **0,5839** | ✔ đúng |
| 2 | "Học bổng hỗ trợ học tập trị giá 50% học phí dành cho hộ cận nghèo." | "Thư viện Tạ Quang Bửu mở cửa từ 7h30 đến 21h các ngày trong tuần." | thấp (~0,20) | **0,2719** | ✔ đúng hướng, hơi cao hơn dự đoán |
| 3 | "Sinh viên thuộc **hộ nghèo** được cấp học bổng **toàn phần 100%** học phí." | "Sinh viên thuộc **hộ cận nghèo** được cấp học bổng **bán phần 50%** học phí." | cao (~0,80) | **0,8384** | ✔ đúng |
| 4 | "Điều kiện xét học bổng khuyến khích học tập loại A là GPA từ 3.6." | "Học phí chương trình ELITECH là 35 đến 40 triệu đồng một năm." | thấp–TB (~0,35) | **0,3093** | ✔ đúng |
| 5 | "Hồ sơ đăng ký học bổng hỗ trợ học tập nộp ở đâu?" | "Hồ sơ đăng ký gửi về: Phòng Tuyển sinh, Phòng 202, Nhà D7, trường ĐHBK Hà Nội." | cao (~0,60) | **0,5743** | ✔ đúng |

5/5 dự đoán đúng hướng. Sai lệch lớn nhất là cặp 2 (0,27 so với dự đoán 0,20) — hai câu khác hẳn chủ đề vẫn không xuống gần 0, vì cùng thuộc trường ngữ nghĩa "trường đại học".

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> **Bất ngờ nhất là cặp 3 (0,8384) cao hơn hẳn cặp 1 (0,5839).** Cặp 1 gồm hai câu **cùng nghĩa** nhưng khác từ vựng. Cặp 3 gồm hai câu có **đáp án ngược nhau** — hộ nghèo được 100%, hộ cận nghèo được 50% — nhưng dùng gần như cùng bộ từ. Embedding chấm cặp "trái nghĩa" cao hơn cặp "đồng nghĩa" tới 0,25 điểm.
>
> Điều này nói rằng cosine similarity đo **độ giống về chủ đề và từ vựng**, chứ không đo sự đồng nhất về *nội dung khẳng định*. Với văn bản quy định thì đây là điểm yếu nghiêm trọng: các điều khoản trong cùng một văn bản được viết theo khuôn mẫu giống hệt nhau, chỉ khác đúng vài chữ mang toàn bộ ý nghĩa pháp lý ("nghèo" vs "cận nghèo", "100%" vs "50%", "được" vs "không được").
>
> Đây không phải nhận xét lý thuyết — nó giải thích đúng một lỗi đã xảy ra trong benchmark của nhóm. Ở câu 1, chiến lược `sentence` đưa lên hạng 1 đoạn nói **hộ cận nghèo 50%** trong khi câu hỏi hỏi về **hộ nghèo 100%**, và bị 0 điểm. Cặp 3 ở trên chính là phép đo lý giải vì sao: với embedding, hai đoạn đó gần như không phân biệt được.

### Chẩn đoán thêm — vì sao câu 3 của benchmark thất bại

Đo độ tương tự giữa câu hỏi *"Hồ sơ đăng ký học bổng hỗ trợ học tập nộp ở đâu?"* và ba đoạn văn bản khác nhau trong cùng tài liệu:

| Đoạn văn bản | Similarity |
|---|---|
| Đoạn **liệt kê giấy tờ** ("Hồ sơ đăng ký học bổng hỗ trợ học tập gồm: Đơn đăng ký..., Bản sao sổ hộ khẩu...") | **0,7417** |
| Đoạn **chứa đáp án** ("Hồ sơ đăng ký gửi về: Phòng Tuyển sinh, Phòng 202, Nhà D7...") | 0,5792 |
| Đoạn nói về giải Học sinh Giỏi Quốc gia (đoạn thực tế thắng top-1 khi chạy `recursive`) | 0,4784 |

Đoạn **không trả lời được câu hỏi** lại đạt điểm cao nhất, hơn đoạn chứa đáp án tới 0,16. Lý do: nó lặp lại gần như nguyên văn cụm "Hồ sơ đăng ký học bổng hỗ trợ học tập" trong câu hỏi, trong khi đoạn chứa đáp án lại nặng về địa danh và số phòng — những từ hoàn toàn không xuất hiện trong câu hỏi. Từ khoá "ở đâu" không hề kéo embedding về phía một địa chỉ.

> *Lưu ý phương pháp:* ba con số trên đo trên các câu trích rời, không phải trên chunk nguyên vẹn, nên không trùng khớp tuyệt đối với `score` trong `ket_qua_benchmark.txt`. Thứ đáng tin ở đây là **thứ tự xếp hạng**, và thứ tự đó tái hiện đúng lỗi đã quan sát được.

Kết luận thực hành rút ra: với câu hỏi tra cứu thực thể (địa chỉ, số phòng, số tiền, ngày tháng), **retrieval thuần embedding là lựa chọn yếu**. Cần kết hợp tìm kiếm từ khoá hoặc chunk theo heading để đoạn chứa dữ kiện vẫn mang ngữ cảnh của mục mà nó thuộc về.

Mã nguồn để chạy lại phần này:

```python
from pathlib import Path
from dotenv import load_dotenv
from src import OpenAIEmbedder, compute_similarity

load_dotenv(dotenv_path=Path(".env"), override=False)
embed = OpenAIEmbedder()
a = embed("Sinh viên thuộc hộ nghèo được cấp học bổng toàn phần 100% học phí.")
b = embed("Sinh viên thuộc hộ cận nghèo được cấp học bổng bán phần 50% học phí.")
print(compute_similarity(a, b))   # 0.8384
```

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

**Chiến lược của tôi:** `RecursiveChunker(chunk_size=500)` — 48 chunks, min 88 / max 495 ký tự.
**Embedding backend:** `text-embedding-3-small` (OpenAI), vector 1536 chiều đã chuẩn hoá (`||v|| = 1.000000`).
**Lệnh chạy:** `python bench.py --strategy recursive` → kết quả đầy đủ trong `ket_qua_benchmark.txt`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Hộ nghèo được bao nhiêu % học phí? | `tieu-chi-xet-hoc-bong#2` — "Căn cứ vào các tiêu chí xét học bổng HTHT: Sinh viên K64 thuộc **hộ nghèo**..." | +0,7167 | **Có** — chunk chứa đúng "100% học phí" | "Sinh viên thuộc hộ nghèo được cấp học bổng hỗ trợ học tập trị giá 100% học phí (so với chương trình đào tạo chuẩn) **[1]**." ✔ đúng |
| 2 | Điều kiện GPA loại A? | `ho-tro-tai-chinh-tan-sinh-vien#4` — "## 4. Học bổng khuyến khích học tập..." | +0,6321 | **Có** — chứa cả "3.6" và "90" | "...là GPA từ 3.6 và điểm rèn luyện từ 90 **[1]**." ✔ đúng |
| 3 | Hồ sơ nộp ở đâu? | `tieu-chi-xet-hoc-bong#6` — "Ngoài ra, những học sinh đạt giải Nhất, Nhì Kỳ thi HSG Quốc gia..." | +0,6055 | **Không** — đúng tài liệu, sai đoạn; địa chỉ nộp không có trong top-3 | **"Không tìm thấy trong tài liệu."** — agent từ chối trả lời thay vì bịa |
| 4 | Học phí ELITECH? | `hoc-phi-dai-hoc-2022#1` — "Các chương trình chuẩn: 24-30 triệu... ELITECH: 35 đ..." | +0,7164 | **Có** — chứa "35" và "40 triệu" | "...từ 35 đến 40 triệu đồng/năm học; riêng IT-E10 và EM-E14 khoảng 60 triệu đồng/năm học **[1]**." ✔ đúng |
| 5 | Chương trình vi mạch 4.2 triệu? | `nghi-dinh-55#12` — "### Chương trình vi mạch bán dẫn nhận mức 4.200.000 đồng/tháng..." | +0,7204 | **Có** — chứa ET1 và ET-E9 | "...bao gồm: Kỹ thuật Điện tử - Viễn thông (ET1), Hệ thống nhúng thông minh và IoT (tăng cường tiếng Nhật) (ET-E9), và chương trình Kỹ sư chuyên sâu Thiết kế vi mạch **[1]**." ✔ đúng |

> Cột cuối là **output nguyên văn** của `KnowledgeBaseAgent` khi chạy `python bench.py --strategy recursive --llm` (LLM: `gpt-4o-mini`, `temperature=0`). Cả 4 câu trả lời được đều **trích dẫn số đoạn `[1]`** đúng như prompt yêu cầu, nên mỗi ý đều truy vết ngược được về chunk và file cụ thể.
>
> **Câu 3 là kết quả đáng giá nhất của phần này.** Ngữ cảnh truy xuất được không chứa địa chỉ nộp hồ sơ, và agent trả lời đúng "Không tìm thấy trong tài liệu" thay vì suy đoán một địa chỉ nghe hợp lý. Ràng buộc chống bịa trong prompt đã làm đúng việc của nó: với corpus quy định, **một câu trả lời sai tự tin còn tệ hơn một câu từ chối**.

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **4** / 5

Hai cách chấm cho kết quả khác nhau rõ rệt trên chính chiến lược của tôi:

| Cách chấm | Điểm |
|---|---|
| Theo `doc_id` (tài liệu gold có trong top-3?) | **10/10** — cả 5 câu tài liệu gold đều hạng 1 |
| Theo nội dung (ngữ cảnh có chứa đáp án?) | **8/10** — câu 3 được 0 điểm |

Nếu tôi dừng ở cách chấm thứ nhất, tôi sẽ báo cáo một kết quả hoàn hảo và hoàn toàn bỏ sót lỗi ở câu 3.

**Kết quả A/B của câu cần metadata filter (câu 3):**

| Lần chạy | Top-3 | Hạng gold | Ngữ cảnh chứa đáp án | Điểm |
|---|---|---|---|---|
| Có `metadata_filter={"audience": "student"}` | 3/3 chunk từ tài liệu `student` | 1 | Không | 0/2 |
| Không lọc | `applicant#0` chiếm hạng 1, đẩy tài liệu gold xuống hạng 2 | 2 | Không | 0/2 |

Với chiến lược của tôi, filter **có làm đổi kết quả** (loại được tài liệu `applicant` khỏi top-1) nhưng **không cứu được câu trả lời**, vì đoạn chứa địa chỉ vốn đã không lọt top-3 ngay cả khi đã lọc. Filter sửa được lỗi "sai đối tượng", không sửa được lỗi "sai đoạn".

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Chiến lược `HeadingChunker` của Tín là thứ tôi học được nhiều nhất — và điều làm nên khác biệt không phải ý tưởng chunk theo mục, mà là một chi tiết nhỏ hơn nhiều: **gắn lại tiêu đề mục vào từng mảnh con** khi phải cắt nhỏ một section dài. Chính nhờ tiền tố `## Hồ sơ đăng ký` mà đoạn chứa "Phòng 202, Nhà D7" — vốn là một câu ngắn, khô, ít từ trùng với câu hỏi — vẫn leo được lên hạng 3, trong khi chiến lược của tôi để nó rớt hẳn.
>
> Bài học rộng hơn: ở câu 3, chiến lược của tôi có `score` top-1 là +0,6055 cho một chunk hoàn toàn không trả lời được câu hỏi. **Điểm số cao không có nghĩa là truy xuất đúng** — cosine đo độ giống chủ đề, không đo việc đoạn văn có chứa dữ kiện cần tìm hay không. Tôi sẽ không còn đọc bảng score mà không kiểm nội dung chunk nữa.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá | Căn cứ |
|----------|-------------------|--------|
| Khởi động (Warm-up) | **5** / 5 | Trả lời đủ cả hai bài; đáp án chunking kiểm chứng bằng code thật (23 và 25 chunk) chứ không chỉ áp công thức |
| Hướng tiếp cận của tôi (My Approach) | **10** / 10 | Giải thích đủ 5 phần, nêu được lý do thiết kế (lookbehind, hai chiều đệ quy, lọc trước, đánh số chunk) và tự nêu edge case chưa xử lý được |
| Hoàn thiện code (Core Implementation — tests) | **30** / 30 | `pytest tests/ -v` → 42/42 passed, không còn `NotImplementedError`; `main.py` chạy trọn vẹn |
| Dự đoán độ tương tự (Similarity Predictions) | **5** / 5 | 5/5 dự đoán đúng hướng, dự đoán khoá trước khi đo; phần chẩn đoán thêm giải thích được nguyên nhân lỗi của câu 3 |
| Kết quả truy xuất của tôi (Competition Results) | **10** / 10 | Chạy đủ 5 query của nhóm trên `src` của mình, có bảng top-1 kèm score và A/B cho câu cần filter. Agent trả lời đúng 4/5 câu, câu còn lại từ chối bịa đúng như thiết kế. Câu 3 thất bại đã được truy tới nguyên nhân gốc bằng số đo (0,7417 vs 0,5792) và kèm 4 đề xuất sửa — tiêu chí chấm là chất lượng phân tích kết quả, không phải điểm truy xuất tuyệt đối |
| **Tổng phần cá nhân** | **60 / 60** | |
