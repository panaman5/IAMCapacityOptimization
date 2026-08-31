# Next phase: realistic IAM capacity optimization and AI

This document is the handoff for the next development phase. The goal is to
turn the current transparent prototype into a more realistic IAM operations
decision model and prepare a meaningful follow-up public post in about one
month.

## Why this problem matters

IAM systems contain many operational processes. Some work is scheduled in
advance, while user-driven requests arrive at uncertain times. When both types
of work share people or infrastructure, demand variability can create
contention, growing queues, delays, complaints, missed expectations, and cost.

The central decision is:

> How should an IAM operations system allocate limited capacity when user
> demand is uncertain and scheduled work is known in advance?

## Current baseline

The repository currently contains a reproducible synthetic benchmark with:

- hourly Poisson user demand;
- one shared hourly capacity pool;
- strict priority for user demand;
- scheduled jobs with release times, workloads, and deadlines;
- earliest-deadline-first dispatch for scheduled work;
- backlog and deadline penalties; and
- capacity selection by estimated total cost across common scenarios.

The current result is a prototype, not a production recommendation or a claim
of new mathematical theory. Its purpose is to make the basic trade-offs
visible before adding more structure.

## Target realistic model

The next version should represent a multi-class IAM operations queue more
faithfully.

### Demand

- time-varying hourly and daily patterns;
- different user-request operation types;
- bursts and overdispersion rather than assuming Poisson automatically;
- a documented choice between Poisson, Negative Binomial, or another arrival
  model based on diagnostics.

### Work items

Each work item may need:

- operation type;
- estimated workload or processing time;
- source or request class;
- priority or service class;
- release time;
- deadline or SLA target;
- dependency or precedence relationships;
- retry, failure, cancellation, or completion state.

### Capacity and queue behavior

The model should make explicit whether capacity is:

- fixed or variable by hour;
- measured in requests, work units, or processing minutes;
- preemptive or non-preemptive;
- shared across all work or separated into protected pools.

User-facing work remains protected. Scheduled work receives residual capacity,
subject to its constraints.

## Mathematical direction

The model should evolve in stages:

1. A richer discrete-time, multi-class queue or event-based simulator.
2. A workload-aware scheduled-job allocation model.
3. A constrained stochastic optimization model, with capacity as a decision
   and scheduled-job allocation as recourse.
4. Optional chance constraints or CVaR to control user-SLA and deadline risk.
5. Comparison against the current EDF rule and simpler heuristics.

The model should not become more complex unless the added structure improves a
decision metric or represents a real operational constraint.

## Where AI should be used

AI should support the mathematical decision layer rather than replace it.

Good candidates are:

- forecasting hourly user demand;
- estimating workload or processing duration;
- classifying operation type and service risk;
- detecting unusual demand bursts;
- extracting structured fields from operational logs; and
- explaining the final recommendation in plain language.

The intended architecture is:

> AI predicts and estimates; mathematical optimization decides; simulation
> validates.

The comparison should include at least:

- a simple rule baseline;
- the current stochastic prototype;
- a richer optimization model;
- an AI-assisted forecast plus optimizer; and
- a hybrid variant only if it adds measurable value.

## Evaluation requirements

All approaches must use the same scenarios or held-out periods. Compare:

- total cost;
- user service level and fill rate;
- scheduled-job completion and deadline misses;
- backlog and waiting time;
- capacity utilization;
- worst-case or tail risk; and
- sensitivity to cost weights and demand regimes.

Prediction accuracy alone is not enough. A model is useful only if it improves
the operational decision under comparable conditions.

## One-month execution plan

### Week 1: model contract

Define the system boundary, event schema, units of work, capacity meaning,
service rules, known variables, decision variables, constraints, and success
metrics. Document which assumptions remain synthetic.

### Week 2: realistic simulator

Add operation classes, workload variability, time-varying demand, and explicit
deadline/SLA behavior. Validate the simulator with small hand-checkable cases.

### Week 3: optimization and AI component

Replace or extend EDF with constrained scheduled-job allocation. Add one AI
component, preferably demand or workload estimation, and compare it with a
transparent statistical baseline.

### Week 4: evaluation and communication

Run the common evaluation, sensitivity analysis, and stress tests. Update the
README and notebook, document limitations, and prepare the next public post
around what changed and what was learned.

## Guardrails

- Do not present synthetic results as production IAM evidence.
- Do not describe the project as new theory unless a genuine contribution is
  established.
- Do not use an LLM as an unconstrained scheduler.
- Do not add advanced mathematics only for appearance.
- Keep the implementation reproducible and understandable.

## First task in the next chat

Start by reviewing this file and writing the one-page model contract. Do not
begin with AI implementation. First decide what the realistic IAM system is,
what is known at decision time, what is uncertain, what can be controlled, and
what outcome the optimizer is responsible for improving.
