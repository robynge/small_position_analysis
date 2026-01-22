"""
Graduation Analysis Page
Track stocks that graduated from <1% to >=1%
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.streamlit_config import (
    render_sidebar, calculate_graduation, load_etf_data,
    create_excel_download
)

st.set_page_config(
    page_title="Graduation Analysis",
    page_icon="🎓",
    layout="wide"
)

# Render sidebar
selected_etf, selected_range = render_sidebar()

st.title("🎓 Graduation Analysis")
st.markdown(f"**ETF:** {selected_etf}")

st.markdown("""
This analysis identifies stocks that "graduated" from being small positions (<1% weight)
to larger positions (>=1% weight). It tracks their performance before and after graduation.
""")

st.divider()

# Calculate graduation data
with st.spinner("Analyzing graduations..."):
    summary_df, graduated_stocks = calculate_graduation(selected_etf)

if summary_df.empty:
    st.warning("No graduated stocks found for this ETF.")
    st.stop()

# ============================================================================
# Summary Metrics
# ============================================================================
st.header("Summary Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Graduated", f"{len(summary_df):,}")

with col2:
    avg_days = summary_df['Days_Small'].mean()
    st.metric("Avg Days Before Graduation", f"{avg_days:.0f}")

with col3:
    avg_return_before = summary_df['Return_Before_Graduation'].mean()
    st.metric("Avg Return Before Graduation", f"{avg_return_before:.2f}%")

with col4:
    avg_return_after = summary_df['Return_After_Graduation'].mean()
    st.metric("Avg Return After Graduation", f"{avg_return_after:.2f}%")

st.divider()

# ============================================================================
# Return Comparison
# ============================================================================
st.header("Return Performance: Before vs After Graduation")

col1, col2 = st.columns(2)

with col1:
    # Bar chart comparing returns
    comparison_data = pd.DataFrame({
        'Phase': ['Before Graduation (<1%)', 'After Graduation (>=1%)'],
        'Average Return (%)': [
            summary_df['Return_Before_Graduation'].mean(),
            summary_df['Return_After_Graduation'].mean()
        ]
    })

    fig_bar = px.bar(
        comparison_data,
        x='Phase',
        y='Average Return (%)',
        title='Average Return by Phase',
        color='Phase',
        color_discrete_sequence=['#3498db', '#2ecc71']
    )
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    # Box plot of returns
    fig_box = go.Figure()

    fig_box.add_trace(go.Box(
        y=summary_df['Return_Before_Graduation'],
        name='Before Graduation',
        marker_color='#3498db'
    ))

    fig_box.add_trace(go.Box(
        y=summary_df['Return_After_Graduation'],
        name='After Graduation',
        marker_color='#2ecc71'
    ))

    fig_box.update_layout(
        title='Return Distribution by Phase',
        yaxis_title='Return (%)'
    )

    st.plotly_chart(fig_box, use_container_width=True)

st.divider()

# ============================================================================
# Graduation Timeline
# ============================================================================
st.header("Graduation Timeline")

# Sort by graduation date
timeline_df = summary_df.sort_values('Graduation_Date')

fig_timeline = px.scatter(
    timeline_df,
    x='Graduation_Date',
    y='Days_Small',
    size='Return_Before_Graduation',
    color='Return_After_Graduation',
    hover_name='Stock',
    hover_data=['First_Small_Date', 'Return_Before_Graduation', 'Return_After_Graduation'],
    title='Graduation Timeline (bubble size = return before, color = return after)',
    color_continuous_scale='RdYlGn'
)

fig_timeline.update_layout(
    xaxis_title='Graduation Date',
    yaxis_title='Days in Small Position (<1%)'
)

st.plotly_chart(fig_timeline, use_container_width=True)

st.divider()

# ============================================================================
# Individual Stock Performance
# ============================================================================
st.header("Individual Stock Performance")

# Scatter plot: before vs after
fig_scatter = px.scatter(
    summary_df,
    x='Return_Before_Graduation',
    y='Return_After_Graduation',
    hover_name='Stock',
    hover_data=['Days_Small', 'Graduation_Date'],
    title='Return Before vs After Graduation',
    color='Days_Small',
    color_continuous_scale='Viridis'
)

# Add reference line (y = x)
fig_scatter.add_trace(go.Scatter(
    x=[-100, 500],
    y=[-100, 500],
    mode='lines',
    name='Equal Returns',
    line=dict(color='gray', dash='dash')
))

# Add quadrant shading
fig_scatter.add_hline(y=0, line_dash="dot", line_color="gray")
fig_scatter.add_vline(x=0, line_dash="dot", line_color="gray")

fig_scatter.update_layout(
    xaxis_title='Return Before Graduation (%)',
    yaxis_title='Return After Graduation (%)'
)

st.plotly_chart(fig_scatter, use_container_width=True)

# Categorize stocks by performance quadrant
st.subheader("Performance Quadrant Analysis")

col1, col2, col3, col4 = st.columns(4)

# Quadrant counts
both_positive = len(summary_df[(summary_df['Return_Before_Graduation'] > 0) &
                                (summary_df['Return_After_Graduation'] > 0)])
before_positive = len(summary_df[(summary_df['Return_Before_Graduation'] > 0) &
                                  (summary_df['Return_After_Graduation'] <= 0)])
after_positive = len(summary_df[(summary_df['Return_Before_Graduation'] <= 0) &
                                 (summary_df['Return_After_Graduation'] > 0)])
both_negative = len(summary_df[(summary_df['Return_Before_Graduation'] <= 0) &
                                (summary_df['Return_After_Graduation'] <= 0)])

with col1:
    st.metric("Both Positive", both_positive, help="Positive returns both before and after")

with col2:
    st.metric("Before Only", before_positive, help="Positive before, negative after")

with col3:
    st.metric("After Only", after_positive, help="Negative before, positive after")

with col4:
    st.metric("Both Negative", both_negative, help="Negative returns both before and after")

st.divider()

# ============================================================================
# Top Performers
# ============================================================================
st.header("Top & Bottom Performers")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 10 by Total Return")
    summary_df['Total_Return'] = summary_df['Return_Before_Graduation'] + summary_df['Return_After_Graduation']
    top_10 = summary_df.nlargest(10, 'Total_Return')[['Stock', 'Return_Before_Graduation',
                                                       'Return_After_Graduation', 'Total_Return', 'Days_Small']]
    st.dataframe(
        top_10.style.format({
            'Return_Before_Graduation': '{:.2f}%',
            'Return_After_Graduation': '{:.2f}%',
            'Total_Return': '{:.2f}%'
        }),
        use_container_width=True
    )

with col2:
    st.subheader("Bottom 10 by Total Return")
    bottom_10 = summary_df.nsmallest(10, 'Total_Return')[['Stock', 'Return_Before_Graduation',
                                                          'Return_After_Graduation', 'Total_Return', 'Days_Small']]
    st.dataframe(
        bottom_10.style.format({
            'Return_Before_Graduation': '{:.2f}%',
            'Return_After_Graduation': '{:.2f}%',
            'Total_Return': '{:.2f}%'
        }),
        use_container_width=True
    )

st.divider()

# ============================================================================
# Full Data Table
# ============================================================================
st.header("All Graduated Stocks")

st.dataframe(
    summary_df.style.format({
        'Return_Before_Graduation': '{:.2f}%',
        'Return_After_Graduation': '{:.2f}%',
        'Total_Return': '{:.2f}%'
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
    excel_data = create_excel_download(summary_df, 'graduation_data.xlsx')
    st.download_button(
        label="📥 Download Graduation Data (Excel)",
        data=excel_data,
        file_name=f"{selected_etf}_Graduation_Analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col2:
    html_buffer = fig_scatter.to_html(include_plotlyjs='cdn')
    st.download_button(
        label="📥 Download Chart (HTML)",
        data=html_buffer,
        file_name=f"{selected_etf}_Graduation_Chart.html",
        mime="text/html"
    )
