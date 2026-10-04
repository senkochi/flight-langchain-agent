# 04: Hybrid Agent Architecture with Dynamic Re-planning

**What to build:**
The third reasoning architecture specified in the requirements (Hybrid: Plan + ReAct with adaptive re-planning):
- A LangGraph workflow integrating Macro Planning with Micro ReAct execution.
- **Initial Planner**: Decomposes the booking goal into milestone tasks.
- **Adaptive Execution Loop**: Executes steps with tool-calling capabilities.
- **Evaluator / Monitor Node**: Evaluates observation results after tool calls. If an unexpected condition occurs (e.g., flight sold out, flight exceeds budget, or hold failed), triggers the **Re-planner Node** to generate a revised sub-plan incorporating the newly observed facts.
- Integrated into the existing single seam: `FlightBookingHarness.run(pattern="hybrid", ...)`.
- Automated tests verifying autonomous recovery when primary flight is sold out and alternative flight must be found and booked.

**Blocked by:** #3 (02-harness-safety-handoff), #4 (03-plan-then-execute-pattern)

**Status:** ready-for-agent

- [ ] Hybrid LangGraph topology with Planner, Executor, Evaluator, and Re-planner nodes.
- [ ] Evaluator detects observation anomalies and routes dynamically to Re-planner rather than halting or looping.
- [ ] Re-planner generates adjusted tasks based on current environment state.
- [ ] Accessible via `FlightBookingHarness.run(pattern="hybrid", ...)`.
- [ ] Automated tests pass for sold-out flight scenario where Hybrid pattern successfully re-plans and completes an alternative booking.
