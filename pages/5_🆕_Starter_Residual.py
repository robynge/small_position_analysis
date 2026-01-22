"""
Starter/Residual Analysis Page
Identify new entries vs positions falling into range
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add code directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))
from utils.streamlit_config import (
    render_sidebar, calculate_starter_residual,
    create_excel_download, create_multi_sheet_excel
)

st.set_page_config(
    page_title="Starter/Residual Analysis",
    page_icon="🆕",
    layout="wide"
)

# Render sidebar
selected_etf, selected_range = render_sidebar()

st.title("🆕 Starter / Residual Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']}")

st.markdown("""
This analysis categorizes positions entering the selected weight range:
- **Starters**: New positions entering the range from below (new buys or increasing weight)
- **Residuals**: Positions falling into the range from above (declining weight)
""")

st.divider()

# Calculate starter/residual data
with st.spinner("Analyzing position entries..."):
    summary, starters_df, residuals_df, reappeared_df = calculate_starter_residual(selected_etf, selected_range)

if not summary:
    st.warning("No data available for the selected ETF and weight range.")
    st.stop()

# ============================================================================
# Summary Metrics
# ============================================================================
st.header("Summary Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Starters", summary['total_starters'])

with col2:
    st.metric("Total Residuals", summary['total_residuals'])

with col3:
    st.metric("Starter Graduation Rate", f"{summary['starter_graduation_rate']:.1f}%")

with col4:
    st.metric("Residual Graduation Rate", f"{summary['residual_graduation_rate']:.1f}%")

st.divider()

# ============================================================================
# Outcome Breakdown
# ============================================================================
st.header("Outcome Breakdown")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Starters")

    if not starters_df.empty:
        # Outcome distribution
        starter_outcomes = starters_df['Outcome'].value_counts().reset_index()
        starter_outcomes.columns = ['Outcome', 'Count']

        fig_starter = px.pie(
            starter_outcomes,
            values='Count',
            names='Outcome',
            title='Starter Outcomes',
            color='Outcome',
            color_discrete_map={
                'Graduated': '#2ecc71',
                'Dropped': '#e74c3c',
                'Still Small': '#95a5a6'
            }
        )
        st.plotly_chart(fig_starter, use_container_width=True)

        # Metrics
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Graduated", summary['starter_graduated'])
        with col_b:
            st.metric("Dropped", summary['starter_dropped'])
        with col_c:
            still_small = summary['total_starters'] - summary['starter_graduated'] - summary['starter_dropped']
            st.metric("Still Small", still_small)
    else:
        st.info("No starter positions found")

with col2:
    st.subheader("Residuals")

    if not residuals_df.empty:
        # Outcome distribution
        residual_outcomes = residuals_df['Outcome'].value_counts().reset_index()
        residual_outcomes.columns = ['Outcome', 'Count']

        fig_residual = px.pie(
            residual_outcomes,
            values='Count',
            names='Outcome',
            title='Residual Outcomes',
            color='Outcome',
            color_discrete_map={
                'Graduated': '#2ecc71',
                'Dropped': '#e74c3c',
                'Still Small': '#95a5a6'
            }
        )
        st.plotly_chart(fig_residual, use_container_width=True)

        # Metrics
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Graduated", summary['residual_graduated'])
        with col_b:
            st.metric("Dropped", summary['residual_dropped'])
        with col_c:
            still_small = summary['total_residuals'] - summary['residual_graduated'] - summary['residual_dropped']
            st.metric("Still Small", still_small)
    else:
        st.info("No residual positions found")

st.divider()

# ============================================================================
# Comparison Charts
# ============================================================================
st.header("Starters vs Residuals Comparison")

# Prepare comparison data
comparison_data = pd.DataFrame({
    'Category': ['Starters', 'Residuals'],
    'Total': [summary['total_starters'], summary['total_residuals']],
    'Graduated': [summary['starter_graduated'], summary['residual_graduated']],
    'Dropped': [summary['starter_dropped'], summary['residual_dropped']],
    'Graduation Rate (%)': [summary['starter_graduation_rate'], summary['residual_graduation_rate']]
})

col1, col2 = st.columns(2)

with col1:
    # Bar chart comparison
    fig_compare = go.Figure()

    fig_compare.add_trace(go.Bar(
        name='Total',
        x=comparison_data['Category'],
        y=comparison_data['Total'],
        marker_color='#3498db'
    ))

    fig_compare.add_trace(go.Bar(
        name='Graduated',
        x=comparison_data['Category'],
        y=comparison_data['Graduated'],
        marker_color='#2ecc71'
    ))

    fig_compare.add_trace(go.Bar(
        name='Dropped',
        x=comparison_data['Category'],
        y=comparison_data['Dropped'],
        marker_color='#e74c3c'
    ))

    fig_compare.update_layout(
        title='Position Counts: Starters vs Residuals',
        barmode='group',
        xaxis_title='Category',
        yaxis_title='Count'
    )

    st.plotly_chart(fig_compare, use_container_width=True)

with col2:
    # Graduation rate comparison
    fig_rate = px.bar(
        comparison_data,
        x='Category',
        y='Graduation Rate (%)',
        title='Graduation Rate Comparison',
        color='Category',
        color_discrete_sequence=['#3498db', '#e74c3c']
    )
    fig_rate.update_layout(showlegend=False)
    st.plotly_chart(fig_rate, use_container_width=True)

st.divider()

# ============================================================================
# Days in Range Analysis
# ============================================================================
st.header("Time in Range Analysis")

col1, col2 = st.columns(2)

with col1:
    if not starters_df.empty:
        fig_starter_days = px.histogram(
            starters_df,
            x='Days_In_Range',
            color='Outcome',
            title='Starters: Days in Range by Outcome',
            color_discrete_map={
                'Graduated': '#2ecc71',
                'Dropped': '#e74c3c',
                'Still Small': '#95a5a6'
            },
            nbins=30
        )
        st.plotly_chart(fig_starter_days, use_container_width=True)

        # Average days by outcome
        if len(starters_df) > 0:
            avg_days = starters_df.groupby('Outcome')['Days_In_Range'].mean().reset_index()
            avg_days.columns = ['Outcome', 'Avg Days']
            st.dataframe(avg_days.style.format({'Avg Days': '{:.0f}'}), use_container_width=True)
    else:
        st.info("No starter data available")

with col2:
    if not residuals_df.empty:
        fig_residual_days = px.histogram(
            residuals_df,
            x='Days_In_Range',
            color='Outcome',
            title='Residuals: Days in Range by Outcome',
            color_discrete_map={
                'Graduated': '#2ecc71',
                'Dropped': '#e74c3c',
                'Still Small': '#95a5a6'
            },
            nbins=30
        )
        st.plotly_chart(fig_residual_days, use_container_width=True)

        # Average days by outcome
        if len(residuals_df) > 0:
            avg_days = residuals_df.groupby('Outcome')['Days_In_Range'].mean().reset_index()
            avg_days.columns = ['Outcome', 'Avg Days']
            st.dataframe(avg_days.style.format({'Avg Days': '{:.0f}'}), use_container_width=True)
    else:
        st.info("No residual data available")

st.divider()

# ============================================================================
# Timeline View
# ============================================================================
st.header("Entry Timeline")

# Combine starters and residuals for timeline
if not starters_df.empty or not residuals_df.empty:
    all_entries = []

    if not starters_df.empty:
        starters_copy = starters_df.copy()
        starters_copy['Type'] = 'Starter'
        all_entries.append(starters_copy)

    if not residuals_df.empty:
        residuals_copy = residuals_df.copy()
        residuals_copy['Type'] = 'Residual'
        all_entries.append(residuals_copy)

    combined_df = pd.concat(all_entries, ignore_index=True)
    combined_df = combined_df.sort_values('Entry_Date')

    # Timeline scatter
    fig_timeline = px.scatter(
        combined_df,
        x='Entry_Date',
        y='Entry_Weight',
        color='Type',
        symbol='Outcome',
        hover_name='Stock',
        hover_data=['Days_In_Range', 'Outcome'],
        title='Position Entry Timeline',
        color_discrete_map={'Starter': '#3498db', 'Residual': '#e74c3c'}
    )

    fig_timeline.update_layout(
        xaxis_title='Entry Date',
        yaxis_title='Entry Weight (%)'
    )

    st.plotly_chart(fig_timeline, use_container_width=True)

st.divider()

# ============================================================================
# Data Tables
# ============================================================================
st.header("Detailed Data")

tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Starters", "Residuals", "Reappeared"])

with tab1:
    st.subheader("Summary Statistics")

    summary_table = pd.DataFrame({
        'Metric': [
            'Total Starters',
            'Total Residuals',
            'Starter Graduated',
            'Starter Dropped',
            'Residual Graduated',
            'Residual Dropped',
            'Starter Graduation Rate (%)',
            'Residual Graduation Rate (%)'
        ],
        'Value': [
            summary['total_starters'],
            summary['total_residuals'],
            summary['starter_graduated'],
            summary['starter_dropped'],
            summary['residual_graduated'],
            summary['residual_dropped'],
            summary['starter_graduation_rate'],
            summary['residual_graduation_rate']
        ]
    })

    st.dataframe(summary_table, use_container_width=True)

with tab2:
    st.subheader("Starter Positions")
    if not starters_df.empty:
        st.dataframe(
            starters_df.style.format({
                'Entry_Weight': '{:.2f}%'
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.info("No starter positions found")

with tab3:
    st.subheader("Residual Positions")
    if not residuals_df.empty:
        st.dataframe(
            residuals_df.style.format({
                'Entry_Weight': '{:.2f}%'
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.info("No residual positions found")

with tab4:
    st.subheader("Reappeared Positions")
    st.markdown("Positions that exited and later re-entered the weight range.")
    if not reappeared_df.empty:
        st.dataframe(
            reappeared_df.style.format({
                'Re_entry_Weight': '{:.2f}%'
            }),
            use_container_width=True,
            height=400
        )

        # Summary metrics for reappeared
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Total Reappeared", len(reappeared_df))
        with col_b:
            avg_days = reappeared_df['Days_Absent'].mean() if 'Days_Absent' in reappeared_df.columns else 0
            st.metric("Avg Days Absent", f"{avg_days:.0f}")
        with col_c:
            avg_weight = reappeared_df['Re_entry_Weight'].mean() if 'Re_entry_Weight' in reappeared_df.columns else 0
            st.metric("Avg Re-entry Weight", f"{avg_weight:.2f}%")
    else:
        st.info("No reappeared positions found")

st.divider()

# ============================================================================
# Download Section
# ============================================================================
st.header("Download Data")

col1, col2 = st.columns(2)

with col1:
    sheets = {
        'Summary': pd.DataFrame([summary]),
        'Starters': starters_df if not starters_df.empty else pd.DataFrame(),
        'Residuals': residuals_df if not residuals_df.empty else pd.DataFrame(),
        'Reappeared': reappeared_df if not reappeared_df.empty else pd.DataFrame()
    }

    excel_data = create_multi_sheet_excel(sheets, 'starter_residual.xlsx')
    st.download_button(
        label="📥 Download All Data (Excel)",
        data=excel_data,
        file_name=f"{selected_etf}_{selected_range['folder']}_Starter_Residual.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col2:
    if not starters_df.empty or not residuals_df.empty:
        html_buffer = fig_timeline.to_html(include_plotlyjs='cdn')
        st.download_button(
            label="📥 Download Timeline Chart (HTML)",
            data=html_buffer,
            file_name=f"{selected_etf}_{selected_range['folder']}_Timeline_Chart.html",
            mime="text/html"
        )
