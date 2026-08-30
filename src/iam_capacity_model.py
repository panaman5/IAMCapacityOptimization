"""Hourly IAM capacity model with stochastic user demand.

This is the first realistic application layer built on top of the original
capacity baseline. It models:

* an hourly Poisson profile for user-driven demand;
* one shared capacity pool;
* user demand with strict priority;
* scheduled jobs with release times, workloads, and deadlines; and
* earliest-deadline-first dispatch for scheduled work.

The dispatch rule is deliberately fixed. This version optimizes total
capacity, not the ordering of scheduled jobs. That separation keeps the
experiment interpretable and leaves schedule optimization for a later stage.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Sequence

from capacity_model import poisson_sample


@dataclass(frozen=True)
class ScheduledJob:
    """A prescheduled workload item."""

    job_id: str
    release_period: int
    deadline_period: int
    workload: int


@dataclass(frozen=True)
class IAMPeriodResult:
    """Detailed result for one simulated hour."""

    period: int
    capacity: int
    user_arrivals: int
    user_served: int
    scheduled_work_released: int
    scheduled_work_served: int
    user_backlog_end: int
    scheduled_backlog_end: int
    deadline_misses_new: int


@dataclass(frozen=True)
class IAMScenarioResult:
    """Aggregated result for one capacity and one demand path."""

    capacity: int
    capacity_cost: float
    user_backlog_cost: float
    scheduled_backlog_cost: float
    deadline_penalty: float
    total_cost: float
    user_fill_rate: float
    scheduled_work_fill_rate: float
    deadline_misses: int
    completed_scheduled_jobs: int
    periods: tuple[IAMPeriodResult, ...] = ()


def validate_scheduled_jobs(
    scheduled_jobs: Sequence[ScheduledJob],
    horizon: int,
) -> None:
    """Validate the finite-horizon scheduled-job input."""

    if horizon < 0:
        raise ValueError("horizon must be non-negative")

    seen_ids: set[str] = set()
    for job in scheduled_jobs:
        if not job.job_id:
            raise ValueError("job_id must not be empty")
        if job.job_id in seen_ids:
            raise ValueError(f"duplicate job_id: {job.job_id}")
        seen_ids.add(job.job_id)
        if job.workload < 0:
            raise ValueError("job workload must be non-negative")
        if not 0 <= job.release_period < horizon:
            raise ValueError("job release_period must fall inside the horizon")
        if job.deadline_period < job.release_period:
            raise ValueError("job deadline must not precede its release")
        if job.deadline_period >= horizon:
            raise ValueError("job deadline must fall inside the horizon")


def business_hour_lambda_profile(
    horizon: int = 24,
    *,
    overnight_rate: float = 2.0,
    business_rate: float = 8.0,
    peak_rate: float = 14.0,
) -> tuple[float, ...]:
    """Create a simple, documented hourly demand profile.

    Hours 08:00-17:00 use the business rate, with a higher 10:00-13:00 peak.
    All other hours use the overnight rate.
    """

    if horizon < 0:
        raise ValueError("horizon must be non-negative")
    rates: list[float] = []
    for hour in range(horizon):
        hour_of_day = hour % 24
        if 10 <= hour_of_day < 14:
            rates.append(peak_rate)
        elif 8 <= hour_of_day < 18:
            rates.append(business_rate)
        else:
            rates.append(overnight_rate)
    if any(rate < 0 for rate in rates):
        raise ValueError("demand rates must be non-negative")
    return tuple(rates)


def generate_hourly_poisson_scenarios(
    lambda_profile: Sequence[float],
    scenarios: int,
    *,
    seed: int = 20260830,
) -> tuple[tuple[int, ...], ...]:
    """Generate reproducible hourly user-demand paths."""

    if scenarios < 1:
        raise ValueError("scenarios must be positive")
    if any(rate < 0 for rate in lambda_profile):
        raise ValueError("demand rates must be non-negative")

    rng = random.Random(seed)
    return tuple(
        tuple(poisson_sample(rng, rate) for rate in lambda_profile)
        for _ in range(scenarios)
    )


def simulate_iam_scenario(
    capacity: int,
    user_arrivals: Sequence[int],
    scheduled_jobs: Sequence[ScheduledJob],
    *,
    capacity_cost_per_unit: float = 1.0,
    user_backlog_cost_per_unit: float = 10.0,
    scheduled_backlog_cost_per_unit: float = 1.0,
    deadline_penalty_per_job: float = 25.0,
) -> IAMScenarioResult:
    """Simulate one capacity choice for one hourly demand path.

    User demand is served first. Remaining capacity is allocated to released
    scheduled jobs using earliest-deadline-first dispatch. A job can continue
    after its deadline, but it incurs one deadline penalty when it is first
    found incomplete at the end of its deadline period.
    """

    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    if any(arrivals < 0 for arrivals in user_arrivals):
        raise ValueError("user arrivals must be non-negative")

    horizon = len(user_arrivals)
    validate_scheduled_jobs(scheduled_jobs, horizon)

    jobs_by_release: dict[int, list[ScheduledJob]] = {}
    for job in scheduled_jobs:
        jobs_by_release.setdefault(job.release_period, []).append(job)

    remaining = {job.job_id: job.workload for job in scheduled_jobs}
    jobs_by_id = {job.job_id: job for job in scheduled_jobs}
    missed_job_ids: set[str] = set()
    user_backlog = 0
    scheduled_backlog = 0
    user_work_seen = 0
    user_work_served = 0
    scheduled_work_seen = 0
    scheduled_work_served = 0
    periods: list[IAMPeriodResult] = []

    for period, new_user in enumerate(user_arrivals):
        released_jobs = jobs_by_release.get(period, [])
        released_work = sum(job.workload for job in released_jobs)
        scheduled_work_seen += released_work

        user_available = user_backlog + new_user
        user_served = min(capacity, user_available)
        residual_capacity = capacity - user_served

        eligible_jobs = sorted(
            (
                job
                for job in scheduled_jobs
                if job.release_period <= period and remaining[job.job_id] > 0
            ),
            key=lambda job: (job.deadline_period, job.release_period, job.job_id),
        )

        scheduled_served = 0
        for job in eligible_jobs:
            if residual_capacity == 0:
                break
            allocation = min(residual_capacity, remaining[job.job_id])
            remaining[job.job_id] -= allocation
            residual_capacity -= allocation
            scheduled_served += allocation

        user_backlog = user_available - user_served
        scheduled_backlog = sum(
            remaining[job.job_id]
            for job in scheduled_jobs
            if job.release_period <= period
        )

        newly_missed = 0
        for job in scheduled_jobs:
            if (
                job.deadline_period <= period
                and remaining[job.job_id] > 0
                and job.job_id not in missed_job_ids
            ):
                missed_job_ids.add(job.job_id)
                newly_missed += 1

        user_work_seen += user_available
        user_work_served += user_served
        scheduled_work_served += scheduled_served
        periods.append(
            IAMPeriodResult(
                period=period,
                capacity=capacity,
                user_arrivals=new_user,
                user_served=user_served,
                scheduled_work_released=released_work,
                scheduled_work_served=scheduled_served,
                user_backlog_end=user_backlog,
                scheduled_backlog_end=scheduled_backlog,
                deadline_misses_new=newly_missed,
            )
        )

    user_backlog_cost = user_backlog_cost_per_unit * sum(
        result.user_backlog_end for result in periods
    )
    scheduled_backlog_cost = scheduled_backlog_cost_per_unit * sum(
        result.scheduled_backlog_end for result in periods
    )
    capacity_cost = capacity_cost_per_unit * capacity * horizon
    deadline_penalty = deadline_penalty_per_job * len(missed_job_ids)
    total_cost = (
        capacity_cost
        + user_backlog_cost
        + scheduled_backlog_cost
        + deadline_penalty
    )
    completed_jobs = sum(
        remaining[job.job_id] == 0 for job in scheduled_jobs
    )

    return IAMScenarioResult(
        capacity=capacity,
        capacity_cost=capacity_cost,
        user_backlog_cost=user_backlog_cost,
        scheduled_backlog_cost=scheduled_backlog_cost,
        deadline_penalty=deadline_penalty,
        total_cost=total_cost,
        user_fill_rate=user_work_served / user_work_seen
        if user_work_seen
        else 1.0,
        scheduled_work_fill_rate=scheduled_work_served / scheduled_work_seen
        if scheduled_work_seen
        else 1.0,
        deadline_misses=len(missed_job_ids),
        completed_scheduled_jobs=completed_jobs,
        periods=tuple(periods),
    )


def evaluate_iam_capacities(
    capacities: Iterable[int],
    demand_scenarios: Sequence[Sequence[int]],
    scheduled_jobs: Sequence[ScheduledJob],
    *,
    capacity_cost_per_unit: float = 1.0,
    user_backlog_cost_per_unit: float = 10.0,
    scheduled_backlog_cost_per_unit: float = 1.0,
    deadline_penalty_per_job: float = 25.0,
) -> tuple[IAMScenarioResult, ...]:
    """Estimate mean outcomes for each capacity on common scenarios."""

    if not demand_scenarios:
        raise ValueError("at least one demand scenario is required")

    results: list[IAMScenarioResult] = []
    for capacity in capacities:
        scenario_results = [
            simulate_iam_scenario(
                capacity,
                demand,
                scheduled_jobs,
                capacity_cost_per_unit=capacity_cost_per_unit,
                user_backlog_cost_per_unit=user_backlog_cost_per_unit,
                scheduled_backlog_cost_per_unit=scheduled_backlog_cost_per_unit,
                deadline_penalty_per_job=deadline_penalty_per_job,
            )
            for demand in demand_scenarios
        ]
        count = len(scenario_results)
        results.append(
            IAMScenarioResult(
                capacity=capacity,
                capacity_cost=sum(r.capacity_cost for r in scenario_results) / count,
                user_backlog_cost=sum(r.user_backlog_cost for r in scenario_results)
                / count,
                scheduled_backlog_cost=sum(
                    r.scheduled_backlog_cost for r in scenario_results
                )
                / count,
                deadline_penalty=sum(r.deadline_penalty for r in scenario_results)
                / count,
                total_cost=sum(r.total_cost for r in scenario_results) / count,
                user_fill_rate=sum(r.user_fill_rate for r in scenario_results)
                / count,
                scheduled_work_fill_rate=sum(
                    r.scheduled_work_fill_rate for r in scenario_results
                )
                / count,
                deadline_misses=sum(r.deadline_misses for r in scenario_results)
                / count,
                completed_scheduled_jobs=sum(
                    r.completed_scheduled_jobs for r in scenario_results
                )
                / count,
            )
        )
    return tuple(results)


def choose_iam_capacity(
    results: Sequence[IAMScenarioResult],
) -> IAMScenarioResult:
    """Select the capacity with the lowest estimated total cost."""

    if not results:
        raise ValueError("at least one capacity result is required")
    return min(results, key=lambda result: (result.total_cost, result.capacity))
