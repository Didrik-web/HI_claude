# Project corrections implemented

1. Step 1.2/1.3 switch/tie line references are treated as `Line 6-7`, `Line 11-4`, and `Line 14-8`. These are excluded from the 12 ordinary line-outage contingencies.
2. From Step 2 onwards, S1, S2 and S3 are explicitly CLOSED for **all** analysis: normal time-series load flow, connection-point screening, uncontrolled charging, smart charging validation, marginal-loss calculation and N-1.
3. N-1 outages are temporary. Each tested line is restored before the next contingency.
