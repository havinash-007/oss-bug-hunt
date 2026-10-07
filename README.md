# oss-bug-hunt

Tooling and notes from hunting for real, unreported bugs in open-source Python libraries.

Browsing "good first issue" lists does not work for popular repos: other contributors
claim issues within hours. What does work is running the library and checking it
against ground truth. The scripts in `audits/` do that.

| Script | Target | What it checks |
|---|---|---|
| `audits/distribution_consistency.py` | skpro | mean, var, cdf, energy vs Monte Carlo |
| `audits/metric_reference_check.py` | sktime | forecasting metrics vs reference formulas |
| `audits/splitter_invariants.py` | sktime | window splitter invariants |
| `tools/pr_status.py` | GitHub | status and score of submitted PRs |

First result: [sktime/skpro#1200](https://github.com/sktime/skpro/pull/1200), a fix for a
numerical derivative that was missing a division by the step size.

See `FINDINGS.md` for the log of what was checked and why each lead was kept or dropped.

## Agent workflow

A scout agent vets candidate issues (`agents/scout_prompt.md`), then one worker agent per issue
fixes and submits a PR (`agents/worker_prompt.md`), under the rules in `agents/RULES.md`.
`dashboard/dashboard.html` is the status page, and `SCOREBOARD.md` the latest PR scores.
