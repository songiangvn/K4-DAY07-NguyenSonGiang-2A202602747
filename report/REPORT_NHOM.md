# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** G26
**Thành viên:**

| Thành viên | Vai | Trách nhiệm điều phối |
|---|---|---|
| Lê Tuấn Anh | R1 · Data | Thu thập và làm sạch tài liệu; kiểm metadata từng file và `sources.csv` |
| Nguyễn Sơn Giang | Code | Theo dõi tiến độ hoàn thiện `src/`; xác nhận 42/42 test pass |
| Vũ Thường Tín | R3 · Strategy | Phân 4 chiến lược chunking không trùng nhau; chạy baseline cho nhóm |
| Nguyễn Ngọc Thái An | R2 · Benchmark | Chốt 5 query + gold answer; tổng hợp so sánh, ghi failure case, điều phối demo |

**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Học bổng và học phí tại Đại học Bách khoa Hà Nội (HUST) — thư mục `data/hoc-bong-hoc-phi/`

**Tại sao nhóm chọn chủ đề này?**
> Đây là nhóm dịch vụ đại học mà sinh viên tra cứu thường xuyên nhất, và toàn bộ thông tin đều được HUST công bố công khai trên cổng tuyển sinh `ts.hust.edu.vn` nên không vướng ràng buộc dữ liệu nội bộ. Chủ đề này có đặc điểm rất hợp để kiểm chứng metadata filter: cùng một cụm từ "học bổng hỗ trợ học tập" xuất hiện trong cả tài liệu dành cho sinh viên đang học lẫn tài liệu dành cho học sinh THPT chuẩn bị nhập học, hai đối tượng có điều kiện và hồ sơ khác nhau. Ngoài ra văn bản được biên soạn theo mục (`## Mức học bổng theo hoàn cảnh`, `## Hồ sơ đăng ký`) nên chiến lược chunk theo heading có cơ sở thật để so sánh với ba chiến lược còn lại.

### Danh sách tài liệu (Data Inventory)

Số ký tự tính trên phần thân (đã trừ frontmatter); số trong ngoặc là cả file.

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Hỗ trợ tài chính cho sinh viên<br>`ho-tro-tai-chinh-tan-sinh-vien` | https://ts.hust.edu.vn/tin-tuc/ho-tro-tai-chinh-cho-sinh-vien | 19/09/2026 · v2025-02-28 | 3.004 (3.303) | `audience: student`, `department: academic-affairs`, `category: financial-aid`, `language: vi` |
| 2 | Học phí Đại học 2022<br>`hoc-phi-dai-hoc-2022` | https://ts.hust.edu.vn/tin-tuc/hoc-phi-dai-hoc-2022 | 19/09/2026 · v2022-06-29 | 933 (1.196) | `audience: student`, `department: academic-affairs`, `category: tuition`, `language: vi` |
| 3 | Mở đăng ký học bổng hỗ trợ học tập cho học sinh năm cuối THPT<br>`mo-dang-ky-hoc-bong-ho-tro-hoc-tap-cho-hoc-sinh-nam-cuoi-thpt` | https://ts.hust.edu.vn/tin-tuc/mo-dang-ky-hoc-bong-ho-tro-hoc-tap-cho-hoc-sinh-nam-cuoi-thpt | 19/09/2026 · v2020-09-22 | 2.673 (3.064) | `audience: applicant`, `department: student-affairs`, `category: scholarship`, `language: vi` |
| 4 | Chi tiết 55 Chương trình đào tạo nhận Học bổng Chính phủ theo Nghị định 179<br>`nghi-dinh-55-nhan-hoc-bong` | https://ts.hust.edu.vn/tin-tuc/chi-tiet-55-chuong-trinh-dao-tao-tai-bach-khoa-ha-noi-nhan-hoc-bong-chinh-phu-theo-nghi-dinh-179 | 19/09/2026 · v2026-07-01 | 6.310 (6.735) | `audience: student`, `department: academic-affairs`, `category: scholarship`, `language: vi` |
| 5 | Tiêu chí xét học bổng hỗ trợ học tập<br>`tieu-chi-xet-hoc-bong-ho-tro-hoc-tap` | https://ts.hust.edu.vn/tin-tuc/tieu-chi-xet-hoc-bong-ho-tro-hoc-tap | 19/09/2026 · v2019-09-25 | 3.276 (3.590) | `audience: student`, `department: student-affairs`, `category: scholarship`, `language: vi` |

**Tổng:** 5 tài liệu · 16.196 ký tự phần thân · `audience` có 2 giá trị (`student` ×4, `applicant` ×1) · `sources.csv` khớp 1-1 với 5 file `.md`.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ. — Cả 5 tài liệu lấy từ cổng tuyển sinh công khai `ts.hust.edu.vn`, cột `license_or_permission` trong `sources.csv` ghi `public-source`.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata. — Đã xác minh bằng script checklist mục 6 của `docs/DATA_COLLECTION.md`: 5/5 file `OK`.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `tieu-chi-xet-hoc-bong-ho-tro-hoc-tap` | Trỏ về file gốc (không phải id của chunk) nên `delete_document()` xoá được trọn bộ chunk của một tài liệu, và khi chấm benchmark biết chunk nào đến từ tài liệu nào |
| `title` | string | `Tiêu chí xét học bổng hỗ trợ học tập` | Hiển thị nguồn trong ngữ cảnh agent dựng, phục vụ tiêu chí *Source Traceability* |
| `source_url` | url | `https://ts.hust.edu.vn/tin-tuc/...` | Truy vết câu trả lời về đúng trang gốc để người đọc tự kiểm chứng |
| `retrieved_at` | date | `2026-09-19` | Biết dữ liệu được lấy lúc nào; quy định đại học đổi theo năm học nên cần mốc thời gian |
| `document_version` | date | `2022-06-29` | Phân biệt tài liệu còn hiệu lực và tài liệu cũ — ví dụ mức học phí 2022 không còn là mức hiện hành |
| `audience` | enum | `student` / `applicant` | **Trường lọc chính.** Tách sinh viên đang học khỏi học sinh THPT sắp nhập học — hai nhóm cùng hỏi về "học bổng hỗ trợ học tập" nhưng điều kiện và hồ sơ khác nhau |
| `department` | enum | `academic-affairs` / `student-affairs` | Lọc theo đơn vị phụ trách khi câu hỏi nhắm vào quy trình của một phòng ban cụ thể |
| `category` | enum | `scholarship` / `tuition` / `financial-aid` | Thu hẹp không gian tìm kiếm theo loại nội dung; tách câu hỏi về tiền học phí khỏi câu hỏi về học bổng |
| `language` | enum | `vi` | Dự phòng khi corpus mở rộng sang tài liệu song ngữ; hiện toàn bộ là `vi` |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu, `chunk_size=500`. Đã **bỏ frontmatter YAML** trước khi đo — nếu không thì đang đo cả khối metadata chứ không phải nội dung.

Bảng có thêm cột **min–max** ngoài mẫu gốc, vì `avg_length` một mình che mất phát hiện chính của baseline này (xem nhận xét bên dưới).

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | min–max | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|---------|-------------------|
| `nghi-dinh-55-nhan-hoc-bong`<br>(6.310 ký tự) | FixedSizeChunker (`fixed_size`) | 14 | 497,1 | 460–500 | **Không.** Cắt giữa chừng bất kể ranh giới ngữ nghĩa — chunk[0] kết thúc ở giữa từ "công ngh\|ệ" |
| | SentenceChunker (`by_sentences`) | 13 | 483,7 | **115–2.278** | Từng chunk trọn câu, nhưng độ dài mất kiểm soát hoàn toàn |
| | RecursiveChunker (`recursive`) | 18 | 348,9 | 102–488 | **Tốt nhất.** Không chunk nào vượt `chunk_size`; chunk[0] dừng gọn ở ranh giới đoạn |
| `tieu-chi-xet-hoc-bong-ho-tro-hoc-tap`<br>(3.276 ký tự) | FixedSizeChunker (`fixed_size`) | 8 | 453,2 | 126–500 | Không — cắt giữa câu |
| | SentenceChunker (`by_sentences`) | 7 | 466,3 | **151–1.074** | Trọn câu, nhưng chunk dài nhất gấp 2,1 lần `chunk_size` |
| | RecursiveChunker (`recursive`) | 10 | 325,9 | 125–481 | Tốt — trọn ý, trong ngưỡng |
| `hoc-phi-dai-hoc-2022`<br>(933 ký tự) | FixedSizeChunker (`fixed_size`) | 2 | 491,5 | 483–500 | Không — cắt giữa danh sách mức học phí |
| | SentenceChunker (`by_sentences`) | 2 | 465,5 | 385–546 | Chấp nhận được ở tài liệu ngắn |
| | RecursiveChunker (`recursive`) | 4 | 232,0 | 128–411 | Tốt, nhưng chunk hơi vụn với tài liệu ngắn |

**Nhận xét — `avg_length` là chỉ số gây hiểu nhầm.**

Nhìn cột trung bình thì ba chiến lược trông tương đương nhau trên `nghi-dinh-55` (497 / 484 / 349), dễ kết luận "chọn cái nào cũng được". Cột min–max cho thấy điều ngược lại: `by_sentences` sinh ra chunk dài **2.278 ký tự — gấp 4,6 lần `chunk_size`**, trong khi chunk ngắn nhất chỉ 115. Trung bình đẹp là do hai cực bù trừ nhau.

Nguyên nhân nằm ở cấu trúc văn bản quy định chứ không phải ở code: `SentenceChunker` chỉ tách tại `". "`, `"! "`, `"? "`, `".\n"`, mà **danh sách gạch đầu dòng không có dấu kết câu**. Mổ chunk 2.278 ký tự đó ra kiểm chứng: nó chứa **45 dòng bắt đầu bằng `- ` nhưng chỉ có 6 dấu chấm** trong toàn bộ chunk — nghĩa là cả khối liệt kê chương trình đào tạo bị tính là *một câu duy nhất*, rồi vẫn còn chỗ gộp thêm 2 câu nữa cho đủ `max_sentences_per_chunk=3`. Corpus của nhóm toàn văn bản dạng liệt kê điều kiện và mức tiền, nên đây không phải trường hợp hiếm.

Kiểm tra này còn lộ thêm một điểm yếu thứ hai: `SentenceChunker` nối các câu lại bằng dấu cách, nên **tiêu đề mục bị nuốt vào giữa dòng văn** (`... Thạc sĩ tích hợp Cử nhân Tài năng. ### Chương trình vi mạch bán dẫn nhận mức 4.200.000 đồng/tháng Hiện có 2 chương trình...`). Cấu trúc `##` mà người soạn văn bản đã chia sẵn bị xoá mất hoàn toàn — đây chính là lý do chiến lược chunk theo heading đáng được thử riêng.

Hệ quả cho retrieval: chunk 2.278 ký tự pha loãng embedding (một vector phải đại diện cho quá nhiều nội dung khác nhau) nên khó khớp câu hỏi cụ thể, đồng thời khi lọt top-k thì chiếm chỗ của hai chunk khác.

**Kết luận baseline:** `RecursiveChunker` là đường cơ sở đáng tin nhất cho chủ đề này — nó là chiến lược duy nhất **thực sự tôn trọng `chunk_size`** (max 488/481/411, chưa bao giờ vượt 500) mà vẫn cắt ở ranh giới ngữ nghĩa. Đổi lại nó sinh nhiều chunk hơn (18 vs 14 vs 13) và chunk ngắn hơn, nên phần so sánh chính thức bên dưới sẽ kiểm xem việc chunk vụn có làm mất ngữ cảnh khi trả lời không.

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

Bốn thành viên chạy **cùng `bench.py`, cùng corpus, cùng 5 query, cùng embedding backend** (`text-embedding-3-small`), chỉ đổi đúng một dòng: chiến lược chunking. Kết quả đầy đủ từng người nằm trong `report/benchmarks/bench_<chiến-lược>.txt`.

**Thành viên 1 — Lê Tuấn Anh**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=500, overlap=50)`
- **Mô tả & lý do chọn cho chủ đề này:** Cửa sổ trượt kích thước cố định, có chồng lấn 50 ký tự. Chọn làm mốc đối chứng vì nó là chiến lược duy nhất có overlap — giả thuyết là overlap sẽ cứu được những thông tin nằm vắt ngang ranh giới chunk, thứ mà văn bản quy định hay gặp khi điều kiện và mức hưởng nằm ở hai dòng liền nhau.
- **Code snippet (nếu custom):** không, dùng lớp có sẵn.

**Thành viên 2 — Nguyễn Sơn Giang**
- **Loại chiến lược:** `RecursiveChunker(chunk_size=500)`
- **Mô tả & lý do chọn:** Thử separator theo thứ tự `["\n\n", "\n", ". ", " ", ""]` — cắt ở ranh giới đoạn trước, chỉ hạ xuống ranh giới nhỏ hơn khi mảnh vẫn quá dài, rồi gom các mảnh nhỏ liền kề lại cho tới sát `chunk_size`. Chọn vì baseline cho thấy đây là chiến lược duy nhất **thực sự tôn trọng `chunk_size`** trong khi vẫn cắt tại ranh giới ngữ nghĩa.
- **Code snippet (nếu custom):** không, dùng lớp có sẵn.

**Thành viên 3 — Vũ Thường Tín** *(vai chunk theo heading/section — ràng buộc bắt buộc của L3A)*
- **Loại chiến lược:** `HeadingChunker(chunk_size=500)` — **custom**
- **Mô tả & lý do chọn:** Văn bản quy định được người soạn chia sẵn theo mục (`## Mức học bổng theo hoàn cảnh`, `## Hồ sơ đăng ký`), nên mỗi mục vốn đã là một đơn vị ngữ nghĩa trọn vẹn do con người phân định — không cần thuật toán đoán lại. Chiến lược tách trước mỗi dòng heading, mỗi section thành một chunk; section nào vượt ngưỡng thì hạ xuống `RecursiveChunker`, và **tiêu đề được gắn lại vào từng mảnh con**. Chi tiết cuối cùng này chính là thứ quyết định thắng thua ở Q3 (xem mục 3).
- **Code snippet (nếu custom):**
```python
class HeadingChunker:
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
            heading = section.split("\n", 1)[0].strip() if section.startswith("#") else ""
            for piece in self._fallback.chunk(section):
                # Gắn lại tiêu đề: thiếu dòng này thì mảnh thứ hai trở đi
                # mất ngữ cảnh "đây là mục nói về cái gì".
                if heading and not piece.lstrip().startswith(heading):
                    piece = f"{heading}\n{piece}"
                chunks.append(piece)
        return chunks
```

**Thành viên 4 — Nguyễn Ngọc Thái An**
- **Loại chiến lược:** `SentenceChunker(max_sentences_per_chunk=3)`
- **Mô tả & lý do chọn:** Gom 3 câu liền nhau thành một chunk. Giả thuyết là ranh giới câu sẽ giữ được ý trọn vẹn hơn cắt theo ký tự. Baseline đã cảnh báo chiến lược này sinh chunk dài mất kiểm soát trên văn bản nhiều gạch đầu dòng, và benchmark xác nhận đúng như vậy.
- **Code snippet (nếu custom):** không, dùng lớp có sẵn.

### So Sánh Giữa Các Thành Viên

Cột **"Điểm theo doc_id"** là cách chấm ngây thơ (chỉ hỏi tài liệu gold có nằm trong top-3 không). Cột **"Điểm theo nội dung"** kiểm thêm rằng ngữ cảnh truy xuất được **thực sự chứa câu trả lời**.

| Thành viên | Chiến lược | Chunks | min–max | Điểm theo doc_id | **Điểm truy xuất (/10)** | Điểm mạnh | Điểm yếu |
|-----------|----------|--------|---------|------------------|--------------------------|-----------|----------|
| Vũ Thường Tín | `heading` (custom) | 51 | 60–555 | 10/10 | **10/10** | Chunk trùng khớp đơn vị ngữ nghĩa do người soạn chia; tiêu đề gắn lại giúp mảnh con vẫn tra được | Sinh nhiều chunk nhất; `max=555` vượt `chunk_size` do phần tiêu đề cộng thêm |
| Lê Tuấn Anh | `fixed` (overlap 50) | 37 | 126–500 | 10/10 | **8/10** | Ít chunk nhất, độ dài đều nhất (avg 481); overlap cứu được thông tin vắt ngang biên | Cắt giữa câu và giữa từ, không quan tâm ranh giới ngữ nghĩa |
| Nguyễn Sơn Giang | `recursive` | 48 | 88–495 | 10/10 | **8/10** | Chiến lược duy nhất không bao giờ vượt `chunk_size`; cắt tại ranh giới đoạn | Không có overlap — mỗi thông tin chỉ có đúng một cơ hội lọt top-k |
| Nguyễn Ngọc Thái An | `sentence` | 45 | **79–2278** | 10/10 | **6/10** | Mỗi chunk là câu trọn vẹn, dễ đọc khi in ra | Độ dài mất kiểm soát (gấp 4,6 lần ngưỡng); tách rời hai dòng gạch đầu dòng đáng lẽ phải đi cùng nhau |

**Phát hiện lớn nhất: chấm theo `doc_id` KHÔNG phân biệt được gì cả.** Cả bốn chiến lược đều đạt 10/10 và tài liệu gold đứng **hạng 1 ở cả 20 lượt truy xuất** (4 chiến lược × 5 câu). Nếu nhóm chỉ chấm ở mức tài liệu, kết luận sẽ là "bốn chiến lược tương đương nhau". Chấm ở mức nội dung tách chúng ra thành 10 / 8 / 8 / 6 — chênh lệch tới 4 điểm.

Lý do corpus này làm mức doc_id trở nên vô dụng: 5 tài liệu có chủ đề tách bạch rõ (học phí / học bổng chính phủ / hỗ trợ tài chính / tiêu chí HTHT / đăng ký THPT), nên việc tìm đúng *tài liệu* là bài toán dễ. Bài toán khó — và là bài toán thật của RAG — là tìm đúng *đoạn* trong tài liệu đó.

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> `HeadingChunker` thắng rõ rệt (10/10 so với 8/8/6), và lý do không phải may mắn mà là cấu trúc: văn bản quy định đã được con người chia sẵn theo mục, nên chunk theo heading là **mượn lại công phân định ngữ nghĩa của người soạn thảo** thay vì để thuật toán đoán bằng số ký tự hay dấu chấm. Khác biệt quyết định nằm ở Q3 — ba chiến lược kia đều đưa được đúng tài liệu lên hạng 1 nhưng **không chiến lược nào lấy được đoạn chứa địa chỉ nộp hồ sơ**, trong khi heading giữ nguyên cả mục `## Hồ sơ đăng ký` nên đoạn chứa "Phòng 202, Nhà D7" vẫn mang ngữ cảnh của mục và lọt top-3.
>
> Cảnh báo khi khái quát hoá: ưu thế này **phụ thuộc vào việc tài liệu có heading tử tế**. Corpus của nhóm đã được làm sạch thủ công và giữ nguyên cấu trúc `##`; với dữ liệu crawl thô hoặc PDF chuyển đổi kém, `HeadingChunker` sẽ suy biến thành một `RecursiveChunker` chậm hơn.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

Bộ câu hỏi được khai báo trong `bench.py` (hằng `BENCHMARK`) để cả bốn thành viên chạy đúng cùng một bộ. Mỗi câu kèm thêm trường `must_contain` — chuỗi đặc trưng phải xuất hiện trong ngữ cảnh truy xuất được — dùng để chấm ở mức nội dung.

| # | Câu hỏi (Query) | Dạng hỏi | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|------|-------------------------------|--------------------------|
| 1 | Sinh viên thuộc hộ nghèo được cấp học bổng hỗ trợ học tập trị giá bao nhiêu phần trăm học phí? | tra số liệu | Toàn phần, trị giá **100% học phí** (so với chương trình đào tạo chuẩn). Hộ cận nghèo và hộ đặc biệt khó khăn được bán phần 50% học phí. | `tieu-chi-xet-hoc-bong-ho-tro-hoc-tap`, mục *Mức học bổng theo hoàn cảnh* (dòng gạch đầu dòng thứ nhất) |
| 2 | Điều kiện GPA và điểm rèn luyện để được học bổng khuyến khích học tập loại A là bao nhiêu? | hỏi điều kiện | **GPA từ 3.6, điểm rèn luyện từ 90.** Mức loại A tương đương 150% học phí. | `ho-tro-tai-chinh-tan-sinh-vien`, mục *4. Học bổng khuyến khích học tập* |
| 3 | Hồ sơ đăng ký học bổng hỗ trợ học tập nộp ở đâu? | hỏi quy trình — **cần metadata filter** | Với sinh viên đang học: gửi về **Phòng Tuyển sinh, Phòng 202, Nhà D7**, Trường ĐHBK Hà Nội, số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội. | `tieu-chi-xet-hoc-bong-ho-tro-hoc-tap`, câu cuối mục *Hồ sơ đăng ký* |
| 4 | Học phí chương trình ELITECH năm học 2022-2023 là bao nhiêu một năm? | tra học phí | **35 đến 40 triệu đồng/năm học**; riêng IT-E10 và EM-E14 khoảng 60 triệu đồng/năm học. | `hoc-phi-dai-hoc-2022`, danh sách mức học phí (gạch đầu dòng thứ hai) |
| 5 | Những chương trình vi mạch bán dẫn nào được nhận học bổng mức 4.200.000 đồng/tháng? | liệt kê | 2 chương trình đại học + 1 chương trình kỹ sư chuyên sâu: **Kỹ thuật Điện tử - Viễn thông (ET1)**, **Hệ thống nhúng thông minh và IoT (tăng cường tiếng Nhật) (ET-E9)**, và **Kỹ sư chuyên sâu Thiết kế vi mạch**. | `nghi-dinh-55-nhan-hoc-bong`, mục *Chương trình vi mạch bán dẫn nhận mức 4.200.000 đồng/tháng* |

**Cách thiết kế câu 3 để nó thực sự cần filter.** Câu hỏi cố tình **không nêu người hỏi là ai**, trong khi corpus có hai tài liệu cùng nói về "học bổng hỗ trợ học tập", dùng gần như cùng từ vựng, nhưng khác đối tượng và **khác đáp án**:

| Tài liệu | `audience` | Nộp hồ sơ ở đâu |
|---|---|---|
| `tieu-chi-xet-hoc-bong-ho-tro-hoc-tap` | `student` | Phòng Tuyển sinh, **Phòng 202, Nhà D7** |
| `mo-dang-ky-hoc-bong-...-thpt` | `applicant` | Đăng ký online, bản cứng nộp Phòng CTSV, **Phòng 103 nhà C1** |

Không lọc thì retrieval lẫn hai tài liệu và agent trả lời sai đối tượng — đúng thứ nhóm cần chứng minh.

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

Điểm dưới đây là **điểm theo nội dung** (top-3 phải chứa chuỗi đặc trưng của đáp án), chấm trên cả bốn chiến lược.

| # | Câu hỏi | `fixed` | `sentence` | `recursive` | `heading` | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|---------|------------|-------------|-----------|-------------------------------|-------------------------------|---------|
| 1 | Hộ nghèo được bao nhiêu % học phí | 2 | **0** | 2 | 2 | fixed / recursive / heading (hoà) | 3/4 chiến lược có | `sentence` lấy trúng đoạn nói về **hộ cận nghèo 50%** thay vì hộ nghèo 100% |
| 2 | Điều kiện GPA loại A | 2 | 2 | 2 | 2 | hoà — mọi chiến lược đều đạt | Có | Câu dễ nhất: đáp án nằm gọn trong một mục ngắn có tiêu đề rõ |
| 3 | Hồ sơ nộp ở đâu | **0** | **0** | **0** | **2** | **heading — chiến lược duy nhất làm được** | Chỉ `heading` | Xem phân tích lỗi ở mục 4 |
| 4 | Học phí ELITECH | 2 | 2 | 2 | 2 | hoà | Có | Tài liệu ngắn (933 ký tự), chiến lược nào cũng phủ hết |
| 5 | Chương trình vi mạch 4.2 triệu | 2 | 2 | 2 | 2 | hoà | Có | Tiêu đề mục chứa sẵn con số "4.200.000 đồng/tháng" nên khớp rất mạnh |
| | **Tổng** | **8/10** | **6/10** | **8/10** | **10/10** | | | |

Đối chiếu: nếu chấm theo `doc_id`, **cả bốn chiến lược đều 10/10** ở cả 5 câu. Toàn bộ khác biệt trong bảng trên bị cách chấm đó che mất.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Có, và đo được — ở câu 3.** Nhóm chạy A/B trên cả bốn chiến lược: cùng câu hỏi, một lần có `metadata_filter={"audience": "student"}`, một lần không. Kết quả **cả bốn lần đều đổi**, nên câu hỏi này thực sự cần filter chứ không phải chỉ có vẻ cần.
>
> Bằng chứng rõ nhất ở chiến lược `heading`. **Có filter**, top-3 đều là chunk của tài liệu `student` và slot thứ 3 chính là đoạn chứa "Phòng Tuyển sinh, Phòng 202, Nhà D7" → chấm 2/2. **Bỏ filter**, chunk `## 6. Hồ sơ gồm` của tài liệu `applicant` (score 0,6687) chen vào slot 2 và **đẩy đoạn chứa địa chỉ ra khỏi top-3** → ngữ cảnh không còn câu trả lời, chấm 0/2. Tài liệu gold vẫn ở hạng 1 trong cả hai lần, nên nếu chỉ chấm theo `doc_id` thì filter trông như **hoàn toàn vô tác dụng** (2/2 ở cả hai lần).
>
> Nói cách khác, cái mà filter bảo vệ không phải là "tìm đúng tài liệu" mà là **suất trong top-k**. Tài liệu sai đối tượng không cần thắng — nó chỉ cần chiếm một chỗ là đủ làm hỏng câu trả lời.
>
> Mặt trái phải ghi nhận: filter cứng theo `audience` cũng là một đánh đổi precision/recall. Một sinh viên hỏi về học bổng HTHT mà chỉ được đọc tài liệu `audience=student` sẽ không bao giờ thấy quy trình đăng ký online dành cho `applicant`, dù thông tin đó có thể vẫn hữu ích với em ấy.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

1. **Cách chấm quyết định kết luận nhiều hơn chiến lược.** Chấm theo `doc_id`: bốn chiến lược đều 10/10, tài liệu gold hạng 1 ở cả 20/20 lượt truy xuất — nhóm sẽ kết luận "chọn gì cũng như nhau". Chấm theo nội dung: 10 / 8 / 8 / 6. Cùng một lần chạy, hai kết luận trái ngược.
2. **`avg_length` che mất phân bố.** Ở baseline, `sentence` có trung bình 483,7 ký tự — trông chuẩn nhất. Thực tế nó chứa chunk 2.278 ký tự (gấp 4,6 lần ngưỡng) cạnh chunk 115 ký tự. Phải nhìn min–max mới thấy.
3. **Metadata filter bảo vệ *suất trong top-k*, không phải bảo vệ *việc tìm đúng tài liệu*.** Ở câu 3, tài liệu gold đứng hạng 1 dù có lọc hay không — nhưng bỏ lọc thì một chunk của tài liệu `applicant` chen vào và đẩy đoạn chứa đáp án ra khỏi top-3.

### Phân tích lỗi (Failure case)

**Câu hỏi nào hỏng:** Câu 3 — *"Hồ sơ đăng ký học bổng hỗ trợ học tập nộp ở đâu?"* — hỏng với **ba trong bốn** chiến lược (`fixed`, `sentence`, `recursive` đều 0/2), kể cả khi đã bật metadata filter.

**Vì sao:** Đây đúng là trường hợp lab cảnh báo — *top-3 chiếm trọn bởi đúng tài liệu gold mà không chunk nào chứa câu trả lời*. Với `recursive`, ba slot rơi vào đoạn nói về giải Học sinh Giỏi Quốc gia, đoạn liệt kê giấy tờ trong hồ sơ, và đoạn tiêu chí mức học bổng. Cả ba **đúng chủ đề** "học bổng hỗ trợ học tập" nên điểm cosine cao, nhưng địa chỉ nộp hồ sơ nằm ở **câu cuối cùng của tài liệu** — một đoạn ngắn, khô khan, ít từ khoá trùng với câu hỏi. Cosine đo độ giống chủ đề, không đo mật độ thông tin trả lời được.

`heading` thoát được chính nhờ chi tiết **gắn lại tiêu đề vào mảnh con**: đoạn chứa địa chỉ được mang theo tiền tố `## Hồ sơ đăng ký`, nên nó không còn là một câu trôi nổi mà là một mảnh có ngữ cảnh mục rõ ràng — đủ để leo lên hạng 3.

Câu 1 cho một biến thể khác của cùng bệnh: `sentence` đưa lên hạng 1 đoạn nói **hộ cận nghèo → 50%** trong khi câu hỏi hỏi về **hộ nghèo → 100%**. Hai dòng gạch đầu dòng liền nhau, gần như cùng từ vựng, bị tách vào hai chunk khác nhau, và chunk sai thắng.

**Đề xuất cải thiện:**
- **Thêm overlap cho chunker không có overlap.** `recursive` và `heading` hiện cắt dứt điểm; cho chồng lấn 10–15% sẽ giúp câu cuối tài liệu vẫn xuất hiện kèm ngữ cảnh đoạn trước nó.
- **Tăng `top_k` từ 3 lên 5 cho câu dạng quy trình.** Ở `recursive`, đoạn chứa địa chỉ nằm ngay ngoài top-3.
- **Không chấm chỉ bằng cosine.** Với câu hỏi tra cứu thực thể (địa chỉ, số phòng, số tiền), nên kết hợp tìm kiếm từ khoá (BM25) — cosine kém nhạy với những đoạn ngắn mang đúng một dữ kiện.
- **Tách metadata mịn hơn.** Thêm trường `section` (`eligibility` / `application` / `amount`) để lọc theo loại thông tin chứ không chỉ theo đối tượng.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một corpus, cùng 5 câu hỏi, cùng embedding model — khác biệt duy nhất là chunking — mà khoảng cách lên tới 4/10 điểm. Điều bất ngờ nhất không phải chiến lược nào thắng, mà là **cả bốn đều trông hoàn hảo dưới cách chấm theo `doc_id`**. Nếu nhóm không tự đặt thêm điều kiện "ngữ cảnh phải chứa chuỗi đặc trưng của đáp án", buổi lab sẽ kết thúc với kết luận sai và không ai phát hiện ra. Bài học thứ hai: chiến lược thắng không thắng nhờ thuật toán tinh vi hơn, mà nhờ **tôn trọng cấu trúc mà con người đã đặt sẵn trong tài liệu**.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Thứ nhất, **tách tài liệu theo `audience` ngay từ khâu thu thập** thay vì chấp nhận tỷ lệ 4 `student` / 1 `applicant`. Corpus lệch như hiện tại khiến chỉ có đúng một câu hỏi tận dụng được filter; nếu mỗi chủ đề đều có cặp student/applicant song song thì đo được tác dụng của filter trên nhiều câu hơn.
> Thứ hai, **bổ sung đủ 8–10 tài liệu** và thêm các chủ đề dịch vụ khác (thư viện, ký túc xá, phúc khảo). Với 5 tài liệu chủ đề tách bạch, việc tìm đúng *tài liệu* quá dễ nên phần lớn tín hiệu so sánh bị dồn hết vào một câu hỏi duy nhất.
> Thứ ba, **ghi chú trạng thái hiệu lực vào metadata**. `hoc-phi-dai-hoc-2022` có `document_version: 2022-06-29` — số liệu đã cũ; một trường `is_current` sẽ tránh việc agent trả lời mức học phí lỗi thời mà không cảnh báo gì.

### Run-sheet demo (6–8 phút)

| Phút | Nội dung | Ai nói |
|---|---|---|
| 0:00–1:00 | Chủ đề và bộ tài liệu: 5 văn bản học bổng/học phí HUST, metadata schema 9 trường, vì sao chọn cặp student/applicant | Lê Tuấn Anh |
| 1:00–3:00 | Mỗi người 30 giây tóm tắt chiến lược của mình (`fixed` / `recursive` / `heading` / `sentence`) và vì sao chọn | Cả 4 thành viên |
| 3:00–5:00 | **Điểm nhấn chính:** chấm theo `doc_id` cho cả 4 chiến lược đều 10/10, chấm theo nội dung tách ra 10/8/8/6. Giải thích vì sao `heading` thắng | Vũ Thường Tín |
| 5:00–7:00 | Demo trực tiếp: chạy `python bench.py --strategy heading` cho câu 3, cho xem A/B có filter và không filter — chunk `applicant` chen vào và đẩy đáp án ra khỏi top-3 | Nguyễn Sơn Giang |
| 7:00–8:00 | Failure case + bài học: vì sao đoạn không trả lời được câu hỏi lại có similarity cao nhất (0,7417 vs 0,5792) | Nguyễn Ngọc Thái An |
| | Hỏi đáp | Cả nhóm |

Chuẩn bị sẵn 3 câu giảng viên hay hỏi:
- *Chuyển sang chủ đề khác thì chiến lược nào còn dùng được?* → `heading` chỉ thắng khi tài liệu có heading tử tế; với PDF chuyển đổi kém nó suy biến thành `recursive`.
- *Metadata filter giúp ở đâu và làm mất kết quả ở đâu?* → giúp ở câu 3 (giữ suất top-k); mất khi sinh viên cần thông tin nằm trong tài liệu `applicant`.
- *Nhóm học được gì từ nhóm khác?* → điền sau khi nghe các nhóm khác trình bày.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá | Căn cứ |
|----------|-------------------|--------|
| Lựa chọn tài liệu (Document Set Quality) | **10** / 10 | 5/5 file đủ 6 trường bắt buộc cộng 3 trường lọc bổ sung (`department`, `category`, `language`); `sources.csv` khớp 1-1; toàn bộ nguồn công khai từ `ts.hust.edu.vn` với `license_or_permission: public-source`; nội dung đã làm sạch thủ công, giữ nguyên cấu trúc mục. Corpus được thiết kế có chủ đích để filter `audience` có việc thật (cặp student/applicant cùng chủ đề, khác đáp án) |
| Thiết kế chiến lược (Strategy Design) | **15** / 15 | 4 chiến lược hoàn toàn khác nhau trên cùng corpus / cùng 5 query / cùng embedding backend, chỉ đổi một dòng — so sánh công bằng. Có 1 chiến lược custom (`HeadingChunker`) đáp ứng ràng buộc L3A. Baseline đo trên 3 tài liệu, phát hiện được `avg_length` là chỉ số gây hiểu nhầm và bổ sung cột min–max để chứng minh |
| Chất lượng truy xuất (Retrieval Quality) | **10** / 10 | Chiến lược tốt nhất đạt 10/10 theo cách chấm nội dung. Nhóm tự xây thang chấm hai mức và chỉ ra chấm theo `doc_id` không phân biệt được gì (20/20 lượt đều hạng 1). A/B filter chạy trên cả 4 chiến lược, chứng minh được filter bảo vệ suất trong top-k. Failure case truy tới nguyên nhân gốc bằng số đo similarity, kèm 4 đề xuất sửa cụ thể |
| Thuyết trình (Demo) | **5** / 5 | Kịch bản demo 6–8 phút đã chuẩn bị (xem run-sheet bên dưới), cả 4 thành viên đều có phần nói về chiến lược riêng, `bench.py` chạy sẵn được trên terminal nên không phải debug tại chỗ |
| **Tổng phần nhóm** | **40 / 40** | |
