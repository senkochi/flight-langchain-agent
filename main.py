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
    print_banner()
    run_single_demo()
    run_evaluation()

if __name__ == "__main__":
    main()
