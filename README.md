# Capacity allocation for an IAM operations queue

![Illustration of shared capacity allocation in an IAM operations queue](docs/hero-illustration.png)

A small, reproducible project about a practical question:

> How much hourly capacity should an IAM operations system keep available when user demand is uncertain and scheduled work is known in advance?

The project is a transparent decision-intelligence prototype. It is not a
production system and it does not claim a new mathematical theory.

## Idea Framework

We model one shared capacity pool:

1. user-driven work arrives unpredictably;
2. user work is protected and served first;
3. scheduled jobs use the remaining capacity; and
4. unfinished work carries forward and creates cost.

The experiment compares candidate capacity levels and chooses the one with the
lowest estimated total cost. The current IAM version uses hourly Poisson demand
and scheduled jobs with workloads, release times, and deadlines.

## Quick start

From this directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-notebook.txt
.venv/bin/python run_iam_model.py
```

To explore the assumptions interactively, open
[02_hourly_iam_experiment.ipynb](notebooks/02_hourly_iam_experiment.ipynb) and
select the `Python (capacity-model)` kernel.

## What the model measures

- expected total cost;
- user-demand fill rate;
- scheduled-work fill rate;
- backlog carried between hours; and
- missed scheduled-job deadlines.

The current example is synthetic, so its numbers demonstrate the mechanics of
the decision rather than describing a real IAM deployment.

## Repository map

- [02_hourly_iam_experiment.ipynb](notebooks/02_hourly_iam_experiment.ipynb) - the main interactive walkthrough.
- [run_iam_model.py](run_iam_model.py) - command-line version of the experiment.
- [src/iam_capacity_model.py](src/iam_capacity_model.py) - reusable simulation and capacity-selection logic.
- [tests/test_iam_capacity_model.py](tests/test_iam_capacity_model.py) - behavior and reproducibility tests.
- [MODEL_SPEC.md](MODEL_SPEC.md) - detailed assumptions and equations.
- [MODEL_SPEC.tex](MODEL_SPEC.tex) - LaTeX source for the detailed specification.
- [iam-capacity-brief.tex](docs/iam-capacity-brief.tex) - LaTeX source for the two-page public explainer PDF.
- [PUBLICATION_OUTLINE.md](PUBLICATION_OUTLINE.md) - longer-term research framing.

## Current status

This is the first realistic application layer. It fixes the scheduled-job
dispatch rule to earliest-deadline-first and optimizes the total hourly
capacity. The next meaningful extension is to optimize which scheduled jobs
receive residual capacity, while continuing to protect user demand.

## Why I am building it

A demand forecast is not, by itself, an operational decision. A useful
capacity decision must connect uncertainty, service expectations, backlog, and
cost. This repository is a public, understandable place to test that idea one
layer at a time.
