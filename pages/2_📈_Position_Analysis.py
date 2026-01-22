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
    calculate_market_value_by_range, format_currency, WEIGHT_RANGES,
    create_excel_download, create_multi_sheet_excel
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
st.header("Position Counts by Weight Range")

# Date range slider
date_range_pos = st.slider("Date Range", min_value=position_counts['Date'].min().to_pydatetime(),
                           max_value=position_counts['Date'].max().to_pydatetime(),
                           value=(position_counts['Date'].min().to_pydatetime(), position_counts['Date'].max().to_pydatetime()),
                           key="position_date_range")
plot_counts = position_counts[(position_counts['Date'] >= date_range_pos[0]) & (position_counts['Date'] <= date_range_pos[1])]

fig_counts = go.Figure()

range_labels = [wr['label'] for wr in WEIGHT_RANGES]
colors = px.colors.qualitative.Set2

for i, label in enumerate(range_labels):
    if label in plot_counts.columns:
        fig_counts.add_trace(go.Scatter(
            x=plot_counts['Date'],
            y=plot_counts[label],
            name=label,
            mode='lines',
            line=dict(color=colors[i % len(colors)], width=2)
        ))

fig_counts.update_layout(
    title=f'{selected_etf} - Position Counts by Weight Range',
    xaxis_title='Date',
    yaxis_title='Number of Positions',
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)

st.plotly_chart(fig_counts, use_container_width=True)

# Current snapshot
st.subheader("Current Position Distribution")

latest = position_counts.iloc[-1]
current_counts = []
for wr in WEIGHT_RANGES:
    if wr['label'] in latest:
        current_counts.append({
            'Range': wr['label'],
            'Count': latest[wr['label']]
        })

current_df = pd.DataFrame(current_counts)

col1, col2 = st.columns(2)

with col1:
    fig_bar = px.bar(
        current_df,
        x='Range',
        y='Count',
        title='Current Position Count by Range',
        color='Range',
        color_discrete_sequence=colors
    )
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    # Metrics cards
    cols = st.columns(3)
    for i, row in current_df.iterrows():
        with cols[i % 3]:
            st.metric(row['Range'], f"{int(row['Count']):,}")

st.divider()

# ============================================================================
# Section 2: Market Value Analysis
# ============================================================================
st.header(f"Market Value Analysis - {selected_range['label']}")

if not market_value.empty:
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    latest_mv = market_value.iloc[-1]

    with col1:
        st.metric("Current Market Value", format_currency(latest_mv['Range_MV']))

    with col2:
        st.metric("% of Total AUM", f"{latest_mv['Pct_of_AUM']:.2f}%")

    with col3:
        st.metric("Total AUM", format_currency(latest_mv['Total_AUM']))

    with col4:
        # Calculate change from first to last
        first_mv = market_value.iloc[0]
        mv_change = latest_mv['Range_MV'] - first_mv['Range_MV']
        st.metric("MV Change", format_currency(mv_change))

    # Market Value trend chart
    date_range_mv = st.slider("Date Range", min_value=market_value['Date'].min().to_pydatetime(),
                              max_value=market_value['Date'].max().to_pydatetime(),
                              value=(market_value['Date'].min().to_pydatetime(), market_value['Date'].max().to_pydatetime()),
                              key="mv_date_range")
    plot_mv = market_value[(market_value['Date'] >= date_range_mv[0]) & (market_value['Date'] <= date_range_mv[1])]

    fig_mv = make_subplots(specs=[[{"secondary_y": True}]])

    fig_mv.add_trace(
        go.Scatter(
            x=plot_mv['Date'],
            y=plot_mv['Range_MV'],
            name='Market Value',
            fill='tozeroy',
            line=dict(color='#3498db', width=2)
        ),
        secondary_y=False
    )

    fig_mv.add_trace(
        go.Scatter(
            x=plot_mv['Date'],
            y=plot_mv['Pct_of_AUM'],
            name='% of AUM',
            line=dict(color='#e74c3c', width=2, dash='dot')
        ),
        secondary_y=True
    )

    fig_mv.update_layout(
        title=f'{selected_etf} - {selected_range["label"]} Market Value (Weekly)',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    fig_mv.update_xaxes(title_text='Date')
    fig_mv.update_yaxes(title_text='Market Value ($)', secondary_y=False)
    fig_mv.update_yaxes(title_text='% of AUM', secondary_y=True)

    st.plotly_chart(fig_mv, use_container_width=True)
else:
    st.warning("No market value data available for the selected range.")

st.divider()

# ============================================================================
# Section 3: Market Value Distribution by Range
# ============================================================================
st.header("Market Value Distribution Across Ranges")

if not mv_by_range.empty:
    # Date range slider for distribution charts
    date_range_dist = st.slider("Date Range", min_value=mv_by_range['Date'].min().to_pydatetime(),
                                max_value=mv_by_range['Date'].max().to_pydatetime(),
                                value=(mv_by_range['Date'].min().to_pydatetime(), mv_by_range['Date'].max().to_pydatetime()),
                                key="dist_date_range")
    plot_mv_range = mv_by_range[(mv_by_range['Date'] >= date_range_dist[0]) & (mv_by_range['Date'] <= date_range_dist[1])]

    # Stacked area chart
    fig_stacked = go.Figure()

    for i, wr in enumerate(WEIGHT_RANGES):
        pct_col = f'{wr["label"]}_Pct'
        if pct_col in plot_mv_range.columns:
            fig_stacked.add_trace(go.Scatter(
                x=plot_mv_range['Date'],
                y=plot_mv_range[pct_col],
                name=wr['label'],
                stackgroup='one',
                fillcolor=colors[i % len(colors)],
                line=dict(width=0.5, color=colors[i % len(colors)])
            ))

    fig_stacked.update_layout(
        title=f'{selected_etf} - Market Value Distribution by Weight Range (%)',
        xaxis_title='Date',
        yaxis_title='% of Total AUM',
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    st.plotly_chart(fig_stacked, use_container_width=True)

    # Market Value by Range over time
    fig_mv_range = go.Figure()

    for i, wr in enumerate(WEIGHT_RANGES):
        mv_col = f'{wr["label"]}_MV'
        if mv_col in plot_mv_range.columns:
            fig_mv_range.add_trace(go.Scatter(
                x=plot_mv_range['Date'],
                y=plot_mv_range[mv_col],
                name=wr['label'],
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=2)
            ))

    fig_mv_range.update_layout(
        title=f'{selected_etf} - Market Value by Weight Range ($)',
        xaxis_title='Date',
        yaxis_title='Market Value ($)',
        hovermode='x unified',
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

st.divider()

# ============================================================================
# Download Section
# ============================================================================
st.header("Download Data")

col1, col2, col3 = st.columns(3)

with col1:
    excel_data = create_excel_download(position_counts, 'position_counts.xlsx')
    st.download_button(
        label="📥 Position Counts (Excel)",
        data=excel_data,
        file_name=f"{selected_etf}_Position_Counts.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col2:
    if not market_value.empty:
        excel_data = create_excel_download(market_value, 'market_value.xlsx')
        st.download_button(
            label="📥 Market Value (Excel)",
            data=excel_data,
            file_name=f"{selected_etf}_{selected_range['folder']}_Market_Value.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with col3:
    if not mv_by_range.empty:
        excel_data = create_excel_download(mv_by_range, 'mv_by_range.xlsx')
        st.download_button(
            label="📥 MV by Range (Excel)",
            data=excel_data,
            file_name=f"{selected_etf}_Market_Value_By_Range.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
