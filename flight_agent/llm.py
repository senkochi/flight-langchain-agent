from __future__ import annotations
import json
import re
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatResult, ChatGeneration

class DeterministicFlightModel(BaseChatModel):
    """
    A deterministic, fully auditable ChatModel implementation conforming to BaseChatModel.
    Emulates an expert flight booking agent adhering to the ReAct loop:
    Reasoning (Thought) -> Action (Tool Call) -> Observation (Tool Output) -> Conclusion.
    Supports edge cases (happy path, sold out recovery, approval rejection, loop traps).
    """

    model_name: str = "deterministic-flight-v1"
    force_loop_trap: bool = False
    force_stall_trap: bool = False

    def _wrap(self, message: AIMessage) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_msg = messages[-1] if messages else None
        
        # 1. Check for intentional test trap modes
        if self.force_loop_trap:
            return self._wrap(
                AIMessage(
                    content="I am searching again for the same route.",
                    tool_calls=[
                        {
                            "name": "search_flights",
                            "args": {"origin": "SGN", "destination": "HAN", "date": "2026-10-15"},
                            "id": f"call_loop_{len(messages)}",
                            "type": "tool_call",
                        }
                    ],
                )
            )

        if self.force_stall_trap:
            stall_step = len(messages) // 2
            stall_actions = [
                ("check_seat_availability", {"flight_id": "VN123"}),
                ("cancel_booking", {"hold_id": "HOLD-UNKNOWN"}),
                ("search_flights", {"origin": "DAD", "destination": "PQC", "date": "2026-10-15"}),
                ("check_seat_availability", {"flight_id": "QH789"}),
            ]
            tool_name, tool_args = stall_actions[stall_step % len(stall_actions)]
            return self._wrap(
                AIMessage(
                    content="Checking around without making progress.",
                    tool_calls=[
                        {
                            "name": tool_name,
                            "args": tool_args,
                            "id": f"call_stall_{stall_step}",
                            "type": "tool_call",
                        }
                    ],
                )
            )

        # 2. Extract constraints from conversation history
        origin = "SGN"
        destination = "HAN"
        date = "2026-10-15"
        passenger = "Nguyen Van A"
        max_budget = 2500000.0

        for msg in messages:
            if isinstance(msg, HumanMessage):
                text = msg.content
                match_route = re.search(r"([A-Z]{3})\s*(?:to|->|đến)\s*([A-Z]{3})", text, re.IGNORECASE)
                if match_route:
                    origin, destination = match_route.group(1).upper(), match_route.group(2).upper()
                match_date = re.search(r"\d{4}-\d{2}-\d{2}", text)
                if match_date:
                    date = match_date.group(0)
                match_name = re.search(r"for\s+([A-Za-z\s]+?)(?:\s+under|\s+with|\s*$)", text, re.IGNORECASE)
                if match_name:
                    passenger = match_name.group(1).strip()
                match_budget = re.search(r"under\s+([\d,.]+)", text, re.IGNORECASE)
                if match_budget:
                    try:
                        max_budget = float(match_budget.group(1).replace(",", ""))
                    except ValueError:
                        pass

        # 3. Handle tool observations
        if isinstance(last_msg, ToolMessage):
            tool_name = last_msg.name
            try:
                content = json.loads(last_msg.content) if isinstance(last_msg.content, str) else last_msg.content
            except Exception:
                content = {}

            status = content.get("status")

            if tool_name == "search_flights":
                flights = content.get("data", [])
                if not flights or status == "NOT_FOUND":
                    return self._wrap(
                        AIMessage(
                            content=f"No suitable flights found for route {origin}->{destination} within budget {max_budget:,.0f} VND. Terminating search."
                        )
                    )
                target_flight = flights[0]["flight_id"]
                return self._wrap(
                    AIMessage(
                        content=f"Thought: Found {len(flights)} flights. Inspecting seat availability for flight {target_flight}.",
                        tool_calls=[
                            {
                                "name": "check_seat_availability",
                                "args": {"flight_id": target_flight},
                                "id": f"call_{len(messages)}",
                                "type": "tool_call",
                            }
                        ],
                    )
                )

            elif tool_name == "check_seat_availability":
                if status == "SUCCESS":
                    flight_id = content["data"]["flight_id"]
                    return self._wrap(
                        AIMessage(
                            content=f"Thought: Flight {flight_id} has available seats. Placing a temporary seat hold for {passenger}.",
                            tool_calls=[
                                {
                                    "name": "hold_booking",
                                    "args": {"flight_id": flight_id, "passenger_name": passenger},
                                    "id": f"call_{len(messages)}",
                                    "type": "tool_call",
                                }
                            ],
                        )
                    )
                else:
                    alt_flight = "QH789"
                    return self._wrap(
                        AIMessage(
                            content=f"Thought: Flight sold out. Checking alternative flight {alt_flight}.",
                            tool_calls=[
                                {
                                    "name": "check_seat_availability",
                                    "args": {"flight_id": alt_flight},
                                    "id": f"call_{len(messages)}",
                                    "type": "tool_call",
                                }
                            ],
                        )
                    )

            elif tool_name == "hold_booking":
                if status == "SUCCESS":
                    hold_id = content["data"]["hold_id"]
                    flight_id = content["data"]["flight_id"]
                    return self._wrap(
                        AIMessage(
                            content=f"Thought: Seat successfully held with {hold_id}. Requesting payment confirmation and ticket issuance.",
                            tool_calls=[
                                {
                                    "name": "confirm_payment_and_issue_ticket",
                                    "args": {
                                        "flight_id": flight_id,
                                        "passenger_name": passenger,
                                        "hold_id": hold_id,
                                    },
                                    "id": f"call_{len(messages)}",
                                    "type": "tool_call",
                                }
                            ],
                        )
                    )
                else:
                    return self._wrap(
                        AIMessage(
                            content=f"Failed to place hold on flight: {content.get('error_code')}."
                        )
                    )

            elif tool_name == "confirm_payment_and_issue_ticket":
                if status == "SUCCESS":
                    booking_id = content["data"]["booking_id"]
                    f_id = content["data"]["flight_id"]
                    return self._wrap(
                        AIMessage(
                            content=f"Success! Booking confirmed with PNR {booking_id} on flight {f_id} for passenger {passenger}."
                        )
                    )
                elif status == "REJECTED":
                    hold_id = None
                    for m in reversed(messages):
                        if isinstance(m, ToolMessage) and m.name == "hold_booking":
                            try:
                                h_data = json.loads(m.content) if isinstance(m.content, str) else m.content
                                hold_id = h_data.get("data", {}).get("hold_id")
                            except Exception:
                                pass
                            break
                    if hold_id:
                        return self._wrap(
                            AIMessage(
                                content="Thought: Payment was rejected by user. Releasing held inventory.",
                                tool_calls=[
                                    {
                                        "name": "cancel_booking",
                                        "args": {"hold_id": hold_id},
                                        "id": f"call_{len(messages)}",
                                        "type": "tool_call",
                                    }
                                ],
                            )
                        )
                    return self._wrap(
                        AIMessage(
                            content="Payment rejected by user. Booking terminated without ticket issuance."
                        )
                    )

            elif tool_name == "cancel_booking":
                return self._wrap(
                    AIMessage(
                        content="Hold successfully cancelled. Booking process stopped as requested."
                    )
                )

        # 4. Initial turn: Search flights
        return self._wrap(
            AIMessage(
                content=f"Thought: Searching for flights from {origin} to {destination} on {date} under {max_budget:,.0f} VND.",
                tool_calls=[
                    {
                        "name": "search_flights",
                        "args": {
                            "origin": origin,
                            "destination": destination,
                            "date": date,
                            "max_price": max_budget,
                        },
                        "id": f"call_{len(messages)}",
                        "type": "tool_call",
                    }
                ],
            )
        )

    @property
    def _llm_type(self) -> str:
        return "deterministic-flight-model"
