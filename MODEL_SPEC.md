# Capacity Model — Mathematical Specification

**Status:** Initial specification  
**Version:** 0.1  
**Scope:** Discrete-time capacity planning under uncertain demand

## 1. Purpose

This document specifies a small capacity-planning model for Project Optimus. The model is intended to be understandable, reproducible, and extensible. Its purpose is not to claim that one probabilistic model is universally superior to a neural or language model. Its purpose is to establish a decision problem in which alternative predictive and decision approaches can be compared fairly.

The central research question is:

> In which capacity decisions does an explicit model of objectives, constraints, uncertainty, and system dynamics add measurable value beyond simpler rules or a predictive model alone?

## 2. Decision definition

The decision-maker chooses a capacity level $c$ before observing future demand. Capacity may represent workers, machines, service slots, compute resources, or another repeatable operational resource.

Let:

- $t = 0, 1, \ldots, T-1$ index discrete planning periods;
- $N_t$ be new demand arriving during period $t$;
- $B_t$ be backlog at the beginning of period $t$;
- $c_t$ be capacity available during period $t$;
- $S_t$ be work completed during period $t$;
- $D_t$ be unmet demand remaining after service; and
- $a_t$ be the capacity action selected by the decision-maker.

For the initial stationary model, capacity is constant:

$$
c_t = c, \qquad c \in \mathcal{C}
$$

where $\mathcal{C}$ is a finite feasible set, for example $\{0,1,\ldots,c_{\max}\}$.

## 3. State transition

The initial model assumes that one unit of capacity can process one unit of work during a period. Total work available at the beginning of period $t$ is $B_t + N_t$. Therefore:

$$
S_t = \min(B_t + N_t, c)
$$

and the next-period backlog is:

$$
B_{t+1} = B_t + N_t - S_t
$$

Equivalently:

$$
B_{t+1} = \max(0, B_t + N_t - c)
$$

with initial condition $B_0 \geq 0$. If a period's arrivals are served immediately whenever capacity is available, the same transition can be written as a reflected workload recursion.

The cumulative unmet work over a horizon is:

$$
U_T(c) = \sum_{t=0}^{T-1} B_{t+1}
$$

This quantity is a simple proxy for delay exposure. A later version may replace it with customer-level waiting time or an explicit service-time model.

## 4. Demand uncertainty

Demand is represented by the random sequence:

$$
N_0, N_1, \ldots, N_{T-1}
$$

The first implementation should support two sources:

1. **Empirical demand:** resampling or replaying observed period-level counts.
2. **Synthetic demand:** generating counts from a documented data-generating process.

For empirical demand, the estimated probability of observing $n$ arrivals is:

$$
\widehat{P}(N=n) = \frac{\left|\{t : N_t=n\}\right|}{T}
$$

Here $\left|\{t : N_t=n\}\right|$ denotes the number of observed periods in which the demand equals $n$. This empirical distribution is a baseline, not evidence that demand is independent or identically distributed.

For a candidate Poisson model:

$$
N_t \sim \operatorname{Poisson}(\lambda)
$$

where $\lambda$ is the expected demand per period. This assumption must be tested against the data and compared with the empirical alternative. Seasonality, bursts, serial dependence, regime changes, and common shocks may make a stationary Poisson model inappropriate.

If demand varies with context $X_t$, a conditional model may instead estimate:

$$
P(N_t \mid X_t)
$$

The predictive model may be statistical, machine-learning-based, or neural. The decision layer should consume its predictive distribution or scenarios rather than treating a point forecast as certainty.

### Initial implementation choice

The first implementation will use a theoretical Poisson demand generator rather than waiting for real operational data. This is a synthetic, controlled experiment. It is intended to test the mechanics of the model, not to make a claim about any particular business system.

The initial demand assumptions are:

- arrivals are independent across periods;
- the average arrival rate is stable;
- demand variance equals its mean; and
- there is no seasonality, burstiness, or regime change.

The parameter $\lambda$ is treated as a controlled input for the experiment. We will evaluate several values of $\lambda$, rather than relying on one arbitrary scenario. Real data is not required to understand the first model, but it is required before making claims about real-world performance.

The implementation should keep the demand generator separate from the rest of the decision system:

$$
\text{demand generator} \rightarrow \text{backlog dynamics} \rightarrow \text{cost function} \rightarrow \text{capacity decision}
$$

Later, the theoretical generator can be replaced or compared with an empirical generator while keeping the backlog, cost, and decision components unchanged. This makes the Poisson version a baseline against which richer demand models can be tested.

## 5. First application: shared capacity with scheduled filler work

The first application extends the single-workload recursion to the IAM-style
case discussed with the model: one shared capacity pool serves stochastic user
demand first, and scheduled work receives whatever capacity remains.

Let:

- $U_t$ be new user-demand arrivals during period $t$;
- $A^S_t$ be scheduled work released during period $t$;
- $B^U_t$ be user-demand backlog at the beginning of period $t$; and
- $B^S_t$ be scheduled-work backlog at the beginning of period $t$.

For a fixed capacity $c$, user demand is served first:

$$
S^U_t = \min(B^U_t + U_t, c)
$$

The residual capacity is:

$$
R_t = c - S^U_t
$$

Scheduled work uses that residual capacity:

$$
S^S_t = \min(B^S_t + A^S_t, R_t)
$$

The two backlogs then evolve as:

$$
B^U_{t+1} = B^U_t + U_t - S^U_t
$$

$$
B^S_{t+1} = B^S_t + A^S_t - S^S_t
$$

The first application deliberately treats scheduled work as a filler. It does
not yet decide which scheduled job runs, and it does not use job importance,
deadlines, dependencies, or sequencing. Its purpose is to answer a narrower
question first:

> Given a fixed capacity and stochastic user demand, how much capacity remains
> for scheduled work, and what backlog and cost does that create?

The implementation evaluates a candidate set of capacities against the same
Poisson demand scenarios. This makes the comparison fair: capacity choices see
the same possible demand paths, and the selected capacity is the one with the
lowest estimated mean total cost.

The baseline cost is:

$$
J(c) = C_{\text{capacity}}(c)
      + k_U \sum_{t=0}^{T-1} B^U_{t+1}
      + k_S \sum_{t=0}^{T-1} B^S_{t+1}
$$

where $k_U$ penalizes user-demand backlog and $k_S$ penalizes scheduled-work
backlog. User backlog receives the larger default penalty because user demand
is protected. These weights are experimental inputs, not universal monetary
truths.

The runnable implementation is in `src/capacity_model.py`, with a small entry
point in `run_baseline.py`. It uses only the Python standard library and
generates reproducible synthetic scenarios.

## 6. Realistic IAM application

The second application makes the baseline closer to an IAM operations queue
without changing the central decision question. Time is measured in hourly
periods, user demand has an hourly rate profile, and scheduled work consists
of known jobs with workloads and deadlines.

For user-driven demand:

$$
U_t \sim \operatorname{Poisson}(\lambda_t)
$$

The hourly rate $\lambda_t$ is low overnight, higher during business hours,
and highest during a defined peak window. The rate profile is synthetic and is
explicitly reported with each experiment.

Each scheduled job $j$ is described by:

- release period $r_j$;
- deadline period $d_j$; and
- workload $w_j$.

For total hourly capacity $c$, user work is served first:

$$
S^U_t = \min(B^U_t + U_t, c)
$$

Residual capacity is:

$$
R_t = c - S^U_t
$$

Scheduled work is selected from released jobs using an earliest-deadline-first
dispatch rule. If $S^S_t$ is scheduled work processed during period $t$:

$$
B^U_{t+1} = B^U_t + U_t - S^U_t
$$

$$
B^S_{t+1} = B^S_t + A^S_t - S^S_t
$$

where $A^S_t$ is the workload released by scheduled jobs during period $t$.
Jobs may finish after their deadline, but each job receives one deadline
penalty when it is first observed to be incomplete at the end of its deadline
period.

The realistic application estimates the same total-capacity decision as the
baseline:

$$
\widehat{J}(c)
= \frac{1}{R}\sum_{r=1}^{R}
\left[
C_{\text{capacity}}(c)
+ k_U \sum_t B^{U,(r)}_{t+1}
+ k_S \sum_t B^{S,(r)}_{t+1}
+ k_D M^{(r)}
\right]
$$

where $M^{(r)}$ is the number of scheduled jobs that miss their deadlines in
scenario $r$. The objective reports user fill rate, scheduled-work fill rate,
scheduled backlog, deadline misses, and completed scheduled jobs.

This version does not optimize the scheduled-job order. Earliest-deadline-first
is a fixed dispatch baseline. The next optimization layer can decide which
eligible scheduled jobs to process under residual capacity.

## 7. Cost function

The baseline total cost for a capacity choice $c$ and realized demand path is:

$$
C(c; N_{0:T-1}) = C_{\text{capacity}}(c) + \sum_{t=0}^{T-1} \left( C_{\text{backlog}}(B_{t+1}) + C_{\text{service}}(S_t) \right)
$$

The first version may use:

$$
C_{\text{capacity}}(c) = k_c c
$$

and:

$$
C_{\text{backlog}}(B_{t+1}) = k_b B_{t+1}
$$

where $k_c \geq 0$ is the cost per unit of capacity and $k_b \geq 0$ is the cost per unit of period-end backlog.

If backlog costs are nonlinear, a penalty function can be used:

$$
C_{\text{backlog}}(B) = k_b B + k_q \max(0, B-b_0)^2
$$

where $b_0$ is a tolerated backlog threshold and $k_q$ penalizes severe overload.

The exact monetary interpretation of each coefficient must be documented. If credible monetary values are not available, the experiment should report normalized costs and sensitivity over a range of weights.

## 8. Objective and constraints

The risk-neutral single-period or finite-horizon decision is:

$$
c^* = \arg\min_{c \in \mathcal{C}} \mathbb{E}\left[C(c; N_{0:T-1})\right]
$$

For simulation, the expectation is approximated with $R$ demand scenarios:

$$
\widehat{J}(c) = \frac{1}{R}\sum_{r=1}^{R} C\left(c; N_{0:T-1}^{(r)}\right)
$$

and:

$$
\hat{c}^* = \arg\min_{c \in \mathcal{C}} \widehat{J}(c)
$$

Capacity may also be selected subject to service requirements:

$$
\min_{c \in \mathcal{C}} \mathbb{E}[C(c;N)]
$$

subject to:

$$
P\left(B_{t+1} > b_{\max}\right) \leq \alpha
$$

and:

$$
P\left(\text{SLA violation}\mid c\right) \leq \alpha_{\text{SLA}}
$$

with optional budget constraint:

$$
C_{\text{capacity}}(c) \leq K
$$

Here $b_{\max}$ is a tolerated backlog threshold, $\alpha$ is the allowed violation probability, and $K$ is the available capacity budget.

## 9. Service-level definitions

The specification must state which service-level definition is used. Candidate definitions include:

- fraction of demand served within the same period;
- fraction of periods with zero backlog;
- fraction of demand completed within a specified number of periods; and
- probability that backlog exceeds a threshold.

For the initial model, same-period service attainment is:

$$
\operatorname{FillRate}(c) = \frac{\sum_{t=0}^{T-1} S_t}{\sum_{t=0}^{T-1}(B_t+N_t)}
$$

This metric should not be confused with a customer-level SLA. It is a workload-level approximation until individual arrival and completion timestamps are modeled.

## 10. Baselines and competing models

Every advanced model must be evaluated against the same scenarios, costs, constraints, and decision horizon.

### 10.1 Rule baseline

A simple policy may choose capacity using a demand quantile:

$$
c_{q} = \inf\{c : P(N \leq c) \geq q\}
$$

This is useful as a transparent operational heuristic.

### 10.2 Empirical model

Use the empirical distribution of demand and optimize the expected cost directly. No parametric arrival assumption is required.

### 10.3 Parametric stochastic model

Fit a candidate distribution such as Poisson, negative binomial, or another justified family. Compare goodness of fit, calibration, tail behavior, and realized decision cost.

### 10.4 Dynamic or queueing model

If demand, service times, or state persistence matter, introduce a richer state and compare the resulting model with the simpler recursion. A queueing approximation such as $M/M/c$ is a later hypothesis, not a default requirement.

### 10.5 ML or foundation-model predictor

Use structured and contextual data to estimate future demand or outcomes. The predictor should be evaluated on held-out periods and then passed to the same decision objective where possible.

### 10.6 Hybrid model

The hybrid system may combine semantic extraction, statistical or ML prediction, simulation, and explicit optimization:

$$
\text{evidence} \rightarrow \text{prediction} \rightarrow \text{uncertainty} \rightarrow \text{optimization} \rightarrow \text{recommendation}
$$

An LLM may help interpret documents, extract context, explain trade-offs, or orchestrate scenarios. It should not be assumed to replace the objective, constraints, simulator, or solver when those components provide measurable value.

## 11. Evaluation protocol

### 11.1 Experimental split

Where historical data exists, use chronological separation:

- training or calibration periods;
- validation periods for model selection; and
- a final evaluation period that remains untouched until comparison.

For synthetic data, generate independent scenario sets for development and evaluation using the same documented data-generating process. Add stress scenarios with deliberately changed assumptions.

### 11.2 Common evaluation conditions

All systems should receive the information available at decision time. The following must be held constant across models:

- decision horizon;
- feasible capacity choices;
- cost coefficients;
- service-level definitions;
- scenario seeds or evaluation paths where appropriate; and
- intervention and override rules.

### 11.3 Primary outcomes

Report mean realized cost with uncertainty:

$$
\overline{C}_M = \frac{1}{R}\sum_{r=1}^{R} C_M^{(r)}
$$

Also report quantiles, tail cost, service-level attainment, utilization, backlog, and compute or operational burden.

Regret for model $M$ on scenario $r$ is:

$$
\operatorname{Regret}_M^{(r)} = C_M^{(r)} - \min_{c \in \mathcal{C}} C\left(c;N_{0:T-1}^{(r)}\right)
$$

Average regret is:

$$
\overline{\operatorname{Regret}}_M = \frac{1}{R}\sum_{r=1}^{R}\operatorname{Regret}_M^{(r)}
$$

The preferred model is the one that produces the best decision outcomes under the stated operating conditions, subject to acceptable reliability and interpretability.

## 12. Sensitivity and stress testing

At minimum, vary:

- mean and variance of demand;
- demand burstiness and serial correlation;
- capacity cost $k_c$;
- backlog cost $k_b$;
- service-level target;
- planning horizon $T$;
- initial backlog $B_0$; and
- the presence of demand regime changes.

The model should identify when the recommended capacity changes and which assumptions drive the change. A recommendation that is optimal only under one narrow parameter setting should be labeled fragile.

## 13. Assumptions and known limitations

The initial recursion assumes:

- discrete and equally spaced time periods;
- one unit of capacity processes one unit of work per period;
- capacity is known during the evaluated period;
- backlog is carried forward rather than discarded;
- all work is initially treated as homogeneous;
- the objective can be represented by an explicit cost function; and
- the chosen demand scenarios are representative of the decision horizon.

These assumptions are simplifications. They are valuable only if they are sufficiently accurate for the decision being made. They may fail when the system includes heterogeneous jobs, priorities, abandonment, setup times, shift constraints, multi-stage service, correlated failures, or strategic capacity lead times.

## 14. Extension roadmap

Possible extensions, in increasing order of complexity, are:

1. time-varying capacity $c_t$;
2. time-varying or seasonal demand;
3. heterogeneous service times;
4. priority classes and separate SLAs;
5. capacity activation and staffing constraints;
6. empirical Monte Carlo simulation;
7. queueing approximations;
8. Markov or state-space models;
9. stochastic or robust optimization;
10. contextual ML forecasting;
11. sequential decisions and MDP formulations; and
12. hybrid agent, simulation, and optimization workflows.

For a sequential policy $\pi$, a general finite-horizon objective can be written as:

$$
\pi^* = \arg\min_{\pi} \mathbb{E}\left[\sum_{t=0}^{T-1} \gamma^t C(s_t,a_t)\right]
$$

where $s_t$ is the system state, $a_t$ is the action, and $\gamma$ is an optional discount factor. This formulation should be introduced only when decisions genuinely depend on evolving state and future consequences.

## 15. Falsifiable hypotheses

The project should record hypotheses before running experiments. Initial examples are:

1. An empirical demand model will outperform a misspecified stationary parametric model under regime changes.
2. Explicit backlog costs will produce better capacity choices than a demand-forecast-only rule.
3. A richer model will improve realized decision utility only when its additional assumptions are supported by data.
4. A hybrid predictor-plus-optimization system will outperform a predictor or LLM-only recommendation on constrained capacity decisions.
5. Under simple, well-specified demand, the added complexity of a hybrid system will not justify its operational cost.

The fifth hypothesis is important. The project is successful even if it shows that a simpler model is the better choice.

## 16. Reproducibility requirements

Each experiment should record:

- dataset or generator version;
- random seeds;
- time granularity and horizon;
- capacity action set;
- initial state;
- cost and constraint parameters;
- model version and configuration;
- evaluation scenarios;
- software environment; and
- the decision made from the result.

Results should include the assumptions required to reproduce them, not only the final chart or selected capacity.

## 17. Decision criterion

The project does not have a preferred model family. The final selection rule is:

$$
M^* = \arg\min_M \left\{\text{realized decision cost}_M\right\}
$$

subject to reliability, service, interpretability, and operational constraints.

The intended outcome is better decisions under uncertainty. Probability, stochastic processes, Markov chains, queueing theory, optimization, simulation, machine learning, and language models are tools that may contribute to that outcome. None is an objective by itself.
