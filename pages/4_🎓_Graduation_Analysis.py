"""
Graduation Analysis Page - Full Version
Track stocks that graduated from <1% to >=1% with daily returns and P&L
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))
from utils.streamlit_config import (
    render_sidebar, calculate_graduation, format_currency,
    create_excel_download, create_multi_sheet_excel
)

st.set_page_config(page_title="Graduation Analysis", page_icon="🎓", layout="wide")

selected_etf, selected_range = render_sidebar()

st.title("🎓 Graduation Analysis")
st.markdown(f"**ETF:** {selected_etf}")
st.markdown("Track stocks that graduated from <1% to >=1% with daily returns and P&L analysis.")

st.divider()

with st.spinner("Analyzing graduations..."):
    summary_df, returns_df, graduated_stocks = calculate_graduation(selected_etf)

if summary_df.empty or len(graduated_stocks) == 0:
    st.warning("No graduated stocks found for this ETF.")
    st.stop()

# ============================================================================
# Summary Statistics
# ============================================================================
st.header("Summary Statistics")

summary_row = summary_df.iloc[0]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Graduated Stocks", int(summary_row['Num_Graduated_Stocks']))
with col2:
    st.metric("Records Before", int(summary_row['Total_Records_Before']))
with col3:
    st.metric("Records After", int(summary_row['Total_Records_After']))
with col4:
    total_pnl = summary_row['Total_PnL_Before'] + summary_row['Total_PnL_After']
    st.metric("Total P&L", format_currency(total_pnl))

st.divider()

# ============================================================================
# Return Statistics Comparison
# ============================================================================
st.header("Return Statistics: Before vs After Graduation")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Before Graduation (<1%)")
    st.metric("Mean Daily Return", f"{summary_row['Mean_Return_Before_%']:.4f}%")
    st.metric("Median Daily Return", f"{summary_row['Median_Return_Before_%']:.4f}%")
    st.metric("Std Dev", f"{summary_row['Std_Return_Before_%']:.4f}%")
    st.metric("Total P&L", format_currency(summary_row['Total_PnL_Before']))

with col2:
    st.subheader("After Graduation (>=1%)")
    st.metric("Mean Daily Return", f"{summary_row['Mean_Return_After_%']:.4f}%")
    st.metric("Median Daily Return", f"{summary_row['Median_Return_After_%']:.4f}%")
    st.metric("Std Dev", f"{summary_row['Std_Return_After_%']:.4f}%")
    st.metric("Total P&L", format_currency(summary_row['Total_PnL_After']))

st.divider()

# ============================================================================
# P&L Comparison Chart
# ============================================================================
st.header("P&L Comparison")

col1, col2 = st.columns(2)

with col1:
    pnl_data = pd.DataFrame({
        'Period': ['Before Graduation', 'After Graduation'],
        'Total P&L': [summary_row['Total_PnL_Before'], summary_row['Total_PnL_After']]
    })
    fig_pnl = px.bar(pnl_data, x='Period', y='Total P&L', title='Total P&L by Period',
                     color='Period', color_discrete_sequence=['#3498db', '#2ecc71'])
    st.plotly_chart(fig_pnl, use_container_width=True)

with col2:
    return_data = pd.DataFrame({
        'Period': ['Before', 'After'],
        'Mean Return (%)': [summary_row['Mean_Return_Before_%'], summary_row['Mean_Return_After_%']],
        'Median Return (%)': [summary_row['Median_Return_Before_%'], summary_row['Median_Return_After_%']]
    })
    fig_return = go.Figure()
    fig_return.add_trace(go.Bar(name='Mean', x=return_data['Period'], y=return_data['Mean Return (%)'], marker_color='#3498db'))
    fig_return.add_trace(go.Bar(name='Median', x=return_data['Period'], y=return_data['Median Return (%)'], marker_color='#2ecc71'))
    fig_return.update_layout(title='Return Statistics by Period', barmode='group', yaxis_title='Return (%)')
    st.plotly_chart(fig_return, use_container_width=True)

st.divider()

# ============================================================================
# Daily Returns Distribution
# ============================================================================
st.header("Daily Returns Distribution")

if not returns_df.empty:
    before_returns = returns_df[returns_df['Period'] == 'Before_Graduation_<1%']['Daily_Return'] * 100
    after_returns = returns_df[returns_df['Period'] == 'After_Graduation_>=1%']['Daily_Return'] * 100

    col1, col2 = st.columns(2)

    with col1:
        fig_hist = go.Figure()
        if len(before_returns) > 0:
            fig_hist.add_trace(go.Histogram(x=before_returns, name='Before (<1%)', opacity=0.7, marker_color='#3498db', nbinsx=50))
        if len(after_returns) > 0:
            fig_hist.add_trace(go.Histogram(x=after_returns, name='After (>=1%)', opacity=0.7, marker_color='#2ecc71', nbinsx=50))
        fig_hist.update_layout(title='Daily Return Distribution', barmode='overlay', xaxis_title='Return (%)')
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        fig_box = go.Figure()
        if len(before_returns) > 0:
            fig_box.add_trace(go.Box(y=before_returns, name='Before (<1%)', marker_color='#3498db'))
        if len(after_returns) > 0:
            fig_box.add_trace(go.Box(y=after_returns, name='After (>=1%)', marker_color='#2ecc71'))
        fig_box.update_layout(title='Return Box Plot', yaxis_title='Return (%)')
        st.plotly_chart(fig_box, use_container_width=True)

st.divider()

# ============================================================================
# Graduated Stocks List
# ============================================================================
st.header("Graduated Stocks")

grad_list = []
for ticker, info in graduated_stocks.items():
    ticker_data = returns_df[returns_df['Ticker'] == ticker]
    before_data = ticker_data[ticker_data['Period'] == 'Before_Graduation_<1%']
    after_data = ticker_data[ticker_data['Period'] == 'After_Graduation_>=1%']

    grad_list.append({
        'Ticker': ticker,
        'Graduation Date': info['graduation_date'],
        'Days Before': len(before_data),
        'Days After': len(after_data),
        'Total P&L Before': before_data['Daily_PnL'].sum() if len(before_data) > 0 else 0,
        'Total P&L After': after_data['Daily_PnL'].sum() if len(after_data) > 0 else 0,
        'Avg Return Before (%)': before_data['Daily_Return'].mean() * 100 if len(before_data) > 0 else 0,
        'Avg Return After (%)': after_data['Daily_Return'].mean() * 100 if len(after_data) > 0 else 0
    })

grad_df = pd.DataFrame(grad_list)
grad_df = grad_df.sort_values('Graduation Date', ascending=False)

st.dataframe(grad_df.style.format({
    'Total P&L Before': '${:,.0f}',
    'Total P&L After': '${:,.0f}',
    'Avg Return Before (%)': '{:.4f}',
    'Avg Return After (%)': '{:.4f}'
}), use_container_width=True, height=400)

st.divider()

# ============================================================================
# Detailed Returns Data
# ============================================================================
st.header("Detailed Returns Data")

if not returns_df.empty:
    display_returns = returns_df.copy()
    display_returns['Daily_Return_%'] = display_returns['Daily_Return'] * 100

    st.dataframe(display_returns[['Date', 'Ticker', 'Weight', 'Daily_Return_%', 'Daily_PnL', 'Period']].style.format({
        'Weight': '{:.2f}%',
        'Daily_Return_%': '{:.4f}%',
        'Daily_PnL': '${:,.0f}'
    }), use_container_width=True, height=400)

st.divider()

# ============================================================================
# Download
# ============================================================================
st.header("Download Data")

col1, col2 = st.columns(2)

with col1:
    sheets = {
        'Summary': summary_df,
        'Graduated_Stocks': grad_df,
        'Daily_Returns': returns_df
    }
    excel_data = create_multi_sheet_excel(sheets, 'graduation.xlsx')
    st.download_button("📥 Download All Data (Excel)", excel_data,
                       f"{selected_etf}_Graduation_Analysis.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with col2:
    if 'fig_pnl' in dir():
        st.download_button("📥 Download Chart (HTML)", fig_pnl.to_html(include_plotlyjs='cdn'),
                           f"{selected_etf}_Graduation_Chart.html", "text/html")
