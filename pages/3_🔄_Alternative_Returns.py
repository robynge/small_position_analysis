"""
Alternative Returns Analysis Page
Compare returns: Actual vs ExcludeCurrent vs CurrentOnly
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))
from utils.streamlit_config import (
    render_sidebar, calculate_alternative_returns
)

st.set_page_config(page_title="Alternative Returns", page_icon="🔄", layout="wide")

selected_etf, selected_range = render_sidebar()

st.title("🔄 Alternative Returns Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']}")

st.markdown("""
Compare three return metrics:
- **Actual**: Full ETF returns
- **Exclude Current**: Returns without positions in selected range
- **Current Only**: Returns of positions in selected range only
""")

st.divider()

with st.spinner("Calculating alternative returns..."):
    returns_df = calculate_alternative_returns(selected_etf, selected_range)

if returns_df.empty:
    st.warning("No data available for the selected ETF and weight range.")
    st.stop()

# ============================================================================
# Summary Statistics
# ============================================================================
st.header("Summary Statistics")

col1, col2, col3, col4 = st.columns(4)

actual_cumulative = returns_df['Cumulative_Actual'].iloc[-1] * 100
exclude_cumulative = returns_df['Cumulative_ExcludeSmall'].iloc[-1] * 100
small_cumulative = returns_df['Cumulative_SmallOnly'].iloc[-1] * 100

with col1:
    st.subheader("Actual")
    st.metric("Cumulative", f"{actual_cumulative:.2f}%")
    st.metric("Mean Daily", f"{returns_df['Return_Actual'].mean() * 100:.2f}%")
    st.metric("Std Dev", f"{returns_df['Return_Actual'].std() * 100:.2f}%")

with col2:
    st.subheader(f"Excl. {selected_range['label']}")
    st.metric("Cumulative", f"{exclude_cumulative:.2f}%")
    st.metric("Mean Daily", f"{returns_df['Return_ExcludeSmall'].mean() * 100:.2f}%")
    st.metric("Std Dev", f"{returns_df['Return_ExcludeSmall'].std() * 100:.2f}%")

with col3:
    st.subheader(f"{selected_range['label']} Only")
    st.metric("Cumulative", f"{small_cumulative:.2f}%")
    st.metric("Mean Daily", f"{returns_df['Return_SmallOnly'].mean() * 100:.2f}%")
    st.metric("Std Dev", f"{returns_df['Return_SmallOnly'].std() * 100:.2f}%")

with col4:
    st.subheader("Impact")
    diff = actual_cumulative - exclude_cumulative
    st.metric("Contribution", f"{diff:.2f}%",
              delta="Positive" if diff >= 0 else "Negative",
              delta_color="normal" if diff >= 0 else "inverse")
    st.metric("Current vs Total", f"{small_cumulative - actual_cumulative:.2f}%")

st.divider()

# ============================================================================
# Cumulative Returns Chart (All 3 lines)
# ============================================================================
fig_cumulative = go.Figure()

fig_cumulative.add_trace(go.Scatter(
    x=returns_df['Date'], y=returns_df['Cumulative_Actual'] * 100,
    name='Actual (All)', line=dict(color='#3498db', width=2),
    hovertemplate='%{x}<br>Actual: %{y:.2f}%<extra></extra>'
))
fig_cumulative.add_trace(go.Scatter(
    x=returns_df['Date'], y=returns_df['Cumulative_ExcludeSmall'] * 100,
    name=f'Excluding {selected_range["label"]}', line=dict(color='#e74c3c', width=2, dash='dash'),
    hovertemplate='%{x}<br>Excl. Current: %{y:.2f}%<extra></extra>'
))
fig_cumulative.add_trace(go.Scatter(
    x=returns_df['Date'], y=returns_df['Cumulative_SmallOnly'] * 100,
    name=f'{selected_range["label"]} Only', line=dict(color='#2ecc71', width=2, dash='dot'),
    hovertemplate='%{x}<br>Current Only: %{y:.2f}%<extra></extra>'
))

fig_cumulative.update_layout(
    title=f'{selected_etf} - Cumulative Returns Comparison',
    xaxis_title='', yaxis_title='Cumulative Return (%)',
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    xaxis=dict(
        hoverformat='%Y-%m-%d',
        rangeslider=dict(visible=True, thickness=0.1),
        title=dict(text="Date Range", font=dict(size=11, color='gray'), standoff=0),
    ),
)

st.plotly_chart(fig_cumulative, use_container_width=True)

st.divider()

# ============================================================================
# Daily Return Comparison
# ============================================================================
st.header("Daily Returns")

col1, col2 = st.columns(2)

with col1:
    fig_diff = go.Figure()
    diff_values = (returns_df['Return_Actual'] - returns_df['Return_ExcludeSmall']) * 100
    fig_diff.add_trace(go.Bar(
        x=returns_df['Date'], y=diff_values,
        name='Difference', marker_color=diff_values.apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c'),
        hovertemplate='%{x}<br>Diff: %{y:.2f}%<extra></extra>'
    ))
    fig_diff.update_layout(title='Daily Difference (Actual - Exclude)', yaxis_title='%', hovermode='x unified',
                           xaxis=dict(hoverformat='%Y-%m-%d'))
    st.plotly_chart(fig_diff, use_container_width=True)

with col2:
    fig_small = go.Figure()
    small_values = returns_df['Return_SmallOnly'] * 100
    fig_small.add_trace(go.Bar(
        x=returns_df['Date'], y=small_values,
        name='Current Only', marker_color=small_values.apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c'),
        hovertemplate='%{x}<br>Return: %{y:.2f}%<extra></extra>'
    ))
    fig_small.update_layout(title=f'{selected_range["label"]} Only Daily Returns', yaxis_title='%', hovermode='x unified',
                            xaxis=dict(hoverformat='%Y-%m-%d'))
    st.plotly_chart(fig_small, use_container_width=True)

st.divider()

# ============================================================================
# Distribution Analysis
# ============================================================================
st.header("Return Distribution")

col1, col2 = st.columns(2)

with col1:
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(x=returns_df['Return_ExcludeSmall'] * 100, name='Excl. Current', opacity=0.5, marker_color='#e74c3c', nbinsx=50,
                                     hovertemplate='Return: %{x:.2f}%<br>Count: %{y}<extra></extra>'))
    fig_hist.add_trace(go.Histogram(x=returns_df['Return_SmallOnly'] * 100, name='Current Only', opacity=0.5, marker_color='#2ecc71', nbinsx=50,
                                     hovertemplate='Return: %{x:.2f}%<br>Count: %{y}<extra></extra>'))
    fig_hist.update_layout(title='Daily Return Distribution', barmode='overlay', xaxis_title='Return (%)',
                           legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    box_categories = [
        ('Actual', returns_df['Return_Actual'] * 100, '#3498db'),
        ('Excl. Current', returns_df['Return_ExcludeSmall'] * 100, '#e74c3c'),
        ('Current Only', returns_df['Return_SmallOnly'] * 100, '#2ecc71'),
    ]
    # Build strip data
    strip_data = pd.DataFrame({
        'Category': sum([[name] * len(vals) for name, vals, _ in box_categories], []),
        'Return_%': pd.concat([vals.reset_index(drop=True) for _, vals, _ in box_categories], ignore_index=True),
    })
    box_color_map = {name: color for name, _, color in box_categories}
    box_order = [name for name, _, _ in box_categories]

    fig_box = px.strip(
        strip_data, x='Category', y='Return_%', color='Category',
        category_orders={'Category': box_order},
        color_discrete_map=box_color_map,
    )
    fig_box.update_traces(
        marker=dict(size=3, opacity=0.4), jitter=0.4,
        hoverinfo='skip', hovertemplate=None,
    )

    for name, vals, _ in box_categories:
        subset = vals.dropna()
        q1, median, q3 = subset.quantile(0.25), subset.median(), subset.quantile(0.75)
        iqr = q3 - q1
        whisker_lo = max(subset.min(), q1 - 1.5 * iqr)
        whisker_hi = min(subset.max(), q3 + 1.5 * iqr)
        fig_box.add_trace(go.Box(
            x=[name], q1=[q1], median=[median], q3=[q3],
            lowerfence=[whisker_lo], upperfence=[whisker_hi],
            marker_color='rgba(255,255,255,0.6)',
            line=dict(color='white', width=1.5),
            fillcolor='rgba(0,0,0,0)',
            width=0.5, showlegend=False, hoverinfo='skip',
        ))
        fig_box.add_trace(go.Bar(
            x=[name], y=[whisker_hi - whisker_lo], base=whisker_lo,
            width=0.5, marker=dict(color='rgba(0,0,0,0)'),
            showlegend=False,
            hovertemplate=(
                f'<b>{name}</b><br>'
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

    fig_box.update_layout(title='Box Plot Comparison', yaxis_title='Return (%)', showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

st.divider()

# ============================================================================
# Statistics Table
# ============================================================================
st.header("Detailed Statistics")

stats_data = {
    'Metric': ['Mean', 'Median', 'Std Dev', 'Min', 'Max', 'Skewness', 'Kurtosis'],
    'Actual (%)': [
        returns_df['Return_Actual'].mean() * 100, returns_df['Return_Actual'].median() * 100,
        returns_df['Return_Actual'].std() * 100, returns_df['Return_Actual'].min() * 100,
        returns_df['Return_Actual'].max() * 100, returns_df['Return_Actual'].skew(), returns_df['Return_Actual'].kurtosis()
    ],
    'Exclude Current (%)': [
        returns_df['Return_ExcludeSmall'].mean() * 100, returns_df['Return_ExcludeSmall'].median() * 100,
        returns_df['Return_ExcludeSmall'].std() * 100, returns_df['Return_ExcludeSmall'].min() * 100,
        returns_df['Return_ExcludeSmall'].max() * 100, returns_df['Return_ExcludeSmall'].skew(), returns_df['Return_ExcludeSmall'].kurtosis()
    ],
    'Current Only (%)': [
        returns_df['Return_SmallOnly'].mean() * 100, returns_df['Return_SmallOnly'].median() * 100,
        returns_df['Return_SmallOnly'].std() * 100, returns_df['Return_SmallOnly'].min() * 100,
        returns_df['Return_SmallOnly'].max() * 100, returns_df['Return_SmallOnly'].skew(), returns_df['Return_SmallOnly'].kurtosis()
    ]
}

stats_df = pd.DataFrame(stats_data)
st.dataframe(stats_df.style.format({
    'Actual (%)': '{:.4f}', 'Exclude Current (%)': '{:.4f}', 'Current Only (%)': '{:.4f}'
}), use_container_width=True)

st.divider()

# ============================================================================
# Raw Output
# ============================================================================
st.header("Raw Output")

display_df = returns_df.copy()
display_df['Actual_%'] = display_df['Return_Actual'] * 100
display_df['ExcludeCurrent_%'] = display_df['Return_ExcludeSmall'] * 100
display_df['CurrentOnly_%'] = display_df['Return_SmallOnly'] * 100
display_df['Cum_Actual_%'] = display_df['Cumulative_Actual'] * 100
display_df['Cum_ExcludeCurrent_%'] = display_df['Cumulative_ExcludeSmall'] * 100
display_df['Cum_CurrentOnly_%'] = display_df['Cumulative_SmallOnly'] * 100

st.dataframe(display_df[['Date', 'Actual_%', 'ExcludeCurrent_%', 'CurrentOnly_%',
                          'Cum_Actual_%', 'Cum_ExcludeCurrent_%', 'Cum_CurrentOnly_%']],
             use_container_width=True, height=400)

