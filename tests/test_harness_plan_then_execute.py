import pytest
from flight_agent.harness import FlightBookingHarness
from flight_agent.models import (
    BookingRequest,
    AgentPattern,
    ApprovalRequest,
    ApprovalDecision,
    ExecutionStatus,
)

def test_plan_then_execute_happy_path():
    """
    Test Plan-then-Execute pattern:
    1. Planner decomposes the booking goal into an explicit sequence of steps.
    2. Executor executes each step in order through the harness.
    3. Authority control intercepts the payment step.
    4. Code sensor objectively verifies completion.
    """
    harness = FlightBookingHarness()
    request = BookingRequest(
        passenger_name="Dang Van E",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
        cabin_class="ECONOMY",
    )

    approvals_requested = []
    def human_approver(req: ApprovalRequest) -> ApprovalDecision:
        approvals_requested.append(req)
        return ApprovalDecision.approve()

    result = harness.run(
        pattern=AgentPattern.PLAN_THEN_EXECUTE,
        request=request,
        approval_callback=human_approver,
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert result.booking is not None
    assert result.booking["status"] == "CONFIRMED"
    assert result.booking["passenger_name"] == "Dang Van E"
    assert result.code_verification_passed is True
    assert len(approvals_requested) == 1
    # Check that plan was generated and captured in trace
    assert any("plan" in (step.thought or "").lower() for step in result.trace)


def test_plan_then_execute_fails_on_sold_out_without_replanning():
    """
    Demonstrates the core vulnerability of pure Plan-then-Execute noted in SE373:
    When the preferred flight in the fixed plan is sold out (VJ456),
    pure Plan-then-Execute halts on step failure without adapting or re-planning.
    """
    # Mock database where only VJ456 matches or is targeted
    db = FlightBookingHarness().db
    # Force VN123 to 0 seats as well
    db.flights["VN123"]["available_seats"] = 0

    harness = FlightBookingHarness(db=db)
    request = BookingRequest(
        passenger_name="Dang Van E",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2000000.0,
        cabin_class="ECONOMY",
    )

    result = harness.run(
        pattern=AgentPattern.PLAN_THEN_EXECUTE,
        request=request,
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.booking is None
    assert result.code_verification_passed is False
