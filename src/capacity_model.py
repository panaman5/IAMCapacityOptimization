"""First application of the capacity model.

The baseline has two workloads competing for one shared capacity pool:

* stochastic user demand, generated as Poisson arrivals;
* scheduled work, treated as filler and processed with residual capacity.

User demand always has priority. Both workloads carry backlog forward.
This module intentionally uses only the Python standard library so that the
model remains easy to run and inspect.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Iterable, Sequence


@dataclass(frozen=True)
class PeriodResult:
    """One period of the shared-capacity simulation."""

    period: int
    user_arrivals: int
    scheduled_arrivals: int
    user_served: int
    scheduled_served: int
    user_backlog_end: int
    scheduled_backlog_end: int


@dataclass(frozen=True)
class ScenarioResult:
    """Aggregated outcome for one demand scenario."""

    capacity: int
    capacity_cost: float
    user_backlog_cost: float
    scheduled_backlog_cost: float
    total_cost: float
    user_fill_rate: float
    periods: tuple[PeriodResult, ...]


def poisson_sample(rng: random.Random, lam: float) -> int:
    """Draw one Poisson random variable using inverse recurrence.

    This implementation is intended for the small-to-moderate rates used in
    the first experiment. It avoids requiring NumPy or SciPy.
    """

    if lam < 0:
        raise ValueError("lam must be non-negative")
    if lam == 0:
        return 0

    probability = math.exp(-lam)
    cumulative = probability
    target = rng.random()
    value = 0
    while target > cumulative:
        value += 1
        probability *= lam / value
        cumulative += probability
    return value


def poisson_quantile(lam: float, confidence: float) -> int:
    """Return the smallest integer q with P(N <= q) >= confidence."""

    if lam < 0:
        raise ValueError("lam must be non-negative")
    if not 0 < confidence <= 1:
        raise ValueError("confidence must be in (0, 1]")
    if lam == 0:
        return 0

    probability = math.exp(-lam)
    cumulative = probability
    value = 0
    while cumulative < confidence:
        value += 1
        probability *= lam / value
        cumulative += probability
    return value


def simulate_scenario(
    capacity: int,
    user_arrivals: Sequence[int],
    scheduled_arrivals: Sequence[int] | int = 0,
    *,
    capacity_cost_per_unit: float = 1.0,
    user_backlog_cost_per_unit: float = 10.0,
    scheduled_backlog_cost_per_unit: float = 1.0,
) -> ScenarioResult:
    """Simulate one fixed-capacity scenario.

    ``capacity`` is available in every period. User demand is served first;
    scheduled work receives the remaining capacity. A scalar
    ``scheduled_arrivals`` value means the same amount of scheduled work is
    released in every period.
    """

    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    if any(arrivals < 0 for arrivals in user_arrivals):
        raise ValueError("user arrivals must be non-negative")

    horizon = len(user_arrivals)
    if isinstance(scheduled_arrivals, int):
        scheduled_path = [scheduled_arrivals] * horizon
    else:
        scheduled_path = list(scheduled_arrivals)
        if len(scheduled_path) != horizon:
            raise ValueError("scheduled_arrivals must match user_arrivals length")
    if any(arrivals < 0 for arrivals in scheduled_path):
        raise ValueError("scheduled arrivals must be non-negative")

    user_backlog = 0
    scheduled_backlog = 0
    user_work_seen = 0
    user_work_served = 0
    periods: list[PeriodResult] = []

    for period, (new_user, new_scheduled) in enumerate(
        zip(user_arrivals, scheduled_path)
    ):
        user_available = user_backlog + new_user
        user_served = min(capacity, user_available)
        residual_capacity = capacity - user_served

        scheduled_available = scheduled_backlog + new_scheduled
        scheduled_served = min(residual_capacity, scheduled_available)

        user_backlog = user_available - user_served
        scheduled_backlog = scheduled_available - scheduled_served
        user_work_seen += user_available
        user_work_served += user_served

        periods.append(
            PeriodResult(
                period=period,
                user_arrivals=new_user,
                scheduled_arrivals=new_scheduled,
                user_served=user_served,
                scheduled_served=scheduled_served,
                user_backlog_end=user_backlog,
                scheduled_backlog_end=scheduled_backlog,
            )
        )

    user_backlog_cost = user_backlog_cost_per_unit * sum(
        result.user_backlog_end for result in periods
    )
    scheduled_backlog_cost = scheduled_backlog_cost_per_unit * sum(
        result.scheduled_backlog_end for result in periods
    )
    capacity_cost = capacity_cost_per_unit * capacity * horizon
    total_cost = capacity_cost + user_backlog_cost + scheduled_backlog_cost
    fill_rate = user_work_served / user_work_seen if user_work_seen else 1.0

    return ScenarioResult(
        capacity=capacity,
        capacity_cost=capacity_cost,
        user_backlog_cost=user_backlog_cost,
        scheduled_backlog_cost=scheduled_backlog_cost,
        total_cost=total_cost,
        user_fill_rate=fill_rate,
        periods=tuple(periods),
    )


def generate_poisson_scenarios(
    lam: float,
    horizon: int,
    scenarios: int,
    *,
    seed: int = 20260830,
) -> tuple[tuple[int, ...], ...]:
    """Generate reproducible user-demand paths for capacity comparison."""

    if horizon < 0 or scenarios < 1:
        raise ValueError("horizon must be non-negative and scenarios must be positive")
    rng = random.Random(seed)
    return tuple(
        tuple(poisson_sample(rng, lam) for _ in range(horizon))
        for _ in range(scenarios)
    )


def evaluate_capacities(
    capacities: Iterable[int],
    demand_scenarios: Sequence[Sequence[int]],
    scheduled_arrivals: Sequence[int] | int = 0,
    *,
    capacity_cost_per_unit: float = 1.0,
    user_backlog_cost_per_unit: float = 10.0,
    scheduled_backlog_cost_per_unit: float = 1.0,
) -> tuple[ScenarioResult, ...]:
    """Evaluate each capacity on the same scenarios and return mean results."""

    if not demand_scenarios:
        raise ValueError("at least one demand scenario is required")

    results: list[ScenarioResult] = []
    for capacity in capacities:
        scenario_results = [
            simulate_scenario(
                capacity,
                demand,
                scheduled_arrivals,
                capacity_cost_per_unit=capacity_cost_per_unit,
                user_backlog_cost_per_unit=user_backlog_cost_per_unit,
                scheduled_backlog_cost_per_unit=scheduled_backlog_cost_per_unit,
            )
            for demand in demand_scenarios
        ]
        horizon = len(scenario_results[0].periods)
        mean_periods = tuple(
            PeriodResult(
                period=period,
                user_arrivals=round(
                    sum(result.periods[period].user_arrivals for result in scenario_results)
                    / len(scenario_results)
                ),
                scheduled_arrivals=round(
                    sum(
                        result.periods[period].scheduled_arrivals
                        for result in scenario_results
                    )
                    / len(scenario_results)
                ),
                user_served=round(
                    sum(result.periods[period].user_served for result in scenario_results)
                    / len(scenario_results)
                ),
                scheduled_served=round(
                    sum(
                        result.periods[period].scheduled_served
                        for result in scenario_results
                    )
                    / len(scenario_results)
                ),
                user_backlog_end=round(
                    sum(
                        result.periods[period].user_backlog_end
                        for result in scenario_results
                    )
                    / len(scenario_results)
                ),
                scheduled_backlog_end=round(
                    sum(
                        result.periods[period].scheduled_backlog_end
                        for result in scenario_results
                    )
                    / len(scenario_results)
                ),
            )
            for period in range(horizon)
        )
        results.append(
            ScenarioResult(
                capacity=capacity,
                capacity_cost=sum(result.capacity_cost for result in scenario_results)
                / len(scenario_results),
                user_backlog_cost=sum(
                    result.user_backlog_cost for result in scenario_results
                )
                / len(scenario_results),
                scheduled_backlog_cost=sum(
                    result.scheduled_backlog_cost for result in scenario_results
                )
                / len(scenario_results),
                total_cost=sum(result.total_cost for result in scenario_results)
                / len(scenario_results),
                user_fill_rate=sum(result.user_fill_rate for result in scenario_results)
                / len(scenario_results),
                periods=mean_periods,
            )
        )
    return tuple(results)


def choose_capacity(results: Sequence[ScenarioResult]) -> ScenarioResult:
    """Select the capacity with the lowest estimated mean total cost."""

    if not results:
        raise ValueError("at least one capacity result is required")
    return min(results, key=lambda result: (result.total_cost, result.capacity))
