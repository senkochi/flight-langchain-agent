from __future__ import annotations
import uuid
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

class MockFlightDatabase:
    """In-memory flight and booking repository."""

    def __init__(self):
        self.flights: Dict[str, Dict[str, Any]] = {
            "VN123": {
                "flight_id": "VN123",
                "airline": "Vietnam Airlines",
                "origin": "SGN",
                "destination": "HAN",
                "departure_date": "2026-10-15",
                "departure_time": "08:00",
                "price": 1950000.0,
                "available_seats": 5,
                "cabin_class": "ECONOMY",
            },
            "VJ456": {
                "flight_id": "VJ456",
                "airline": "Vietjet Air",
                "origin": "SGN",
                "destination": "HAN",
                "departure_date": "2026-10-15",
                "departure_time": "12:00",
                "price": 1800000.0,
                "available_seats": 0,  # Sold out for adaptive scenario
                "cabin_class": "ECONOMY",
            },
            "QH789": {
                "flight_id": "QH789",
                "airline": "Bamboo Airways",
                "origin": "SGN",
                "destination": "HAN",
                "departure_date": "2026-10-15",
                "departure_time": "16:00",
                "price": 2200000.0,
                "available_seats": 4,
                "cabin_class": "ECONOMY",
            },
            "VN999": {
                "flight_id": "VN999",
                "airline": "Vietnam Airlines",
                "origin": "SGN",
                "destination": "HAN",
                "departure_date": "2026-10-15",
                "departure_time": "20:00",
                "price": 4500000.0,
                "available_seats": 2,
                "cabin_class": "BUSINESS",
            },
            "VN202": {
                "flight_id": "VN202",
                "airline": "Vietnam Airlines",
                "origin": "HAN",
                "destination": "DAD",
                "departure_date": "2026-10-20",
                "departure_time": "09:30",
                "price": 1500000.0,
                "available_seats": 8,
                "cabin_class": "ECONOMY",
            },
        }
        self.bookings: Dict[str, Dict[str, Any]] = {}
        self.holds: Dict[str, Dict[str, Any]] = {}

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        return self.bookings.get(booking_id)

    def search_flights(
        self,
        origin: str,
        destination: str,
        date: str,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        matched = []
        for f in self.flights.values():
            if f["origin"].upper() == origin.upper() and f["destination"].upper() == destination.upper():
                if f["departure_date"] == date:
                    if max_price is None or f["price"] <= max_price:
                        matched.append(f)

        if not matched:
            return {
                "status": "NOT_FOUND",
                "data": [],
                "error_code": "NO_MATCHING_FLIGHTS",
                "hint": f"No flights found for route {origin}->{destination} on {date}. Try widening date or budget criteria.",
            }

        return {
            "status": "SUCCESS",
            "data": matched,
            "error_code": None,
            "hint": f"Found {len(matched)} matching flights. Next: check seat availability for desired flight.",
        }

    def check_seat_availability(self, flight_id: str) -> Dict[str, Any]:
        flight = self.flights.get(flight_id)
        if not flight:
            return {
                "status": "NOT_FOUND",
                "data": None,
                "error_code": "FLIGHT_NOT_FOUND",
                "hint": f"Flight {flight_id} does not exist. Call search_flights to see valid flight IDs.",
            }

        seats = flight["available_seats"]
        if seats <= 0:
            return {
                "status": "FAILED",
                "data": {"flight_id": flight_id, "available_seats": 0},
                "error_code": "FLIGHT_SOLD_OUT",
                "hint": f"Flight {flight_id} has 0 seats remaining. Select an alternative flight from search results.",
            }

        return {
            "status": "SUCCESS",
            "data": {
                "flight_id": flight_id,
                "airline": flight["airline"],
                "origin": flight["origin"],
                "destination": flight["destination"],
                "departure_time": flight["departure_time"],
                "price": flight["price"],
                "available_seats": seats,
                "cabin_class": flight["cabin_class"],
            },
            "error_code": None,
            "hint": f"Flight {flight_id} has {seats} seats available. Proceed to hold_booking before purchasing.",
        }

    def hold_booking(self, flight_id: str, passenger_name: str) -> Dict[str, Any]:
        flight = self.flights.get(flight_id)
        if not flight:
            return {
                "status": "NOT_FOUND",
                "data": None,
                "error_code": "FLIGHT_NOT_FOUND",
                "hint": f"Flight {flight_id} does not exist.",
            }

        if flight["available_seats"] <= 0:
            return {
                "status": "FAILED",
                "data": None,
                "error_code": "INSUFFICIENT_SEATS",
                "hint": f"Cannot hold flight {flight_id} as it is sold out.",
            }

        # Deduct temporary seat
        flight["available_seats"] -= 1
        hold_id = f"HOLD-{uuid.uuid4().hex[:6].upper()}"
        hold_record = {
            "hold_id": hold_id,
            "flight_id": flight_id,
            "passenger_name": passenger_name,
            "price": flight["price"],
            "status": "HELD",
        }
        self.holds[hold_id] = hold_record

        return {
            "status": "SUCCESS",
            "data": hold_record,
            "error_code": None,
            "hint": f"Seat held under {hold_id}. Human approval is REQUIRED before calling confirm_payment_and_issue_ticket.",
        }

    def confirm_payment_and_issue_ticket(
        self,
        flight_id: str,
        passenger_name: str,
        hold_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        flight = self.flights.get(flight_id)
        if not flight:
            return {
                "status": "NOT_FOUND",
                "data": None,
                "error_code": "FLIGHT_NOT_FOUND",
                "hint": "Flight not found.",
            }

        # If hold was used, resolve hold
        if hold_id and hold_id in self.holds:
            self.holds[hold_id]["status"] = "CONVERTED"
        elif flight["available_seats"] > 0:
            flight["available_seats"] -= 1
        else:
            return {
                "status": "FAILED",
                "data": None,
                "error_code": "SEATS_UNAVAILABLE",
                "hint": "No seat held and inventory is empty.",
            }

        booking_id = f"PNR-{uuid.uuid4().hex[:6].upper()}"
        booking = {
            "booking_id": booking_id,
            "flight_id": flight_id,
            "passenger_name": passenger_name,
            "origin": flight["origin"],
            "destination": flight["destination"],
            "departure_date": flight["departure_date"],
            "departure_time": flight["departure_time"],
            "price": flight["price"],
            "cabin_class": flight["cabin_class"],
            "status": "CONFIRMED",
        }
        self.bookings[booking_id] = booking

        return {
            "status": "SUCCESS",
            "data": booking,
            "error_code": None,
            "hint": f"Ticket confirmed with PNR {booking_id}. Booking is complete.",
        }

    def cancel_booking(self, hold_id: str) -> Dict[str, Any]:
        if hold_id in self.holds:
            hold = self.holds[hold_id]
            if hold["status"] == "HELD":
                flight_id = hold["flight_id"]
                if flight_id in self.flights:
                    self.flights[flight_id]["available_seats"] += 1
                hold["status"] = "CANCELLED"
                return {
                    "status": "SUCCESS",
                    "data": {"hold_id": hold_id, "status": "CANCELLED"},
                    "error_code": None,
                    "hint": "Hold cancelled and seat released.",
                }

        return {
            "status": "NOT_FOUND",
            "data": None,
            "error_code": "HOLD_NOT_FOUND",
            "hint": "Invalid or expired hold_id.",
        }


def create_flight_tools(db: MockFlightDatabase):
    """Creates LangChain tool callables bound to a given database instance."""

    @tool
    def search_flights(origin: str, destination: str, date: str, max_price: Optional[float] = None) -> Dict[str, Any]:
        """Search available flights between origin and destination on a given date (YYYY-MM-DD)."""
        return db.search_flights(origin, destination, date, max_price)

    @tool
    def check_seat_availability(flight_id: str) -> Dict[str, Any]:
        """Check available seats, fare, and departure time for a flight ID."""
        return db.check_seat_availability(flight_id)

    @tool
    def hold_booking(flight_id: str, passenger_name: str) -> Dict[str, Any]:
        """Hold a seat temporarily for a passenger. Call this before requesting payment confirmation."""
        return db.hold_booking(flight_id, passenger_name)

    @tool
    def confirm_payment_and_issue_ticket(flight_id: str, passenger_name: str, hold_id: Optional[str] = None) -> Dict[str, Any]:
        """Confirm payment and issue official flight ticket (PNR). SENSITIVE: Requires human approval."""
        return db.confirm_payment_and_issue_ticket(flight_id, passenger_name, hold_id)

    @tool
    def cancel_booking(hold_id: str) -> Dict[str, Any]:
        """Cancel a temporary seat hold and release inventory back to the flight."""
        return db.cancel_booking(hold_id)

    return [
        search_flights,
        check_seat_availability,
        hold_booking,
        confirm_payment_and_issue_ticket,
        cancel_booking,
    ]
