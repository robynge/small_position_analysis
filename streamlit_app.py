"""
ARK ETF Small Position Analysis Dashboard
Main entry point for Streamlit application
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add code directory to path for imports
CODE_DIR = Path(__file__).parent / "code"
sys.path.insert(0, str(CODE_DIR))

from utils.streamlit_config import (
    render_sidebar, load_etf_data, get_selected_etf,
    get_selected_range, WEIGHT_RANGES, format_currency,
    init_session_state
)

# Page config
st.set_page_config(
    page_title="ARK ETF Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
init_session_state()

# Render sidebar and get selections
selected_etf, selected_range = render_sidebar()

# Main content
st.title("ARK ETF Small Position Analysis Dashboard")

st.markdown("""
This dashboard provides comprehensive analysis of small positions in ARK Invest ETF portfolios.
Use the sidebar to select an ETF and weight range, then navigate to different analysis pages.
""")

st.divider()

# Load data for overview
with st.spinner("Loading data..."):
    df = load_etf_data(selected_etf)

if df.empty:
    st.error("Failed to load data. Please check that the data file exists.")
    st.stop()

# Overview metrics
st.header(f"📈 {selected_etf} Overview")

col1, col2, col3, col4 = st.columns(4)

# Calculate metrics
latest_date = df['Date'].max()
latest_data = df[df['Date'] == latest_date]

total_positions = len(latest_data[latest_data['Position'] > 0])
total_aum = latest_data['MV'].sum()

# Filter by selected range
range_data = latest_data[
    (latest_data['Weight'] >= selected_range['min']) &
    (latest_data['Weight'] < selected_range['max'])
]
range_positions = len(range_data)
range_mv = range_data['MV'].sum()

with col1:
    st.metric("Total Positions", f"{total_positions:,}")

with col2:
    st.metric("Total AUM", format_currency(total_aum))

with col3:
    st.metric(f"Positions in {selected_range['label']}", f"{range_positions:,}")

with col4:
    pct_aum = (range_mv / total_aum * 100) if total_aum > 0 else 0
    st.metric(f"{selected_range['label']} % of AUM", f"{pct_aum:.2f}%")

st.divider()

# Weight distribution chart
st.subheader("Weight Distribution (Current)")

# Calculate distribution
dist_data = []
for wr in WEIGHT_RANGES:
    mask = (latest_data['Weight'] >= wr['min']) & (latest_data['Weight'] < wr['max'])
    count = mask.sum()
    mv = latest_data.loc[mask, 'MV'].sum()
    dist_data.append({
        'Range': wr['label'],
        'Position Count': count,
        'Market Value': mv
    })

dist_df = pd.DataFrame(dist_data)

col1, col2 = st.columns(2)

with col1:
    fig_count = px.bar(
        dist_df,
        x='Range',
        y='Position Count',
        title='Position Count by Weight Range',
        color='Range',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_count.update_layout(showlegend=False)
    st.plotly_chart(fig_count, use_container_width=True)

with col2:
    fig_mv = px.pie(
        dist_df,
        values='Market Value',
        names='Range',
        title='Market Value Distribution by Weight Range',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    st.plotly_chart(fig_mv, use_container_width=True)

st.divider()

# Date range info
st.subheader("Data Information")

col1, col2, col3 = st.columns(3)
with col1:
    st.info(f"**Data Start:** {df['Date'].min().strftime('%Y-%m-%d')}")
with col2:
    st.info(f"**Data End:** {df['Date'].max().strftime('%Y-%m-%d')}")
with col3:
    st.info(f"**Total Trading Days:** {df['Date'].nunique():,}")

# Navigation guide
st.divider()
st.subheader("📚 Analysis Modules")

st.markdown("""
Navigate to different analysis pages using the sidebar:

| Page | Description |
|------|-------------|
| **P&L Analysis** | Calculate adjusted P&L for positions in the selected weight range |
| **Position Analysis** | Track position counts and market value trends |
| **Alternative Returns** | Compare returns with vs without small positions |
| **Graduation Analysis** | Track stocks graduating from <1% to >=1% |
| **Starter/Residual** | Identify new entries vs positions falling into range |
""")
