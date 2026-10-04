# 01: Tracer Bullet: Foundation Harness & ReAct Flight Booking (Happy Path)

**What to build:**
A functioning end-to-end flight booking flow using the ReAct reasoning pattern with core harness protections:
- User requirements ingested as immutable structured data (`BookingRequest`), eliminating goal drift.
- Standardized mock flight database and tools (`search_flights`, `check_seat_availability`, `hold_booking`, `confirm_payment_and_issue_ticket`, `cancel_booking`) returning actionable `{status, data, error_code, hint}` JSON.
- Deterministic Python completion sensor (`verify_booking_completion`) directly verifying database records against constraints without relying on model assertions.
- Pre-tool Authority Control interception hook for sensitive actions (`confirm_payment_and_issue_ticket`) that requires explicit human approval.
- The unified external seam `FlightBookingHarness.run(pattern="react", ...)` orchestrating a LangGraph ReAct agent loop.
- Complete happy path automated test verifying the entire reservation flow from inquiry to verified booking.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `BookingRequest` Pydantic model validates and freezes origin, destination, date, max budget, cabin class, and passenger info.
- [ ] Mock tools return structured JSON containing `status`, `data`, `error_code`, and `hint`.
- [ ] `confirm_payment_and_issue_ticket` triggers the pre-tool authority hook and awaits human approval before executing.
- [ ] Objective completion sensor verifies that a booking exists in the database with status `CONFIRMED`, correct flight ID, date, passenger name, and total cost within budget.
- [ ] External seam `FlightBookingHarness.run` executes the LangGraph ReAct pattern and returns an `ExecutionResult`.
- [ ] Happy path test passes: Agent searches, checks seats, holds booking, requests approval, receives approval, completes booking, and passes code sensor verification.
