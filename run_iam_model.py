"""Run the first realistic hourly IAM capacity experiment."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from capacity_model import poisson_quantile  # noqa: E402
from iam_capacity_model import (  # noqa: E402
    ScheduledJob,
    business_hour_lambda_profile,
    choose_iam_capacity,
    evaluate_iam_capacities,
    generate_hourly_poisson_scenarios,
)


def demo_scheduled_jobs() -> tuple[ScheduledJob, ...]:
    """Return a small, documented prescheduled IAM workload."""

    return (
        ScheduledJob("nightly-reconcile", 0, 5, 12),
        ScheduledJob("directory-sync", 5, 10, 10),
        ScheduledJob("access-review", 8, 14, 14),
        ScheduledJob("policy-refresh", 12, 18, 16),
        ScheduledJob("report-export", 15, 23, 20),
    )


def main() -> None:
    lambda_profile = business_hour_lambda_profile()
    demand_scenarios = generate_hourly_poisson_scenarios(
        lambda_profile,
        scenarios=500,
        seed=20260830,
    )
    jobs = demo_scheduled_jobs()
    results = evaluate_iam_capacities(
        range(0, 25),
        demand_scenarios,
        jobs,
        capacity_cost_per_unit=1.0,
        user_backlog_cost_per_unit=10.0,
        scheduled_backlog_cost_per_unit=1.0,
        deadline_penalty_per_job=25.0,
    )
    selected = choose_iam_capacity(results)

    print("Hourly IAM capacity-model application")
    print("-------------------------------------")
    print("Demand profile: overnight 2, business hours 8, peak hours 14")
    print(f"95% peak-hour user-demand reserve: {poisson_quantile(14.0, 0.95)}")
    print(f"Scheduled jobs: {len(jobs)}")
    print()
    print(
        "capacity | expected cost | user fill | scheduled fill | "
        "deadline misses | scheduled backlog cost"
    )
    for result in results:
        print(
            f"{result.capacity:8d} | {result.total_cost:14.2f} | "
            f"{result.user_fill_rate:9.2%} | "
            f"{result.scheduled_work_fill_rate:15.2%} | "
            f"{result.deadline_misses:15.2f} | "
            f"{result.scheduled_backlog_cost:22.2f}"
        )
    print()
    print(
        f"Selected capacity: {selected.capacity} "
        f"(lowest estimated total cost: {selected.total_cost:.2f})"
    )


if __name__ == "__main__":
    main()
