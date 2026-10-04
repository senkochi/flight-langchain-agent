from __future__ import annotations
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from langchain_core.messages import HumanMessage, ToolMessage

from flight_agent.models import (
    AgentPattern,
    BookingRequest,
    ApprovalRequest,
    ApprovalDecision,
    ExecutionBudget,
    ExecutionResult,
    ExecutionStatus,
    ExecutionMetrics,
    TraceStep,
    HandoffSummary,
)
from flight_agent.tools import MockFlightDatabase
from flight_agent.sensor import verify_booking_completion
from flight_agent.llm import DeterministicFlightModel
from flight_agent.agents.react_agent import build_react_graph
from flight_agent.agents.plan_execute_agent import build_plan_execute_graph
from flight_agent.agents.hybrid_agent import build_hybrid_graph

class FlightBookingHarness:
    """
    Authoritative Harness governing Agent execution across all patterns.
    Implements:
    1. Constraints as Data (Pydantic immutable request)
    2. Objective Completion Sensor (verify_booking_completion code check)
    3. Authority Control (Pre-tool Human Approval hook for payment/issuance)
    4. 30-Second State Handoff
    5. 5-Stage Termination Pipeline (Approval -> Goal -> Loop -> Stall -> Budget)
    """

    def __init__(
        self,
        db: Optional[MockFlightDatabase] = None,
        model: Optional[Any] = None,
    ):
        self.db = db if db is not None else MockFlightDatabase()
        self.model = model if model is not None else DeterministicFlightModel()

    def run(
        self,
        pattern: AgentPattern,
        request: BookingRequest,
        approval_callback: Optional[Callable[[ApprovalRequest], ApprovalDecision]] = None,
        limits: ExecutionBudget = ExecutionBudget(),
    ) -> ExecutionResult:
        start_time = time.time()
        metrics = ExecutionMetrics()
        trace: List[TraceStep] = []
        confirmed_booking_id: Optional[str] = None
        current_hold_id: Optional[str] = None
        inspected_flights: set = set()

        halt_reason: Optional[ExecutionStatus] = None
        halt_detail: Optional[str] = None
        tool_call_history: List[Tuple[str, str]] = []
        stall_counter: int = 0

        def should_halt() -> bool:
            return halt_reason is not None

        # Pre-tool authority control & post-observation termination dispatcher
        def tool_dispatcher(tool_calls: List[Dict[str, Any]]) -> List[ToolMessage]:
            nonlocal confirmed_booking_id, current_hold_id, halt_reason, halt_detail, stall_counter
            tool_messages: List[ToolMessage] = []

            for call in tool_calls:
                if halt_reason is not None:
                    break

                metrics.total_steps += 1
                metrics.tool_call_count += 1
                tool_name = call["name"]
                args = call["args"]
                call_id = call["id"]

                # 1. Termination Condition 1: Human Approval Check (Pre-Tool)
                trace_step = TraceStep(
                    step_number=metrics.total_steps,
                    pattern=pattern.value,
                    tool_name=tool_name,
                    tool_input=args,
                )

                if tool_name == "confirm_payment_and_issue_ticket":
                    cost = request.max_budget
                    flight_record = self.db.flights.get(args.get("flight_id", ""))
                    if flight_record:
                        cost = flight_record["price"]

                    app_req = ApprovalRequest(
                        tool_name=tool_name,
                        details=args,
                        cost=cost,
                        summary=f"Authorize payment and issuance of {cost:,.0f} VND for flight {args.get('flight_id')} under passenger {args.get('passenger_name')}.",
                    )

                    decision = ApprovalDecision.approve()
                    if approval_callback is not None:
                        decision = approval_callback(app_req)

                    if not decision.approved:
                        trace_step.interception = f"REJECTED: {decision.reason}"
                        out = {
                            "status": "REJECTED",
                            "data": None,
                            "error_code": "APPROVAL_REJECTED",
                            "hint": f"User denied payment: {decision.reason}. Please cancel hold or search alternative.",
                        }
                        trace_step.tool_output = out
                        trace.append(trace_step)
                        tool_messages.append(
                            ToolMessage(
                                content=json.dumps(out),
                                name=tool_name,
                                tool_call_id=call_id,
                            )
                        )
                        continue
                    else:
                        trace_step.interception = "APPROVED"

                # Execute tool against DB
                made_progress = False
                if tool_name == "search_flights":
                    out = self.db.search_flights(
                        args["origin"], args["destination"], args["date"], args.get("max_price")
                    )
                    if out["status"] == "SUCCESS" and len(out["data"]) > 0:
                        made_progress = True
                elif tool_name == "check_seat_availability":
                    f_id = args.get("flight_id")
                    out = self.db.check_seat_availability(f_id)
                    if f_id not in inspected_flights:
                        inspected_flights.add(f_id)
                        made_progress = True
                elif tool_name == "hold_booking":
                    out = self.db.hold_booking(args["flight_id"], args["passenger_name"])
                    if out["status"] == "SUCCESS":
                        current_hold_id = out["data"]["hold_id"]
                        made_progress = True
                elif tool_name == "confirm_payment_and_issue_ticket":
                    out = self.db.confirm_payment_and_issue_ticket(
                        args["flight_id"], args["passenger_name"], args.get("hold_id")
                    )
                    if out["status"] == "SUCCESS":
                        confirmed_booking_id = out["data"]["booking_id"]
                        made_progress = True
                elif tool_name == "cancel_booking":
                    out = self.db.cancel_booking(args["hold_id"])
                    if out["status"] == "SUCCESS":
                        current_hold_id = None
                        made_progress = True
                else:
                    out = {"status": "FAILED", "error_code": "UNKNOWN_TOOL", "hint": "Tool not found"}

                trace_step.tool_output = out
                trace.append(trace_step)
                tool_messages.append(
                    ToolMessage(
                        content=json.dumps(out),
                        name=tool_name,
                        tool_call_id=call_id,
                    )
                )

                # 2. Termination Condition 2: Goal Achieved (Post-observation)
                if confirmed_booking_id:
                    # Verified by sensor below
                    pass

                # 3. Termination Condition 3: Loop Detection (Post-observation)
                call_sig = (tool_name, json.dumps(args, sort_keys=True))
                tool_call_history.append(call_sig)
                if len(tool_call_history) >= 2 and tool_call_history[-1] == tool_call_history[-2]:
                    halt_reason = ExecutionStatus.LOOP_DETECTED
                    halt_detail = f"Loop detected: tool '{tool_name}' invoked repeatedly with identical parameters {args}."
                    break

                # 4. Termination Condition 4: Stall Detection (Post-observation)
                if made_progress:
                    stall_counter = 0
                else:
                    stall_counter += 1
                    if stall_counter >= 3:
                        halt_reason = ExecutionStatus.STALL_DETECTED
                        halt_detail = "Stall detected: agent executed 3 consecutive actions without advancing booking state."
                        break

                # 5. Termination Condition 5: Hard Budget Limits (Evaluated Last)
                if metrics.total_steps >= limits.max_steps:
                    halt_reason = ExecutionStatus.BUDGET_EXCEEDED
                    halt_detail = f"Budget exceeded: reached maximum limit of {limits.max_steps} steps."
                    break
                elapsed = time.time() - start_time
                if elapsed >= limits.max_time_seconds:
                    halt_reason = ExecutionStatus.BUDGET_EXCEEDED
                    halt_detail = f"Budget exceeded: execution duration {elapsed:.2f}s exceeded limit of {limits.max_time_seconds}s."
                    break

            return tool_messages

        # Dispatch based on pattern
        if pattern == AgentPattern.REACT:
            app = build_react_graph(self.model, tool_dispatcher, should_halt=should_halt)
            user_prompt = (
                f"Please book a flight from {request.origin} to {request.destination} "
                f"on {request.departure_date} for {request.passenger_name} "
                f"under {request.max_budget:,.0f} VND with {request.cabin_class} class."
            )
            initial_state = {"messages": [HumanMessage(content=user_prompt)]}
            try:
                final_state = app.invoke(initial_state)
            except Exception as e:
                if halt_reason is None:
                    halt_reason = ExecutionStatus.FAILED
                    halt_detail = str(e)

        elif pattern == AgentPattern.PLAN_THEN_EXECUTE:
            def on_plan(plan):
                trace.append(
                    TraceStep(
                        step_number=0,
                        pattern=pattern.value,
                        thought=f"Plan generated: {len(plan)} sequential steps: " + " -> ".join(p['description'] for p in plan),
                    )
                )

            app = build_plan_execute_graph(
                self.model,
                tool_dispatcher,
                should_halt=should_halt,
                on_plan_created=on_plan,
            )
            initial_state = {
                "request": request,
                "plan": [],
                "current_step_index": 0,
                "step_results": [],
                "last_flight_id": None,
                "last_hold_id": None,
                "completed": False,
            }
            try:
                final_state = app.invoke(initial_state)
            except Exception as e:
                if halt_reason is None:
                    halt_reason = ExecutionStatus.FAILED
                    halt_detail = str(e)

        elif pattern == AgentPattern.HYBRID:
            def on_hybrid_plan(plan, is_replan: bool):
                if is_replan:
                    metrics.replan_count += 1
                    trace.append(
                        TraceStep(
                            step_number=metrics.total_steps,
                            pattern=pattern.value,
                            thought=f"Re-plan triggered (count={metrics.replan_count}): " + " -> ".join(p['description'] for p in plan),
                        )
                    )
                else:
                    trace.append(
                        TraceStep(
                            step_number=0,
                            pattern=pattern.value,
                            thought=f"Initial macro plan created: {len(plan)} tasks: " + " -> ".join(p['description'] for p in plan),
                        )
                    )

            app = build_hybrid_graph(
                self.model,
                tool_dispatcher,
                should_halt=should_halt,
                on_plan_created=on_hybrid_plan,
            )
            initial_state = {
                "request": request,
                "plan": [],
                "current_step_index": 0,
                "step_results": [],
                "last_flight_id": "VN123",
                "last_hold_id": None,
                "failed_flight_ids": [],
                "replan_count": 0,
                "needs_replan": False,
                "replan_reason": None,
                "available_candidates": [],
                "completed": False,
            }
            try:
                final_state = app.invoke(initial_state)
            except Exception as e:
                if halt_reason is None:
                    halt_reason = ExecutionStatus.FAILED
                    halt_detail = str(e)

        # Estimate metrics
        metrics.elapsed_seconds = round(time.time() - start_time, 4)
        metrics.total_tokens = metrics.total_steps * 450 + 200

        # Post-observation: Computational sensor verification if booking confirmed
        if confirmed_booking_id and halt_reason is None:
            sensor_result = verify_booking_completion(self.db, confirmed_booking_id, request)
            if sensor_result.is_valid:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    booking=sensor_result.booking_data,
                    code_verification_passed=True,
                    verification_reason=sensor_result.reason,
                    metrics=metrics,
                    trace=trace,
                )
            else:
                metrics.constraint_violations += 1
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    booking=sensor_result.booking_data,
                    code_verification_passed=False,
                    verification_reason=sensor_result.reason,
                    metrics=metrics,
                    trace=trace,
                )

        # Check if stopped by approval rejection
        for step in trace:
            if step.interception and "REJECTED" in step.interception:
                halt_reason = ExecutionStatus.APPROVAL_REJECTED
                halt_detail = "Human user rejected payment confirmation."
                break

        # Generate Layer 4: 30-Second State Handoff
        current_state_str = "IDLE"
        if confirmed_booking_id:
            current_state_str = f"CONFIRMED({confirmed_booking_id})"
        elif current_hold_id:
            current_state_str = f"HOLD_ACTIVE({current_hold_id})"
        elif inspected_flights:
            current_state_str = f"INSPECTED_FLIGHTS({', '.join(sorted(inspected_flights))})"

        stop_desc = halt_detail or "Loop ended without ticket confirmation."
        status_to_return = halt_reason or ExecutionStatus.FAILED

        handoff = HandoffSummary(
            goal=f"Book flight {request.origin}->{request.destination} on {request.departure_date} for {request.passenger_name}",
            constraints=request.model_dump(),
            current_state=current_state_str,
            attempted_actions=[s.tool_name for s in trace if s.tool_name],
            stop_reason=stop_desc,
            next_recommendations=[
                "Verify flight availability on alternative dates or airports.",
                "Review constraint budget if no flights matched price criteria.",
                "Inspect trace logs to analyze failure mode round.",
            ],
        )

        return ExecutionResult(
            status=status_to_return,
            booking=None,
            code_verification_passed=False,
            verification_reason=stop_desc,
            handoff=handoff,
            metrics=metrics,
            trace=trace,
        )
