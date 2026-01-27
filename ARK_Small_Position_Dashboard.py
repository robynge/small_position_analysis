"""
ARK Small Position Dashboard
Main entry point for Streamlit application
"""
import streamlit as st
from pathlib import Path
import sys

# Add code directory to path for imports
CODE_DIR = Path(__file__).parent / "code"
sys.path.insert(0, str(CODE_DIR))

from utils.streamlit_config import (
    render_sidebar, load_etf_data, init_session_state
)

# Page config
st.set_page_config(
    page_title="ARK Small Position Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Render sidebar and get selections
selected_etf, selected_range = render_sidebar()

# Main content
st.title("ARK Small Position Dashboard")

st.divider()

# Load data for overview
with st.spinner("Loading data..."):
    df = load_etf_data(selected_etf)

if df.empty:
    st.error("Failed to load data. Please check that the data file exists.")
    st.stop()

# Data range info
st.header(f"{selected_etf} Data Range")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Data Start", df['Date'].min().strftime('%Y-%m-%d'))
with col2:
    st.metric("Data End", df['Date'].max().strftime('%Y-%m-%d'))
with col3:
    st.metric("Total Trading Days", f"{df['Date'].nunique():,}")

st.divider()

# Project description and analysis modules
st.header("About This Dashboard")

st.markdown(f"""
This dashboard analyzes **small positions** (by portfolio weight) in ARK Invest ETF portfolios.
ARK ETFs hold a mix of high-conviction large positions and smaller exploratory positions. This tool
investigates how these smaller positions behave over time — whether they contribute positively to
overall returns, how often they "graduate" into larger positions, and what happens to positions that
enter or exit specific weight ranges.

Use the **sidebar** to select an ETF and weight range, then navigate to the analysis pages below.

**Currently analyzing:** {selected_etf} | **Weight range:** {selected_range['label']}
""")

st.divider()

st.header("Analysis Modules")

st.markdown("""
| Page | Description |
|------|-------------|
| **P&L Analysis** | Calculate adjusted P&L for positions in the selected weight range. Identifies which positions contribute most to portfolio gains or losses. |
| **Position Analysis** | Track how the number of positions in each weight range changes over time, along with the market value allocated to each range as a percentage of total AUM. |
| **Alternative Returns** | Compare three return streams: actual full-ETF returns, returns excluding small positions, and returns of small positions only — to quantify the impact of small positions on overall performance. |
| **Crossing Analysis** | Boundary crossing analysis examining how stocks perform before, during, and after entering the selected weight range. Classifies stocks by movement between three zones (below range, in range, above range) with 6 crossing types and 3 native types, tracking cumulative return, P&L, and distribution. |
| **Stock Drill-Down** | Select any stock to view its weight and price history on a dual-axis chart, with crossing events marked as colored markers and both boundary lines displayed. |
""")
