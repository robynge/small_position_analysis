"""
Streamlit configuration module for ARK ETF analysis dashboard
Provides data loading, caching, and utility functions for Streamlit app
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import io

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Get the absolute path to the project root
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
    """Initialize session state variables"""
    if 'selected_etf' not in st.session_state:
        st.session_state.selected_etf = 'ARKK'
    if 'selected_range_idx' not in st.session_state:
        st.session_state.selected_range_idx = 0

def get_selected_etf():
    """Get currently selected ETF"""
    return st.session_state.get('selected_etf', 'ARKK')

def get_selected_range():
    """Get currently selected weight range"""
    idx = st.session_state.get('selected_range_idx', 0)
    return WEIGHT_RANGES[idx]

# ============================================================================
# DATA LOADING FUNCTIONS (WITH CACHING)
# ============================================================================

@st.cache_data(ttl=3600)
def load_consolidated_data():
    """Load the consolidated ETF holdings file (cached)"""
    consolidated_file = INPUT_DIR / "Consolidated_ETF_Holdings.xlsx"
    if not consolidated_file.exists():
        st.error(f"Data file not found: {consolidated_file}")
        return None
    return pd.read_excel(consolidated_file, sheet_name='Sheet1')

@st.cache_data
def load_etf_data(etf_name: str) -> pd.DataFrame:
    """
    Load and preprocess data for a specific ETF

    Args:
        etf_name: ETF name (ARKF, ARKG, ARKK, ARKQ, ARKW, ARKX)

    Returns:
        DataFrame with standardized columns
    """
    consolidated_df = load_consolidated_data()
    if consolidated_df is None:
        return pd.DataFrame()

    # Extract columns for specific ETF
    position_col = f'{etf_name}_Position'
    mv_col = f'{etf_name}_MV'
    weight_col = f'{etf_name}_Weight'

    # Select relevant columns
    df = consolidated_df[['Date', 'Bloomberg Name', position_col, mv_col, weight_col, 'affiliation check']].copy()

    # Rename columns to standard names
    df.rename(columns={
        position_col: 'Position',
        mv_col: 'MV',
        weight_col: 'Weight',
        'affiliation check': 'affiliation_check'
    }, inplace=True)

    # Calculate Stock_Price from MV and Position
    df['Stock_Price'] = np.where(df['Position'] > 0, df['MV'] / df['Position'], np.nan)

    # Convert Date to datetime
    df['Date'] = pd.to_datetime(df['Date'])

    # Filter out rows where the ETF doesn't hold this position
    df = df.dropna(subset=['Position', 'Weight'], how='all').copy()

    # Filter out currency assets and problematic stocks
    if 'Bloomberg Name' in df.columns:
        df = df[~df['Bloomberg Name'].str.contains('Curncy', case=False, na=False)].copy()
        df = df[df['Bloomberg Name'] != 'TCS LI Equity'].copy()

    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100

    # Add backward compatibility columns
    df['Company_Name'] = df['Bloomberg Name']
    df['Market Value'] = df['MV']

    return df

def filter_by_weight_range(df: pd.DataFrame, weight_range: dict = None, exclude_affiliated: bool = True) -> pd.DataFrame:
    """
    Filter DataFrame by weight range

    Args:
        df: DataFrame with 'Weight' column (in percentage format)
        weight_range: Weight range dict with 'min' and 'max' keys
        exclude_affiliated: Whether to exclude affiliated positions

    Returns:
        Filtered DataFrame
    """
    if weight_range is None:
        weight_range = get_selected_range()

    filtered = df[(df['Weight'] >= weight_range['min']) &
                  (df['Weight'] < weight_range['max'])].copy()

    if exclude_affiliated and 'affiliation_check' in filtered.columns:
        filtered = filtered[filtered['affiliation_check'] == 0].copy()

    return filtered

def calculate_yesterday_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate yesterday's position, price, and values for P&L calculation
    """
    df = df.copy()
    df = df.sort_values(['Bloomberg Name', 'Date'])

    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Yesterday_Value'] = df['Yesterday_Position'] * df['Yesterday_Price']
    df['Today_Value'] = df['Yesterday_Position'] * df['Stock_Price']
    df['Price_Changed'] = df['Stock_Price'] != df['Yesterday_Price']

    return df

# ============================================================================
# P&L CALCULATION FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_pnl(etf_name: str, weight_range: dict) -> tuple:
    """
    Calculate adjusted P&L for positions in the weight range

    Returns:
        Tuple of (daily_pnl_df, stock_pnl_df)
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Filter by weight range
    filtered_df = filter_by_weight_range(df, weight_range)
    if filtered_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Calculate yesterday values
    filtered_df = calculate_yesterday_values(filtered_df)

    # Filter out non-trading days
    filtered_df = filtered_df[filtered_df['Price_Changed'] == True].copy()

    # Calculate P&L components
    filtered_df['Dollar_PnL'] = filtered_df['MV'] - filtered_df['Yesterday_Value'].fillna(0)

    # Calculate position changes
    filtered_df['Position_Change'] = filtered_df['Position'] - filtered_df['Yesterday_Position'].fillna(0)
    filtered_df['Avg_Price'] = (filtered_df['Stock_Price'] + filtered_df['Yesterday_Price'].fillna(filtered_df['Stock_Price'])) / 2

    # Calculate inflows/outflows
    filtered_df['Inflows_Outflows'] = filtered_df['Position_Change'] * filtered_df['Avg_Price']

    # Handle entry case (first day - entire position is inflow)
    entry_mask = filtered_df['Yesterday_Position'].isna()
    filtered_df.loc[entry_mask, 'Inflows_Outflows'] = filtered_df.loc[entry_mask, 'Position'] * filtered_df.loc[entry_mask, 'Stock_Price']

    # Calculate adjusted P&L
    filtered_df['Adj_PnL'] = filtered_df['Dollar_PnL'] - filtered_df['Inflows_Outflows']

    # Handle exit case (set to 0)
    exit_mask = filtered_df['Position'] == 0
    filtered_df.loc[exit_mask, 'Adj_PnL'] = 0

    # Aggregate daily P&L
    daily_pnl = filtered_df.groupby('Date').agg({
        'Adj_PnL': 'sum',
        'Dollar_PnL': 'sum',
        'Inflows_Outflows': 'sum'
    }).reset_index()
    daily_pnl['Cumulative_PnL'] = daily_pnl['Adj_PnL'].cumsum()
    daily_pnl = daily_pnl.sort_values('Date')

    # Aggregate by stock
    stock_pnl = filtered_df.groupby('Bloomberg Name').agg({
        'Adj_PnL': 'sum'
    }).reset_index()
    stock_pnl = stock_pnl.sort_values('Adj_PnL', ascending=False)
    stock_pnl.rename(columns={'Bloomberg Name': 'Stock', 'Adj_PnL': 'Total_PnL'}, inplace=True)

    return daily_pnl, stock_pnl

# ============================================================================
# POSITION ANALYSIS FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_position_counts(etf_name: str) -> pd.DataFrame:
    """Calculate daily position counts across all weight ranges"""
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    # Filter out affiliated positions
    if 'affiliation_check' in df.columns:
        df = df[df['affiliation_check'] == 0].copy()

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
    """Calculate weekly market value for positions in the weight range"""
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    # Filter by weight range
    filtered_df = filter_by_weight_range(df, weight_range)

    # Get total AUM per day
    total_aum = df.groupby('Date')['MV'].sum().reset_index()
    total_aum.rename(columns={'MV': 'Total_AUM'}, inplace=True)

    # Aggregate filtered positions by date
    daily_mv = filtered_df.groupby('Date')['MV'].sum().reset_index()
    daily_mv.rename(columns={'MV': 'Range_MV'}, inplace=True)

    # Merge with total AUM
    daily_mv = daily_mv.merge(total_aum, on='Date', how='left')
    daily_mv['Pct_of_AUM'] = (daily_mv['Range_MV'] / daily_mv['Total_AUM']) * 100

    # Convert to weekly
    daily_mv['Week'] = pd.to_datetime(daily_mv['Date']).dt.to_period('W')
    weekly_mv = daily_mv.groupby('Week').agg({
        'Date': 'last',
        'Range_MV': 'last',
        'Total_AUM': 'last',
        'Pct_of_AUM': 'last'
    }).reset_index()
    weekly_mv = weekly_mv.sort_values('Date')

    return weekly_mv

@st.cache_data
def calculate_market_value_by_range(etf_name: str) -> pd.DataFrame:
    """Calculate weekly market value for all weight ranges"""
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    # Filter out affiliated positions
    if 'affiliation_check' in df.columns:
        df = df[df['affiliation_check'] == 0].copy()

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

    # Aggregate to weekly
    agg_dict = {'Date': 'last'}
    for wr in WEIGHT_RANGES:
        agg_dict[f'{wr["label"]}_MV'] = 'last'
        agg_dict[f'{wr["label"]}_Pct'] = 'last'

    weekly_df = result_df.groupby('Week').agg(agg_dict).reset_index()
    weekly_df = weekly_df.sort_values('Date')

    return weekly_df

# ============================================================================
# ALTERNATIVE RETURNS FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_alternative_returns(etf_name: str, weight_range: dict) -> pd.DataFrame:
    """
    Calculate returns with and without small positions

    Returns:
        DataFrame with actual vs excluding-small returns
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame()

    # Filter out affiliated positions
    if 'affiliation_check' in df.columns:
        df = df[df['affiliation_check'] == 0].copy()

    # Sort by stock and date
    df = df.sort_values(['Bloomberg Name', 'Date'])

    # Calculate daily returns for each stock
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Stock_Return'] = (df['Stock_Price'] - df['Yesterday_Price']) / df['Yesterday_Price']

    # Filter out first day for each stock (no return)
    df = df.dropna(subset=['Stock_Return'])

    results = []
    for date in df['Date'].unique():
        day_data = df[df['Date'] == date].copy()

        if day_data.empty:
            continue

        # Normalize weights for actual returns
        total_weight = day_data['Weight'].sum()
        if total_weight == 0:
            continue
        day_data['Norm_Weight'] = day_data['Weight'] / total_weight

        # Calculate actual return (all positions)
        actual_return = (day_data['Stock_Return'] * day_data['Norm_Weight']).sum()

        # Filter out positions in the selected weight range
        large_positions = day_data[(day_data['Weight'] < weight_range['min']) |
                                   (day_data['Weight'] >= weight_range['max'])]

        if large_positions.empty:
            exclude_return = 0
        else:
            large_total_weight = large_positions['Weight'].sum()
            if large_total_weight == 0:
                exclude_return = 0
            else:
                large_positions = large_positions.copy()
                large_positions['Norm_Weight'] = large_positions['Weight'] / large_total_weight
                exclude_return = (large_positions['Stock_Return'] * large_positions['Norm_Weight']).sum()

        results.append({
            'Date': date,
            'Actual_Return': actual_return,
            'Exclude_Small_Return': exclude_return,
            'Return_Diff': actual_return - exclude_return
        })

    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values('Date')
        result_df['Cumulative_Actual'] = result_df['Actual_Return'].cumsum()
        result_df['Cumulative_Exclude'] = result_df['Exclude_Small_Return'].cumsum()

    return result_df

# ============================================================================
# GRADUATION ANALYSIS FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_graduation(etf_name: str) -> tuple:
    """
    Identify stocks that graduated from <1% to >=1%

    Returns:
        Tuple of (summary_df, graduated_stocks_list)
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return pd.DataFrame(), []

    # Filter out affiliated positions
    if 'affiliation_check' in df.columns:
        df = df[df['affiliation_check'] == 0].copy()

    df = df.sort_values(['Bloomberg Name', 'Date'])

    graduated_stocks = []

    for stock in df['Bloomberg Name'].unique():
        stock_data = df[df['Bloomberg Name'] == stock].copy()

        # Find first date where weight < 1%
        small_dates = stock_data[stock_data['Weight'] < 1]
        if small_dates.empty:
            continue

        first_small_date = small_dates['Date'].min()

        # Find first date where weight >= 1% after being small
        after_small = stock_data[stock_data['Date'] > first_small_date]
        large_dates = after_small[after_small['Weight'] >= 1]

        if large_dates.empty:
            continue

        graduation_date = large_dates['Date'].min()

        # Calculate returns before and after graduation
        before_data = stock_data[(stock_data['Date'] >= first_small_date) &
                                  (stock_data['Date'] < graduation_date)]
        after_data = stock_data[stock_data['Date'] >= graduation_date]

        if len(before_data) < 2 or len(after_data) < 2:
            continue

        # Calculate price returns
        before_return = (before_data['Stock_Price'].iloc[-1] / before_data['Stock_Price'].iloc[0] - 1) * 100
        after_return = (after_data['Stock_Price'].iloc[-1] / after_data['Stock_Price'].iloc[0] - 1) * 100 if len(after_data) > 1 else 0

        graduated_stocks.append({
            'Stock': stock,
            'First_Small_Date': first_small_date,
            'Graduation_Date': graduation_date,
            'Days_Small': (graduation_date - first_small_date).days,
            'Return_Before_Graduation': before_return,
            'Return_After_Graduation': after_return
        })

    summary_df = pd.DataFrame(graduated_stocks)
    if not summary_df.empty:
        summary_df = summary_df.sort_values('Graduation_Date', ascending=False)

    return summary_df, [s['Stock'] for s in graduated_stocks]

# ============================================================================
# STARTER/RESIDUAL ANALYSIS FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_starter_residual(etf_name: str, weight_range: dict) -> tuple:
    """
    Identify starter and residual positions

    Returns:
        Tuple of (summary_stats, starters_df, residuals_df)
    """
    df = load_etf_data(etf_name)
    if df.empty:
        return {}, pd.DataFrame(), pd.DataFrame()

    # Filter out affiliated positions
    if 'affiliation_check' in df.columns:
        df = df[df['affiliation_check'] == 0].copy()

    df = df.sort_values(['Bloomberg Name', 'Date'])

    starters = []
    residuals = []

    for stock in df['Bloomberg Name'].unique():
        stock_data = df[df['Bloomberg Name'] == stock].copy()
        stock_data = stock_data.sort_values('Date')

        # Find all entries into the weight range
        in_range = (stock_data['Weight'] >= weight_range['min']) & (stock_data['Weight'] < weight_range['max'])
        stock_data['In_Range'] = in_range
        stock_data['Prev_In_Range'] = stock_data['In_Range'].shift(1).fillna(False)
        stock_data['Prev_Weight'] = stock_data['Weight'].shift(1)

        # Find entry dates
        entries = stock_data[(stock_data['In_Range']) & (~stock_data['Prev_In_Range'])]

        for _, entry_row in entries.iterrows():
            entry_date = entry_row['Date']
            prev_weight = entry_row['Prev_Weight']

            # Determine if starter or residual
            is_starter = pd.isna(prev_weight) or prev_weight < weight_range['min']

            # Find outcome
            future_data = stock_data[stock_data['Date'] > entry_date]

            if future_data.empty:
                outcome = 'Still Small'
                days_in_range = (stock_data['Date'].max() - entry_date).days
            else:
                graduated = future_data[future_data['Weight'] >= weight_range['max']]
                dropped = future_data[future_data['Weight'] < weight_range['min']]

                if not graduated.empty and (dropped.empty or graduated['Date'].min() < dropped['Date'].min()):
                    outcome = 'Graduated'
                    days_in_range = (graduated['Date'].min() - entry_date).days
                elif not dropped.empty:
                    outcome = 'Dropped'
                    days_in_range = (dropped['Date'].min() - entry_date).days
                else:
                    outcome = 'Still Small'
                    days_in_range = (stock_data['Date'].max() - entry_date).days

            record = {
                'Stock': stock,
                'Entry_Date': entry_date,
                'Entry_Weight': entry_row['Weight'],
                'Outcome': outcome,
                'Days_In_Range': days_in_range
            }

            if is_starter:
                starters.append(record)
            else:
                residuals.append(record)

    starters_df = pd.DataFrame(starters)
    residuals_df = pd.DataFrame(residuals)

    # Calculate summary stats
    summary = {
        'total_starters': len(starters_df),
        'total_residuals': len(residuals_df),
        'starter_graduated': len(starters_df[starters_df['Outcome'] == 'Graduated']) if not starters_df.empty else 0,
        'starter_dropped': len(starters_df[starters_df['Outcome'] == 'Dropped']) if not starters_df.empty else 0,
        'residual_graduated': len(residuals_df[residuals_df['Outcome'] == 'Graduated']) if not residuals_df.empty else 0,
        'residual_dropped': len(residuals_df[residuals_df['Outcome'] == 'Dropped']) if not residuals_df.empty else 0,
    }

    if summary['total_starters'] > 0:
        summary['starter_graduation_rate'] = summary['starter_graduated'] / summary['total_starters'] * 100
    else:
        summary['starter_graduation_rate'] = 0

    if summary['total_residuals'] > 0:
        summary['residual_graduation_rate'] = summary['residual_graduated'] / summary['total_residuals'] * 100
    else:
        summary['residual_graduation_rate'] = 0

    return summary, starters_df, residuals_df

# ============================================================================
# DOWNLOAD HELPER FUNCTIONS
# ============================================================================

def create_excel_download(df: pd.DataFrame, filename: str) -> bytes:
    """Create Excel file bytes for download"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def create_multi_sheet_excel(sheets: dict, filename: str) -> bytes:
    """Create Excel file with multiple sheets"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()

# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_currency(value):
    """Format value as currency with B/M/K suffix"""
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
    """Format value as percentage"""
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"

# ============================================================================
# SIDEBAR COMPONENT
# ============================================================================

def render_sidebar():
    """Render common sidebar with ETF and weight range selection"""
    init_session_state()

    st.sidebar.title("Settings")

    # ETF Selection
    etf_idx = ETFS.index(st.session_state.selected_etf) if st.session_state.selected_etf in ETFS else 0
    selected_etf = st.sidebar.selectbox(
        "Select ETF",
        ETFS,
        index=etf_idx,
        key='etf_selector'
    )
    st.session_state.selected_etf = selected_etf

    # Weight Range Selection
    range_labels = [wr['label'] for wr in WEIGHT_RANGES]
    selected_range_label = st.sidebar.selectbox(
        "Select Weight Range",
        range_labels,
        index=st.session_state.selected_range_idx,
        key='range_selector'
    )
    st.session_state.selected_range_idx = range_labels.index(selected_range_label)

    st.sidebar.divider()

    # Display current selection
    st.sidebar.markdown(f"**Current Selection:**")
    st.sidebar.markdown(f"- ETF: `{selected_etf}`")
    st.sidebar.markdown(f"- Range: `{selected_range_label}`")

    return selected_etf, WEIGHT_RANGES[st.session_state.selected_range_idx]
