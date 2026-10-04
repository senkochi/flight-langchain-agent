# Tổng hợp Bài học SE373: Agent Fundamentals (Kỹ thuật xây dựng hệ thống Agentic AI)

### Thông tin chung
- **Môn học**: SE373 - Kỹ thuật xây dựng hệ thống Agentic AI (Buổi 03).
- **Giảng viên lý thuyết**: TS. Đỗ Trọng Hợp, ThS. Ngô Ngọc Đăng Khoa, ThS. Phạm Hoàng Hải.
- **Giảng viên thực hành**: Bùi Cao Doanh, Dương Nguyễn Phương Nam, Nguyễn Hiếu Nghĩa, Nguyễn Ngọc Quí, Nguyễn Thị Hoàng Anh, Quan Chí Khánh An.
- **Mục tiêu chính**: Dựng được vòng lặp agent có điều kiện dừng kiểm chứng được, và đọc trace để chỉ ra chỗ hỏng.

Bài học được cấu trúc thành **05 nội dung cốt lõi**:
1. Vòng lặp Agent (Agent Loop)
2. ReAct và các mẫu suy luận (Reasoning Patterns)
3. Điều kiện dừng (Termination Condition)
4. Gỡ lỗi Agent (Agent Debugging)
5. Bài tập về nhà & Tổng kết

---

## Phần 1: Vòng lặp Agent (Agent Loop)

### 1. Khái niệm & Đặc tính của AI Agent
- **Định nghĩa**: Agent là phần mềm có khả năng tự chủ hoạt động, đưa ra quyết định để đạt mục tiêu mà không cần con người can thiệp liên tục.
- **3 đặc tính cốt lõi**:
  - **Tự chủ**: Tự quản lý và quyết định bước đi tiếp theo.
  - **Chủ động**: Tự lên kế hoạch và khởi xướng hành động.
  - **Phản ứng / Thích ứng**: Nhận thức môi trường và thích ứng kịp thời với tình huống.
- **Phân biệt hệ thống**:
  - **Chain**: Lập trình viên quyết định sẵn luồng thực thi cố định.
  - **Workflow**: Model lựa chọn nhánh trong tập kịch bản có sẵn.
  - **AI Agent**: Model trực tiếp quyết định bước đi tại thời điểm chạy (runtime).

### 2. Bốn thành phần tối thiểu của Agent
Hệ thống Agent được thể hiện qua công thức: **`agent = goal + tools + loop + termination`**:
1. **Goal (Mục tiêu)**: Mô tả trạng thái cần đạt tới, không phải danh sách các bước phải làm (ví dụ: *"Tìm commit làm hỏng test_checkout và mở issue"*).
2. **Tools (Công cụ)**: Các hàm bên ngoài mà model gọi qua giao thức tool calling (gồm tên, mô tả và schema tham số). Nếu không có tool, model chỉ có thể sinh văn bản.
3. **Loop (Vòng lặp)**: Chu trình đưa kết quả hành động trở lại làm đầu vào cho lần suy luận tiếp theo. Việc chỉ gọi tool một lần không phải là Agent.
4. **Termination (Cơ chế dừng)**: Quy tắc quyết định dừng hay chạy tiếp, gồm tiêu chí hoàn thành và các giới hạn cứng. Thiếu termination là nguyên nhân gây tốn kém chi phí nhất.

### 3. Ranh giới giữa Model và Harness
Trong sơ đồ vòng lặp AI Agent, có sự phân chia trách nhiệm rõ ràng:
- **Model**: Chỉ chịu trách nhiệm đề xuất gọi công cụ (`tool_calls`) tại bước 2.
- **Harness (Code lập trình viên tự viết)**: Đảm nhận 4 bước còn lại gồm:
  1. Dựng ngữ cảnh (Context).
  2. Parse, validate và thực thi công cụ.
  3. Ghi lại kết quả (State & Observation) dưới định dạng chuẩn (như JSON).
  4. Xét điều kiện dừng (lặp tiếp, chờ người duyệt, hoặc thoát).

### 4. Chi phí lịch sử và Ngân sách vòng lặp
- **Chi phí lịch sử**: Do mỗi vòng lặp phải nạp lại toàn bộ lịch sử hội thoại, tổng chi phí token tăng theo bình phương số vòng lặp (gấp đôi số vòng thì chi phí tăng khoảng 4 lần).
- **Ngân sách vòng lặp (Giới hạn cứng)**: Cần thiết lập giới hạn cứng về số bước tối đa, lượng token tối đa, thời gian chạy tối đa (giây), và trần chi phí tiền bạc.

---

## Phần 2: ReAct và các mẫu suy luận (Reasoning Patterns)

### 1. Kiến trúc ReAct (Reasoning + Acting)
- **ReAct** (Yao et al., 2022) là kiến trúc cốt lõi giúp AI Agent liên tục **Suy luận (Reasoning) \\(\rightarrow\\) Hành động (Acting) \\(\rightarrow\\) Quan sát (Observation)**.
- **Lý do hiệu quả**: Dữ kiện từ môi trường đi vào giữa chuỗi suy luận thay vì chỉ dựa vào trí nhớ của model; hướng đi được điều chỉnh linh hoạt sau từng quan sát; trace ghi lại từng vòng giúp chẩn đoán lỗi dễ dàng.
- **So sánh 3 cách tổ chức suy luận**:
  - *Chain of Thought*: Suy luận nhiều bước nhưng không sử dụng môi trường ngoài.
  - *Action Only*: Hành động nhưng không có bước suy luận tường minh.
  - *ReAct*: Suy luận, hành động, quan sát, rồi tiếp tục suy luận.

### 2. Các mẫu suy luận nâng cao
- **Plan-then-execute**: Model gọi một lần để sinh toàn bộ kế hoạch, người duyệt (nếu cần), rồi thực thi từng bước.
  - *Ưu điểm*: Kế hoạch nhìn thấy trước, dễ kiểm duyệt và ước lượng chi phí.
  - *Nhược điểm*: Kém linh hoạt khi môi trường thay đổi, sai ở bước đầu sẽ hỏng toàn bộ.
- **Mẫu lai (ReAct + Plan)**: Lập kế hoạch \\(\rightarrow\\) Thực thi \\(k\\) bước \\(\rightarrow\\) Đánh giá observation \\(\rightarrow\\) Nếu có thay đổi đáng kể thì lập lại kế hoạch.
- **Self-Reflection (Tự phản tỉnh)**: Agent tự sinh bản nháp \\(\rightarrow\\) Tự đánh giá/chấm điểm dựa trên tiêu chí (chính xác, logic, văn phong) \\(\rightarrow\\) Sửa lại theo góp ý cho đến khi đạt yêu cầu.

### 3. Bảng tổng hợp chọn mẫu kiến trúc

| Mẫu kiến trúc | Bối cảnh nên chọn | Rủi ro chính |
| :--- | :--- | :--- |
| **ReAct** | Không đoán trước được số bước xử lý | Lặp vô hạn, trôi mục tiêu |
| **Plan-then-execute** | Cần người duyệt trước kế hoạch | Kế hoạch bị lỗi thời khi chạy |
| **Mẫu lai** | Tác vụ dài, môi trường biến động | Khó debug hơn |
| **Reflection** | Có tín hiệu kiểm chứng ngoài | Nhân đôi chi phí token |

*Lưu ý*: Có công cụ chưa chắc Agent sẽ dùng công cụ, hệ thống cần có System Prompt rõ ràng để định hướng việc tra cứu dữ liệu thực tế.

---

## Phần 3: Điều kiện dừng (Termination Condition)

### 1. 5 điều kiện dừng trong Agent Loop
Mặc định của framework chỉ dừng khi model không gọi tool nữa. Hệ thống cần cài đặt **5 điều kiện dừng**:

1. **Cần con người (Human Approval)**: Chạy *trước* khi thực thi công cụ đối với các hành động vượt thẩm quyền (xoá dữ liệu, chuyển tiền, gửi email khách hàng).
2. **Đạt mục tiêu (Goal Achieved)**: Chạy *sau* khi có observation, kiểm tra kết quả thực tế thỏa mãn tiêu chí hoàn thành.
3. **Phát hiện lặp (Loop Detection)**: Chạy *sau* khi có observation, phát hiện gọi lại cùng công cụ/tham số hoặc nhận kết quả trùng.
4. **Bế tắc (Stall Detection)**: Chạy *sau* khi có observation, phát hiện Agent đổi công cụ mỗi vòng nhưng đại lượng tiến triển đứng yên.
5. **Hết ngân sách (Budget Exceeded)**: Kiểm tra chạm trần số bước, token, thời gian hoặc chi phí. *Lưu ý*: Ngân sách phải được kiểm tra cuối cùng trong checklist harness để không che giấu các lý do lỗi khác.

### 2. Phân loại dừng & Tiêu chí hoàn thành
- **Phân loại**:
  - *Dừng bình thường*: Đạt mục tiêu, Cần con người.
  - *Dừng bất thường*: Hết ngân sách, Phát hiện lặp, Bế tắc (cần log và báo cho con người).
- **Tiêu chí hoàn thành khách quan**: Phải dựa trên quy tắc lập trình khách quan (code, vị từ logic, schema Pydantic, API chéo) thay vì tin vào lời tự tuyên bố chủ quan của model. Ưu tiên **Sensor computational** (chạy bằng code, xác định, không tốn token) hơn **Sensor inferential** (dùng model khác chấm).
- **Bàn giao cho con người (Handoff)**: Bàn giao tốt phải giúp người nhận nắm được trạng thái, các hướng đã thử và đưa ra quyết định trong vòng 30 giây.

---

## Phần 4: Agent Debugging (Gỡ lỗi Agent)

### 1. Quy trình 4 bước debug Agent
Quy trình chuẩn để khắc phục lỗi hệ thống Agent:
- **Bước 01: Tái hiện**: Chạy lại với đúng đầu vào cũ và lưu toàn bộ log trace.
- **Bước 02: Khoanh vùng**: Tìm vòng lặp sai đầu tiên, không chỉ nhìn vào kết quả cuối.
- **Bước 03: Xác định loại lỗi**: Phân loại chính xác 1 trong 4 dạng lỗi (failure modes).
- **Bước 04: Đặt kiểm tra**: Thêm code chặn tại vòng bị lỗi và chạy lại.

### 2. Bảng tra cứu 4 dạng lỗi lặp lại (Failure Modes)

| Tên loại lỗi | Dấu hiệu trong Log Trace | Nguyên nhân sâu xa | Cách xử lý bằng Harness / Tool |
| :--- | :--- | :--- | :--- |
| **01. Lặp không tiến bộ** | Gọi liên tục một công cụ với tham số/kết quả y hệt | Công cụ trả lỗi không chi tiết ("not found") | Thêm mã lỗi kèm `hint` định hướng trong tool output; đếm số lần gọi không tiến triển |
| **02. Bịa đặt thông tin (Hallucination)** | Xuất hiện số liệu, ngày, ID không có trong dữ liệu thật từ tool | Model tự chế dữ liệu khi thiếu thông tin | Kiểm tra chéo (validate) dữ liệu câu trả lời với kết quả thật từ tool |
| **03. Quên yêu cầu ban đầu** | Vòng cuối bị lạc đề so với yêu cầu gốc | Lịch sử cuộc gọi quá dài làm mờ mục tiêu gốc | Ghi yêu cầu/ràng buộc thành dữ liệu cố định, kiểm tra lại trước khi chốt |
| **04. Tin vào dữ liệu sai** | Log "sạch", không lặp nhưng sai từ kết luận đầu | Công cụ trả về kết quả mơ hồ (`{}`), Agent diễn dịch sai | Ép công cụ trả định dạng rõ ràng (JSON gồm `status`, `error`, `hint`) |

---

## Phần 5: Bài tập về nhà & Tổng kết bài học

### Bài tập về nhà (BTVN #3)
- **Yêu cầu**: Dựng Agent đặt vé máy bay bằng LangChain / LangGraph.
- **Yêu cầu kỹ thuật**:
  1. Xây dựng đầy đủ các lớp Harness: Lưu ràng buộc thành dữ liệu, kiểm tra tiêu chí hoàn thành bằng code, kiểm soát thẩm quyền, bàn giao trạng thái.
  2. Cài đặt Agent với 3 mẫu thiết kế: ReAct, Plan-then-execute, và Mẫu lai.
  3. Đánh giá và so sánh hiệu quả giữa 3 mẫu thiết kế.

---

### Tổng kết cốt lõi
1. **Agent** = Goal + Tools + Loop + Termination; Model chọn bước chạy trong giới hạn điều phối của Harness.
2. **ReAct** giúp kết nối suy luận với quan sát thực tế; chọn mẫu suy luận phù hợp với rủi ro của bài toán.
3. **5 Điều kiện dừng** giúp kiểm soát chi phí và độ tin cậy; tiêu chí hoàn thành phải do code kiểm chứng khách quan.
4. **Agent Debugging** gồm 4 bước xử lý 4 failure modes phổ biến.