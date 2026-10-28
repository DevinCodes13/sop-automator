# Outage Drill: Database Down

**What we did:** Stopped the database on purpose and sent 20 requests to the API, to check that monitoring catches an outage.

**Result:** All 20 requests returned 500, and the Grafana "Server errors (5xx %)" chart spiked.

## Findings
| # | Finding | Impact | Fix |
|---|---------|--------|-----|
| 1 | Unhandled exceptions skipped the metrics middleware | 500 errors were invisible on dashboards | Middleware now counts the error before re-raising |
| 2 | No database connection timeout | Requests hung instead of failing | Added a 3-second `connect_timeout` |
| 3 | Hung requests used up every worker thread | Whole API froze, including `/metrics` | Fixed at the root by finding #2 |
| 4 | API can't start while the database is down | No self-recovery after an outage | Planned for Phase 6: retry the database connection at startup |

## Lesson
Monitoring only works if you test it. One drill found four problems that normal testing never showed.
