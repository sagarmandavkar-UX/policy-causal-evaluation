"""Interactive decision dashboard for the causal policy evaluation."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis import event_study, estimate_did, group_trends, make_demo_panel, parallel_trends_check, placebo_test, validate_panel


st.set_page_config(page_title="Policy Impact Lab", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
st.title("Policy Impact Lab")
st.caption("Difference-in-differences diagnostics for a regional policy rollout · seeded demonstration data")

uploaded = st.sidebar.file_uploader("Use your own panel CSV", type="csv")
policy_month = st.sidebar.number_input("Policy month", min_value=2, max_value=34, value=20)
panel = pd.read_csv(uploaded) if uploaded else make_demo_panel()
quality = validate_panel(panel)
did = estimate_did(panel)
pretrend = parallel_trends_check(panel)
placebo = placebo_test(panel, placebo_month=max(2, int(policy_month) - 8), actual_policy_month=int(policy_month))

left, middle, right, far = st.columns(4)
left.metric("Estimated ATT", f"{did['effect']:.2f}", help="Average treatment effect on treated regions")
middle.metric("95% confidence interval", f"[{did['ci_low']:.2f}, {did['ci_high']:.2f}]")
right.metric("Pre-trend p-value", f"{pretrend['p_value']:.3f}", "Pass" if pretrend["passes_at_5pct"] else "Review")
far.metric("Panel coverage", f"{quality['regions']} × {quality['periods']}", "Balanced" if quality["balanced_panel"] else "Unbalanced")

st.subheader("Outcome trajectory")
trends = group_trends(panel)
trend_chart = px.line(trends, x="month", y="outcome", color="group", markers=True, color_discrete_map={"Treated": "#2563EB", "Comparison": "#64748B"})
trend_chart.add_vline(x=policy_month, line_dash="dash", line_color="#DC2626", annotation_text="Policy starts")
trend_chart.update_layout(yaxis_title="Average outcome", xaxis_title="Month", legend_title="Group", hovermode="x unified")
st.plotly_chart(trend_chart, width="stretch")

st.subheader("Dynamic treatment effects")
events = event_study(panel, policy_month=int(policy_month))
event_chart = go.Figure()
event_chart.add_trace(go.Scatter(x=events["relative_month"], y=events["effect"], mode="lines+markers", name="Estimate", line_color="#2563EB"))
event_chart.add_trace(go.Scatter(x=list(events["relative_month"]) + list(events["relative_month"])[::-1], y=list(events["ci_high"]) + list(events["ci_low"])[::-1], fill="toself", fillcolor="rgba(37,99,235,.15)", line_color="rgba(0,0,0,0)", name="95% CI"))
event_chart.add_hline(y=0, line_color="#334155")
event_chart.add_vline(x=-0.5, line_dash="dash", line_color="#DC2626")
event_chart.update_layout(xaxis_title="Months relative to policy", yaxis_title="Effect relative to month -1", hovermode="x unified")
st.plotly_chart(event_chart, width="stretch")

with st.expander("Identification and robustness checks", expanded=True):
    st.write({"parallel_trends": pretrend, "pre_policy_placebo": placebo, "cluster_level": "region"})
    st.info("A non-significant pre-trend or placebo test supports—but does not prove—the identifying assumptions. Check spillovers, anticipation, and concurrent policies before using a real estimate for decisions.")

st.download_button("Download event-study estimates", events.to_csv(index=False), "event_study.csv", "text/csv")
