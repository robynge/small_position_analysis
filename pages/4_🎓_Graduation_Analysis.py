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
    render_sidebar, calculate_crossing_analysis,
    get_current_period, get_current_dates
)

st.set_page_config(page_title="Crossing Analysis", page_icon="🎓", layout="wide")

selected_etf, selected_range = render_sidebar()

lo = selected_range['min']
hi = selected_range['max']

st.title("Crossing Analysis")

current_period = get_current_period()
start_date, end_date = get_current_dates()
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']} | **Boundaries:** {lo}% / {hi}% | **Period:** {current_period}")

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
    crossing_df, returns_df, summary = calculate_crossing_analysis(selected_etf, selected_range, start_date, end_date)

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
        label_visibility="collapsed",
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
        xaxis=dict(hoverformat='%Y-%m-%d'),
    )
    for trace in fig_cum.data:
        name = trace.name
        pad = '&nbsp;' * max(0, 20 - len(name))
        trace.hovertemplate = f'{pad}%{{y:>8.2f}}%'
    st.plotly_chart(fig_cum, use_container_width=True)
else:
    st.info("No returns data available.")

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
            hoverformat='%Y-%m-%d',
        ),
    )
    fig_area.update_traces(hovertemplate='$%{y:,.2f}')
    st.plotly_chart(fig_area, use_container_width=True)
else:
    st.info("No returns data available.")

# ============================================================================
# Violin — Daily Return Distribution by Category
# ============================================================================
st.header("Daily Return Distribution by Category")

if not returns_df.empty:
    plot_df = returns_df.copy()
    plot_df['Daily_Return_%'] = plot_df['Daily_Return'] * 100

    existing_periods = plot_df['Period'].unique().tolist()
    active_order = [c for c in category_order if c in existing_periods]

    # Auto-detect outlier tickers: daily return beyond 99.99th percentile
    violin_threshold = plot_df['Daily_Return_%'].abs().quantile(0.9999)
    violin_outlier_tickers = plot_df[
        plot_df['Daily_Return_%'].abs() > violin_threshold
    ]['Ticker'].unique().tolist()

    violin_outlier_mode = st.radio(
        "Outliers",
        options=["Exclude Outliers", "Include Outliers"],
        horizontal=True,
        key="violin_outlier_mode",
        label_visibility="collapsed",
    )

    if violin_outlier_mode == "Exclude Outliers" and violin_outlier_tickers:
        plot_df = plot_df[~plot_df['Ticker'].isin(violin_outlier_tickers)].copy()

    fig_dist = px.strip(
        plot_df,
        x='Period',
        y='Daily_Return_%',
        color='Period',
        category_orders={'Period': active_order},
        color_discrete_map=color_map,
    )
    fig_dist.update_traces(
        marker=dict(size=3, opacity=0.4),
        jitter=0.4,
        hoverinfo='skip',
        hovertemplate=None,
    )

    # Overlay box plot
    for period in active_order:
        subset = plot_df[plot_df['Period'] == period]['Daily_Return_%']
        if len(subset) == 0:
            continue
        q1, median, q3 = subset.quantile(0.25), subset.median(), subset.quantile(0.75)
        iqr = q3 - q1
        whisker_lo = max(subset.min(), q1 - 1.5 * iqr)
        whisker_hi = min(subset.max(), q3 + 1.5 * iqr)
        fig_dist.add_trace(go.Box(
            x=[period], q1=[q1], median=[median], q3=[q3],
            lowerfence=[whisker_lo], upperfence=[whisker_hi],
            marker_color='rgba(255,255,255,0.6)',
            line=dict(color='white', width=1.5),
            fillcolor='rgba(0,0,0,0)',
            width=0.5,
            showlegend=False,
            hoverinfo='skip',
        ))
        # Invisible bar spanning box range for single hover tooltip
        fig_dist.add_trace(go.Bar(
            x=[period],
            y=[whisker_hi - whisker_lo],
            base=whisker_lo,
            width=0.5,
            marker=dict(color='rgba(0,0,0,0)'),
            showlegend=False,
            hovertemplate=(
                f'<b>{period}</b><br>'
                f'<span style="font-family:monospace">'
                f'Max:&nbsp;&nbsp;&nbsp;{whisker_hi:>8.2f}%<br>'
                f'Q3:&nbsp;&nbsp;&nbsp;&nbsp;{q3:>8.2f}%<br>'
                f'Median:{median:>8.2f}%<br>'
                f'Q1:&nbsp;&nbsp;&nbsp;&nbsp;{q1:>8.2f}%<br>'
                f'Min:&nbsp;&nbsp;&nbsp;{whisker_lo:>8.2f}%<br>'
                f'Mean:&nbsp;&nbsp;{subset.mean():>8.2f}%<br>'
                f'N:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{len(subset):>8,}'
                f'</span>'
                '<extra></extra>'
            ),
        ))

    fig_dist.update_layout(
        yaxis_title='Daily Return (%)',
        xaxis_title='',
        showlegend=False,
    )

    st.plotly_chart(fig_dist, use_container_width=True)
    if violin_outlier_tickers and violin_outlier_mode == "Exclude Outliers":
        excluded_names = ", ".join(sorted(set(t.replace(" US Equity", "") for t in violin_outlier_tickers)))
        st.caption(f"\\* Excluded (daily return beyond 99.99th percentile, >{violin_threshold:.1f}%): {excluded_names}")
else:
    st.info("No returns data available.")

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

    # Compute days to next crossing per ticker
    scatter_src = crossing_df.copy()
    scatter_src = scatter_src.sort_values(['Ticker', 'Crossing_Date'])
    scatter_src['Next_Crossing_Date'] = scatter_src.groupby('Ticker')['Crossing_Date'].shift(-1)
    scatter_src['Days_To_Next'] = (
        pd.to_datetime(scatter_src['Next_Crossing_Date']) - pd.to_datetime(scatter_src['Crossing_Date'])
    ).dt.days
    scatter_src['Next_Crossing_Str'] = scatter_src['Days_To_Next'].apply(
        lambda x: f"{int(x)} days later" if pd.notna(x) else "N/A"
    )
    scatter_src['Date_Str'] = pd.to_datetime(scatter_src['Crossing_Date']).dt.strftime('%m/%d/%Y')

    # Auto-detect outlier tickers: short window (<=2 days) with return beyond 99.5th percentile
    all_returns = pd.concat([
        scatter_src['Avg_Return_Before_Crossing'],
        scatter_src['Avg_Return_After_Crossing']
    ]).abs()
    extreme_threshold = all_returns.quantile(0.995)
    short_before = scatter_src['Days_Before_Crossing'] <= 2
    short_after = scatter_src['Days_After_Crossing'] <= 2
    extreme_before = scatter_src['Avg_Return_Before_Crossing'].abs() > extreme_threshold
    extreme_after = scatter_src['Avg_Return_After_Crossing'].abs() > extreme_threshold
    outlier_tickers = scatter_src[
        (short_before & extreme_before) | (short_after & extreme_after)
    ]['Ticker'].unique().tolist()

    outlier_mode = st.radio(
        "Outliers",
        options=["Exclude Outliers", "Include Outliers"],
        horizontal=True,
        key="scatter_outlier_mode",
        label_visibility="collapsed",
    )

    if outlier_mode == "Exclude Outliers" and outlier_tickers:
        scatter_df = scatter_src[~scatter_src['Ticker'].isin(outlier_tickers)].copy()
    else:
        scatter_df = scatter_src.copy()

    fig_scatter = px.scatter(
        scatter_df,
        x='Avg_Return_Before_Crossing',
        y='Avg_Return_After_Crossing',
        color='Direction',
        color_discrete_map=color_map_dir,
        custom_data=['Ticker', 'Date_Str', 'Days_Before_Crossing', 'Days_After_Crossing', 'Direction', 'Next_Crossing_Str'],
    )
    fig_scatter.update_traces(
        hovertemplate=(
            '<b>%{customdata[0]}</b> — %{customdata[4]}<br>'
            'Crossing Date: %{customdata[1]}<br>'
            'Before: %{x:.2f}% (%{customdata[2]} days)<br>'
            'After: %{y:.2f}% (%{customdata[3]} days)<br>'
            'Next Crossing: %{customdata[5]}'
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
    if outlier_tickers and outlier_mode == "Exclude Outliers":
        excluded_names = ", ".join(sorted(set(t.replace(" US Equity", "") for t in outlier_tickers)))
        st.caption(f"\\* Excluded (crossing window ≤2 days with statistically extreme return): {excluded_names}")
else:
    st.info("No crossing events detected for this ETF and weight range.")

st.divider()

# ============================================================================
# Crossing Events Table
# ============================================================================
st.header("Crossing Events Data")

if not crossing_df.empty:
    display_crossings = crossing_df.copy()
    display_crossings['Crossing_Date'] = pd.to_datetime(display_crossings['Crossing_Date']).dt.strftime('%m/%d/%Y')
    display_crossings['Avg_Return_Before_Crossing'] = display_crossings['Avg_Return_Before_Crossing'].round(2)
    display_crossings['Avg_Return_After_Crossing'] = display_crossings['Avg_Return_After_Crossing'].round(2)
    display_crossings = display_crossings.sort_values('Crossing_Date', ascending=False)
    st.dataframe(display_crossings, use_container_width=True, height=400)

    st.caption(f"Total crossing events: {len(display_crossings)}")
else:
    st.info("No crossing events detected for this ETF and weight range.")

# ============================================================================
# Detailed Returns Data
# ============================================================================
st.header("Detailed Returns Data")

if not returns_df.empty:
    display_cols = returns_df.copy()
    display_cols['Date'] = pd.to_datetime(display_cols['Date']).dt.strftime('%m/%d/%Y')
    display_cols['Daily_Return_%'] = display_cols['Daily_Return'] * 100
    display_cols = display_cols[['Date', 'Ticker', 'Weight', 'Daily_Return_%', 'Daily_PnL', 'Period']]
    display_cols['Weight'] = display_cols['Weight'].round(2)
    display_cols['Daily_Return_%'] = display_cols['Daily_Return_%'].round(2)
    display_cols['Daily_PnL'] = display_cols['Daily_PnL'].round(2)
    display_cols = display_cols.sort_values('Date', ascending=False)
    st.dataframe(display_cols, use_container_width=True, height=400)
else:
    st.info("No returns data available.")
