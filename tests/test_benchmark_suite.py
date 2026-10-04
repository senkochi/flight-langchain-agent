import pytest
from flight_agent.benchmark import run_full_benchmark, generate_markdown_report

def test_benchmark_suite_runs_all_scenarios():
    """
    Verifies that the benchmark runner executes all 3 agent architectures
    across all 5 standardized scenarios (15 runs total) and generates
    a comprehensive Markdown comparison report.
    """
    report_data = run_full_benchmark()

    # 3 patterns x 5 scenarios = 15 runs
    assert len(report_data["runs"]) == 15
    assert "summary_table" in report_data

    # Check Markdown report generation
    md_report = generate_markdown_report(report_data)
    assert "# Báo Cáo Đánh Giá Hiệu Quả Agent Đặt Vé Máy Bay" in md_report
    assert "ReAct" in md_report
    assert "Plan-then-Execute" in md_report
    assert "Hybrid" in md_report
    assert "Failure Modes" in md_report
