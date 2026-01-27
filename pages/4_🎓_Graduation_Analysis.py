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
# 1. Box Plot — Daily Return Distribution by Period
# ============================================================================
st.header("Daily Return Distribution by Category")

if not returns_df.empty:
    plot_df = returns_df.copy()
    plot_df['Daily_Return_%'] = plot_df['Daily_Return'] * 100

    # Order categories and assign colors
    category_order = ['Starter', 'Residual', 'Native Small', 'Native Large']
    color_map = {
        'Starter': '#3498db',
        'Residual': '#e74c3c',
        'Native Small': '#95a5a6',
        'Native Large': '#2ecc71',
    }

    fig_box = px.box(
        plot_df,
        x='Period',
        y='Daily_Return_%',
        color='Period',
        category_orders={'Period': category_order},
        color_discrete_map=color_map,
    )
    fig_box.update_layout(
        yaxis_title='Daily Return (%)',
        xaxis_title='',
        showlegend=False,
    )
    fig_box.update_traces(hovertemplate='%{y:.4f}%<extra></extra>')

    # Add count + mean annotations above each box
    for period in category_order:
        subset = plot_df[plot_df['Period'] == period]['Daily_Return_%']
        if len(subset) == 0:
            continue
        fig_box.add_annotation(
            x=period,
            y=subset.quantile(0.75) + 1.5 * (subset.quantile(0.75) - subset.quantile(0.25)),
            text=f"n={len(subset):,}<br>mean={subset.mean():.4f}%",
            showarrow=False,
            font=dict(size=11),
            yshift=15,
        )

    st.plotly_chart(fig_box, use_container_width=True)
else:
    st.info("No returns data available.")

st.divider()

# ============================================================================
# 2. Scatter — Before vs After Crossing Returns
# ============================================================================
st.header("Crossing Events: Before vs After Return")

if not crossing_df.empty:
    color_map_dir = {'Starter': '#3498db', 'Residual': '#e74c3c'}

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

    # Add diagonal reference line (before == after)
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
# 3. Crossing Events Table
# ============================================================================
st.header("Crossing Events Data")

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
