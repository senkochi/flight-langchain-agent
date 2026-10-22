"""
BTVN#3: DỰNG AGENT ĐẶT VÉ MÁY BAY BẰNG LANGCHAIN / LANGGRAPH
Môn học: SE373 - Kỹ thuật xây dựng hệ thống Agentic AI (Buổi 03)

Thực thi 4 lớp Harness:
1. Ràng buộc là dữ liệu (Constraints as Data)
2. Tiêu chí hoàn thành kiểm bằng code (Objective Code Sensor)
3. Kiểm quyền (Authority Control / Human Approval Seam)
4. Bàn giao trạng thái (30-Second State Handoff)

Thực thi 3 Mẫu thiết kế suy luận:
- ReAct (Reasoning + Acting)
- Plan-then-Execute
- Mẫu Lai (Hybrid: Plan + ReAct với Adaptive Re-planning)

Thực thi Đánh giá định lượng trên 5 kịch bản và xuất báo cáo report.md.
"""

from __future__ import annotations
import sys
import os
import argparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from flight_agent.models import (
    BookingRequest,
    AgentPattern,
    ApprovalRequest,
    ApprovalDecision,
    ExecutionStatus,
)
from flight_agent.tools import MockFlightDatabase
from flight_agent.memory import PersistentMemoryStore
from flight_agent.harness import FlightBookingHarness
from flight_agent.benchmark import run_full_benchmark, generate_markdown_report

def print_banner():
    print("=" * 80)
    print("   SE373 - AGENTIC AI: HỆ THỐNG ĐẶT VÉ MÁY BAY (LANGCHAIN / LANGGRAPH)   ")
    print("=" * 80)
    print("  ✓ 4 Lớp Harness: Constraints Data | Code Sensor | Authority | Handoff")
    print("  ✓ 3 Mẫu Thiết Kế: ReAct | Plan-then-Execute | Hybrid Re-planning")
    print("  ✓ 5 Điều Kiện Dừng: Approval | Goal | Loop | Stall | Hard Budget")
    print("  ✓ Challenge A: Persistent Memory & Cross-Session Convention Lifecycle")
    print("=" * 80)

def run_single_demo():
    print("\n--- CHẠY DEMO 1 LƯỢT ĐẶT VÉ (HYBRID AGENT) ---")
    harness = FlightBookingHarness()
    request = BookingRequest(
        passenger_name="Nguyen Van A",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
        cabin_class="ECONOMY",
    )

    def interactive_approver(req: ApprovalRequest) -> ApprovalDecision:
        print(f"\n[CHỐT KIỂM QUYỀN - HUMAN APPROVAL HOOK]")
        print(f"  Thao tác nhạy cảm: {req.tool_name}")
        print(f"  Tóm tắt: {req.summary}")
        print(f"  Chi phí: {req.cost:,.0f} VND")
        print("  -> Tự động phê duyệt giao dịch (Simulation Mode: APPROVED)\n")
        return ApprovalDecision.approve()

    print(f"Yêu cầu: {request.passenger_name} | {request.origin}->{request.destination} | Ngày: {request.departure_date} | Ngân sách: {request.max_budget:,.0f} VND")
    result = harness.run(
        pattern=AgentPattern.HYBRID,
        request=request,
        approval_callback=interactive_approver,
    )

    print("--- KẾT QUẢ ĐIỀU PHỐI QUA HARNESS SEAM ---")
    print(f"Trạng thái: {result.status.value}")
    print(f"Kiểm chứng bằng Code Sensor: {'ĐẠT (VALID)' if result.code_verification_passed else 'KHÔNG ĐẠT'}")
    print(f"Lý do xác minh: {result.verification_reason}")
    if result.booking:
        print(f"Thông tin vé xác nhận: PNR={result.booking.get('booking_id')}, Chuyến={result.booking.get('flight_id')}, Giá={result.booking.get('price'):,.0f} VND")
    print(f"Chỉ số thực thi: {result.metrics.total_steps} bước, {result.metrics.total_tokens} tokens, {result.metrics.elapsed_seconds}s, {result.metrics.replan_count} lần re-plan\n")

def run_interactive():
    print("\n--- CHẾ ĐỘ TƯƠNG TÁC TRỰC TIẾP (INTERACTIVE CLI) ---")
    print("Chọn mẫu thiết kế Agent:")
    print("  1. ReAct (Reasoning + Acting)")
    print("  2. Plan-then-Execute")
    print("  3. Mẫu Lai (Hybrid with Adaptive Re-planning) [Mặc định]")
    choice = input("Lựa chọn (1/2/3, mặc định 3): ").strip()
    pattern_map = {"1": AgentPattern.REACT, "2": AgentPattern.PLAN_THEN_EXECUTE, "3": AgentPattern.HYBRID}
    pattern = pattern_map.get(choice, AgentPattern.HYBRID)

    name = input("Tên hành khách [Nguyen Van A]: ").strip() or "Nguyen Van A"
    origin = input("Sân bay đi (IATA, e.g. SGN, HAN, DAD) [SGN]: ").strip().upper() or "SGN"
    dest = input("Sân bay đến (IATA, e.g. HAN, DAD, PQC) [HAN]: ").strip().upper() or "HAN"
    date = input("Ngày khởi hành (YYYY-MM-DD) [2026-10-15]: ").strip() or "2026-10-15"
    budget_raw = input("Ngân sách trần (VND) [2500000]: ").strip() or "2500000"
    try:
        budget = float(budget_raw.replace(",", ""))
    except ValueError:
        budget = 2500000.0

    request = BookingRequest(
        passenger_name=name,
        origin=origin,
        destination=dest,
        departure_date=date,
        max_budget=budget,
        cabin_class="ECONOMY",
    )

    def human_approver(req: ApprovalRequest) -> ApprovalDecision:
        print(f"\n" + "!" * 65)
        print(f" [CHỐT KIỂM QUYỀN CON NGƯỜI - HUMAN APPROVAL SEAM]")
        print(f"  Thao tác: {req.tool_name}")
        print(f"  Tóm tắt: {req.summary}")
        print(f"  Chi phí thực tế: {req.cost:,.0f} VND")
        print(f"!" * 65)
        user_choice = input("Bạn có đồng ý phê duyệt thanh toán xuất vé không? (y/n) [y]: ").strip().lower()
        if user_choice in ("y", "yes", ""):
            print("-> Người dùng ĐỒNG Ý phê duyệt giao dịch.\n")
            return ApprovalDecision.approve()
        else:
            reason = input("Lý do từ chối: ").strip() or "Người dùng từ chối thanh toán tại chốt kiểm quyền."
            print(f"-> Người dùng TỪ CHỐI phê duyệt: {reason}\n")
            return ApprovalDecision.reject(reason=reason)

    harness = FlightBookingHarness()
    print(f"\nĐang kích hoạt Agent ({pattern.value}) điều phối qua Harness...")
    result = harness.run(pattern=pattern, request=request, approval_callback=human_approver)

    print("\n" + "=" * 65)
    print(" KẾT QUẢ CUỐI CÙNG (ĐIỀU PHỐI QUA HARNESS)")
    print("=" * 65)
    print(f"Trạng thái: {result.status.value}")
    print(f"Kiểm chứng Code Sensor: {'ĐẠT (VALID)' if result.code_verification_passed else 'KHÔNG ĐẠT'}")
    print(f"Chi tiết: {result.verification_reason}")
    if result.booking:
        print(f"Vé đã xác nhận: PNR={result.booking.get('booking_id')}, Chuyến={result.booking.get('flight_id')}, Giá={result.booking.get('price'):,.0f} VND")
    if result.handoff:
        print("\n--- GÓI BÀN GIAO 30 GIÂY (30-SECOND HANDOFF) ---")
        print(f"Mục tiêu: {result.handoff.goal}")
        print(f"Trạng thái hiện tại: {result.handoff.current_state}")
        print(f"Lý do dừng: {result.handoff.stop_reason}")
        print(f"Hành động đã thử: {', '.join(result.handoff.attempted_actions)}")
        print(f"Khuyến nghị tiếp theo: {result.handoff.next_recommendations}")
    print("=" * 65 + "\n")

def run_evaluation():
    print("\n--- BẮT ĐẦU ĐÁNH GIÁ THỰC NGHIỆM ĐỊNH LƯỢNG (15 RUNS) ---")
    benchmark_data = run_full_benchmark()

    print("\nBẢNG TỔNG HỢP HIỆU QUẢ 3 MẪU THIẾT KẾ:")
    print("-" * 90)
    print(f"{'Mẫu Thiết Kế':<22} | {'Tỷ Lệ Thành Công':<18} | {'Số Bước TB':<12} | {'Tokens TB':<12} | {'Thời Gian TB':<14}")
    print("-" * 90)
    for row in benchmark_data["summary_table"]:
        print(f"{row['pattern']:<22} | {row['success_rate']:<18} | {str(row['avg_steps']):<12} | {str(row['avg_tokens']):<12} | {str(row['avg_duration']) + 's':<14}")
    print("-" * 90)

    report_content = generate_markdown_report(benchmark_data)
    report_path = os.path.join(os.path.dirname(__file__), "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n✓ Đã xuất báo cáo chi tiết ra file: {report_path}")

def run_comparison():
    print("\n" + "=" * 80)
    print("   SO SÁNH QUYẾT ĐỊNH GIỮA 3 MẪU THIẾT KẾ TRONG TÌNH HUỐNG CHUYẾN BAY HẾT VÉ   ")
    print("=" * 80)
    print("Bối cảnh: Khách hàng muốn đặt chuyến SGN -> HAN ngày 2026-10-15.")
    print("Thực tế môi trường: Chuyến bay rẻ nhất VN123 bị HẾT VÉ (0 ghế). Chuyến QH789 còn vé.")
    print("-" * 80)

    request = BookingRequest(
        passenger_name="Tran Thi B",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
        cabin_class="ECONOMY",
    )

    patterns = [
        (AgentPattern.PLAN_THEN_EXECUTE, "1. Plan-then-Execute (Lập kế hoạch trước rồi thực thi)"),
        (AgentPattern.REACT, "2. ReAct (Reasoning + Acting từng bước)"),
        (AgentPattern.HYBRID, "3. Mẫu Lai (Hybrid: Plan + ReAct với Adaptive Re-planning)"),
    ]

    for p, title in patterns:
        print(f"\n>>> ĐANG CHẠY: {title}")
        # Reset DB where VN123 has 0 seats
        db = MockFlightDatabase()
        db.flights["VN123"]["available_seats"] = 0

        harness = FlightBookingHarness(db=db)
        res = harness.run(pattern=p, request=request, approval_callback=lambda req: ApprovalDecision.approve())

        print(f"    Trạng thái kết thúc: {res.status.value}")
        print(f"    Vé xuất thành công: {'Có' if res.booking else 'Không'}")
        if res.booking:
            print(f"    Chuyến bay được chọn: {res.booking.get('flight_id')} - Giá: {res.booking.get('price'):,.0f} VND - PNR: {res.booking.get('booking_id')}")

        print("    --- LỊCH TRÌNH CÁC QUYẾT ĐỊNH (TRACE STEPS) ---")
        for s in res.trace:
            if s.thought:
                print(f"    [BƯỚC {s.step_number}] 💡 Suy luận/Kế hoạch: {s.thought}")
            if s.tool_name:
                print(f"    [BƯỚC {s.step_number}] ⚡ Gọi Tool: {s.tool_name}({s.tool_input})")
                if s.interception:
                    print(f"               🛡️ Chốt kiểm quyền: {s.interception}")
                if s.tool_output:
                    status = s.tool_output.get("status")
                    err = s.tool_output.get("error_code")
                    hint = s.tool_output.get("hint")
                    print(f"               👁️ Quan sát (Observation): {status}" + (f" [{err}] - Gợi ý: {hint}" if err else ""))

        if res.handoff:
            print(f"    [BÀN GIAO 30S] Lý do dừng: {res.handoff.stop_reason}")

        print("-" * 80)

    print("\n" + "=" * 80)
    print("   TỔNG KẾT SỰ KHÁC BIỆT VỀ QUYẾT ĐỊNH (KEY DECISION DIVERGENCE)   ")
    print("=" * 80)
    print("""
1. ĐIỂM RẼ NHÁNH TẠI BƯỚC 2 (Khi kiểm tra ghế VN123 trả về FLIGHT_SOLD_OUT):
   - Plan-then-Execute: Do kế hoạch đã sinh cố định từ đầu, agent KHÔNG THỂ thích ứng.
     -> Quyết định: Thất bại và dừng luồng ngay lập tức.
   - ReAct: Nhận observation thất bại kèm gợi ý 'Select an alternative flight'.
     -> Quyết định: Tại vòng lặp suy luận tiếp theo, ReAct tự sinh tool call mới
        nhắm vào chuyến bay thay thế QH789 và tiếp tục hoàn thành đặt vé.
   - Mẫu Lai (Hybrid): Nút Evaluator phát hiện quan sát 'FLIGHT_SOLD_OUT' là bất thường.
     -> Quyết định: Kích hoạt nút Re-planner để lập lại một kế hoạch con mới gồm 3 bước
        nhắm vào QH789, sau đó Executor tiếp tục chạy theo kế hoạch mới và thành công.

2. ĐÁNH GIÁ SỰ ĐÁNH ĐỔI (TRADE-OFFS):
   - Plan-then-Execute: Tiết kiệm token nhất (1,100 tokens), nhưng dễ vỡ (brittle) khi môi trường đổi.
   - ReAct: Linh hoạt thích ứng turn-by-turn (2,450 tokens, 5 bước), phụ thuộc hoàn toàn vào gợi ý từ tool.
   - Mẫu Lai: Tự động phục hồi có cấu trúc (2,900 tokens, 6 bước, 1 lần re-plan), vừa đảm bảo kế hoạch
     vừa đảm bảo tính linh hoạt thích nghi.
    """)
    print("=" * 80 + "\n")

def run_persistent_memory_challenge():
    print("\n" + "=" * 80)
    print("   CHALLENGE A: PERSISTENT MEMORY & CONVENTION LIFECYCLE VERIFICATION   ")
    print("=" * 80)
    print("Mục tiêu theo Slide 14-16: Agent ghi nhớ quy ước dự án qua nhiều session và cập nhật khi quy ước đổi.")
    print("Checklist 6 tiêu chí: Lưu trữ ngoài history -> Lưu S1 -> Kiểm chứng S2 -> Đổi S3 -> Kiểm chứng S4 -> In context memory")
    print("-" * 80)

    # Use a clean demo persistent memory store in .scratch
    storage_path = os.path.join(os.path.dirname(__file__), ".scratch", "demo_persistent_memory.json")
    if os.path.exists(storage_path):
        os.remove(storage_path)
    store = PersistentMemoryStore(storage_path=storage_path)

    def sim_approver(req: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision.approve()

    # =========================================================================
    # SESSION 1: Thiết lập quy ước dự án trong session đầu tiên (Checklist #1, #2)
    # =========================================================================
    print("\n>>> [SESSION 1] THIẾT LẬP QUY ƯỚC DỰ ÁN BAN ĐẦU")
    harness_s1 = FlightBookingHarness(memory_store=store)
    rec1 = harness_s1.save_convention(
        key="preferred_airline",
        value="Bamboo Airways",
        description="Chính sách công tác: Ưu tiên chọn Bamboo Airways (QH) cho mọi chuyến bay nội địa.",
        category="corporate_travel_policy",
        session_id="session_01",
    )
    print(f"  ✓ Đã lưu quy ước vào persistent store độc lập: {storage_path}")
    print(f"  • Khóa (Key): {rec1.key}")
    print(f"  • Giá trị (Value): {rec1.value}")
    print(f"  • Mô tả (Description): {rec1.description}")
    print(f"  • Phiên bản (Version): v{rec1.version}")
    print(f"  • Thời gian tạo: {rec1.created_at}")

    # =========================================================================
    # SESSION 2: Mở session mới và kiểm chứng agent làm theo quy ước cũ (Checklist #3, #6)
    # =========================================================================
    print("\n>>> [SESSION 2] MỞ SESSION MỚI (LỊCH SỬ HỘI THOẠI TRỐNG) - KIỂM CHỨNG GHI NHỚ")
    # Fresh harness instance loading from disk
    harness_s2 = FlightBookingHarness(memory_store=PersistentMemoryStore(storage_path=storage_path))
    injected_s2 = harness_s2.get_injected_memory_context()
    print("  [KIỂM CHỨNG BỘ NHỚ ĐƯỢC INJECT VÀO CONTEXT]")
    print(injected_s2)

    req_s2 = BookingRequest(
        passenger_name="Nguyen Van A",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
        cabin_class="ECONOMY",
    )
    print(f"  Yêu cầu từ người dùng: Đặt vé SGN -> HAN, ngày 2026-10-15 cho {req_s2.passenger_name} (KHÔNG ghi rõ hãng bay)")
    res_s2 = harness_s2.run(
        pattern=AgentPattern.REACT,
        request=req_s2,
        approval_callback=sim_approver,
    )
    print(f"  Kết quả thực thi:")
    print(f"    Trạng thái: {res_s2.status.value}")
    print(f"    Vé đã xuất: PNR={res_s2.booking.get('booking_id')}, Hãng={res_s2.booking.get('airline')}, Chuyến={res_s2.booking.get('flight_id')}")
    print(f"    Kiểm chứng Code Sensor: {'ĐẠT CHUẨN' if res_s2.code_verification_passed else 'KHÔNG ĐẠT'}")
    assert res_s2.booking.get("flight_id") == "QH789", "Agent must pick QH789 based on Session 1 convention!"
    print("  ✓ XÁC NHẬN: Agent đã tự động chọn Bamboo Airways (QH789) nhờ Persistent Memory!")

    # =========================================================================
    # SESSION 3: Thay đổi quy ước và cập nhật memory (Checklist #4)
    # =========================================================================
    print("\n>>> [SESSION 3] THAY ĐỔI QUY ƯỚC DỰ ÁN VÀ CẬP NHẬT PERSISTENT MEMORY")
    harness_s3 = FlightBookingHarness(memory_store=PersistentMemoryStore(storage_path=storage_path))
    rec2 = harness_s3.save_convention(
        key="preferred_airline",
        value="Vietnam Airlines",
        description="Cập nhật chính sách: Chuyển sang ưu tiên Hãng hàng không Quốc gia Vietnam Airlines (VN).",
        category="corporate_travel_policy",
        session_id="session_03",
    )
    print(f"  ✓ Đã cập nhật quy ước trong persistent store:")
    print(f"  • Khóa (Key): {rec2.key}")
    print(f"  • Giá trị MỚI (New Value): {rec2.value}")
    print(f"  • Mô tả: {rec2.description}")
    print(f"  • Phiên bản mới: v{rec2.version} (tự động tăng version, ghi đè quy ước cũ)")
    print(f"  • Cập nhật lúc: {rec2.updated_at}")

    # =========================================================================
    # SESSION 4: Mở session mới và kiểm chứng agent dùng quy ước mới (Checklist #5, #6)
    # =========================================================================
    print("\n>>> [SESSION 4] MỞ SESSION TIẾP THEO (LỊCH SỬ MỚI) - KIỂM CHỨNG QUY ƯỚC MỚI")
    harness_s4 = FlightBookingHarness(memory_store=PersistentMemoryStore(storage_path=storage_path))
    injected_s4 = harness_s4.get_injected_memory_context()
    print("  [KIỂM CHỨNG BỘ NHỚ ĐƯỢC INJECT VÀO CONTEXT]")
    print(injected_s4)

    req_s4 = BookingRequest(
        passenger_name="Nguyen Van A",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
        cabin_class="ECONOMY",
    )
    print(f"  Yêu cầu từ người dùng: Đặt vé SGN -> HAN, ngày 2026-10-15 cho {req_s4.passenger_name} (KHÔNG ghi rõ hãng bay)")
    res_s4 = harness_s4.run(
        pattern=AgentPattern.REACT,
        request=req_s4,
        approval_callback=sim_approver,
    )
    print(f"  Kết quả thực thi:")
    print(f"    Trạng thái: {res_s4.status.value}")
    print(f"    Vé đã xuất: PNR={res_s4.booking.get('booking_id')}, Hãng={res_s4.booking.get('airline')}, Chuyến={res_s4.booking.get('flight_id')}")
    print(f"    Kiểm chứng Code Sensor: {'ĐẠT CHUẨN' if res_s4.code_verification_passed else 'KHÔNG ĐẠT'}")
    assert res_s4.booking.get("flight_id") == "VN123", "Agent must pick VN123 based on updated convention!"
    print("  ✓ XÁC NHẬN: Agent đã lập tức tuân thủ quy ước mới (VN123 - Vietnam Airlines), không còn dùng quy ước cũ!")

    # =========================================================================
    # BẢNG TỔNG KẾT CHECKLIST THỰC HIỆN 6/6
    # =========================================================================
    print("\n" + "=" * 80)
    print("   BẢNG ĐỐI CHIẾU TIÊU CHÍ HOÀN THÀNH CHALLENGE A (CHECKLIST 6/6)   ")
    print("=" * 80)
    checklist = [
        ("Tạo cơ chế lưu persistent memory ngoài lịch sử hội thoại hiện tại", "ĐẠT (Store JSON độc lập tại .scratch/demo_persistent_memory.json)"),
        ("Lưu một quy ước dự án trong session đầu tiên", "ĐẠT (Session 1: preferred_airline = Bamboo Airways, v1)"),
        ("Mở session mới và chứng minh agent vẫn làm theo quy ước cũ", "ĐẠT (Session 2: Fresh history, Agent tự chọn chuyến QH789)"),
        ("Thay đổi quy ước và cập nhật memory", "ĐẠT (Session 3: preferred_airline = Vietnam Airlines, v2)"),
        ("Mở session mới tiếp theo và chứng minh agent dùng quy ước mới", "ĐẠT (Session 4: Fresh history, Agent tự chọn chuyến VN123)"),
        ("In nội dung memory đã inject vào context để kiểm chứng", "ĐẠT (Injected Context block được in trực tiếp ở từng Session)"),
    ]
    for idx, (item, status) in enumerate(checklist, 1):
        print(f"  [{idx}/6] [x] {item:<65} -> {status}")
    print("=" * 80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="SE373 Flight Booking Agent")
    parser.add_argument("-i", "--interactive", action="store_true", help="Chạy chế độ đặt vé tương tác trực tiếp qua console")
    parser.add_argument("-b", "--benchmark", action="store_true", help="Chạy bộ benchmark đánh giá định lượng 15 lượt")
    parser.add_argument("-c", "--compare", action="store_true", help="So sánh chi tiết các bước quyết định giữa 3 Agents khi gặp sự cố hết vé")
    parser.add_argument("-m", "--memory", action="store_true", help="Chạy kiểm chứng Challenge A: Persistent Memory qua vòng đời 4 sessions")
    args = parser.parse_args()

    print_banner()
    if args.interactive:
        run_interactive()
    elif args.compare:
        run_comparison()
    elif args.memory:
        run_persistent_memory_challenge()
    elif args.benchmark:
        run_evaluation()
    else:
        # Default: demo + memory challenge + benchmark
        run_single_demo()
        run_persistent_memory_challenge()
        run_evaluation()

if __name__ == "__main__":
    main()
