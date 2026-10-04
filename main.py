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
from flight_agent.harness import FlightBookingHarness
from flight_agent.benchmark import run_full_benchmark, generate_markdown_report

def print_banner():
    print("=" * 80)
    print("   SE373 - AGENTIC AI: HỆ THỐNG ĐẶT VÉ MÁY BAY (LANGCHAIN / LANGGRAPH)   ")
    print("=" * 80)
    print("  ✓ 4 Lớp Harness: Constraints Data | Code Sensor | Authority | Handoff")
    print("  ✓ 3 Mẫu Thiết Kế: ReAct | Plan-then-Execute | Hybrid Re-planning")
    print("  ✓ 5 Điều Kiện Dừng: Approval | Goal | Loop | Stall | Hard Budget")
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

def main():
    parser = argparse.ArgumentParser(description="SE373 Flight Booking Agent")
    parser.add_argument("-i", "--interactive", action="store_true", help="Chạy chế độ đặt vé tương tác trực tiếp qua console")
    parser.add_argument("-b", "--benchmark", action="store_true", help="Chạy bộ benchmark đánh giá định lượng 15 lượt")
    args = parser.parse_args()

    print_banner()
    if args.interactive:
        run_interactive()
    elif args.benchmark:
        run_evaluation()
    else:
        # Default: demo + benchmark
        run_single_demo()
        run_evaluation()

if __name__ == "__main__":
    main()
