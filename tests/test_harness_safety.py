import pytest
from flight_agent.harness import FlightBookingHarness
from flight_agent.models import (
    BookingRequest,
    AgentPattern,
    ApprovalRequest,
    ApprovalDecision,
    ExecutionStatus,
    ExecutionBudget,
)
from flight_agent.llm import DeterministicFlightModel

def test_human_approval_rejection():
    """
    Scenario: User rejects payment confirmation.
    Harness should intercept, skip payment, allow agent to cancel hold,
    and output a structured 30-second handoff context with APPROVAL_REJECTED status.
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

    def reject_approver(req: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision.reject(reason="Price too expensive; passenger declined.")

    result = harness.run(
        pattern=AgentPattern.REACT,
        request=request,
        approval_callback=reject_approver,
    )

    assert result.status == ExecutionStatus.APPROVAL_REJECTED
    assert result.booking is None
    assert result.code_verification_passed is False
    assert result.handoff is not None
    assert "Human user rejected" in result.handoff.stop_reason or "rejected" in result.handoff.stop_reason.lower()
    assert len(result.handoff.attempted_actions) > 0
    assert len(result.handoff.next_recommendations) > 0


def test_loop_detection():
    """
    Scenario: Defective agent or ambiguous tool error causes agent to repeatedly
    call search_flights with the exact same arguments.
    Harness loop detector must flag this and terminate with LOOP_DETECTED status.
    """
    model = DeterministicFlightModel(force_loop_trap=True)
    harness = FlightBookingHarness(model=model)
    request = BookingRequest(
        passenger_name="Tran Thi B",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
    )

    result = harness.run(
        pattern=AgentPattern.REACT,
        request=request,
        limits=ExecutionBudget(max_steps=10),
    )

    assert result.status == ExecutionStatus.LOOP_DETECTED
    assert result.handoff is not None
    assert "loop" in result.handoff.stop_reason.lower()
    assert result.metrics.total_steps < 10  # Stopped well before budget exhaustion


def test_stall_detection():
    """
    Scenario: Agent changes tools each round but makes zero progress toward booking.
    Harness stall detector must detect this and terminate with STALL_DETECTED status.
    """
    model = DeterministicFlightModel(force_stall_trap=True)
    harness = FlightBookingHarness(model=model)
    request = BookingRequest(
        passenger_name="Le Van C",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
    )

    result = harness.run(
        pattern=AgentPattern.REACT,
        request=request,
        limits=ExecutionBudget(max_steps=12),
    )

    assert result.status == ExecutionStatus.STALL_DETECTED
    assert result.handoff is not None
    assert "stall" in result.handoff.stop_reason.lower()


def test_budget_exceeded():
    """
    Scenario: Complex task hits hard budget limit (e.g. max_steps=2).
    Harness must terminate with BUDGET_EXCEEDED and generate a 30-second handoff.
    """
    harness = FlightBookingHarness()
    request = BookingRequest(
        passenger_name="Pham Thi D",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        max_budget=2500000.0,
    )

    result = harness.run(
        pattern=AgentPattern.REACT,
        request=request,
        limits=ExecutionBudget(max_steps=2),
    )

    assert result.status == ExecutionStatus.BUDGET_EXCEEDED
    assert result.handoff is not None
    assert "budget" in result.handoff.stop_reason.lower()
    assert result.metrics.total_steps <= 2
