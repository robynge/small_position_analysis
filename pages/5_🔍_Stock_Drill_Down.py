"""
Stock Drill-Down Page
Select a stock to view its weight/price history with crossing events marked
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))
from utils.streamlit_config import (
    render_sidebar, calculate_crossing_analysis, load_etf_data
)

st.set_page_config(page_title="Stock Drill-Down", page_icon="🔍", layout="wide")

selected_etf, selected_range = render_sidebar()

boundary = selected_range['max']

st.title("Stock Drill-Down")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']} | **Boundary:** {boundary}%")

st.divider()

with st.spinner("Loading data..."):
    crossing_df, returns_df, summary = calculate_crossing_analysis(selected_etf, selected_range)
    full_df = load_etf_data(selected_etf)

if full_df.empty:
    st.warning("No data available.")
    st.stop()

# Get all tickers, sorted alphabetically
all_tickers = sorted(full_df['Bloomberg Name'].unique())

# Default to a ticker that has crossings if possible
default_idx = 0
if not crossing_df.empty:
    first_crossing_ticker = crossing_df.iloc[0]['Ticker']
    if first_crossing_ticker in all_tickers:
        default_idx = all_tickers.index(first_crossing_ticker)

selected_ticker = st.selectbox("Select Stock", all_tickers, index=default_idx)

st.divider()

# Get data for selected ticker
ticker_data = full_df[full_df['Bloomberg Name'] == selected_ticker].copy()
ticker_data = ticker_data.sort_values('Date')

if ticker_data.empty:
    st.warning(f"No data for {selected_ticker}.")
    st.stop()

# Get crossing events for this ticker
ticker_crossings = crossing_df[crossing_df['Ticker'] == selected_ticker] if not crossing_df.empty else pd.DataFrame()

# ============================================================================
# Dual-axis chart: Weight + Price with crossing arrows
# ============================================================================
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Weight line
fig.add_trace(
    go.Scatter(
        x=ticker_data['Date'],
        y=ticker_data['Weight'],
        name='Weight (%)',
        line=dict(color='#3498db', width=2),
        hovertemplate='%{x}<br>Weight: %{y:.2f}%<extra></extra>',
    ),
    secondary_y=False,
)

# Price line
fig.add_trace(
    go.Scatter(
        x=ticker_data['Date'],
        y=ticker_data['Stock_Price'],
        name='Price ($)',
        line=dict(color='#95a5a6', width=1.5),
        hovertemplate='%{x}<br>Price: $%{y:.2f}<extra></extra>',
    ),
    secondary_y=True,
)

# Boundary line as a legend trace
fig.add_trace(
    go.Scatter(
        x=[ticker_data['Date'].min(), ticker_data['Date'].max()],
        y=[boundary, boundary],
        name=f'Boundary ({boundary}%)',
        line=dict(color='orange', dash='dash', width=1.5),
        hoverinfo='skip',
    ),
    secondary_y=False,
)

# Add crossing event markers — one trace per direction to keep hover clean
if not ticker_crossings.empty:
    for direction, color, symbol in [('Starter', '#2ecc71', 'triangle-up'),
                                      ('Residual', '#e74c3c', 'triangle-down')]:
        events = ticker_crossings[ticker_crossings['Direction'] == direction]
        if events.empty:
            continue

        dates = []
        weights = []
        for _, event in events.iterrows():
            day_row = ticker_data[ticker_data['Date'] == event['Crossing_Date']]
            if day_row.empty:
                continue
            dates.append(event['Crossing_Date'])
            weights.append(day_row['Weight'].iloc[0])

        if dates:
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=weights,
                    mode='markers',
                    marker=dict(size=14, color=color, symbol=symbol,
                                line=dict(width=1, color='white')),
                    name=f'{direction} ({len(dates)})',
                    hovertemplate=f'{direction}<br>%{{x}}<br>Weight: %{{y:.2f}}%<extra></extra>',
                ),
                secondary_y=False,
            )

fig.update_layout(
    title=f"{selected_ticker}",
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
)
fig.update_yaxes(title_text='Weight (%)', secondary_y=False)
fig.update_yaxes(title_text='Price ($)', secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================================================
# Crossing events table for this ticker
# ============================================================================
if not ticker_crossings.empty:
    st.header("Crossing Events")
    display = ticker_crossings[['Direction', 'Crossing_Date', 'Days_Before_Crossing',
                                 'Days_After_Crossing', 'Avg_Return_Before_Crossing',
                                 'Avg_Return_After_Crossing']].copy()
    display['Avg_Return_Before_Crossing'] = display['Avg_Return_Before_Crossing'].round(4)
    display['Avg_Return_After_Crossing'] = display['Avg_Return_After_Crossing'].round(4)
    st.dataframe(display, use_container_width=True)
else:
    st.info(f"No crossing events for {selected_ticker} at boundary {boundary}%.")
