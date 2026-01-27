"""
Position Analysis Page
Track position counts and market value trends across weight ranges
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

# Add code directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))
from utils.streamlit_config import (
    render_sidebar, calculate_position_counts, calculate_market_value,
    calculate_market_value_by_range, format_currency, WEIGHT_RANGES
)

st.set_page_config(
    page_title="Position Analysis",
    page_icon="📈",
    layout="wide"
)

# Render sidebar
selected_etf, selected_range = render_sidebar()

st.title("📈 Position & Market Value Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']}")

st.divider()

# Load data
with st.spinner("Loading position data..."):
    position_counts = calculate_position_counts(selected_etf)
    market_value = calculate_market_value(selected_etf, selected_range)
    mv_by_range = calculate_market_value_by_range(selected_etf)

if position_counts.empty:
    st.warning("No data available for the selected ETF.")
    st.stop()

# ============================================================================
# Section 1: Position Counts
# ============================================================================

fig_counts = go.Figure()

range_labels = [wr['label'] for wr in WEIGHT_RANGES]
colors = px.colors.qualitative.Set2

for i, label in enumerate(range_labels):
    if label in position_counts.columns:
        fig_counts.add_trace(go.Scatter(
            x=position_counts['Date'],
            y=position_counts[label],
            name=label,
            mode='lines',
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate='%{x}<br>' + label + ': %{y:.2f}<extra></extra>'
        ))

fig_counts.update_layout(
    title=f'{selected_etf} - Position Counts by Weight Range',
    xaxis_title='',
    yaxis_title='Number of Positions',
    hovermode='x unified',
    xaxis=dict(
        hoverformat='%Y-%m-%d',
        rangeslider=dict(visible=True, thickness=0.1),
        title=dict(text="Date Range", font=dict(size=11, color='gray'), standoff=0),
    ),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)

st.plotly_chart(fig_counts, use_container_width=True)

# ============================================================================
# Section 2: Market Value Analysis
# ============================================================================

if not market_value.empty:
    fig_mv = make_subplots(specs=[[{"secondary_y": True}]])

    fig_mv.add_trace(
        go.Scatter(
            x=market_value['Date'],
            y=market_value['Range_MV'],
            name='Market Value',
            fill='tozeroy',
            line=dict(color='#3498db', width=2),
            hovertemplate='%{x}<br>MV: $%{y:,.2f}<extra></extra>'
        ),
        secondary_y=False
    )

    fig_mv.add_trace(
        go.Scatter(
            x=market_value['Date'],
            y=market_value['Pct_of_AUM'],
            name='% of AUM',
            line=dict(color='#e74c3c', width=2, dash='dot'),
            hovertemplate='%{x}<br>% of AUM: %{y:.2f}%<extra></extra>'
        ),
        secondary_y=True
    )

    fig_mv.update_layout(
        title=f'{selected_etf} - {selected_range["label"]} Market Value (Weekly)',
        hovermode='x unified',
        xaxis=dict(
            hoverformat='%Y-%m-%d',
            rangeslider=dict(visible=True, thickness=0.1),
            title=dict(text="Date Range", font=dict(size=11, color='gray'), standoff=0),
        ),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    fig_mv.update_yaxes(title_text='Market Value ($)', secondary_y=False)
    fig_mv.update_yaxes(title_text='% of AUM', secondary_y=True)

    st.plotly_chart(fig_mv, use_container_width=True)
else:
    st.warning("No market value data available for the selected range.")

# ============================================================================
# Section 3: Market Value Distribution by Range
# ============================================================================

if not mv_by_range.empty:
    # Stacked area chart
    fig_stacked = go.Figure()

    for i, wr in enumerate(WEIGHT_RANGES):
        pct_col = f'{wr["label"]}_Pct'
        if pct_col in mv_by_range.columns:
            fig_stacked.add_trace(go.Scatter(
                x=mv_by_range['Date'],
                y=mv_by_range[pct_col],
                name=wr['label'],
                stackgroup='one',
                fillcolor=colors[i % len(colors)],
                line=dict(width=0.5, color=colors[i % len(colors)]),
                hovertemplate='%{x}<br>' + wr['label'] + ': %{y:.2f}%<extra></extra>'
            ))

    fig_stacked.update_layout(
        title=f'{selected_etf} - Market Value Distribution by Weight Range (%)',
        xaxis_title='',
        yaxis_title='% of Total AUM',
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        xaxis=dict(
            hoverformat='%Y-%m-%d',
            rangeslider=dict(visible=True, thickness=0.1),
            title=dict(text="Date Range", font=dict(size=11, color='gray'), standoff=0),
        ),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    st.plotly_chart(fig_stacked, use_container_width=True)

    # Market Value by Range over time
    fig_mv_range = go.Figure()

    for i, wr in enumerate(WEIGHT_RANGES):
        mv_col = f'{wr["label"]}_MV'
        if mv_col in mv_by_range.columns:
            fig_mv_range.add_trace(go.Scatter(
                x=mv_by_range['Date'],
                y=mv_by_range[mv_col],
                name=wr['label'],
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate='%{x}<br>' + wr['label'] + ': $%{y:,.2f}<extra></extra>'
            ))

    fig_mv_range.update_layout(
        title=f'{selected_etf} - Market Value by Weight Range ($)',
        xaxis_title='',
        yaxis_title='Market Value ($)',
        hovermode='x unified',
        xaxis=dict(
            hoverformat='%Y-%m-%d',
            rangeslider=dict(visible=True, thickness=0.1),
            title=dict(text="Date Range", font=dict(size=11, color='gray'), standoff=0),
        ),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    st.plotly_chart(fig_mv_range, use_container_width=True)

st.divider()

# ============================================================================
# Data Tables
# ============================================================================
st.header("Data Tables")

tab1, tab2, tab3 = st.tabs(["Position Counts", "Market Value (Selected Range)", "Market Value by Range"])

with tab1:
    st.dataframe(position_counts, use_container_width=True, height=400)

with tab2:
    if not market_value.empty:
        st.dataframe(
            market_value.style.format({
                'Range_MV': '${:,.0f}',
                'Total_AUM': '${:,.0f}',
                'Pct_of_AUM': '{:.2f}%'
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.info("No data available")

with tab3:
    if not mv_by_range.empty:
        st.dataframe(mv_by_range, use_container_width=True, height=400)
    else:
        st.info("No data available")

