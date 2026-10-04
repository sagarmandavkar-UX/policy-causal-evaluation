"""Difference-in-differences case study with fixed effects and clustered errors."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm


def make_demo_panel(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    regions, periods = 24, 36
    rows = []
    region_effect = rng.normal(0, 2.5, regions)
    for region in range(regions):
        treated = int(region < regions // 2)
        for month in range(periods):
            post = int(month >= 20)
            seasonal = 1.6 * np.sin(2 * np.pi * month / 12)
            outcome = (
                22 + region_effect[region] + 0.10 * month + seasonal
                - 3.2 * treated * post + rng.normal(0, 1.4)
            )
            rows.append((f"region_{region:02d}", month, treated, post, outcome))
    return pd.DataFrame(rows, columns=["region", "month", "treated", "post", "outcome"])


def _ols_clustered(y: np.ndarray, x: np.ndarray, clusters: np.ndarray):
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    residual = y - x @ beta
    meat = np.zeros((x.shape[1], x.shape[1]))
    for cluster in np.unique(clusters):
        idx = clusters == cluster
        score = x[idx].T @ residual[idx]
        meat += np.outer(score, score)
    groups, n, k = len(np.unique(clusters)), len(y), x.shape[1]
    correction = (groups / (groups - 1)) * ((n - 1) / (n - k))
    covariance = correction * xtx_inv @ meat @ xtx_inv
    return beta, np.sqrt(np.maximum(np.diag(covariance), 0))


def estimate_did(panel: pd.DataFrame) -> dict[str, float | str]:
    data = panel.copy()
    data["did"] = data["treated"] * data["post"]
    fixed_effects = pd.concat(
        [
            pd.get_dummies(data["region"], prefix="region", drop_first=True, dtype=float),
            pd.get_dummies(data["month"], prefix="month", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    x = np.column_stack([np.ones(len(data)), data["did"], fixed_effects.to_numpy()])
    beta, se = _ols_clustered(data["outcome"].to_numpy(), x, data["region"].to_numpy())
    effect, effect_se = float(beta[1]), float(se[1])
    z = effect / effect_se
    return {
        "estimand": "ATT",
        "effect": effect,
        "clustered_se": effect_se,
        "ci_low": effect - 1.96 * effect_se,
        "ci_high": effect + 1.96 * effect_se,
        "p_value": float(2 * norm.sf(abs(z))),
        "interpretation": "Average treated-region outcome change after the policy, net of region and month effects.",
    }


def parallel_trends_check(panel: pd.DataFrame) -> dict[str, float | bool]:
    pre = panel.loc[panel["post"] == 0].copy()
    x = np.column_stack([np.ones(len(pre)), pre["month"], pre["treated"], pre["month"] * pre["treated"]])
    beta, se = _ols_clustered(pre["outcome"].to_numpy(), x, pre["region"].to_numpy())
    z = float(beta[3] / se[3])
    p = float(2 * norm.sf(abs(z)))
    return {"differential_pretrend": float(beta[3]), "p_value": p, "passes_at_5pct": p >= 0.05}


def main() -> None:
    out = Path(__file__).parent / "outputs"
    out.mkdir(exist_ok=True)
    panel = make_demo_panel()
    result = {"did": estimate_did(panel), "parallel_trends": parallel_trends_check(panel)}
    panel.to_csv(out / "demo_panel.csv", index=False)
    (out / "results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
