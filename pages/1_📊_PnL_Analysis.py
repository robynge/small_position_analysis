"""
P&L Analysis Page
Calculate and visualize adjusted P&L for positions in the selected weight range
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
    render_sidebar, calculate_pnl, format_currency,
    create_excel_download, create_multi_sheet_excel
)

st.set_page_config(
    page_title="P&L Analysis",
    page_icon="📊",
    layout="wide"
)

# Render sidebar
selected_etf, selected_range = render_sidebar()

st.title("📊 P&L Analysis")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']}")

st.divider()

# Calculate P&L
with st.spinner("Calculating P&L..."):
    daily_pnl, stock_pnl = calculate_pnl(selected_etf, selected_range)

if daily_pnl.empty:
    st.warning("No data available for the selected ETF and weight range.")
    st.stop()

# Summary metrics
st.subheader("Summary Metrics")

col1, col2, col3, col4 = st.columns(4)

total_pnl = daily_pnl['Adj_PnL'].sum()
avg_daily_pnl = daily_pnl['Adj_PnL'].mean()
max_pnl = daily_pnl['Adj_PnL'].max()
min_pnl = daily_pnl['Adj_PnL'].min()

with col1:
    color = "normal" if total_pnl >= 0 else "inverse"
    st.metric("Total Adjusted P&L", format_currency(total_pnl))

with col2:
    st.metric("Avg Daily P&L", format_currency(avg_daily_pnl))

with col3:
    st.metric("Best Day", format_currency(max_pnl))

with col4:
    st.metric("Worst Day", format_currency(min_pnl))

st.divider()

# P&L Line Chart
st.subheader("P&L Trend")

fig_line = make_subplots(specs=[[{"secondary_y": True}]])

# Daily P&L bars
fig_line.add_trace(
    go.Bar(
        x=daily_pnl['Date'],
        y=daily_pnl['Adj_PnL'],
        name='Daily P&L',
        marker_color=daily_pnl['Adj_PnL'].apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c'),
        opacity=0.6
    ),
    secondary_y=False
)

# Cumulative P&L line
fig_line.add_trace(
    go.Scatter(
        x=daily_pnl['Date'],
        y=daily_pnl['Cumulative_PnL'],
        name='Cumulative P&L',
        line=dict(color='#3498db', width=2),
        mode='lines'
    ),
    secondary_y=True
)

fig_line.update_layout(
    title=f'{selected_etf} - {selected_range["label"]} Position P&L',
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)
fig_line.update_xaxes(title_text='Date')
fig_line.update_yaxes(title_text='Daily P&L', secondary_y=False)
fig_line.update_yaxes(title_text='Cumulative P&L', secondary_y=True)

st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# Stock P&L Breakdown
st.subheader("P&L by Stock")

col1, col2 = st.columns([1, 1])

with col1:
    # Top contributors pie chart
    st.markdown("**Top P&L Contributors**")

    # Separate positive and negative
    positive_pnl = stock_pnl[stock_pnl['Total_PnL'] > 0].copy()
    negative_pnl = stock_pnl[stock_pnl['Total_PnL'] < 0].copy()

    # Top 10 positive
    top_positive = positive_pnl.head(10)

    if not top_positive.empty:
        fig_pie_pos = px.pie(
            top_positive,
            values='Total_PnL',
            names='Stock',
            title='Top 10 Positive Contributors',
            color_discrete_sequence=px.colors.sequential.Greens_r
        )
        fig_pie_pos.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie_pos, use_container_width=True)
    else:
        st.info("No positive P&L contributors found.")

with col2:
    # Bottom contributors
    st.markdown("**Bottom P&L Contributors**")

    top_negative = negative_pnl.head(10)

    if not top_negative.empty:
        # Make values positive for pie chart
        top_negative_abs = top_negative.copy()
        top_negative_abs['Total_PnL'] = top_negative_abs['Total_PnL'].abs()

        fig_pie_neg = px.pie(
            top_negative_abs,
            values='Total_PnL',
            names='Stock',
            title='Top 10 Negative Contributors (by absolute value)',
            color_discrete_sequence=px.colors.sequential.Reds_r
        )
        fig_pie_neg.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie_neg, use_container_width=True)
    else:
        st.info("No negative P&L contributors found.")

st.divider()

# Bar chart of all stocks
st.subheader("All Stocks P&L Ranking")

# Limit to top 30 for readability
display_stocks = stock_pnl.head(30) if len(stock_pnl) > 30 else stock_pnl

fig_bar = px.bar(
    display_stocks,
    x='Stock',
    y='Total_PnL',
    title=f'Stock P&L Ranking (Top {len(display_stocks)})',
    color='Total_PnL',
    color_continuous_scale=['#e74c3c', '#f5f5f5', '#2ecc71'],
    color_continuous_midpoint=0
)
fig_bar.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# Data tables
st.subheader("Data Tables")

tab1, tab2 = st.tabs(["Daily P&L", "Stock P&L"])

with tab1:
    st.dataframe(
        daily_pnl.style.format({
            'Adj_PnL': '${:,.0f}',
            'Dollar_PnL': '${:,.0f}',
            'Inflows_Outflows': '${:,.0f}',
            'Cumulative_PnL': '${:,.0f}'
        }),
        use_container_width=True,
        height=400
    )

with tab2:
    st.dataframe(
        stock_pnl.style.format({
            'Total_PnL': '${:,.0f}'
        }),
        use_container_width=True,
        height=400
    )

st.divider()

# Download buttons
st.subheader("Download Data")

col1, col2 = st.columns(2)

with col1:
    excel_data = create_multi_sheet_excel({
        'Daily_PnL': daily_pnl,
        'Stock_PnL': stock_pnl
    }, 'pnl_data.xlsx')

    st.download_button(
        label="📥 Download Excel (All Data)",
        data=excel_data,
        file_name=f"{selected_etf}_{selected_range['folder']}_PnL_Data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col2:
    # Download chart as HTML (interactive)
    html_buffer = fig_line.to_html(include_plotlyjs='cdn')
    st.download_button(
        label="📥 Download Chart (HTML)",
        data=html_buffer,
        file_name=f"{selected_etf}_{selected_range['folder']}_PnL_Chart.html",
        mime="text/html"
    )
