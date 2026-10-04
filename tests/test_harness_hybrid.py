import pytest
from flight_agent.harness import FlightBookingHarness
from flight_agent.models import (
    BookingRequest,
    AgentPattern,
    ApprovalRequest,
    ApprovalDecision,
    ExecutionStatus,
)
from flight_agent.tools import MockFlightDatabase

def test_hybrid_agent_recovers_from_sold_out_flight():
    """
    Scenario: Primary flight is sold out (VN123 has 0 seats).
    Pure Plan-then-Execute failed in this scenario.
    Hybrid Agent must:
    1. Plan initial booking.
    2. Detect sold-out status via Evaluator.
    3. Trigger Re-planner node to adapt plan using alternative flight (QH789).
    4. Successfully hold seat and complete booking under human approval.
    5. Pass code sensor verification.
    """
    db = MockFlightDatabase()
    db.flights["VN123"]["available_seats"] = 0  # Force sold-out

    harness = FlightBookingHarness(db=db)
    request = BookingRequest(
        passenger_name="Hoang Thi F",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
        cabin_class="ECONOMY",
    )

    approvals = []
    def approver(req: ApprovalRequest) -> ApprovalDecision:
        approvals.append(req)
        return ApprovalDecision.approve()

    result = harness.run(
        pattern=AgentPattern.HYBRID,
        request=request,
        approval_callback=approver,
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert result.booking is not None
    assert result.booking["status"] == "CONFIRMED"
    assert result.booking["flight_id"] == "QH789"  # Successfully adapted to alternative flight!
    assert result.booking["passenger_name"] == "Hoang Thi F"
    assert result.code_verification_passed is True
    assert result.metrics.replan_count >= 1
    assert len(approvals) == 1
