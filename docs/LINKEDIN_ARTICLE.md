# From demand forecasts to capacity decisions

I have been thinking about a simple operational problem that appears in many
systems: work arrives, capacity is limited, and not every type of work can be
treated in the same way.

In an IAM operations queue, for example, user-driven requests may arrive at
any time, while other jobs are already scheduled: synchronizations, reviews,
exports, reconciliations, or policy updates. The system has to protect the
user-facing work while still making useful progress on the scheduled work.

That led me to a question that is easy to state but less easy to answer well:

> How much capacity should the system keep available when future user demand
> is uncertain?

A forecast alone does not answer that question. We also need to consider the
cost of capacity, the cost of waiting work, service expectations, and the
deadlines attached to scheduled jobs.

## The first prototype

I built a small, reproducible model around one shared hourly capacity pool.

- User demand is generated stochastically with an hourly Poisson profile.
- User demand is served first.
- Scheduled jobs receive the capacity that remains.
- Unfinished work carries forward as backlog.
- Candidate capacity levels are compared by estimated total cost.

The current scheduled-job rule is deliberately simple: eligible jobs are
processed in earliest-deadline-first order. The model is therefore not trying
to solve every scheduling problem yet. It is establishing a transparent
baseline for the capacity decision.

## What I am trying to learn

The important output is not a single magic capacity number. The useful output
is the trade-off:

- more capacity reduces user backlog and missed deadlines;
- less capacity costs less to operate; and
- the best decision depends on how those consequences are valued.

With the current illustrative assumptions, the simulation selects an hourly
capacity of 17. That number is not a recommendation for a real IAM system. It
is a reproducible result from a synthetic benchmark that makes the decision
logic visible.

## Why share this now?

This is not a new mathematical theory, and I am not presenting it as one. I am
sharing it as the first step in a broader exploration of decision intelligence:
how probabilistic models, optimization, simulation, machine learning, and
human judgment can work together around an operational decision.

The project is intentionally open and understandable. The repository includes
the model code, an interactive notebook, tests, a mathematical specification,
and the assumptions behind the experiment.

The next step is to replace the fixed scheduled-job rule with an explicit
prescheduled allocation decision. After that, the same decision can be
compared with simpler rules, forecasting models, and hybrid approaches under
the same evaluation conditions.

For now, the project is a small public prototype with a practical question at
its center:

> What is the value of adding more structure to a capacity decision under
> uncertainty?

The code and notebook are available here: **[add GitHub repository link]**
