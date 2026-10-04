# Data dictionary

| Field | Type | Grain | Definition |
|---|---|---|---|
| `region` | string | Region-month | Stable geographic or market identifier |
| `month` | integer/date | Region-month | Ordered analysis period |
| `treated` | binary | Region | Whether the region belongs to the treatment group |
| `post` | binary | Region-month | Whether the observation is after policy implementation |
| `outcome` | numeric | Region-month | Measured outcome used in the causal estimand |

The demo data are synthetic and seeded. They demonstrate the workflow and must not be interpreted as an estimate for a real policy.
