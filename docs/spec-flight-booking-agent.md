# SPECIFICATION: Autonomous Flight Booking Agent with LangChain/LangGraph & 4 Harness Layers

## Problem Statement

When building autonomous AI agents for transactional workflows such as flight booking, naive LLM implementations suffer from critical operational vulnerabilities. As identified in the SE373 Agent Fundamentals curriculum, unbounded agent loops frequently succumb to four primary failure modes:
1. **Looping without progress (Lặp không tiến bộ)**: The model repeatedly invokes tools with identical or ineffective arguments when encountering vague errors or unavailable inventory.
2. **Hallucination (Bịa đặt thông tin)**: The model fabricates flight numbers, departure times, booking codes (PNR), or prices instead of sourcing ground truth from flight databases.
3. **Goal drift (Quên yêu cầu ban đầu)**: Long conversational loops or extensive tool observations dilute the context window, causing the model to violate initial constraints such as maximum budget, dates, or passenger counts.
4. **Misinterpreting flawed data (Tin vào dữ liệu sai)**: The model misinterprets empty or ambiguous tool responses (`{}`), claiming successful booking when no reservation occurred.

Furthermore, autonomous agents operating without human oversight risk triggering irreversible side effects (e.g., executing unapproved financial transactions or finalizing incorrect tickets). Lastly, without empirical comparison across reasoning paradigms (ReAct vs. Plan-then-Execute vs. Hybrid), developers lack quantitative rationale for selecting the optimal architecture balance among latency, token cost, robustness, and constraint adherence.

## Solution

An end-to-end Autonomous Flight Booking Agent system built on LangChain and LangGraph, governed by an authoritative **Harness architecture** that enforces strict boundaries between the probabilistic model and deterministic execution logic.

The system features:
1. **The Four Essential Harness Layers**:
   - **Constraints as Data**: User criteria (origin, destination, dates, budget ceiling, passenger details, cabin class) are modeled as immutable structured data schemas (Pydantic), anchored in the execution state to eliminate goal drift.
   - **Objective Completion Verification (Code-based Computational Sensor)**: Deterministic Python code validates completion criteria (verifying active PNR, confirmed database record, exact passenger matching, and budget compliance) rather than trusting self-declarations from the model.
   - **Authority Control (Human Approval Seam)**: A pre-execution interception barrier halts execution before sensitive side-effect tools (`confirm_payment_and_issue_ticket`) and requests human approval with formatted booking summaries.
   - **30-Second State Handoff**: On termination—whether normal, approval-blocked, budget-capped, or aborted due to loop/stall detection—the harness compiles a structured handoff document detailing current progress, tried alternatives, failure diagnostics, and recommended next actions.
2. **Five Deterministic Termination Conditions**:
   - Human Approval required (evaluated pre-tool).
   - Goal Achieved verified by computational sensor (evaluated post-observation).
   - Loop Detection (evaluated post-observation).
   - Stall Detection (evaluated post-observation).
   - Hard Budget Exceeded (max steps, max tokens, max elapsed seconds—evaluated last).
3. **Three Reasoning Pattern Implementations**:
   - **ReAct (Reasoning + Acting)**: Continuous dynamic loop of Thought -> Tool Execution -> Observation.
   - **Plan-then-Execute**: Explicit pre-planning phase generating an ordered step plan, followed by sequential step execution.
   - **Hybrid (Plan + ReAct with Re-planning)**: Macro planning decomposed into sub-goals, executed via adaptive micro-steps, with automatic trigger-based re-planning whenever observation surprises or booking conflicts occur.
4. **Mock Tool Suite with Resilient Feedback**:
   - Realistic mock flight database and operations (`search_flights`, `check_seat_availability`, `hold_booking`, `confirm_payment_and_issue_ticket`, `cancel_booking`).
   - Standardized structured responses (`status`, `data`, `error_code`, `hint`) explicitly engineered to provide corrective guidance to the model.
5. **Comprehensive Quantitative Evaluation Suite**:
   - A multi-scenario benchmark evaluating all three patterns across Happy Path, Flight Sold-Out / Rescheduling, Human Approval Rejection/Approval, Loop/Stall Traps, and Strict Constraint Violations.
   - Comparative metrics covering Success Rate, Step Count, Token Usage, Latency, Constraint Adherence, and Error Recovery.

## User Stories

1. As a traveler, I want to input my flight requirements (origin, destination, date, maximum budget, passenger count), so that the agent can find and book appropriate options without manual searching.
2. As a system administrator, I want user requirements to be validated and stored as immutable structured data, so that the agent's reasoning loop cannot lose or mutate original constraints over multi-turn execution.
3. As a developer, I want mock flight tools that return structured JSON responses with explicit `status`, `data`, `error_code`, and corrective `hint`, so that the agent never misinterprets empty results or loops blindly.
4. As a flight searcher, I want the agent to search for available flights between specified airports on specific dates, so that I can see viable departure times, airlines, and prices.
5. As a traveler, I want the agent to check actual seat availability for a selected flight, so that bookings are only attempted on flights with open inventory.
6. As a customer, I want the agent to temporarily hold a seat before initiating payment, so that inventory is secured while booking details are being verified.
7. As a traveler, I want the agent to respect my maximum price budget, so that it never attempts to reserve or book an over-budget ticket.
8. As a compliance officer, I want sensitive financial transactions (ticket issuance and payment) to be gated by an Authority Control layer, so that the agent cannot spend money without explicit human authorization.
9. As an approver, I want to receive an approval request containing complete flight details, passenger name, and total cost, so that I can make an informed approve/reject decision in under 30 seconds.
10. As a traveler, if I reject an approval request, I want the agent to cancel the temporary seat hold and gracefully hand off the session rather than forcing an unauthorized purchase.
11. As a system operator, I want the agent's task completion to be verified by a deterministic code-based sensor rather than model self-affirmation, so that tickets are never marked booked without a confirmed record in the database.
12. As a system operator, I want the code-based sensor to verify that the final booked ticket matches all initial data constraints (origin, destination, date, passenger name, price limit), so that hallucinated or mis-booked tickets fail verification.
13. As a platform engineer, I want the harness to detect identical tool invocations and duplicate observations (Loop Detection), so that the agent aborts promptly instead of burning tokens in infinite loops.
14. As a platform engineer, I want the harness to detect lack of progress across consecutive steps even if different tools are called (Stall Detection), so that bumbling behavior is arrested early.
15. As a finance officer, I want hard budget caps on maximum iterations, total token consumption, and runtime execution seconds, so that defective queries never incur unbounded API expenses.
16. As a developer, I want budget checks to be evaluated as the final termination rule, so that specific logical failures (loop, stall, constraint mismatch) are not masked as generic out-of-budget errors.
17. As an on-call human operator, I want any abnormal termination or approval pause to produce a structured 30-Second Handoff summary, so that I can review current state, tried actions, and remaining tasks in under half a minute.
18. As an AI engineer, I want a ReAct flight booking agent that interleaves thought, action, and observation, so that the agent can dynamically adapt to unexpected search outcomes on the fly.
19. As an AI engineer, I want a Plan-then-Execute flight booking agent that generates a transparent plan before executing sequential steps, so that the complete booking strategy is visible and auditable prior to execution.
20. As an AI engineer, I want a Hybrid agent that creates an initial plan, executes steps, and dynamically triggers re-planning when an observation contradicts expectations (e.g., flight sold out), so that it combines structural clarity with runtime resilience.
21. As a tester, I want to run all three agent patterns through a single, uniform testing seam, so that benchmark comparisons are completely fair and unpolluted by differing interfaces.
22. As an evaluator, I want a benchmark test suite covering 5 distinct scenarios (Happy Path, Sold-Out Recovery, Human Approval Rejection, Loop Trap, Budget Constraint), so that agents are tested across realistic edge cases.
23. As a researcher, I want to record and compare execution metrics (success rate, step count, input/output tokens, execution latency, error recovery rate) across all three patterns, so that architectural trade-offs can be objectively analyzed.
24. As a developer debugging an agent run, I want a full chronological trace containing thoughts, tool inputs, structured tool outputs, and harness decisions, so that I can quickly pinpoint the exact failure round.
25. As a student/author, I want the implementation packaged in a clean, self-contained Python script alongside a comprehensive evaluation report, so that the assignment can be run, reproduced, and graded effortlessly.

## Implementation Decisions

1. **Single Testing Seam at the Highest Level**:
   - The entire system exposes exactly one external seam: `FlightBookingHarness.run(agent_pattern, booking_request, approval_callback) -> ExecutionResult`.
   - All tests, benchmarks, and CLI callers interact exclusively through this seam.
   - Internal mechanics (LangGraph state transitions, tool execution hooks, termination evaluators) are completely private behind this seam.

   *Type shape for the seam*:
   ```python
   class FlightBookingHarness:
       def run(
           self,
           pattern: AgentPattern, # "react" | "plan_then_execute" | "hybrid"
           request: BookingRequest,
           approval_callback: Optional[Callable[[ApprovalRequest], ApprovalDecision]] = None,
           limits: ExecutionBudget = ExecutionBudget(max_steps=12, max_tokens=15000, max_time_seconds=60),
       ) -> ExecutionResult:
           ...
   ```

2. **Constraints as Structured Data**:
   - User inputs are converted into an immutable `BookingRequest` Pydantic model containing:
     - `passenger_name`: str
     - `origin`: str (IATA code)
     - `destination`: str (IATA code)
     - `departure_date`: str (YYYY-MM-DD)
     - `max_budget`: float
     - `cabin_class`: str ("ECONOMY" | "BUSINESS")
   - This object is stored in the harness context and passed to verification sensors; prompt text references this data but cannot mutate it.

3. **Deterministic Completion Sensor (Code-Based)**:
   - A dedicated Python function `verify_booking_completion(db, booking_id, request) -> VerificationResult` acts as the objective computational sensor.
   - It performs direct database lookups on the mock flight database to confirm:
     - Record exists with status `CONFIRMED`.
     - `flight.origin == request.origin` and `flight.destination == request.destination`.
     - `flight.departure_date == request.departure_date`.
     - `ticket.passenger_name == request.passenger_name`.
     - `ticket.total_price <= request.max_budget`.
   - The agent's subjective declaration ("I have booked your flight") is ignored unless verified by this sensor.

4. **Authority Control Hook (Human-in-the-Loop)**:
   - The tool `confirm_payment_and_issue_ticket` is flagged as `REQUIRES_APPROVAL`.
   - When any agent pattern generates a tool call to this method, the harness intercepts before tool execution:
     - Suspends execution and constructs an `ApprovalRequest(tool_name, flight_details, price, passenger)`.
     - Invokes the `approval_callback`.
     - If approved: executes the tool and injects the success observation.
     - If rejected: skips tool execution, injects a structured rejection observation (`status="REJECTED", hint="User rejected payment. Cancel hold or find alternatives."`), and logs the intervention.

5. **5-Stage Termination Pipeline**:
   - Order of execution is strictly enforced:
     1. Pre-tool: `check_human_approval()` -> triggers approval hook if required.
     2. Post-observation: `check_goal_achieved()` -> runs computational sensor.
     3. Post-observation: `check_loop_detected()` -> hash tool calls and compare window of last $N$ calls.
     4. Post-observation: `check_stall_detected()` -> detect repeated empty results or oscillation without progress.
     5. End-of-turn: `check_budget_exceeded()` -> checks steps, token counts, and wall-clock duration.

6. **Structured Mock Tool Protocol**:
   - All mock tools return a uniform dictionary schema:
     ```python
     {
         "status": "SUCCESS" | "FAILED" | "REJECTED" | "NOT_FOUND",
         "data": Any,
         "error_code": Optional[str],
         "hint": Optional[str] # Direct actionable advice to prevent failure modes 01 & 04
     }
     ```
   - Eliminates empty dictionary returns and guides the model toward recovery paths.

7. **Three Architectural Agent Implementations in LangGraph**:
   - **Pattern 1: ReAct**: Single-graph loop containing `agent` (LLM reasoning with bind_tools) -> conditional edge -> `tools` node -> loop back to `agent` until termination condition or final text.
   - **Pattern 2: Plan-then-Execute**: Dual-phase architecture:
     - Planner node produces a structured step sequence (`PydanticPlan`).
     - Executor node steps through each plan item, invoking specialized tools.
     - Graph finishes once all planned steps execute or a step triggers a critical stop.
   - **Pattern 3: Hybrid (Plan + ReAct with Re-planning)**:
     - Planner generates milestone plan.
     - ReAct sub-loop executes tasks with tool awareness.
     - An Evaluator/Monitor node inspects each observation: if an action fails (e.g., flight sold out) or tool yields unexpected state, state routes to Re-planner node to synthesize revised steps based on current findings.

8. **Standardized 30-Second Handoff Artifact**:
   - If execution terminates without reaching the goal, or pauses for human attention, the harness outputs `HandoffSummary`:
     - Goal summary and original constraints.
     - Current state (e.g., `HOLD_ACTIVE`, flight ID, seat held).
     - Attempted actions (chronological list of tools called and outcomes).
     - Failure / Pause Reason (e.g., `BUDGET_EXCEEDED`, `LOOP_DETECTED`, `APPROVAL_PENDING`).
     - Immediate action items for the human operator.

## Testing Decisions

1. **What Makes a Good Test**:
   - Tests exercise only external behavior through `FlightBookingHarness.run(...)`.
   - Tests never inspect internal LangGraph node states, private agent memories, or intermediary LLM prompt strings.
   - Tests assert purely on `ExecutionResult`: final status, verified booking data, handoff payload completeness, and termination reason.

2. **Modules Tested via the Seam**:
   - All 4 Harness layers (Data Constraints, Code Sensor, Authority Hook, Handoff generation).
   - All 5 Termination conditions (Goal Achieved, Human Approval, Loop, Stall, Budget).
   - All 3 Agent Patterns (ReAct, Plan-then-Execute, Hybrid) across identical test fixtures.
   - The Evaluation and Benchmark suite.

3. **Core Test Scenarios (The 5 Benchmark Test Cases)**:
   - **Scenario 1: Happy Path**: Direct flight available within budget; requires human approval; upon approval, verifies valid booking and code sensor passes.
   - **Scenario 2: Inventory Depleted (Adaptive Recovery)**: Primary flight is sold out; ReAct and Hybrid patterns must detect sold-out status, read hint, search alternative flights, hold, and request approval; Plan-then-Execute highlights replanning vulnerability unless adapted.
   - **Scenario 3: Human Approval Rejection**: User denies payment; harness verifies that ticket is not issued, hold is safely released, and clean handoff is returned.
   - **Scenario 4: Loop / Stall Trap**: Querying a non-existent route; agent repeatedly tries invalid queries; harness intercepts via Loop/Stall detection before token exhaustion.
   - **Scenario 5: Budget Ceiling Exceeded**: User specifies an unrealistically low budget; agent correctly identifies that no flights meet constraints and halts gracefully without booking over-budget tickets.

## Out of Scope

- Connecting to live commercial Global Distribution Systems (Sabre, Amadeus) or real airline REST APIs.
- Real credit card payment gateway integrations (Stripe, PayPal).
- Production multi-tenant database systems and persistent session management.
- Web frontend UI or mobile interface development (the system is delivered as Python modules, automated test suite, CLI evaluation harness, and markdown report).

## Further Notes

- System requirements adhere directly to the SE373 Assignment 3 guidelines:
  1. Complete harness layer implementation.
  2. 3 Agent design patterns (ReAct, Plan-then-Execute, Hybrid).
  3. Quantitative evaluation and comparison report.
- Deliverables will include:
  - `main.py` / executable script containing harness, mock environment, agents, and runner.
  - `report.md` detailing the comparative evaluation results with quantitative tables and architectural analysis.
