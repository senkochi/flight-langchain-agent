# BÁO CÁO NỘP BÀI: CHALLENGE A - PERSISTENT MEMORY
**Môn học**: SE373 - Kỹ thuật xây dựng hệ thống Agentic AI  
**Bài tập**: Challenge A - Persistent Memory cho Agent Đặt vé máy bay  
**Kho mã nguồn**: `flight-langchain-agent` (LangChain / LangGraph / Python 3.13)  

---

## 1. Mục Tiêu & Thiết Kế Kiến Trúc (Slide 14–16)

Mục tiêu chính: Xây dựng cơ chế **Persistent Memory** giúp Agent ghi nhớ quy ước dự án qua nhiều session khác nhau và tự động cập nhật khi quy ước thay đổi.

### Bảng giải quyết 5 câu hỏi thiết kế (Slide 15):
| Vấn đề | Quyết định thiết kế | Triển khai thực tế |
| :--- | :--- | :--- |
| **Lưu trữ** | File JSON độc lập | `.scratch/persistent_memory.json` (Atomic write, lưu ngoài conversation history). |
| **Ghi memory** | Cơ chế kép (Harness + Tools) | Harness API `harness.save_convention` & Tool `save_project_convention`. |
| **Nạp memory** | Context Injection lúc mở session | Tự động inject vào `SystemMessage` / Context Prefix trước khi Agent suy luận. |
| **Cập nhật** | Version increment & overwrite | Tự động tăng version (`v1` $\rightarrow$ `v2`), ghi đè quy ước mới nhất để tránh mâu thuẫn context. |
| **Kiểm chứng** | Trích xuất ngữ cảnh đã tiêm | Phương thức `harness.get_injected_memory_context()` và in trực tiếp ra log console. |

---

## 2. Kiểm Chứng Thực Nghiệm Qua 4 Session (Kèm Ảnh Chụp)

Chạy lệnh kiểm chứng tự động toàn bộ vòng đời:
```powershell
python main.py -m
```

### 2.1. Session 1 & Session 2: Thiết Lập & Kiểm Chứng Ghi Nhớ Quy Ước Cũ
* **Session 1**: Thiết lập quy ước ban đầu: `preferred_airline = Bamboo Airways` (version `v1`).
* **Session 2**: Mở session mới hoàn toàn (lịch sử rỗng). Người dùng yêu cầu: *"Đặt vé SGN -> HAN ngày 2026-10-15 cho Nguyen Van A"* (hoàn toàn **không nêu tên hãng**). Agent đọc Injected Context, tự động chọn chuyến bay **`QH789` (Bamboo Airways)** và được Code Sensor xác nhận hợp lệ.

<!-- CHỖ CHÈN ẢNH 1: Chụp terminal chạy Session 1 và Session 2 -->
![Minh chứng Session 1 và Session 2](screenshots/01_session_1_2.png)
*(Hình 1: Session 1 lưu quy ước Bamboo Airways; Session 2 mở mới, inject context và tự động chọn chuyến QH789)*

---

### 2.2. Session 3 & Session 4: Cập Nhật & Kiểm Chứng Tuân Thủ Quy Ước Mới
* **Session 3**: Cập nhật quy ước sang hãng quốc gia: `preferred_airline = Vietnam Airlines` (version `v2`, ghi đè quy ước cũ).
* **Session 4**: Mở session mới tiếp theo (lịch sử rỗng). Cùng câu lệnh đặt vé, Agent đọc Injected Context mới và lập tức chuyển sang chọn chuyến **`VN123` (Vietnam Airlines)** thay vì tiếp tục dùng Bamboo Airways.

<!-- CHỖ CHÈN ẢNH 2: Chụp terminal chạy Session 3, Session 4 và Bảng Checklist 6/6 -->
![Minh chứng Session 3 và Session 4](screenshots/02_session_3_4.png)
*(Hình 2: Session 3 cập nhật quy ước Vietnam Airlines; Session 4 tự động đổi sang chuyến VN123 và Bảng Checklist 6/6)*

---

## 3. Kiểm Thử Tự Động (Unit Test TDD)

Chạy bộ kiểm thử tự động của Challenge A:
```powershell
python -m pytest tests/test_persistent_memory.py -v
```

<!-- CHỖ CHÈN ẢNH 3: Chụp terminal chạy pytest pass 4/4 -->
![Kết quả chạy kiểm thử tự động Pytest](screenshots/03_pytest.png)
*(Hình 3: 4 bài test TDD của Persistent Memory đều đạt 100% PASSED)*

---

## 4. Bảng Checklist Hoàn Thành Tiêu Chí Đánh Giá (6/6)

| STT | Tiêu Chí Theo Yêu Cầu Của Slide | Hiện Trạng Trong Dự Án | Kết Quả |
| :---: | :--- | :--- | :---: |
| 1 | Tạo cơ chế lưu persistent memory ngoài lịch sử hội thoại hiện tại | Lưu file JSON độc lập qua `PersistentMemoryStore` | **ĐẠT (PASSED)** |
| 2 | Lưu một quy ước dự án trong session đầu tiên | Session 1: `preferred_airline = Bamboo Airways` (v1) | **ĐẠT (PASSED)** |
| 3 | Mở session mới và chứng minh agent vẫn làm theo quy ước cũ | Session 2: Lịch sử mới, Agent tự chọn chuyến `QH789` | **ĐẠT (PASSED)** |
| 4 | Thay đổi quy ước và cập nhật memory | Session 3: Cập nhật thành `Vietnam Airlines` (v2) | **ĐẠT (PASSED)** |
| 5 | Mở session mới tiếp theo và chứng minh agent dùng quy ước mới | Session 4: Lịch sử mới, Agent tự chọn chuyến `VN123` | **ĐẠT (PASSED)** |
| 6 | In nội dung memory đã inject vào context để kiểm chứng | In khối ngữ cảnh `[PERSISTENT PROJECT MEMORY]` rõ ràng ở mỗi session | **ĐẠT (PASSED)** |

---

## 5. Kết Luận

Hệ thống đã chứng minh trọn vẹn vòng đời của **Persistent Memory**:
1. Lưu trữ độc lập bền vững, tách biệt với runtime context và hội thoại.
2. Tiêm ngữ cảnh có kiểm soát vào context window của LLM tại mỗi session mới.
3. Cơ chế giải quyết xung đột bằng phiên bản hóa (versioning) giúp Agent chuyển đổi hành vi chính xác ngay khi quy ước thay đổi.
