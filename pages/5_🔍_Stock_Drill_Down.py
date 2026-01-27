"""
Stock Drill-Down Page
Select a stock to view its weight/price history with crossing events marked
"""
import streamlit as st
import pandas as pd
import numpy as np
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

lo = selected_range['min']
hi = selected_range['max']

st.title("Stock Drill-Down")
st.markdown(f"**ETF:** {selected_etf} | **Weight Range:** {selected_range['label']} | **Boundaries:** {lo}% / {hi}%")

with st.spinner("Loading data..."):
    crossing_df, returns_df, summary = calculate_crossing_analysis(selected_etf, selected_range)
    full_df = load_etf_data(selected_etf)

if full_df.empty:
    st.warning("No data available.")
    st.stop()

# Build ticker display labels: "Ticker — Company Name (XX% in range)"
ticker_info = {}
for ticker in full_df['Bloomberg Name'].unique():
    tdata = full_df[full_df['Bloomberg Name'] == ticker]
    company = tdata['Company_Name'].iloc[0] if 'Company_Name' in tdata.columns else ticker
    total_days = len(tdata)
    days_in_range = len(tdata[(tdata['Weight'] >= lo) &
                               (tdata['Weight'] < hi)])
    pct_in_range = days_in_range / total_days * 100 if total_days > 0 else 0
    ticker_info[ticker] = {
        'company': company,
        'pct_in_range': pct_in_range,
        'label': f"{ticker} — {company} ({pct_in_range:.1f}%*)",
    }

display_labels = sorted(ticker_info.values(), key=lambda x: x['label'])
label_to_ticker = {v['label']: k for k, v in ticker_info.items()}
labels = [v['label'] for v in display_labels]

# Default to a ticker that has crossings if possible
default_idx = 0
if not crossing_df.empty:
    first_ticker = crossing_df.iloc[0]['Ticker']
    if first_ticker in ticker_info:
        target_label = ticker_info[first_ticker]['label']
        if target_label in labels:
            default_idx = labels.index(target_label)

selected_label = st.selectbox("Select Stock", labels, index=default_idx)
st.caption(f"\\* Percentage of days the stock's weight fell within the {selected_range['label']} range.")

selected_ticker = label_to_ticker[selected_label]

# Get data for selected ticker
ticker_data = full_df[full_df['Bloomberg Name'] == selected_ticker].copy()
ticker_data = ticker_data.sort_values('Date')

if ticker_data.empty:
    st.warning(f"No data for {selected_ticker}.")
    st.stop()

# Get crossing events for this ticker
ticker_crossings = crossing_df[crossing_df['Ticker'] == selected_ticker] if not crossing_df.empty else pd.DataFrame()

min_date = ticker_data['Date'].min().to_pydatetime()
max_date = ticker_data['Date'].max().to_pydatetime()

# ============================================================================
# Dual-axis chart: Weight + Price with crossing arrows
# ============================================================================
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Insert NaN rows at gaps > 7 days to break the line
ticker_data = ticker_data.copy()
ticker_data['Gap'] = ticker_data['Date'].diff().dt.days
gap_rows = ticker_data[ticker_data['Gap'] > 7].index
for idx in reversed(gap_rows.tolist()):
    nan_row = ticker_data.loc[[idx]].copy()
    nan_row['Date'] = ticker_data.loc[idx, 'Date'] - pd.Timedelta(days=1)
    nan_row[['Weight', 'Stock_Price']] = np.nan
    ticker_data = pd.concat([ticker_data.loc[:idx-1], nan_row, ticker_data.loc[idx:]])
ticker_data = ticker_data.sort_values('Date').reset_index(drop=True)

# Weight line
fig.add_trace(
    go.Scatter(
        x=ticker_data['Date'],
        y=ticker_data['Weight'],
        name='Weight (%)',
        line=dict(color='#3498db', width=2),
        connectgaps=False,
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
        connectgaps=False,
        hovertemplate='%{x}<br>Price: $%{y:.2f}<extra></extra>',
    ),
    secondary_y=True,
)

# Two boundary lines (lo and hi)
fig.add_trace(
    go.Scatter(
        x=[ticker_data['Date'].min(), ticker_data['Date'].max()],
        y=[lo, lo],
        name=f'Lower Boundary ({lo}%)',
        line=dict(color='orange', dash='dash', width=1.5),
        hoverinfo='skip',
    ),
    secondary_y=False,
)
fig.add_trace(
    go.Scatter(
        x=[ticker_data['Date'].min(), ticker_data['Date'].max()],
        y=[hi, hi],
        name=f'Upper Boundary ({hi}%)',
        line=dict(color='orange', dash='dash', width=1.5),
        hoverinfo='skip',
    ),
    secondary_y=False,
)

# Add crossing event markers — one trace per direction
if not ticker_crossings.empty:
    crossing_styles = {
        'Small Starter':  {'color': '#2ecc71', 'symbol': 'triangle-up'},
        'Big Starter':    {'color': '#27ae60', 'symbol': 'triangle-up'},
        'Super Starter':  {'color': '#1e8449', 'symbol': 'diamond'},
        'Small Residual': {'color': '#e74c3c', 'symbol': 'triangle-down'},
        'Big Residual':   {'color': '#c0392b', 'symbol': 'triangle-down'},
        'Super Residual': {'color': '#922b21', 'symbol': 'diamond'},
    }

    for direction, style in crossing_styles.items():
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
                    marker=dict(size=14, color=style['color'], symbol=style['symbol'],
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
    xaxis=dict(
        rangeslider=dict(visible=True, thickness=0.05),
        title=dict(text="Date Range", font=dict(size=11, color='gray'), standoff=0),
    ),
)

st.plotly_chart(fig, use_container_width=True)

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
    st.info(f"No crossing events for {selected_ticker} at boundaries {lo}% / {hi}%.")
