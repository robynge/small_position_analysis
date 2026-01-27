"""
Crossing Analysis Page
Unified analysis of stocks crossing the weight range boundaries in either direction
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))
from utils.streamlit_config import (
    render_sidebar, calculate_crossing_analysis
)

st.set_page_config(page_title="Crossing Analysis", page_icon="🎓", layout="wide")

selected_etf, selected_range = render_sidebar()

lo = selected_range['min']
hi = selected_range['max']

st.title("Crossing Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']} | **Boundaries:** {lo}% / {hi}%")

# ============================================================================
# Crossing Type Definitions
# ============================================================================
st.markdown(f"""
**Crossing Types (6):**

| Direction | From | To | Description |
|-----------|------|----|-------------|
| **Small Starter** | Below (<{lo}%) | In Range ({lo}%-{hi}%) | Stock entered the range from below |
| **Big Starter** | In Range ({lo}%-{hi}%) | Above (≥{hi}%) | Stock grew out of the range upward |
| **Super Starter** | Below (<{lo}%) | Above (≥{hi}%) | Stock jumped from below range to above |
| **Small Residual** | Above (≥{hi}%) | In Range ({lo}%-{hi}%) | Stock fell into the range from above |
| **Big Residual** | In Range ({lo}%-{hi}%) | Below (<{lo}%) | Stock fell out of the range downward |
| **Super Residual** | Above (≥{hi}%) | Below (<{lo}%) | Stock dropped from above range to below |

**Native Types (3):**

| Type | Description |
|------|-------------|
| **Native Smaller** | Stock has always been below {lo}% — never crossed either boundary |
| **Native Small** | Stock has always been within {lo}%-{hi}% — never crossed either boundary |
| **Native Large** | Stock has always been ≥{hi}% — never crossed either boundary |
""")

st.divider()

with st.spinner("Analyzing crossings..."):
    crossing_df, returns_df, summary = calculate_crossing_analysis(selected_etf, selected_range)

if not summary:
    st.warning("No data available for the selected ETF and weight range.")
    st.stop()

# ============================================================================
# Summary Metrics
# ============================================================================
st.header("Overview")

cts = summary.get('crossing_type_counts', {})
ns, nsm, nl = summary['count_native_smaller'], summary['count_native_small'], summary['count_native_large']
hs, hr = summary['count_had_starter'], summary['count_had_residual']
stf, rtg = summary['count_starter_then_fell'], summary['count_residual_then_grew']

overview_md = f"""
| | Current Holdings | Total Ever | Native Smaller | Native Small | Native Large | Had Starter | Had Residual | Starter then fell | Residual then grew |
|---|---|---|---|---|---|---|---|---|---|
| **Stocks** | {summary['current_holdings']} | {summary['total_stocks_ever']} | {ns} | {nsm} | {nl} | {hs} | {hr} | {stf}/{hs} | {rtg}/{hr} |
"""
st.markdown(overview_md)

if cts:
    type_order = ['Small Starter', 'Big Starter', 'Super Starter',
                  'Small Residual', 'Big Residual', 'Super Residual']
    header = "| | " + " | ".join(type_order) + " |"
    sep = "|---|" + "|".join(["---"] * 6) + "|"
    vals = "| **Events** | " + " | ".join(str(cts.get(t, 0)) for t in type_order) + " |"
    st.markdown(f"{header}\n{sep}\n{vals}")

st.divider()

# ============================================================================
# Cumulative Return by Category
# ============================================================================
category_order = ['Small Starter', 'Big Starter', 'Super Starter',
                  'Small Residual', 'Big Residual', 'Super Residual',
                  'Native Smaller', 'Native Small', 'Native Large']
color_map = {
    'Small Starter': '#3498db',
    'Big Starter': '#2980b9',
    'Super Starter': '#1a5276',
    'Small Residual': '#e74c3c',
    'Big Residual': '#c0392b',
    'Super Residual': '#922b21',
    'Native Smaller': '#bdc3c7',
    'Native Small': '#95a5a6',
    'Native Large': '#2ecc71',
}

st.header("Cumulative Return by Category")

if not returns_df.empty:
    # Only show categories that exist in the data
    existing_periods = returns_df['Period'].unique().tolist()
    active_order = [c for c in category_order if c in existing_periods]

    daily_cat = returns_df.groupby(['Date', 'Period'])['Daily_Return'].mean().reset_index()
    daily_cat = daily_cat.sort_values('Date')
    daily_cat['Cumulative_Return'] = daily_cat.groupby('Period')['Daily_Return'].cumsum() * 100

    fig_cum = px.line(
        daily_cat,
        x='Date',
        y='Cumulative_Return',
        color='Period',
        category_orders={'Period': active_order},
        color_discrete_map=color_map,
    )
    fig_cum.update_layout(
        yaxis_title='Cumulative Return (%)',
        xaxis_title='',
        hovermode='x unified',
    )
    fig_cum.update_traces(hovertemplate='%{y:.4f}%')
    st.plotly_chart(fig_cum, use_container_width=True)
else:
    st.info("No returns data available.")

st.divider()

# ============================================================================
# Stacked Area — Daily P&L Contribution by Category
# ============================================================================
st.header("Daily P&L Contribution by Category")

if not returns_df.empty:
    existing_periods = returns_df['Period'].unique().tolist()
    active_order = [c for c in category_order if c in existing_periods]

    daily_pnl = returns_df.groupby(['Date', 'Period'])['Daily_PnL'].sum().reset_index()
    daily_pnl = daily_pnl.sort_values('Date')
    daily_pnl['Cumulative_PnL'] = daily_pnl.groupby('Period')['Daily_PnL'].cumsum()

    fig_area = px.area(
        daily_pnl,
        x='Date',
        y='Cumulative_PnL',
        color='Period',
        category_orders={'Period': active_order},
        color_discrete_map=color_map,
    )
    fig_area.update_layout(
        yaxis_title='Cumulative P&L ($)',
        xaxis_title='',
        hovermode='x unified',
    )
    fig_area.update_traces(hovertemplate='$%{y:,.2f}')
    st.plotly_chart(fig_area, use_container_width=True)
else:
    st.info("No returns data available.")

st.divider()

# ============================================================================
# Violin — Daily Return Distribution by Category
# ============================================================================
st.header("Daily Return Distribution by Category")

if not returns_df.empty:
    plot_df = returns_df.copy()
    plot_df['Daily_Return_%'] = plot_df['Daily_Return'] * 100

    existing_periods = plot_df['Period'].unique().tolist()
    active_order = [c for c in category_order if c in existing_periods]

    fig_violin = px.violin(
        plot_df,
        x='Period',
        y='Daily_Return_%',
        color='Period',
        box=True,
        category_orders={'Period': active_order},
        color_discrete_map=color_map,
    )
    fig_violin.update_layout(
        yaxis_title='Daily Return (%)',
        xaxis_title='',
        showlegend=False,
    )
    fig_violin.update_traces(hovertemplate='%{y:.4f}%<extra></extra>')

    for period in active_order:
        subset = plot_df[plot_df['Period'] == period]['Daily_Return_%']
        if len(subset) == 0:
            continue
        q75 = subset.quantile(0.75)
        iqr = q75 - subset.quantile(0.25)
        fig_violin.add_annotation(
            x=period,
            y=q75 + 1.5 * iqr,
            text=f"n={len(subset):,}  mean={subset.mean():.4f}%",
            showarrow=False,
            font=dict(size=11),
            yshift=15,
        )

    st.plotly_chart(fig_violin, use_container_width=True)
else:
    st.info("No returns data available.")

st.divider()

# ============================================================================
# Scatter — Before vs After Crossing Returns
# ============================================================================
st.header("Crossing Events: Before vs After Return")

if not crossing_df.empty:
    color_map_dir = {
        'Small Starter': '#3498db',
        'Big Starter': '#2980b9',
        'Super Starter': '#1a5276',
        'Small Residual': '#e74c3c',
        'Big Residual': '#c0392b',
        'Super Residual': '#922b21',
    }

    fig_scatter = px.scatter(
        crossing_df,
        x='Avg_Return_Before_Crossing',
        y='Avg_Return_After_Crossing',
        color='Direction',
        color_discrete_map=color_map_dir,
        hover_data={'Ticker': True, 'Crossing_Date': True,
                    'Days_Before_Crossing': True, 'Days_After_Crossing': True,
                    'Avg_Return_Before_Crossing': ':.4f',
                    'Avg_Return_After_Crossing': ':.4f'},
    )

    all_vals = list(crossing_df['Avg_Return_Before_Crossing']) + list(crossing_df['Avg_Return_After_Crossing'])
    line_min, line_max = min(all_vals), max(all_vals)
    margin = (line_max - line_min) * 0.05
    fig_scatter.add_shape(
        type='line',
        x0=line_min - margin, y0=line_min - margin,
        x1=line_max + margin, y1=line_max + margin,
        line=dict(color='gray', dash='dash', width=1),
    )

    fig_scatter.update_layout(
        xaxis_title='Avg Daily Return Before Crossing (%)',
        yaxis_title='Avg Daily Return After Crossing (%)',
    )

    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("Points above the diagonal = return improved after crossing. Below = worsened.")
else:
    st.info("No crossing events detected for this ETF and weight range.")

st.divider()

# ============================================================================
# Crossing Events Table
# ============================================================================
st.header("Crossing Events Data")

if not crossing_df.empty:
    all_directions = sorted(crossing_df['Direction'].unique().tolist())
    direction_filter = st.multiselect(
        "Filter by Direction",
        options=all_directions,
        default=all_directions,
        key='crossing_direction_filter'
    )

    filtered_crossings = crossing_df[crossing_df['Direction'].isin(direction_filter)].copy()
    filtered_crossings = filtered_crossings.sort_values('Crossing_Date', ascending=False)

    display_crossings = filtered_crossings.copy()
    display_crossings['Avg_Return_Before_Crossing'] = display_crossings['Avg_Return_Before_Crossing'].round(4)
    display_crossings['Avg_Return_After_Crossing'] = display_crossings['Avg_Return_After_Crossing'].round(4)
    st.dataframe(display_crossings, use_container_width=True, height=400)

    st.caption(f"Total crossing events: {len(filtered_crossings)}")
else:
    st.info("No crossing events detected for this ETF and weight range.")

st.divider()

# ============================================================================
# Detailed Returns Data
# ============================================================================
st.header("Detailed Returns Data")

if not returns_df.empty:
    period_filter = st.multiselect(
        "Filter by Period",
        options=sorted(returns_df['Period'].unique()),
        default=sorted(returns_df['Period'].unique()),
        key='returns_period_filter'
    )

    filtered_returns = returns_df[returns_df['Period'].isin(period_filter)].copy()
    filtered_returns['Daily_Return_%'] = filtered_returns['Daily_Return'] * 100

    display_cols = filtered_returns[['Date', 'Ticker', 'Weight', 'Daily_Return_%', 'Daily_PnL', 'Period']].copy()
    display_cols['Weight'] = display_cols['Weight'].round(2)
    display_cols['Daily_Return_%'] = display_cols['Daily_Return_%'].round(2)
    display_cols['Daily_PnL'] = display_cols['Daily_PnL'].round(2)
    display_cols = display_cols.sort_values('Date', ascending=False)
    st.dataframe(display_cols, use_container_width=True, height=400)
else:
    st.info("No returns data available.")
