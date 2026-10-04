from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import ToolMessage
from flight_agent.models import BookingRequest

class PlanExecuteState(TypedDict):
    request: BookingRequest
    plan: List[Dict[str, Any]]
    current_step_index: int
    step_results: List[Dict[str, Any]]
    last_flight_id: Optional[str]
    last_hold_id: Optional[str]
    completed: bool

def build_plan_execute_graph(
    model: Any,
    tool_executor: Callable[[List[Dict[str, Any]]], List[ToolMessage]],
    should_halt: Optional[Callable[[], bool]] = None,
    on_plan_created: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
):
    """
    Constructs a LangGraph Plan-then-Execute topology:
    START -> planner -> executor -> (has_more_steps?) -> executor ... -> END
    """
    def planner_node(state: PlanExecuteState) -> Dict[str, Any]:
        req = state["request"]
        # Deconstruct into ordered plan
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
                "description": "Inspect seat availability for candidate flight",
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
            on_plan_created(plan)
        return {
            "plan": plan,
            "current_step_index": 0,
            "step_results": [],
            "last_flight_id": None,
            "last_hold_id": None,
            "completed": False,
        }

    def executor_node(state: PlanExecuteState) -> Dict[str, Any]:
        idx = state["current_step_index"]
        plan = state["plan"]
        current_task = plan[idx]

        tool_name = current_task["tool_name"]
        args = current_task["args_generator"](state)

        tool_calls = [
            {
                "name": tool_name,
                "args": args,
                "id": f"pe_call_{idx}_{tool_name}",
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
        }

        # Update contextual state from observations
        if tool_name == "search_flights" and last_out.get("status") == "SUCCESS":
            flights = last_out.get("data", [])
            if flights:
                updates["last_flight_id"] = flights[0]["flight_id"]

        elif tool_name == "hold_booking" and last_out.get("status") == "SUCCESS":
            updates["last_hold_id"] = last_out.get("data", {}).get("hold_id")

        if idx + 1 >= len(plan):
            updates["completed"] = True

        return updates

    def should_continue(state: PlanExecuteState) -> str:
        if should_halt and should_halt():
            return END
        if state["current_step_index"] < len(state["plan"]):
            # Check if last step critically failed
            if state["step_results"]:
                last_res = state["step_results"][-1]
                if last_res.get("status") in ("FAILED", "NOT_FOUND", "REJECTED"):
                    # Plan cannot adaptively continue in pure Plan-then-Execute
                    return END
            return "executor"
        return END

    workflow = StateGraph(PlanExecuteState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_conditional_edges("executor", should_continue, {"executor": "executor", END: END})

    return workflow.compile()
