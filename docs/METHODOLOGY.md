# Methodology

## Estimand

The primary estimand is the average treatment effect on treated regions after the policy begins. The model is:

`outcome_rt = region_r + month_t + ATT × treated_r × post_t + error_rt`

Region fixed effects absorb time-invariant regional differences. Month fixed effects absorb shocks common to all regions. Standard errors are clustered by region because observations within a region may be correlated over time.

## Identification checklist

1. Treatment timing is defined before inspecting outcomes.
2. Comparison regions are not exposed to the policy or meaningful spillovers.
3. Treated and comparison outcomes would have evolved in parallel without treatment.
4. No other treated-only policy begins at the same time.
5. The composition and measurement of the outcome remain stable.

## Diagnostics included

- Differential pre-period slope test.
- Dynamic event-study coefficients relative to month -1.
- Pre-policy placebo timing test.
- Balanced-panel and duplicate-key checks.
- Region-clustered 95% confidence intervals.

## Production extensions

For a real Medicaid, labor, or local-policy study, add covariate balance, staggered-adoption estimators when timing varies, alternative comparison pools, leave-one-region-out sensitivity, policy anticipation windows, and a documented missing-data strategy.
