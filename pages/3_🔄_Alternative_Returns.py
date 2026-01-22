"""
Alternative Returns Analysis Page
Compare returns: Actual vs ExcludeSmall vs SmallOnly
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
    render_sidebar, calculate_alternative_returns, create_excel_download
)

st.set_page_config(page_title="Alternative Returns", page_icon="🔄", layout="wide")


selected_etf, selected_range = render_sidebar()

st.title("🔄 Alternative Returns Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']}")

st.markdown("""
Compare three return metrics:
- **Actual**: Full ETF returns
- **Exclude Small**: Returns without positions in selected range
- **Small Only**: Returns of positions in selected range only
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
    st.metric("Mean Daily", f"{returns_df['Return_Actual'].mean() * 100:.4f}%")
    st.metric("Std Dev", f"{returns_df['Return_Actual'].std() * 100:.4f}%")

with col2:
    st.subheader(f"Excl. {selected_range['label']}")
    st.metric("Cumulative", f"{exclude_cumulative:.2f}%")
    st.metric("Mean Daily", f"{returns_df['Return_ExcludeSmall'].mean() * 100:.4f}%")
    st.metric("Std Dev", f"{returns_df['Return_ExcludeSmall'].std() * 100:.4f}%")

with col3:
    st.subheader(f"{selected_range['label']} Only")
    st.metric("Cumulative", f"{small_cumulative:.2f}%")
    st.metric("Mean Daily", f"{returns_df['Return_SmallOnly'].mean() * 100:.4f}%")
    st.metric("Std Dev", f"{returns_df['Return_SmallOnly'].std() * 100:.4f}%")

with col4:
    st.subheader("Impact")
    diff = actual_cumulative - exclude_cumulative
    st.metric("Contribution", f"{diff:.2f}%",
              delta="Positive" if diff >= 0 else "Negative",
              delta_color="normal" if diff >= 0 else "inverse")
    st.metric("Small vs Total", f"{small_cumulative - actual_cumulative:.2f}%")

st.divider()

# ============================================================================
# Cumulative Returns Chart (All 3 lines)
# ============================================================================
st.header("Cumulative Returns Comparison")

# Date range selector
min_date = returns_df['Date'].min().date()
max_date = returns_df['Date'].max().date()

date_range = st.slider(
    "Select Date Range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filter data by selected date range
mask = (returns_df['Date'].dt.date >= date_range[0]) & (returns_df['Date'].dt.date <= date_range[1])
filtered_df = returns_df[mask].copy()

# Recalculate cumulative returns for filtered period
filtered_df['Cumulative_Actual'] = (1 + filtered_df['Return_Actual']).cumprod() - 1
filtered_df['Cumulative_ExcludeSmall'] = (1 + filtered_df['Return_ExcludeSmall']).cumprod() - 1
filtered_df['Cumulative_SmallOnly'] = (1 + filtered_df['Return_SmallOnly']).cumprod() - 1

fig_cumulative = go.Figure()

fig_cumulative.add_trace(go.Scatter(
    x=filtered_df['Date'], y=filtered_df['Cumulative_Actual'] * 100,
    name='Actual (All)', line=dict(color='#3498db', width=2)
))
fig_cumulative.add_trace(go.Scatter(
    x=filtered_df['Date'], y=filtered_df['Cumulative_ExcludeSmall'] * 100,
    name=f'Excluding {selected_range["label"]}', line=dict(color='#e74c3c', width=2, dash='dash')
))
fig_cumulative.add_trace(go.Scatter(
    x=filtered_df['Date'], y=filtered_df['Cumulative_SmallOnly'] * 100,
    name=f'{selected_range["label"]} Only', line=dict(color='#2ecc71', width=2, dash='dot')
))

fig_cumulative.update_layout(
    title=f'{selected_etf} - Cumulative Returns Comparison',
    xaxis_title='Date', yaxis_title='Cumulative Return (%)',
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
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
        name='Difference', marker_color=diff_values.apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c')
    ))
    fig_diff.update_layout(title='Daily Difference (Actual - Exclude)', yaxis_title='%')
    st.plotly_chart(fig_diff, use_container_width=True)

with col2:
    fig_small = go.Figure()
    small_values = returns_df['Return_SmallOnly'] * 100
    fig_small.add_trace(go.Bar(
        x=returns_df['Date'], y=small_values,
        name='Small Only', marker_color=small_values.apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c')
    ))
    fig_small.update_layout(title=f'{selected_range["label"]} Only Daily Returns', yaxis_title='%')
    st.plotly_chart(fig_small, use_container_width=True)

st.divider()

# ============================================================================
# Distribution Analysis
# ============================================================================
st.header("Return Distribution")

col1, col2 = st.columns(2)

with col1:
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(x=returns_df['Return_Actual'] * 100, name='Actual', opacity=0.6, marker_color='#3498db', nbinsx=50))
    fig_hist.add_trace(go.Histogram(x=returns_df['Return_ExcludeSmall'] * 100, name='Excl. Small', opacity=0.6, marker_color='#e74c3c', nbinsx=50))
    fig_hist.add_trace(go.Histogram(x=returns_df['Return_SmallOnly'] * 100, name='Small Only', opacity=0.6, marker_color='#2ecc71', nbinsx=50))
    fig_hist.update_layout(title='Daily Return Distribution', barmode='overlay', xaxis_title='Return (%)')
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    fig_box = go.Figure()
    fig_box.add_trace(go.Box(y=returns_df['Return_Actual'] * 100, name='Actual', marker_color='#3498db'))
    fig_box.add_trace(go.Box(y=returns_df['Return_ExcludeSmall'] * 100, name='Excl. Small', marker_color='#e74c3c'))
    fig_box.add_trace(go.Box(y=returns_df['Return_SmallOnly'] * 100, name='Small Only', marker_color='#2ecc71'))
    fig_box.update_layout(title='Box Plot Comparison', yaxis_title='Return (%)')
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
    'Exclude Small (%)': [
        returns_df['Return_ExcludeSmall'].mean() * 100, returns_df['Return_ExcludeSmall'].median() * 100,
        returns_df['Return_ExcludeSmall'].std() * 100, returns_df['Return_ExcludeSmall'].min() * 100,
        returns_df['Return_ExcludeSmall'].max() * 100, returns_df['Return_ExcludeSmall'].skew(), returns_df['Return_ExcludeSmall'].kurtosis()
    ],
    'Small Only (%)': [
        returns_df['Return_SmallOnly'].mean() * 100, returns_df['Return_SmallOnly'].median() * 100,
        returns_df['Return_SmallOnly'].std() * 100, returns_df['Return_SmallOnly'].min() * 100,
        returns_df['Return_SmallOnly'].max() * 100, returns_df['Return_SmallOnly'].skew(), returns_df['Return_SmallOnly'].kurtosis()
    ]
}

stats_df = pd.DataFrame(stats_data)
st.dataframe(stats_df.style.format({
    'Actual (%)': '{:.4f}', 'Exclude Small (%)': '{:.4f}', 'Small Only (%)': '{:.4f}'
}), use_container_width=True)

st.divider()

# ============================================================================
# Raw Data
# ============================================================================
st.header("Raw Data")

display_df = returns_df.copy()
display_df['Actual_%'] = display_df['Return_Actual'] * 100
display_df['ExcludeSmall_%'] = display_df['Return_ExcludeSmall'] * 100
display_df['SmallOnly_%'] = display_df['Return_SmallOnly'] * 100
display_df['Cum_Actual_%'] = display_df['Cumulative_Actual'] * 100
display_df['Cum_ExcludeSmall_%'] = display_df['Cumulative_ExcludeSmall'] * 100
display_df['Cum_SmallOnly_%'] = display_df['Cumulative_SmallOnly'] * 100

st.dataframe(display_df[['Date', 'Actual_%', 'ExcludeSmall_%', 'SmallOnly_%',
                          'Cum_Actual_%', 'Cum_ExcludeSmall_%', 'Cum_SmallOnly_%']],
             use_container_width=True, height=400)

st.divider()

# ============================================================================
# Download
# ============================================================================
st.header("Download")

col1, col2 = st.columns(2)
with col1:
    st.download_button("📥 Download Excel", create_excel_download(returns_df, 'returns.xlsx'),
                       f"{selected_etf}_{selected_range['folder']}_Alternative_Returns.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with col2:
    st.download_button("📥 Download Chart (HTML)", fig_cumulative.to_html(include_plotlyjs='cdn'),
                       f"{selected_etf}_{selected_range['folder']}_Returns_Chart.html", "text/html")
