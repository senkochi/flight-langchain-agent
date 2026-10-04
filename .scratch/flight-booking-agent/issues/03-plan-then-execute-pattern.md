# 03: Plan-then-Execute Agent Architecture

**What to build:**
The second reasoning architecture specified in the requirements:
- A LangGraph workflow implementing Plan-then-Execute.
- **Planner Node**: Synthesizes an explicit, ordered plan (`BookingPlan` containing step descriptions and targeted tools) based on the user's `BookingRequest`.
- **Executor Node**: Takes the generated plan and executes tasks step-by-step using the mock tools and harness controls.
- Integrated into the existing single seam: `FlightBookingHarness.run(pattern="plan_then_execute", ...)`.
- Transparent execution: Plan is exposed in trace before any tools run.
- Automated tests verifying planned execution for standard booking and handling of plan interruptions.

**Blocked by:** #2 (01-foundation-harness-react)

**Status:** ready-for-agent

- [ ] Planner node outputs structured `BookingPlan` (sequence of action items with parameters).
- [ ] Executor node executes planned tasks sequentially, dispatching to mock tools through the harness interceptor.
- [ ] Accessible via `FlightBookingHarness.run(pattern="plan_then_execute", ...)`.
- [ ] Plan and step execution history captured in the result trace.
- [ ] Automated tests pass for happy path execution with Plan-then-Execute pattern.
