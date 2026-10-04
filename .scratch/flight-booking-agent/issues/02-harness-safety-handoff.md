# 02: Harness Safety: 5 Termination Conditions & 30-Second State Handoff

**What to build:**
Comprehensive implementation of the 5 termination rules and state handoff system:
- Pre-tool Human Approval check (already intercepted at seam; records decisions).
- Post-observation Goal Achieved verification using computational sensor.
- Post-observation Loop Detection (detects identical tool arguments or cycle of redundant tool calls).
- Post-observation Stall Detection (detects changing tool calls that yield no progress or advance toward the booking goal).
- Budget Cap verification (max steps, max tokens, max elapsed seconds - evaluated strictly last).
- 30-Second State Handoff generator: Whenever execution stops abnormally (budget reached, loop/stall detected, or human approval rejected), compiles a clear handoff context (constraints, current reservation state, attempted actions, stop reason, actionable operator steps).
- End-to-end tests for all edge failure modes.

**Blocked by:** #2 (01-foundation-harness-react)

**Status:** ready-for-agent

- [ ] Termination pipeline evaluates in strict sequence: Pre-tool Approval -> Post-observation Goal -> Loop Detection -> Stall Detection -> Budget Exceeded.
- [ ] Loop detector flags repeated calls with identical parameters or repeated observations.
- [ ] Stall detector flags steps without state progression.
- [ ] Budget cap terminates execution when max_steps, max_tokens, or max_time is reached without masking earlier errors.
- [ ] 30-Second Handoff context packet generated on abnormal stop or human escalation.
- [ ] Automated tests pass for: Loop trap scenario, Stall trap scenario, Human rejection scenario, and Budget limit exceeded scenario.
