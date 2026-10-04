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


def validate_panel(panel: pd.DataFrame) -> dict[str, int | bool]:
    """Validate the unit-period panel before any causal estimate is produced."""
    required = {"region", "month", "treated", "post", "outcome"}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    duplicated = int(panel.duplicated(["region", "month"]).sum())
    if duplicated:
        raise ValueError(f"Panel contains {duplicated} duplicate region-month rows")
    if not set(panel["treated"].dropna().unique()).issubset({0, 1}):
        raise ValueError("treated must be binary")
    if not set(panel["post"].dropna().unique()).issubset({0, 1}):
        raise ValueError("post must be binary")
    return {
        "rows": len(panel),
        "regions": int(panel["region"].nunique()),
        "periods": int(panel["month"].nunique()),
        "balanced_panel": len(panel) == panel["region"].nunique() * panel["month"].nunique(),
    }


def event_study(panel: pd.DataFrame, policy_month: int = 20, window: tuple[int, int] = (-8, 10)) -> pd.DataFrame:
    """Estimate dynamic treatment effects relative to month -1."""
    data = panel.copy()
    data["relative_month"] = data["month"] - policy_month
    periods = [p for p in range(window[0], window[1] + 1) if p != -1]
    event_columns = []
    for period in periods:
        column = f"event_{period}"
        data[column] = ((data["relative_month"] == period) & (data["treated"] == 1)).astype(float)
        event_columns.append(column)
    fixed_effects = pd.concat(
        [
            pd.get_dummies(data["region"], prefix="region", drop_first=True, dtype=float),
            pd.get_dummies(data["month"], prefix="month", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    x = np.column_stack([np.ones(len(data)), data[event_columns].to_numpy(), fixed_effects.to_numpy()])
    beta, se = _ols_clustered(data["outcome"].to_numpy(), x, data["region"].to_numpy())
    rows = [{"relative_month": -1, "effect": 0.0, "se": 0.0, "ci_low": 0.0, "ci_high": 0.0}]
    for index, period in enumerate(periods, start=1):
        rows.append({
            "relative_month": period,
            "effect": float(beta[index]),
            "se": float(se[index]),
            "ci_low": float(beta[index] - 1.96 * se[index]),
            "ci_high": float(beta[index] + 1.96 * se[index]),
        })
    return pd.DataFrame(rows).sort_values("relative_month").reset_index(drop=True)


def placebo_test(panel: pd.DataFrame, placebo_month: int = 12, actual_policy_month: int = 20) -> dict[str, float]:
    """Run a pre-policy placebo DiD to detect spurious treatment timing."""
    pre = panel.loc[panel["month"] < actual_policy_month].copy()
    pre["post"] = (pre["month"] >= placebo_month).astype(int)
    result = estimate_did(pre)
    return {"placebo_month": placebo_month, "effect": result["effect"], "p_value": result["p_value"]}


def group_trends(panel: pd.DataFrame) -> pd.DataFrame:
    labels = {0: "Comparison", 1: "Treated"}
    trends = panel.groupby(["month", "treated"], as_index=False)["outcome"].mean()
    trends["group"] = trends["treated"].map(labels)
    return trends


def main() -> None:
    out = Path(__file__).parent / "outputs"
    out.mkdir(exist_ok=True)
    panel = make_demo_panel()
    result = {
        "data_quality": validate_panel(panel),
        "did": estimate_did(panel),
        "parallel_trends": parallel_trends_check(panel),
        "placebo": placebo_test(panel),
    }
    panel.to_csv(out / "demo_panel.csv", index=False)
    event_study(panel).to_csv(out / "event_study.csv", index=False)
    group_trends(panel).to_csv(out / "group_trends.csv", index=False)
    (out / "results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
