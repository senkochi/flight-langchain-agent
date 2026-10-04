import pytest
from flight_agent.harness import FlightBookingHarness
from flight_agent.models import (
    BookingRequest,
    AgentPattern,
    ApprovalRequest,
    ApprovalDecision,
    ExecutionStatus,
)

def test_happy_path_react_agent():
    """
    Happy Path Test:
    User wants to book a flight SGN -> HAN on 2026-10-15 under 2,500,000 VND.
    Agent searches flights, checks seat availability, places a hold,
    requests human approval before payment, receives approval,
    issues the ticket, and passes objective code sensor verification.
    """
    harness = FlightBookingHarness()
    request = BookingRequest(
        passenger_name="Nguyen Van A",
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
        pattern=AgentPattern.REACT,
        request=request,
        approval_callback=human_approver,
    )

    # External Seam Assertions
    assert result.status == ExecutionStatus.SUCCESS
    assert result.booking is not None
    assert result.booking["status"] == "CONFIRMED"
    assert result.booking["passenger_name"] == "Nguyen Van A"
    assert result.booking["origin"] == "SGN"
    assert result.booking["destination"] == "HAN"
    assert result.booking["price"] <= 2500000.0
    assert result.code_verification_passed is True

    # Authority Control Assertion
    assert len(approvals_requested) == 1
    assert approvals_requested[0].tool_name == "confirm_payment_and_issue_ticket"
    assert approvals_requested[0].details["passenger_name"] == "Nguyen Van A"
