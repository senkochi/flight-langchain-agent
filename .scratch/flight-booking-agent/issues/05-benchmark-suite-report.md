# 05: Quantitative Benchmark Suite & Comparative Evaluation Report

**What to build:**
A comprehensive quantitative evaluation suite and reporting generator comparing all 3 agent architectures:
- Benchmark runner executing ReAct, Plan-then-Execute, and Hybrid across 5 standardized scenarios:
  1. *Scenario 1: Happy Path* (Direct available flight within budget)
  2. *Scenario 2: Inventory Depleted / Rescheduling* (Preferred flight sold out, requires finding alternative)
  3. *Scenario 3: Human Approval Rejection* (User denies payment at authority seam)
  4. *Scenario 4: Loop / Stall Trap* (Non-existent route / repetitive queries)
  5. *Scenario 5: Budget Ceiling Violation* (Unrealistic low budget constraint)
- Metrics collected per run: Success Rate (%), Step count, Prompt/Completion token usage, Latency (seconds), Constraint adherence rate, Error recovery rate.
- Generation of detailed comparative evaluation report (`report.md`) with Markdown tables, radar/trade-off analysis, and explicit answers to BTVN#3 questions.
- Clean CLI runnable entrypoint `main.py` allowing single-command evaluation and report generation.

**Blocked by:** #5 (04-hybrid-agent-replanning)

**Status:** ready-for-agent

- [ ] Benchmark runner executes all 3 patterns across all 5 test scenarios through the harness seam.
- [ ] Quantitative metrics recorded accurately (success rate, steps, tokens, duration, constraint adherence).
- [ ] Evaluation report `report.md` generated with comparative analysis, pros/cons of each pattern, and failure mode mitigation insights.
- [ ] `main.py` entrypoint runs end-to-end evaluation and prints a formatted summary table.
