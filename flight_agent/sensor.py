from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel
from flight_agent.models import BookingRequest

class VerificationResult(BaseModel):
    is_valid: bool
    reason: str
    booking_data: Optional[Dict[str, Any]] = None

def verify_booking_completion(
    db: Any,
    booking_id: str,
    request: BookingRequest,
) -> VerificationResult:
    """
    Layer 2: Objective Completion Sensor (Computational Sensor).
    Runs deterministic Python logic to verify that the booking is real,
    confirmed, and matches all immutable data constraints without relying
    on probabilistic model self-declarations.
    """
    booking = db.get_booking(booking_id)
    if not booking:
        return VerificationResult(
            is_valid=False,
            reason=f"Booking ID '{booking_id}' does not exist in flight database.",
        )

    if booking["status"] != "CONFIRMED":
        return VerificationResult(
            is_valid=False,
            reason=f"Booking '{booking_id}' status is '{booking['status']}', expected 'CONFIRMED'.",
            booking_data=booking,
        )

    # Constraint cross-verification
    if booking["passenger_name"] != request.passenger_name:
        return VerificationResult(
            is_valid=False,
            reason=f"Passenger mismatch: booked '{booking['passenger_name']}', expected '{request.passenger_name}'.",
            booking_data=booking,
        )

    if booking["origin"] != request.origin or booking["destination"] != request.destination:
        return VerificationResult(
            is_valid=False,
            reason=f"Route mismatch: booked {booking['origin']}->{booking['destination']}, expected {request.origin}->{request.destination}.",
            booking_data=booking,
        )

    if booking["departure_date"] != request.departure_date:
        return VerificationResult(
            is_valid=False,
            reason=f"Date mismatch: booked {booking['departure_date']}, expected {request.departure_date}.",
            booking_data=booking,
        )

    if booking["price"] > request.max_budget:
        return VerificationResult(
            is_valid=False,
            reason=f"Budget violation: booked price {booking['price']:,.0f} VND exceeds budget {request.max_budget:,.0f} VND.",
            booking_data=booking,
        )

    return VerificationResult(
        is_valid=True,
        reason="Booking successfully verified: confirmed, correct passenger, route, date, and under budget.",
        booking_data=booking,
    )
