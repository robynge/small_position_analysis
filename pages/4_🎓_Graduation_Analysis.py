"""
Crossing Analysis Page
Unified analysis of stocks crossing the weight range boundary in either direction
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

boundary = selected_range['max']

st.title("Crossing Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']} | **Boundary:** {boundary}%")
st.markdown("""
Classifies stocks by how they relate to the weight range boundary:
- **Starter**: crossed from small to large (upward)
- **Residual**: crossed from large to small (downward)
- **Native Small**: always within range, never crossed
- **Native Large**: always above range, never crossed
""")

st.divider()

with st.spinner("Analyzing crossings..."):
    crossing_df, returns_df, summary = calculate_crossing_analysis(selected_etf, selected_range)

if not summary:
    st.warning("No data available for the selected ETF and weight range.")
    st.stop()

# ============================================================================
# Summary Metric Cards
# ============================================================================
st.header("Category Counts")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Starter", summary['count_starter'])
with col2:
    st.metric("Residual", summary['count_residual'])
with col3:
    st.metric("Native Small", summary['count_native_small'])
with col4:
    st.metric("Native Large", summary['count_native_large'])

st.divider()

# ============================================================================
# Mean Daily Return Comparison
# ============================================================================
st.header("Mean Daily Return by Category")

categories = ['Starter', 'Residual', 'Native Small', 'Native Large']
mean_returns = [
    summary['mean_return_starter'],
    summary['mean_return_residual'],
    summary['mean_return_native_small'],
    summary['mean_return_native_large'],
]
colors = ['#3498db', '#e74c3c', '#95a5a6', '#2ecc71']

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=categories,
    y=mean_returns,
    marker_color=colors,
    hovertemplate='%{x}<br>Mean Daily Return: %{y:.4f}%<extra></extra>'
))
fig_bar.update_layout(
    yaxis_title='Mean Daily Return (%)',
    xaxis_title='Category',
)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ============================================================================
# Crossing Events Table
# ============================================================================
st.header("Crossing Events")

if not crossing_df.empty:
    direction_filter = st.multiselect(
        "Filter by Direction",
        options=['Starter', 'Residual'],
        default=['Starter', 'Residual'],
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
