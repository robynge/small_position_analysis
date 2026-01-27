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
| **Smaller to Current** | Below (<{lo}%) | In Range ({lo}%-{hi}%) | Stock entered the range from below |
| **Current to Larger** | In Range ({lo}%-{hi}%) | Above (≥{hi}%) | Stock grew out of the range upward |
| **Smaller to Larger** | Below (<{lo}%) | Above (≥{hi}%) | Stock jumped from below range to above |
| **Larger to Current** | Above (≥{hi}%) | In Range ({lo}%-{hi}%) | Stock fell into the range from above |
| **Current to Smaller** | In Range ({lo}%-{hi}%) | Below (<{lo}%) | Stock fell out of the range downward |
| **Larger to Smaller** | Above (≥{hi}%) | Below (<{lo}%) | Stock dropped from above range to below |

**Native Types (3):**

| Type | Description |
|------|-------------|
| **Native Smaller** | Stock has always been below {lo}% — never crossed either boundary |
| **Native Current** | Stock has always been within {lo}%-{hi}% — never crossed either boundary |
| **Native Larger** | Stock has always been ≥{hi}% — never crossed either boundary |
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
total = summary['total_stocks_ever']
current = summary['current_holdings']
crossed = total - ns - nsm - nl

crossing_parts = []
for t in ['Smaller to Current', 'Current to Larger', 'Smaller to Larger', 'Larger to Current', 'Current to Smaller', 'Larger to Smaller']:
    c = cts.get(t, 0)
    if c > 0:
        crossing_parts.append(f"{c} {t}")
crossing_str = ", ".join(crossing_parts) if crossing_parts else "none"

st.markdown(
    f"{selected_etf} has **{current}** current holdings out of **{total}** stocks ever held. "
    f"Of these, **{ns}** are Native Smaller, **{nsm}** Native Current, and **{nl}** Native Larger (never crossed either boundary). "
    f"**{crossed}** stocks crossed at least one boundary, producing **{sum(cts.values())}** total crossing events ({crossing_str}). "
    f"**{hs}** stocks had at least one upward crossing, **{hr}** had at least one downward crossing. "
    f"Of those, **{stf}/{hs}** starters later fell back, and **{rtg}/{hr}** residuals later grew back."
)

st.divider()

# ============================================================================
# Cumulative Return by Category
# ============================================================================
category_order = ['Smaller to Current', 'Current to Larger', 'Smaller to Larger',
                  'Larger to Current', 'Current to Smaller', 'Larger to Smaller',
                  'Native Smaller', 'Native Current', 'Native Larger']
color_map = {
    'Smaller to Current': '#3498db',
    'Current to Larger': '#2980b9',
    'Smaller to Larger': '#1a5276',
    'Larger to Current': '#e74c3c',
    'Current to Smaller': '#c0392b',
    'Larger to Smaller': '#922b21',
    'Native Smaller': '#bdc3c7',
    'Native Current': '#95a5a6',
    'Native Larger': '#2ecc71',
}

st.header("Cumulative Return by Category")

if not returns_df.empty:
    # Only show categories that exist in the data
    existing_periods = returns_df['Period'].unique().tolist()
    active_order = [c for c in category_order if c in existing_periods]

    weighting_mode = st.radio(
        "Weighting",
        options=["Without Weighting", "With Weighting"],
        horizontal=True,
        key="cum_return_weighting",
    )

    if weighting_mode == "Without Weighting":
        daily_cat = returns_df.groupby(['Date', 'Period'])['Daily_Return'].mean().reset_index()
    else:
        weighted = returns_df.copy()
        weighted['Weighted_Return'] = weighted['Daily_Return'] * weighted['Weight']
        daily_cat = weighted.groupby(['Date', 'Period'])['Weighted_Return'].sum().reset_index()
        daily_cat.rename(columns={'Weighted_Return': 'Daily_Return'}, inplace=True)

    # Fill missing date/period combos with 0 so cumsum carries forward
    all_dates = sorted(daily_cat['Date'].unique())
    full_idx = pd.MultiIndex.from_product([all_dates, active_order], names=['Date', 'Period'])
    daily_cat = daily_cat.set_index(['Date', 'Period']).reindex(full_idx, fill_value=0).reset_index()
    daily_cat['Cumulative_Return'] = daily_cat.groupby('Period')['Daily_Return'].cumsum() * 100

    fig_cum = px.line(
        daily_cat,
        x='Date',
        y='Cumulative_Return',
        color='Period',
        category_orders={'Period': active_order},
        color_discrete_map=color_map,
    )
    y_label = 'Cumulative Weighted Return (%)' if weighting_mode == "With Weighting" else 'Cumulative Return (%)'
    fig_cum.update_layout(
        yaxis_title=y_label,
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
st.header("Cumulative Daily P&L by Category")

if not returns_df.empty:
    existing_periods = returns_df['Period'].unique().tolist()
    active_order = [c for c in category_order if c in existing_periods]

    daily_pnl = returns_df.groupby(['Date', 'Period'])['Daily_PnL'].sum().reset_index()
    all_dates = sorted(daily_pnl['Date'].unique())
    full_idx = pd.MultiIndex.from_product([all_dates, active_order], names=['Date', 'Period'])
    daily_pnl = daily_pnl.set_index(['Date', 'Period']).reindex(full_idx, fill_value=0).reset_index()
    daily_pnl['Cumulative_PnL'] = daily_pnl.groupby('Period')['Daily_PnL'].cumsum()

    fig_area = px.line(
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
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.1),
            title=dict(text="Date Range", font=dict(size=11, color='gray'), standoff=0),
        ),
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
        'Smaller to Current': '#3498db',
        'Current to Larger': '#2980b9',
        'Smaller to Larger': '#1a5276',
        'Larger to Current': '#e74c3c',
        'Current to Smaller': '#c0392b',
        'Larger to Smaller': '#922b21',
    }

    # Exclude MCRB (extreme outlier)
    scatter_df = crossing_df[~crossing_df['Ticker'].str.contains('MCRB', case=False, na=False)].copy()

    fig_scatter = px.scatter(
        scatter_df,
        x='Avg_Return_Before_Crossing',
        y='Avg_Return_After_Crossing',
        color='Direction',
        color_discrete_map=color_map_dir,
        custom_data=['Ticker', 'Crossing_Date', 'Days_Before_Crossing', 'Days_After_Crossing'],
    )
    fig_scatter.update_traces(
        hovertemplate=(
            '<b>%{customdata[0]}</b><br>'
            'Date: %{customdata[1]}<br>'
            'Before: %{x:.4f}% (%{customdata[2]} days)<br>'
            'After: %{y:.4f}% (%{customdata[3]} days)'
            '<extra></extra>'
        )
    )

    all_vals = list(scatter_df['Avg_Return_Before_Crossing']) + list(scatter_df['Avg_Return_After_Crossing'])
    if all_vals:
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
    st.caption("\\* MCRB excluded due to extreme outlier values.")
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
