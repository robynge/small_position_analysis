"""
Alternative Returns Analysis Page
Compare returns with and without small positions
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.streamlit_config import (
    render_sidebar, calculate_alternative_returns,
    create_excel_download
)

st.set_page_config(
    page_title="Alternative Returns",
    page_icon="🔄",
    layout="wide"
)

# Render sidebar
selected_etf, selected_range = render_sidebar()

st.title("🔄 Alternative Returns Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']}")

st.markdown("""
This analysis compares the ETF's actual returns with hypothetical returns if positions
in the selected weight range were excluded. This helps understand the contribution of
small positions to overall performance.
""")

st.divider()

# Calculate returns
with st.spinner("Calculating alternative returns..."):
    returns_df = calculate_alternative_returns(selected_etf, selected_range)

if returns_df.empty:
    st.warning("No data available for the selected ETF and weight range.")
    st.stop()

# ============================================================================
# Summary Statistics
# ============================================================================
st.header("Summary Statistics")

col1, col2, col3 = st.columns(3)

# Calculate stats
actual_cumulative = returns_df['Cumulative_Actual'].iloc[-1] * 100
exclude_cumulative = returns_df['Cumulative_Exclude'].iloc[-1] * 100
diff_cumulative = actual_cumulative - exclude_cumulative

actual_mean = returns_df['Actual_Return'].mean() * 100
exclude_mean = returns_df['Exclude_Small_Return'].mean() * 100

actual_std = returns_df['Actual_Return'].std() * 100
exclude_std = returns_df['Exclude_Small_Return'].std() * 100

with col1:
    st.subheader("Actual Returns")
    st.metric("Cumulative Return", f"{actual_cumulative:.2f}%")
    st.metric("Mean Daily Return", f"{actual_mean:.4f}%")
    st.metric("Std Dev (Daily)", f"{actual_std:.4f}%")

with col2:
    st.subheader(f"Excluding {selected_range['label']}")
    st.metric("Cumulative Return", f"{exclude_cumulative:.2f}%")
    st.metric("Mean Daily Return", f"{exclude_mean:.4f}%")
    st.metric("Std Dev (Daily)", f"{exclude_std:.4f}%")

with col3:
    st.subheader("Difference")
    delta_color = "normal" if diff_cumulative >= 0 else "inverse"
    st.metric(
        "Return Contribution",
        f"{diff_cumulative:.2f}%",
        delta=f"{'Positive' if diff_cumulative >= 0 else 'Negative'} impact",
        delta_color=delta_color
    )
    st.metric("Mean Diff", f"{(actual_mean - exclude_mean):.4f}%")

    # Win rate
    win_days = (returns_df['Return_Diff'] > 0).sum()
    total_days = len(returns_df)
    win_rate = win_days / total_days * 100
    st.metric("Win Rate", f"{win_rate:.1f}%", help="% of days where small positions added value")

st.divider()

# ============================================================================
# Cumulative Returns Chart
# ============================================================================
st.header("Cumulative Returns Comparison")

fig_cumulative = go.Figure()

fig_cumulative.add_trace(go.Scatter(
    x=returns_df['Date'],
    y=returns_df['Cumulative_Actual'] * 100,
    name='Actual Returns',
    line=dict(color='#3498db', width=2),
    fill='tozeroy',
    fillcolor='rgba(52, 152, 219, 0.1)'
))

fig_cumulative.add_trace(go.Scatter(
    x=returns_df['Date'],
    y=returns_df['Cumulative_Exclude'] * 100,
    name=f'Excluding {selected_range["label"]}',
    line=dict(color='#e74c3c', width=2, dash='dash')
))

fig_cumulative.update_layout(
    title=f'{selected_etf} - Cumulative Returns: Actual vs Excluding {selected_range["label"]}',
    xaxis_title='Date',
    yaxis_title='Cumulative Return (%)',
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)

st.plotly_chart(fig_cumulative, use_container_width=True)

st.divider()

# ============================================================================
# Daily Return Difference
# ============================================================================
st.header("Daily Return Difference")

fig_diff = go.Figure()

fig_diff.add_trace(go.Bar(
    x=returns_df['Date'],
    y=returns_df['Return_Diff'] * 100,
    name='Return Difference',
    marker_color=returns_df['Return_Diff'].apply(
        lambda x: '#2ecc71' if x >= 0 else '#e74c3c'
    )
))

fig_diff.update_layout(
    title=f'Daily Return Difference (Actual - Excluding {selected_range["label"]})',
    xaxis_title='Date',
    yaxis_title='Return Difference (%)',
    hovermode='x unified'
)

st.plotly_chart(fig_diff, use_container_width=True)

st.divider()

# ============================================================================
# Distribution Analysis
# ============================================================================
st.header("Return Distribution Analysis")

col1, col2 = st.columns(2)

with col1:
    # Histogram comparison
    fig_hist = go.Figure()

    fig_hist.add_trace(go.Histogram(
        x=returns_df['Actual_Return'] * 100,
        name='Actual Returns',
        opacity=0.7,
        marker_color='#3498db',
        nbinsx=50
    ))

    fig_hist.add_trace(go.Histogram(
        x=returns_df['Exclude_Small_Return'] * 100,
        name=f'Excluding {selected_range["label"]}',
        opacity=0.7,
        marker_color='#e74c3c',
        nbinsx=50
    ))

    fig_hist.update_layout(
        title='Daily Return Distribution',
        xaxis_title='Daily Return (%)',
        yaxis_title='Frequency',
        barmode='overlay',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    # Box plot comparison
    fig_box = go.Figure()

    fig_box.add_trace(go.Box(
        y=returns_df['Actual_Return'] * 100,
        name='Actual',
        marker_color='#3498db'
    ))

    fig_box.add_trace(go.Box(
        y=returns_df['Exclude_Small_Return'] * 100,
        name=f'Excl. {selected_range["label"]}',
        marker_color='#e74c3c'
    ))

    fig_box.update_layout(
        title='Return Distribution Box Plot',
        yaxis_title='Daily Return (%)'
    )

    st.plotly_chart(fig_box, use_container_width=True)

st.divider()

# ============================================================================
# Statistical Summary Table
# ============================================================================
st.header("Detailed Statistics")

stats_data = {
    'Metric': ['Mean', 'Median', 'Std Dev', 'Min', 'Max', 'Skewness', 'Kurtosis'],
    'Actual (%)': [
        returns_df['Actual_Return'].mean() * 100,
        returns_df['Actual_Return'].median() * 100,
        returns_df['Actual_Return'].std() * 100,
        returns_df['Actual_Return'].min() * 100,
        returns_df['Actual_Return'].max() * 100,
        returns_df['Actual_Return'].skew(),
        returns_df['Actual_Return'].kurtosis()
    ],
    f'Excluding {selected_range["label"]} (%)': [
        returns_df['Exclude_Small_Return'].mean() * 100,
        returns_df['Exclude_Small_Return'].median() * 100,
        returns_df['Exclude_Small_Return'].std() * 100,
        returns_df['Exclude_Small_Return'].min() * 100,
        returns_df['Exclude_Small_Return'].max() * 100,
        returns_df['Exclude_Small_Return'].skew(),
        returns_df['Exclude_Small_Return'].kurtosis()
    ]
}

stats_df = pd.DataFrame(stats_data)

# Calculate difference
stats_df['Difference'] = stats_df['Actual (%)'] - stats_df[f'Excluding {selected_range["label"]} (%)']

st.dataframe(
    stats_df.style.format({
        'Actual (%)': '{:.4f}',
        f'Excluding {selected_range["label"]} (%)': '{:.4f}',
        'Difference': '{:.4f}'
    }),
    use_container_width=True
)

st.divider()

# ============================================================================
# Data Table
# ============================================================================
st.header("Raw Data")

display_df = returns_df.copy()
display_df['Actual_Return_Pct'] = display_df['Actual_Return'] * 100
display_df['Exclude_Small_Pct'] = display_df['Exclude_Small_Return'] * 100
display_df['Return_Diff_Pct'] = display_df['Return_Diff'] * 100
display_df['Cumulative_Actual_Pct'] = display_df['Cumulative_Actual'] * 100
display_df['Cumulative_Exclude_Pct'] = display_df['Cumulative_Exclude'] * 100

st.dataframe(
    display_df[['Date', 'Actual_Return_Pct', 'Exclude_Small_Pct', 'Return_Diff_Pct',
                'Cumulative_Actual_Pct', 'Cumulative_Exclude_Pct']].style.format({
        'Actual_Return_Pct': '{:.4f}%',
        'Exclude_Small_Pct': '{:.4f}%',
        'Return_Diff_Pct': '{:.4f}%',
        'Cumulative_Actual_Pct': '{:.2f}%',
        'Cumulative_Exclude_Pct': '{:.2f}%'
    }),
    use_container_width=True,
    height=400
)

st.divider()

# ============================================================================
# Download Section
# ============================================================================
st.header("Download Data")

col1, col2 = st.columns(2)

with col1:
    excel_data = create_excel_download(returns_df, 'alternative_returns.xlsx')
    st.download_button(
        label="📥 Download Returns Data (Excel)",
        data=excel_data,
        file_name=f"{selected_etf}_{selected_range['folder']}_Alternative_Returns.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col2:
    html_buffer = fig_cumulative.to_html(include_plotlyjs='cdn')
    st.download_button(
        label="📥 Download Chart (HTML)",
        data=html_buffer,
        file_name=f"{selected_etf}_{selected_range['folder']}_Returns_Chart.html",
        mime="text/html"
    )
