"""
Streamlit configuration module for ARK ETF analysis dashboard
Provides data loading, caching, and utility functions for Streamlit app
Full functionality matching CLI version
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import io
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

CODE_DIR = Path(__file__).parent.parent.absolute()
PROJECT_ROOT = CODE_DIR.parent.absolute()
INPUT_DIR = PROJECT_ROOT / 'input'
OUTPUT_DIR = PROJECT_ROOT / 'output'

# ============================================================================
# CONSTANTS
# ============================================================================

ETFS = ['ARKF', 'ARKG', 'ARKK', 'ARKQ', 'ARKW', 'ARKX']

WEIGHT_RANGES = [
    {'min': 0, 'max': 1, 'label': '<1%', 'folder': 'under_1pct'},
    {'min': 1, 'max': 2.5, 'label': '1-2.5%', 'folder': '1_to_2.5pct'},
    {'min': 2.5, 'max': 5, 'label': '2.5-5%', 'folder': '2.5_to_5pct'},
    {'min': 5, 'max': 7.5, 'label': '5-7.5%', 'folder': '5_to_7.5pct'},
    {'min': 7.5, 'max': 100, 'label': '>7.5%', 'folder': 'over_7.5pct'}
]

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    if 'selected_etf' not in st.session_state:
        st.session_state.selected_etf = 'ARKK'
    if 'selected_range_idx' not in st.session_state:
        st.session_state.selected_range_idx = 0

def get_selected_etf():
    return st.session_state.get('selected_etf', 'ARKK')

def get_selected_range():
    idx = st.session_state.get('selected_range_idx', 0)
    return WEIGHT_RANGES[idx]

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

@st.cache_data
def load_etf_data(etf_name: str) -> pd.DataFrame:
    etf_file = INPUT_DIR / f"{etf_name}_Transformed_Data.xlsx"
    if not etf_file.exists():
        st.error(f"Data file not found: {etf_file}")
        return pd.DataFrame()

    df = pd.read_excel(etf_file)

    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
    df.rename(columns={'Market Value': 'MV'}, inplace=True)

    df = df.dropna(subset=['Position', 'Weight'], how='all').copy()
    df = df[df['Stock_Price'].notna() & (df['Stock_Price'] > 0)].copy()

    if 'Bloomberg Name' in df.columns:
        df = df[~df['Bloomberg Name'].str.contains('Curncy', case=False, na=False)].copy()
        # Exclude money market funds (no price movement, distort return analysis)
        EXCLUDED_TICKERS = [
            'MVRXX US Equity', 'FEDXX1Y US Equity', 'DGCXX US Equity',
            'FTOXX US Equity', 'FIRXX US Equity', 'MRVXX US Equity',
            'LAQ25 Comdty', '9991429D US Equity',
        ]
        df = df[~df['Bloomberg Name'].isin(EXCLUDED_TICKERS)].copy()

    df['Weight'] = df['Weight'] * 100
    df['Company_Name'] = df['Bloomberg Name']
    df['Market Value'] = df['MV']

    return df

def filter_by_weight_range(df: pd.DataFrame, weight_range: dict = None) -> pd.DataFrame:
    if weight_range is None:
        weight_range = get_selected_range()

    filtered = df[(df['Weight'] >= weight_range['min']) &
                  (df['Weight'] < weight_range['max'])].copy()

    return filtered

# ============================================================================
# P&L CALCULATION FUNCTIONS (FULL VERSION)
# ============================================================================

@st.cache_data
def calculate_pnl(etf_name: str, weight_range: dict) -> tuple:
    """
    Calculate adjusted P&L with detailed Position_Status tracking
    Matches original CLI version exactly
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Filter out invalid prices
    df = df[(df['Stock_Price'] > 0) & (df['Stock_Price'].notna())]

    # Sort by stock and date
    df = df.sort_values(['Bloomberg Name', 'Date'])

    # Calculate previous day values
    df['Day0_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Day0_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Day0_Date'] = df.groupby('Bloomberg Name')['Date'].shift(1)

    # Invalidate if gap > 7 days or previous price is 0
    gap_days = (df['Date'] - df['Day0_Date']).dt.days
    invalid_prev = (gap_days > 7) | (df['Day0_Price'] == 0)
    df.loc[invalid_prev, 'Day0_Position'] = float('nan')
    df.loc[invalid_prev, 'Day0_Price'] = float('nan')
    df.drop(columns=['Day0_Date'], inplace=True)

    # Adjust for stock splits: both price and position change significantly in opposite directions
    valid_both = (df['Day0_Position'] > 0) & (df['Position'] > 0) & df['Day0_Price'].notna()
    pos_ratio = df['Day0_Position'] / df['Position']
    price_ratio = df['Stock_Price'] / df['Day0_Price']
    price_big = (price_ratio > 1.5) | (price_ratio < 0.67)
    pos_big = (pos_ratio > 1.5) | (pos_ratio < 0.67)
    opposite = ((price_ratio > 1) & (pos_ratio > 1)) | ((price_ratio < 1) & (pos_ratio < 1))
    mv_preserved = (price_ratio / pos_ratio).between(0.5, 2.0)
    is_split = valid_both & price_big & pos_big & opposite & mv_preserved
    df.loc[is_split, 'Day0_Price'] = df.loc[is_split, 'Day0_Price'] * pos_ratio[is_split]
    df.loc[is_split, 'Day0_Position'] = df.loc[is_split, 'Position']

    # Current day (Day1) values
    df['Day1_Position'] = df['Position']
    df['Day1_Price'] = df['Stock_Price']

    # Market values
    df['Day0_MV'] = df['Day0_Position'] * df['Day0_Price']
    df['Day1_MV'] = df['Day1_Position'] * df['Day1_Price']

    # Fill NaN for first day / invalid previous day (treated as Entry)
    df['Day0_Position'] = df['Day0_Position'].fillna(0)
    df['Day0_Price'] = df['Day0_Price'].fillna(0)
    df['Day0_MV'] = df['Day0_MV'].fillna(0)

    # Identify position status
    df['Position_Status'] = 'Ongoing'
    df.loc[(df['Day0_Position'] == 0) & (df['Day1_Position'] > 0), 'Position_Status'] = 'Entry'
    df.loc[(df['Day0_Position'] > 0) & (df['Day1_Position'] == 0), 'Position_Status'] = 'Exit'

    # Calculate Dollar P&L
    df['Dollar_PnL'] = df['Day1_MV'] - df['Day0_MV']

    # Calculate Inflows/Outflows based on position status
    df['Inflows_Outflows'] = 0.0

    # Ongoing positions
    ongoing_mask = df['Position_Status'] == 'Ongoing'
    df.loc[ongoing_mask, 'Inflows_Outflows'] = (
        (df.loc[ongoing_mask, 'Day1_Position'] - df.loc[ongoing_mask, 'Day0_Position']) *
        (df.loc[ongoing_mask, 'Day1_Price'] + df.loc[ongoing_mask, 'Day0_Price']) / 2
    )

    # Entry positions
    entry_mask = df['Position_Status'] == 'Entry'
    df.loc[entry_mask, 'Inflows_Outflows'] = (
        df.loc[entry_mask, 'Day1_Position'] * df.loc[entry_mask, 'Day1_Price']
    )

    # Exit positions
    exit_mask = df['Position_Status'] == 'Exit'
    df.loc[exit_mask, 'Inflows_Outflows'] = (
        -df.loc[exit_mask, 'Day0_Position'] * df.loc[exit_mask, 'Day0_Price']
    )

    # Calculate Adjusted P&L
    df['Adj_PnL'] = df['Dollar_PnL'] - df['Inflows_Outflows']
    df.loc[exit_mask, 'Adj_PnL'] = 0.0

    # Filter for positions in current weight range
    df_small = filter_by_weight_range(df, weight_range)
    df_small = df_small[df_small['Day0_Position'].notna()]

    # Skip non-trading days
    df_small['Price_Changed'] = df_small['Day1_Price'] != df_small['Day0_Price']
    dates_with_changes = df_small.groupby('Date')['Price_Changed'].any()
    valid_dates = dates_with_changes[dates_with_changes].index
    df_small = df_small[df_small['Date'].isin(valid_dates)]

    if df_small.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Daily Total P&L
    daily_pnl = df_small.groupby('Date').agg({
        'Dollar_PnL': 'sum',
        'Inflows_Outflows': 'sum',
        'Adj_PnL': 'sum'
    }).reset_index()
    daily_pnl = daily_pnl.sort_values('Date')
    daily_pnl['Cumulative_Adj_PnL'] = daily_pnl['Adj_PnL'].cumsum()
    daily_pnl.rename(columns={'Cumulative_Adj_PnL': 'Cumulative_PnL'}, inplace=True)

    # Stock Total P&L
    stock_pnl = df_small.groupby('Bloomberg Name')['Adj_PnL'].sum().reset_index()
    stock_pnl.columns = ['Stock', 'Total_PnL']
    stock_pnl = stock_pnl.sort_values('Total_PnL', ascending=False)

    return daily_pnl, stock_pnl

# ============================================================================
# POSITION ANALYSIS FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_position_counts(etf_name: str) -> pd.DataFrame:
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    results = []
    for date in df['Date'].unique():
        day_data = df[df['Date'] == date]
        row = {'Date': date}
        for wr in WEIGHT_RANGES:
            mask = (day_data['Weight'] >= wr['min']) & (day_data['Weight'] < wr['max'])
            row[wr['label']] = mask.sum()
        results.append(row)

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values('Date')
    return result_df

@st.cache_data
def calculate_market_value(etf_name: str, weight_range: dict) -> pd.DataFrame:
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    filtered_df = filter_by_weight_range(df, weight_range)
    total_aum = df.groupby('Date')['MV'].sum().reset_index()
    total_aum.rename(columns={'MV': 'Total_AUM'}, inplace=True)

    daily_mv = filtered_df.groupby('Date')['MV'].sum().reset_index()
    daily_mv.rename(columns={'MV': 'Range_MV'}, inplace=True)
    daily_mv = daily_mv.merge(total_aum, on='Date', how='left')
    daily_mv['Pct_of_AUM'] = (daily_mv['Range_MV'] / daily_mv['Total_AUM']) * 100

    daily_mv['Week'] = pd.to_datetime(daily_mv['Date']).dt.to_period('W')
    weekly_mv = daily_mv.groupby('Week').agg({
        'Date': 'last', 'Range_MV': 'last', 'Total_AUM': 'last', 'Pct_of_AUM': 'last'
    }).reset_index()
    weekly_mv = weekly_mv.sort_values('Date')
    return weekly_mv

@st.cache_data
def calculate_market_value_by_range(etf_name: str) -> pd.DataFrame:
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    results = []
    for date in df['Date'].unique():
        day_data = df[df['Date'] == date]
        row = {'Date': date}
        total_mv = day_data['MV'].sum()
        for wr in WEIGHT_RANGES:
            mask = (day_data['Weight'] >= wr['min']) & (day_data['Weight'] < wr['max'])
            range_mv = day_data.loc[mask, 'MV'].sum()
            row[f'{wr["label"]}_MV'] = range_mv
            row[f'{wr["label"]}_Pct'] = (range_mv / total_mv * 100) if total_mv > 0 else 0
        results.append(row)

    result_df = pd.DataFrame(results)
    result_df['Week'] = pd.to_datetime(result_df['Date']).dt.to_period('W')
    agg_dict = {'Date': 'last'}
    for wr in WEIGHT_RANGES:
        agg_dict[f'{wr["label"]}_MV'] = 'last'
        agg_dict[f'{wr["label"]}_Pct'] = 'last'
    weekly_df = result_df.groupby('Week').agg(agg_dict).reset_index()
    weekly_df = weekly_df.sort_values('Date')
    return weekly_df

# ============================================================================
# ALTERNATIVE RETURNS FUNCTIONS (FULL VERSION WITH SmallOnly)
# ============================================================================

@st.cache_data
def calculate_alternative_returns(etf_name: str, weight_range: dict) -> pd.DataFrame:
    """
    Calculate returns: Actual, ExcludeSmall, AND SmallOnly
    Matches original CLI version
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    df = df.sort_values(['Bloomberg Name', 'Date']).reset_index(drop=True)
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Date'] = df.groupby('Bloomberg Name')['Date'].shift(1)

    # Invalidate if gap > 7 days or previous price is 0
    gap_days = (df['Date'] - df['Yesterday_Date']).dt.days
    invalid_prev = (gap_days > 7) | (df['Yesterday_Price'] == 0)
    df.loc[invalid_prev, 'Yesterday_Price'] = float('nan')
    df.drop(columns=['Yesterday_Date'], inplace=True)

    # Adjust for stock splits: both price and position change significantly in opposite directions
    valid_both = (df['Yesterday_Position'] > 0) & (df['Position'] > 0) & df['Yesterday_Price'].notna()
    pos_ratio = df['Yesterday_Position'] / df['Position']
    price_ratio = df['Stock_Price'] / df['Yesterday_Price']
    price_big = (price_ratio > 1.5) | (price_ratio < 0.67)
    pos_big = (pos_ratio > 1.5) | (pos_ratio < 0.67)
    opposite = ((price_ratio > 1) & (pos_ratio > 1)) | ((price_ratio < 1) & (pos_ratio < 1))
    mv_preserved = (price_ratio / pos_ratio).between(0.5, 2.0)
    is_split = valid_both & price_big & pos_big & opposite & mv_preserved
    df.loc[is_split, 'Yesterday_Price'] = df.loc[is_split, 'Yesterday_Price'] * pos_ratio[is_split]
    df.drop(columns=['Yesterday_Position'], inplace=True)

    df['Stock_Return'] = (df['Stock_Price'] - df['Yesterday_Price']) / df['Yesterday_Price']

    results = []
    for date in df['Date'].unique():
        date_df = df[df['Date'] == date].copy()
        date_df = date_df.dropna(subset=['Yesterday_Price', 'Stock_Return'])

        if len(date_df) == 0:
            continue

        # Skip non-trading days
        if (date_df['Stock_Price'] == date_df['Yesterday_Price']).all():
            continue

        # Positions IN the current range (small)
        small_positions = date_df[
            (date_df['Weight'] >= weight_range['min']) &
            (date_df['Weight'] < weight_range['max'])
        ].copy()

        # Positions OUTSIDE the current range (large)
        large_positions = date_df[
            (date_df['Weight'] < weight_range['min']) |
            (date_df['Weight'] >= weight_range['max'])
        ].copy()

        # Return for ALL positions (actual)
        total_weight = date_df['Weight'].sum()
        if total_weight > 0:
            date_df['Normalized_Weight'] = date_df['Weight'] / total_weight
            return_actual = (date_df['Stock_Return'] * date_df['Normalized_Weight']).sum()
        else:
            return_actual = 0

        # Return for SMALL positions only
        small_weight = small_positions['Weight'].sum()
        if small_weight > 0 and len(small_positions) > 0:
            small_positions['Normalized_Weight'] = small_positions['Weight'] / small_weight
            return_small_only = (small_positions['Stock_Return'] * small_positions['Normalized_Weight']).sum()
        else:
            return_small_only = 0

        # Return for LARGE positions only (excluding small)
        large_weight = large_positions['Weight'].sum()
        if large_weight > 0 and len(large_positions) > 0:
            large_positions['Normalized_Weight'] = large_positions['Weight'] / large_weight
            return_exclude_small = (large_positions['Stock_Return'] * large_positions['Normalized_Weight']).sum()
        else:
            return_exclude_small = 0

        results.append({
            'Date': date,
            'Return_Actual': return_actual,
            'Return_ExcludeSmall': return_exclude_small,
            'Return_SmallOnly': return_small_only
        })

    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values('Date').reset_index(drop=True)
        result_df['Cumulative_Actual'] = result_df['Return_Actual'].fillna(0).cumsum()
        result_df['Cumulative_ExcludeSmall'] = result_df['Return_ExcludeSmall'].fillna(0).cumsum()
        result_df['Cumulative_SmallOnly'] = result_df['Return_SmallOnly'].fillna(0).cumsum()

    return result_df

# ============================================================================
# CROSSING ANALYSIS FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_crossing_analysis(etf_name: str, weight_range: dict) -> tuple:
    """
    Unified crossing analysis that classifies stocks into four categories:
    - Starter: crossed from small -> large (upward crossing)
    - Residual: crossed from large -> small (downward crossing)
    - Native Small: always within range, never crossed
    - Native Large: always above range, never crossed

    Boundary = weight_range['max']. Crossing is bidirectional and each
    crossing event is recorded separately.

    Returns: (crossing_df, returns_df, category_summary)
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), {}

    boundary = weight_range['max']

    df = df.sort_values(['Bloomberg Name', 'Date']).reset_index(drop=True)

    # Calculate yesterday's values
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Weight'] = df.groupby('Bloomberg Name')['Weight'].shift(1)
    df['Yesterday_Date'] = df.groupby('Bloomberg Name')['Date'].shift(1)

    # Invalidate if gap > 7 days or previous price is 0
    gap_days = (df['Date'] - df['Yesterday_Date']).dt.days
    invalid_prev = (gap_days > 7) | (df['Yesterday_Price'] == 0)
    df.loc[invalid_prev, ['Yesterday_Price', 'Yesterday_Position', 'Yesterday_Weight']] = float('nan')
    df.drop(columns=['Yesterday_Date'], inplace=True)

    # Adjust for stock splits
    valid_both = (df['Yesterday_Position'] > 0) & (df['Position'] > 0) & df['Yesterday_Price'].notna()
    pos_ratio = df['Yesterday_Position'] / df['Position']
    price_ratio = df['Stock_Price'] / df['Yesterday_Price']
    price_big = (price_ratio > 1.5) | (price_ratio < 0.67)
    pos_big = (pos_ratio > 1.5) | (pos_ratio < 0.67)
    opposite = ((price_ratio > 1) & (pos_ratio > 1)) | ((price_ratio < 1) & (pos_ratio < 1))
    mv_preserved = (price_ratio / pos_ratio).between(0.5, 2.0)
    is_split = valid_both & price_big & pos_big & opposite & mv_preserved
    df.loc[is_split, 'Yesterday_Price'] = df.loc[is_split, 'Yesterday_Price'] * pos_ratio[is_split]
    df.loc[is_split, 'Yesterday_Position'] = df.loc[is_split, 'Position']

    df['Daily_Return'] = (df['Stock_Price'] - df['Yesterday_Price']) / df['Yesterday_Price']
    df['Daily_PnL'] = df['Yesterday_Position'] * (df['Stock_Price'] - df['Yesterday_Price'])

    # Detect crossings per ticker
    crossing_records = []
    ticker_first_direction = {}  # ticker -> first crossing direction

    for ticker, group in df.groupby('Bloomberg Name'):
        group = group.sort_values('Date').reset_index(drop=True)
        valid = group['Yesterday_Weight'].notna()
        yesterday_large = group['Yesterday_Weight'] >= boundary
        today_large = group['Weight'] >= boundary
        crossed = valid & (yesterday_large != today_large)

        crossing_indices = group.index[crossed].tolist()
        if not crossing_indices:
            continue

        crossings_for_ticker = []
        for idx in crossing_indices:
            row = group.loc[idx]
            direction = 'Starter' if row['Weight'] >= boundary else 'Residual'
            crossings_for_ticker.append({'idx': group.index.get_loc(idx), 'date': row['Date'], 'direction': direction})

        ticker_first_direction[ticker] = crossings_for_ticker[0]['direction']

        # Build crossing_df records with before/after windows
        for ci, crossing in enumerate(crossings_for_ticker):
            before_start = crossings_for_ticker[ci - 1]['idx'] if ci > 0 else 0
            after_end = crossings_for_ticker[ci + 1]['idx'] - 1 if ci < len(crossings_for_ticker) - 1 else len(group) - 1

            before_returns = group.iloc[before_start:crossing['idx']]['Daily_Return'].dropna()
            after_returns = group.iloc[crossing['idx']:after_end + 1]['Daily_Return'].dropna()

            crossing_records.append({
                'Ticker': ticker,
                'Direction': crossing['direction'],
                'Crossing_Date': crossing['date'],
                'Days_Before_Crossing': len(before_returns),
                'Days_After_Crossing': len(after_returns),
                'Avg_Return_Before_Crossing': before_returns.mean() * 100 if len(before_returns) > 0 else 0,
                'Avg_Return_After_Crossing': after_returns.mean() * 100 if len(after_returns) > 0 else 0,
            })

    crossing_df = pd.DataFrame(crossing_records)

    # Build returns_df with Period labels (vectorized)
    # Classify each ticker: crossed tickers use first direction, others are Native
    all_large = df.groupby('Bloomberg Name')['Weight'].apply(lambda w: (w >= boundary).all())
    ticker_period = {}
    for ticker in df['Bloomberg Name'].unique():
        if ticker in ticker_first_direction:
            ticker_period[ticker] = ticker_first_direction[ticker]
        elif all_large[ticker]:
            ticker_period[ticker] = 'Native Large'
        else:
            ticker_period[ticker] = 'Native Small'

    returns_df = df[df['Daily_Return'].notna()][['Date', 'Bloomberg Name', 'Weight', 'Daily_Return', 'Daily_PnL']].copy()
    returns_df.rename(columns={'Bloomberg Name': 'Ticker'}, inplace=True)
    returns_df['Period'] = returns_df['Ticker'].map(ticker_period)

    # Build category_summary from ticker_period (single source of truth)
    period_counts = pd.Series(ticker_period).value_counts()
    category_summary = {}
    for period, key in [('Starter', 'starter'), ('Residual', 'residual'),
                        ('Native Small', 'native_small'), ('Native Large', 'native_large')]:
        category_summary[f'count_{key}'] = int(period_counts.get(period, 0))
        subset = returns_df.loc[returns_df['Period'] == period, 'Daily_Return']
        category_summary[f'mean_return_{key}'] = subset.mean() * 100 if len(subset) > 0 else 0

    return crossing_df, returns_df, category_summary

# ============================================================================
# DOWNLOAD HELPER FUNCTIONS
# ============================================================================

def create_excel_download(df: pd.DataFrame, filename: str) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def create_multi_sheet_excel(sheets: dict, filename: str) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, df in sheets.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()

# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_currency(value):
    if pd.isna(value):
        return "N/A"
    if abs(value) >= 1e9:
        return f"${value/1e9:.2f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:.2f}M"
    elif abs(value) >= 1e3:
        return f"${value/1e3:.2f}K"
    else:
        return f"${value:.2f}"

def format_percentage(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"

# ============================================================================
# SIDEBAR COMPONENT
# ============================================================================

def render_sidebar():
    init_session_state()
    st.sidebar.title("ARK Small Position Dashboard")

    etf_idx = ETFS.index(st.session_state.selected_etf) if st.session_state.selected_etf in ETFS else 0
    selected_etf = st.sidebar.selectbox("Select ETF", ETFS, index=etf_idx, key='etf_selector')
    st.session_state.selected_etf = selected_etf

    range_labels = [wr['label'] for wr in WEIGHT_RANGES]
    selected_range_label = st.sidebar.selectbox(
        "Select Weight Range", range_labels,
        index=st.session_state.selected_range_idx, key='range_selector'
    )
    st.session_state.selected_range_idx = range_labels.index(selected_range_label)

    return selected_etf, WEIGHT_RANGES[st.session_state.selected_range_idx]
