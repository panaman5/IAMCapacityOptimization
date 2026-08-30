import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from iam_capacity_model import (  # noqa: E402
    ScheduledJob,
    business_hour_lambda_profile,
    generate_hourly_poisson_scenarios,
    simulate_iam_scenario,
)


class IAMCapacityModelTests(unittest.TestCase):
    def test_user_demand_has_priority_over_scheduled_work(self):
        result = simulate_iam_scenario(
            capacity=5,
            user_arrivals=[7],
            scheduled_jobs=[
                ScheduledJob("job-a", release_period=0, deadline_period=0, workload=4)
            ],
        )

        period = result.periods[0]
        self.assertEqual(period.user_served, 5)
        self.assertEqual(period.user_backlog_end, 2)
        self.assertEqual(period.scheduled_work_served, 0)
        self.assertEqual(period.scheduled_backlog_end, 4)

    def test_earliest_deadline_first_dispatch(self):
        result = simulate_iam_scenario(
            capacity=4,
            user_arrivals=[0, 0],
            scheduled_jobs=[
                ScheduledJob("late", 0, 1, 3),
                ScheduledJob("early", 0, 0, 3),
            ],
        )

        self.assertEqual(result.periods[0].scheduled_work_served, 4)
        self.assertEqual(result.deadline_misses, 0)
        self.assertEqual(result.completed_scheduled_jobs, 2)

    def test_deadline_miss_is_counted_once(self):
        result = simulate_iam_scenario(
            capacity=0,
            user_arrivals=[0, 0],
            scheduled_jobs=[
                ScheduledJob("job-a", release_period=0, deadline_period=0, workload=1)
            ],
        )

        self.assertEqual(result.deadline_misses, 1)
        self.assertEqual(result.deadline_penalty, 25.0)

    def test_hourly_scenarios_are_reproducible(self):
        profile = business_hour_lambda_profile()
        first = generate_hourly_poisson_scenarios(profile, 4, seed=7)
        second = generate_hourly_poisson_scenarios(profile, 4, seed=7)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(len(first[0]), 24)


if __name__ == "__main__":
    unittest.main()
