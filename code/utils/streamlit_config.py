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
        EXCLUDED_TICKERS = ['MVRXX US Equity', 'FEDXX1Y US Equity', 'DGCXX US Equity']
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
# GRADUATION ANALYSIS FUNCTIONS (FULL VERSION WITH Daily P&L)
# ============================================================================

@st.cache_data
def calculate_graduation(etf_name: str) -> tuple:
    """
    Full graduation analysis with daily returns AND P&L
    Matches original CLI version
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), {}

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
    df.loc[is_split, 'Yesterday_Position'] = df.loc[is_split, 'Position']

    df['Daily_Return'] = (df['Stock_Price'] - df['Yesterday_Price']) / df['Yesterday_Price']
    df['Daily_PnL'] = df['Yesterday_Position'] * (df['Stock_Price'] - df['Yesterday_Price'])

    # Identify graduated stocks
    graduated_stocks = {}
    for ticker, group in df.groupby('Bloomberg Name'):
        group = group.sort_values('Date').reset_index(drop=True)
        started_small = False
        small_period_start_idx = None

        for idx in range(len(group)):
            weight = group.iloc[idx]['Weight']

            if weight < 1 and not started_small:
                started_small = True
                small_period_start_idx = idx

            if started_small and weight >= 1:
                graduation_date = group.iloc[idx]['Date']
                graduated_stocks[ticker] = {
                    'graduation_date': graduation_date,
                    'small_start_idx': small_period_start_idx
                }
                break

    if len(graduated_stocks) == 0:
        return pd.DataFrame(), pd.DataFrame(), {}

    # Collect detailed returns for graduated stocks
    all_returns = []
    for ticker, grad_info in graduated_stocks.items():
        ticker_df = df[df['Bloomberg Name'] == ticker].copy()
        ticker_df = ticker_df.sort_values('Date').reset_index(drop=True)

        graduation_date = grad_info['graduation_date']
        small_start_idx = grad_info['small_start_idx']

        for idx in range(len(ticker_df)):
            row = ticker_df.iloc[idx]
            if pd.isna(row['Yesterday_Price']):
                continue
            if idx < small_start_idx:
                continue

            period = 'Before_Graduation_<1%' if row['Date'] < graduation_date else 'After_Graduation_>=1%'

            all_returns.append({
                'Ticker': ticker,
                'Date': row['Date'],
                'Weight': row['Weight'],
                'Daily_Return': row['Daily_Return'],
                'Daily_PnL': row['Daily_PnL'],
                'Period': period,
                'Graduation_Date': graduation_date
            })

    returns_df = pd.DataFrame(all_returns)

    # Create summary with detailed statistics
    summary_data = []
    if len(returns_df) > 0:
        before_df = returns_df[returns_df['Period'] == 'Before_Graduation_<1%']
        after_df = returns_df[returns_df['Period'] == 'After_Graduation_>=1%']

        summary_data.append({
            'ETF': etf_name,
            'Num_Graduated_Stocks': len(graduated_stocks),
            'Total_Records_Before': len(before_df),
            'Total_Records_After': len(after_df),
            'Mean_Return_Before_%': before_df['Daily_Return'].mean() * 100 if len(before_df) > 0 else 0,
            'Mean_Return_After_%': after_df['Daily_Return'].mean() * 100 if len(after_df) > 0 else 0,
            'Median_Return_Before_%': before_df['Daily_Return'].median() * 100 if len(before_df) > 0 else 0,
            'Median_Return_After_%': after_df['Daily_Return'].median() * 100 if len(after_df) > 0 else 0,
            'Std_Return_Before_%': before_df['Daily_Return'].std() * 100 if len(before_df) > 0 else 0,
            'Std_Return_After_%': after_df['Daily_Return'].std() * 100 if len(after_df) > 0 else 0,
            'Mean_PnL_Before': before_df['Daily_PnL'].mean() if len(before_df) > 0 else 0,
            'Mean_PnL_After': after_df['Daily_PnL'].mean() if len(after_df) > 0 else 0,
            'Total_PnL_Before': before_df['Daily_PnL'].sum() if len(before_df) > 0 else 0,
            'Total_PnL_After': after_df['Daily_PnL'].sum() if len(after_df) > 0 else 0
        })

    summary_df = pd.DataFrame(summary_data)
    return summary_df, returns_df, graduated_stocks

# ============================================================================
# STARTER/RESIDUAL ANALYSIS FUNCTIONS (FULL VERSION WITH Reappeared)
# ============================================================================

@st.cache_data
def calculate_starter_residual(etf_name: str, weight_range: dict) -> tuple:
    """
    Full starter/residual analysis with Reappeared positions
    Matches original CLI version
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df.sort_values(['Bloomberg Name', 'Date'])

    # ===== STARTERS =====
    first_appearance = df.groupby('Bloomberg Name').first().reset_index()
    starter_tickers = first_appearance[
        (first_appearance['Weight'] >= weight_range['min']) &
        (first_appearance['Weight'] < weight_range['max'])
    ]['Bloomberg Name'].unique()

    starter_details = []
    for ticker in starter_tickers:
        ticker_data = df[df['Bloomberg Name'] == ticker].copy()
        entry_date = ticker_data['Date'].min()
        entry_weight = ticker_data['Weight'].iloc[0]
        max_weight = ticker_data['Weight'].max()
        final_weight = ticker_data['Weight'].iloc[-1]
        final_date = ticker_data['Date'].max()

        threshold = weight_range['max']
        if max_weight >= threshold:
            outcome = 'Graduated to Large'
            grad_dates = ticker_data[ticker_data['Weight'] >= threshold]['Date']
            days_to_outcome = (grad_dates.min() - entry_date).days if len(grad_dates) > 0 else 0
        elif final_weight == 0 or pd.isna(final_weight):
            outcome = 'Dropped'
            non_zero = ticker_data[ticker_data['Weight'] > 0]
            days_to_outcome = (non_zero['Date'].max() - entry_date).days if len(non_zero) > 0 else 0
        else:
            outcome = 'Still Small'
            days_to_outcome = (final_date - entry_date).days

        starter_details.append({
            'Bloomberg Name': ticker,
            'Entry Date': entry_date,
            'Entry Weight %': entry_weight,
            'Max Weight Achieved %': max_weight,
            'Final Weight %': final_weight,
            'Outcome': outcome,
            'Days to Outcome': days_to_outcome,
            'Days as Small Position': days_to_outcome
        })

    starters_df = pd.DataFrame(starter_details)

    # ===== RESIDUALS =====
    residual_details = []
    for ticker in df['Bloomberg Name'].unique():
        ticker_data = df[df['Bloomberg Name'] == ticker].copy()
        ticker_data = ticker_data.sort_values('Date')

        ticker_data['Prev_Date'] = ticker_data['Date'].shift(1)
        gap_days = (ticker_data['Date'] - ticker_data['Prev_Date']).dt.days
        valid_prev = gap_days <= 7

        ticker_data['Was_Large'] = (ticker_data['Weight'].shift(1) >= weight_range['max']) & valid_prev
        ticker_data['Is_Small'] = (
            (ticker_data['Weight'] >= weight_range['min']) &
            (ticker_data['Weight'] < weight_range['max'])
        )
        ticker_data['Transition'] = ticker_data['Was_Large'] & ticker_data['Is_Small']

        transitions = ticker_data[ticker_data['Transition']]
        for _, trans in transitions.iterrows():
            trans_date = trans['Date']
            before = ticker_data[ticker_data['Date'] < trans_date]
            after = ticker_data[ticker_data['Date'] >= trans_date]

            peak_weight = before['Weight'].max() if len(before) > 0 else 0
            trans_weight = trans['Weight']
            future_max = after['Weight'].max() if len(after) > 0 else 0
            final_weight = after['Weight'].iloc[-1] if len(after) > 0 else 0

            threshold = weight_range['max']
            if future_max >= threshold:
                outcome = 'Recovered to Large'
                recovery_dates = after[after['Weight'] >= threshold]['Date']
                days_as_residual = (recovery_dates.min() - trans_date).days if len(recovery_dates) > 0 else 0
            elif final_weight == 0 or pd.isna(final_weight):
                outcome = 'Dropped'
                non_zero = after[after['Weight'] > 0]
                days_as_residual = (non_zero['Date'].max() - trans_date).days if len(non_zero) > 0 else 0
            else:
                outcome = 'Still Residual'
                days_as_residual = (after['Date'].max() - trans_date).days if len(after) > 0 else 0

            residual_details.append({
                'Bloomberg Name': ticker,
                'Transition Date': trans_date,
                'Peak Weight Before %': peak_weight,
                'Weight at Transition %': trans_weight,
                'Weight Drawdown %': peak_weight - trans_weight,
                'Max Weight After %': future_max,
                'Final Weight %': final_weight,
                'Outcome': outcome,
                'Days as Residual': days_as_residual
            })

    residuals_df = pd.DataFrame(residual_details)

    # ===== REAPPEARED =====
    reappeared_details = []
    for ticker in df['Bloomberg Name'].unique():
        ticker_data = df[df['Bloomberg Name'] == ticker].copy()
        ticker_data = ticker_data.sort_values('Date')
        ticker_data['Date_Diff'] = ticker_data['Date'].diff().dt.days

        gaps = ticker_data[ticker_data['Date_Diff'] > 30]
        for _, gap in gaps.iterrows():
            gap_date = gap['Date']
            before_gap = ticker_data[ticker_data['Date'] < gap_date]['Date'].max()

            reappeared_details.append({
                'Bloomberg Name': ticker,
                'Exit Date': before_gap,
                'Re-entry Date': gap_date,
                'Days Absent': gap['Date_Diff'],
                'Re-entry Weight %': gap['Weight']
            })

    reappeared_df = pd.DataFrame(reappeared_details)

    # ===== SUMMARY =====
    graduated_count = len(starters_df[starters_df['Outcome'] == 'Graduated to Large']) if len(starters_df) > 0 else 0
    still_small_count = len(starters_df[starters_df['Outcome'] == 'Still Small']) if len(starters_df) > 0 else 0
    dropped_count = len(starters_df[starters_df['Outcome'] == 'Dropped']) if len(starters_df) > 0 else 0
    recovered_count = len(residuals_df[residuals_df['Outcome'] == 'Recovered to Large']) if len(residuals_df) > 0 else 0
    still_residual_count = len(residuals_df[residuals_df['Outcome'] == 'Still Residual']) if len(residuals_df) > 0 else 0
    residual_dropped_count = len(residuals_df[residuals_df['Outcome'] == 'Dropped']) if len(residuals_df) > 0 else 0

    summary = {
        'total_starters': len(starters_df),
        'total_residuals': len(residuals_df),
        'total_reappeared': len(reappeared_df),
        'starter_graduated': graduated_count,
        'starter_still_small': still_small_count,
        'starter_dropped': dropped_count,
        'residual_recovered': recovered_count,
        'residual_still_residual': still_residual_count,
        'residual_dropped': residual_dropped_count,
        'starter_graduation_rate': graduated_count / len(starters_df) * 100 if len(starters_df) > 0 else 0,
        'residual_recovery_rate': recovered_count / len(residuals_df) * 100 if len(residuals_df) > 0 else 0,
        'avg_days_starter': starters_df['Days as Small Position'].mean() if len(starters_df) > 0 else 0,
        'avg_days_residual': residuals_df['Days as Residual'].mean() if len(residuals_df) > 0 else 0,
        'avg_days_absent': reappeared_df['Days Absent'].mean() if len(reappeared_df) > 0 else 0
    }

    return summary, starters_df, residuals_df, reappeared_df

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
