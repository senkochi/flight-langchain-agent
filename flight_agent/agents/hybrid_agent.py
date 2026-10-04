from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import ToolMessage
from flight_agent.models import BookingRequest

class HybridAgentState(TypedDict):
    request: BookingRequest
    plan: List[Dict[str, Any]]
    current_step_index: int
    step_results: List[Dict[str, Any]]
    last_flight_id: Optional[str]
    last_hold_id: Optional[str]
    failed_flight_ids: List[str]
    replan_count: int
    needs_replan: bool
    replan_reason: Optional[str]
    available_candidates: List[Dict[str, Any]]
    completed: bool

def build_hybrid_graph(
    model: Any,
    tool_executor: Callable[[List[Dict[str, Any]]], List[ToolMessage]],
    should_halt: Optional[Callable[[], bool]] = None,
    on_plan_created: Optional[Callable[[List[Dict[str, Any]], bool], None]] = None,
):
    """
    Constructs a LangGraph Hybrid (Plan + ReAct with Re-planning) topology:
    START -> planner -> executor -> evaluator -> (needs_replan?) -> replanner -> executor
                                               -> (more_steps?) -> executor ... -> END
    """
    def planner_node(state: HybridAgentState) -> Dict[str, Any]:
        req = state["request"]
        plan = [
            {
                "step": 1,
                "description": f"Search flights for route {req.origin}->{req.destination} on {req.departure_date}",
                "tool_name": "search_flights",
                "args_generator": lambda s: {
                    "origin": req.origin,
                    "destination": req.destination,
                    "date": req.departure_date,
                    "max_price": req.max_budget,
                },
            },
            {
                "step": 2,
                "description": "Inspect seat availability for primary candidate flight",
                "tool_name": "check_seat_availability",
                "args_generator": lambda s: {"flight_id": s["last_flight_id"] or "VN123"},
            },
            {
                "step": 3,
                "description": f"Hold seat on candidate flight for {req.passenger_name}",
                "tool_name": "hold_booking",
                "args_generator": lambda s: {
                    "flight_id": s["last_flight_id"] or "VN123",
                    "passenger_name": req.passenger_name,
                },
            },
            {
                "step": 4,
                "description": f"Confirm payment and issue official ticket for {req.passenger_name}",
                "tool_name": "confirm_payment_and_issue_ticket",
                "args_generator": lambda s: {
                    "flight_id": s["last_flight_id"] or "VN123",
                    "passenger_name": req.passenger_name,
                    "hold_id": s["last_hold_id"],
                },
            },
        ]
        if on_plan_created:
            on_plan_created(plan, False)
        return {
            "plan": plan,
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

    def executor_node(state: HybridAgentState) -> Dict[str, Any]:
        idx = state["current_step_index"]
        plan = state["plan"]
        current_task = plan[idx]

        tool_name = current_task["tool_name"]
        args = current_task["args_generator"](state)

        tool_calls = [
            {
                "name": tool_name,
                "args": args,
                "id": f"hybrid_call_{idx}_{tool_name}",
                "type": "tool_call",
            }
        ]

        tool_messages = tool_executor(tool_calls)
        last_out = {}
        if tool_messages:
            import json
            try:
                last_out = json.loads(tool_messages[0].content)
            except Exception:
                pass

        updates: Dict[str, Any] = {
            "current_step_index": idx + 1,
            "step_results": state["step_results"] + [last_out],
            "needs_replan": False,
        }

        # Update knowledge from observation
        if tool_name == "search_flights" and last_out.get("status") == "SUCCESS":
            flights = last_out.get("data", [])
            updates["available_candidates"] = flights
            if flights:
                updates["last_flight_id"] = flights[0]["flight_id"]

        elif tool_name == "hold_booking" and last_out.get("status") == "SUCCESS":
            updates["last_hold_id"] = last_out.get("data", {}).get("hold_id")

        return updates

    def evaluator_node(state: HybridAgentState) -> Dict[str, Any]:
        """
        Evaluates observation against expectations.
        Detects surprises (e.g. flight sold out) and triggers re-planning.
        """
        if not state["step_results"]:
            return {"needs_replan": False}

        last_res = state["step_results"][-1]
        status = last_res.get("status")

        # Did check_seat_availability or hold fail due to sold-out or shortage?
        if status in ("FAILED", "NOT_FOUND"):
            last_task = state["plan"][state["current_step_index"] - 1] if state["current_step_index"] > 0 else None
            if last_task and last_task["tool_name"] == "search_flights":
                # If search found nothing, there are no flights on this route
                return {"needs_replan": False}

            err = last_res.get("error_code")
            hint = last_res.get("hint")
            new_failed = list(state.get("failed_flight_ids", []))
            if state.get("last_flight_id") and state["last_flight_id"] not in new_failed:
                new_failed.append(state["last_flight_id"])

            return {
                "needs_replan": True,
                "replan_reason": f"Action failed with {err}: {hint}",
                "failed_flight_ids": new_failed,
            }

        return {"needs_replan": False}

    def replanner_node(state: HybridAgentState) -> Dict[str, Any]:
        """
        Adaptive Re-planning:
        Consumes new observation facts, picks an alternative viable flight,
        and regenerates the remaining execution plan.
        """
        req = state["request"]
        replan_num = state["replan_count"] + 1

        failed_ids = set(state.get("failed_flight_ids", []))
        candidates = state.get("available_candidates", [])
        alt_flight_id = None

        # Find first candidate not already failed and within budget
        for c in candidates:
            if c["flight_id"] not in failed_ids and c["price"] <= req.max_budget:
                alt_flight_id = c["flight_id"]
                break

        if not alt_flight_id:
            # No alternative candidate matches constraints
            return {
                "needs_replan": False,
                "plan": [],
                "current_step_index": 0,
                "completed": True,
            }

        revised_plan = [
            {
                "step": 1,
                "description": f"Verify seat availability for alternative flight {alt_flight_id}",
                "tool_name": "check_seat_availability",
                "args_generator": lambda s, fid=alt_flight_id: {"flight_id": fid},
            },
            {
                "step": 2,
                "description": f"Hold seat on alternative flight {alt_flight_id} for {req.passenger_name}",
                "tool_name": "hold_booking",
                "args_generator": lambda s, fid=alt_flight_id: {
                    "flight_id": fid,
                    "passenger_name": req.passenger_name,
                },
            },
            {
                "step": 3,
                "description": f"Confirm payment and issue ticket for alternative flight {alt_flight_id}",
                "tool_name": "confirm_payment_and_issue_ticket",
                "args_generator": lambda s, fid=alt_flight_id: {
                    "flight_id": fid,
                    "passenger_name": req.passenger_name,
                    "hold_id": s["last_hold_id"],
                },
            },
        ]

        if on_plan_created:
            on_plan_created(revised_plan, True)

        return {
            "plan": revised_plan,
            "current_step_index": 0,
            "last_flight_id": alt_flight_id,
            "replan_count": replan_num,
            "needs_replan": False,
        }

    def route_after_evaluator(state: HybridAgentState) -> str:
        if should_halt and should_halt():
            return END
        if state["needs_replan"]:
            return "replanner"
        if state["step_results"]:
            last_res = state["step_results"][-1]
            if last_res.get("status") in ("FAILED", "NOT_FOUND", "REJECTED"):
                return END
        if state["current_step_index"] < len(state["plan"]):
            return "executor"
        return END

    workflow = StateGraph(HybridAgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("replanner", replanner_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "evaluator")
    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {"replanner": "replanner", "executor": "executor", END: END},
    )
    workflow.add_edge("replanner", "executor")

    return workflow.compile()
