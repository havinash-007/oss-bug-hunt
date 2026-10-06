# Findings log

## Submitted
- **sktime/skpro#1200**: `_approx_derivative` never divided by the step size, so the
  cdf-derived `pdf` was too small by a factor of 1e-7. Issue #1199.
- **Kludex/starlette#3643**: `URL(scope=...)` treated a leading `//` path as an
  authority when the scope had no host, which allowed an open redirect. Closes #3579.

## Checked and dropped
| Lead | Reason |
|---|---|
| sktime bugs (47 open) | every real one already had a PR or claim |
| GMAE returns 0.0 | real, three PRs already open |
| make_mock_estimator on Python 3.14 | reported same day, fix PR open |
| imbalanced-learn, torchmetrics, xarray, statsmodels, dask | PRs or claims everywhere |
| pr-agent, doorstop, rai-toolkit good-first-issues | PRs already open |
| humanize, tabulate, click, jinja, more-itertools | suites pass on Python 3.14 |

## Lessons
- Popular repos lose easy issues within hours. Look for bugs by running code.
- Check the repo's AI policy first; several projects ban or restrict AI contributions.
