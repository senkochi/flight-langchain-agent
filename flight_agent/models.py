from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class AgentPattern(str, Enum):
    REACT = "react"
    PLAN_THEN_EXECUTE = "plan_then_execute"
    HYBRID = "hybrid"

class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    APPROVAL_NEEDED = "APPROVAL_NEEDED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    LOOP_DETECTED = "LOOP_DETECTED"
    STALL_DETECTED = "STALL_DETECTED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    FAILED = "FAILED"

class BookingRequest(BaseModel):
    """
    Layer 1: Constraints as Data.
    User booking requirements are modeled as strongly typed, immutable data
    to prevent goal drift across multi-turn reasoning loops.
    """
    model_config = ConfigDict(frozen=True)

    passenger_name: str = Field(..., description="Full name of the primary passenger")
    origin: str = Field(..., min_length=3, max_length=3, description="3-letter IATA origin airport code")
    destination: str = Field(..., min_length=3, max_length=3, description="3-letter IATA destination airport code")
    departure_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Departure date in YYYY-MM-DD")
    max_budget: float = Field(..., gt=0, description="Strict maximum budget ceiling in VND")
    cabin_class: str = Field(default="ECONOMY", description="Cabin class: ECONOMY or BUSINESS")

class FlightRecord(BaseModel):
    flight_id: str
    airline: str
    origin: str
    destination: str
    departure_date: str
    departure_time: str
    price: float
    available_seats: int
    cabin_class: str = "ECONOMY"

class BookingRecord(BaseModel):
    booking_id: str
    flight_id: str
    passenger_name: str
    origin: str
    destination: str
    departure_date: str
    price: float
    cabin_class: str
    status: str  # "HELD" | "CONFIRMED" | "CANCELLED"

class ApprovalRequest(BaseModel):
    tool_name: str
    details: Dict[str, Any]
    cost: float
    summary: str

class ApprovalDecision(BaseModel):
    approved: bool
    reason: Optional[str] = None

    @classmethod
    def approve(cls) -> ApprovalDecision:
        return cls(approved=True, reason="User approved transaction")

    @classmethod
    def reject(cls, reason: str = "User denied transaction") -> ApprovalDecision:
        return cls(approved=False, reason=reason)

class ExecutionBudget(BaseModel):
    max_steps: int = 15
    max_tokens: int = 20000
    max_time_seconds: float = 60.0

class TraceStep(BaseModel):
    step_number: int
    pattern: str
    thought: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    interception: Optional[str] = None

class HandoffSummary(BaseModel):
    """
    Layer 4: 30-Second State Handoff.
    Concisely packages execution state when stopping or escalating.
    """
    goal: str
    constraints: Dict[str, Any]
    current_state: str
    attempted_actions: List[str]
    stop_reason: str
    next_recommendations: List[str]

class ExecutionMetrics(BaseModel):
    total_steps: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    tool_call_count: int = 0
    replan_count: int = 0
    constraint_violations: int = 0

class ExecutionResult(BaseModel):
    status: ExecutionStatus
    booking: Optional[Dict[str, Any]] = None
    code_verification_passed: bool = False
    verification_reason: Optional[str] = None
    handoff: Optional[HandoffSummary] = None
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    trace: List[TraceStep] = Field(default_factory=list)
