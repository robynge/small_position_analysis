"""
Unified configuration module for ARK ETF analysis
Combines data paths, weight ranges, and common utility functions
"""
import os
import glob
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Get the absolute path to the project root
CODE_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = CODE_DIR.parent.absolute()

# Input and output directories
INPUT_DIR = PROJECT_ROOT / 'input'
OUTPUT_DIR = PROJECT_ROOT / 'output'
BASE_OUTPUT_DIR = '../output'

# Default sheet name for all Excel files
SHEET_NAME = 'Sheet1'

# ============================================================================
# WEIGHT RANGE CONFIGURATION
# ============================================================================

WEIGHT_RANGES = [
    {'min': 0, 'max': 1, 'label': '<1%', 'folder': 'under_1pct'},
    {'min': 1, 'max': 2.5, 'label': '1-2.5%', 'folder': '1_to_2.5pct'},
    {'min': 2.5, 'max': 5, 'label': '2.5-5%', 'folder': '2.5_to_5pct'},
    {'min': 5, 'max': 7.5, 'label': '5-7.5%', 'folder': '5_to_7.5pct'},
    {'min': 7.5, 'max': 100, 'label': '>7.5%', 'folder': 'over_7.5pct'}
]

# Current weight range (will be set dynamically)
CURRENT_RANGE = None

# ============================================================================
# ETF DATA CONFIGURATION
# ============================================================================

# Store the selected data files
DATA_FILES = {}
AVAILABLE_ETF_FILES = {}  # Store the latest file for each ETF
SELECTED_ETF = None  # Currently selected ETF for analysis

# Cache for consolidated data file (to avoid re-reading large file)
_CONSOLIDATED_DATA_CACHE = None

# Initialize with None - will be set when a range is selected
OUTPUT_DIRS = None

# ============================================================================
# DATA FILE DISCOVERY FUNCTIONS
# ============================================================================

def find_latest_etf_files():
    """Find consolidated ETF data file in the input folder"""
    global AVAILABLE_ETF_FILES
    AVAILABLE_ETF_FILES = {}

    # Search for consolidated file
    search_path = INPUT_DIR
    consolidated_file = search_path / "Consolidated_ETF_Holdings.xlsx"

    if consolidated_file.exists():
        # All ETFs use the same consolidated file
        for fund in ['ARKF', 'ARKG', 'ARKK', 'ARKQ', 'ARKW', 'ARKX']:
            AVAILABLE_ETF_FILES[fund] = {
                'path': consolidated_file,
                'date': 'latest',
                'exists': True
            }

def set_selected_etf(etf_name):
    """Set single ETF to use for analysis"""
    global DATA_FILES, SELECTED_ETF
    SELECTED_ETF = etf_name
    DATA_FILES = {}

    if etf_name in AVAILABLE_ETF_FILES:
        DATA_FILES[etf_name] = AVAILABLE_ETF_FILES[etf_name]['path']

    return len(DATA_FILES) > 0

def get_available_etf_files():
    """Get all available ETF files (latest version for each)"""
    if not AVAILABLE_ETF_FILES:
        find_latest_etf_files()
    return AVAILABLE_ETF_FILES

def get_data_path(fund_name):
    """
    Get the absolute path to a fund's historical data file

    Args:
        fund_name: ETF name (ARKF, ARKG, ARKK, ARKQ, ARKW, ARKX)

    Returns:
        Path object to the data file
    """
    if fund_name not in DATA_FILES:
        raise ValueError(f"Unknown fund: {fund_name}. Must be one of {list(DATA_FILES.keys())}")

    path = DATA_FILES[fund_name]
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    return path

def verify_all_data_files():
    """Verify all data files exist"""
    missing = []
    for fund, path in DATA_FILES.items():
        if not path.exists():
            missing.append(f"{fund}: {path}")

    if missing:
        print("❌ Missing data files:")
        for m in missing:
            print(f"   - {m}")
        return False
    else:
        print("✅ All data files found")
        return True

# ============================================================================
# OUTPUT DIRECTORY FUNCTIONS
# ============================================================================

def get_output_dirs():
    """Get output directories based on current ETF and weight range"""
    # Create ETF-specific output directory
    if SELECTED_ETF:
        etf_dir = f'{BASE_OUTPUT_DIR}/{SELECTED_ETF}'
    else:
        etf_dir = f'{BASE_OUTPUT_DIR}/UNKNOWN'

    if CURRENT_RANGE:
        folder_suffix = f"_{CURRENT_RANGE['folder']}"
    else:
        folder_suffix = ""

    return {
        'starter': f'{etf_dir}/00_Starter_Residual{folder_suffix}',
        'pnl': f'{etf_dir}/01_PnL_Analysis{folder_suffix}',
        'position': f'{etf_dir}/02_Position_Analysis{folder_suffix}',
        'market_value': f'{etf_dir}/02_Market_Value_Analysis{folder_suffix}',
        'returns': f'{etf_dir}/03_Alternative_Returns{folder_suffix}',
        'graduation': f'{etf_dir}/04_Graduation_Analysis{folder_suffix}'
    }

def create_directories():
    """Create all output directories if they don't exist"""
    # Update OUTPUT_DIRS based on current range
    global OUTPUT_DIRS
    OUTPUT_DIRS = get_output_dirs()

    # Only create directories if a range is set
    if CURRENT_RANGE is None:
        print("⚠️  No weight range selected. Use set_current_range() first.")
        return

    # Create main directories
    for dir_path in OUTPUT_DIRS.values():
        os.makedirs(dir_path, exist_ok=True)

def set_current_range(weight_range):
    """Set the current weight range for analysis"""
    global CURRENT_RANGE, OUTPUT_DIRS
    CURRENT_RANGE = weight_range
    OUTPUT_DIRS = get_output_dirs()

def get_selected_etfs():
    """Get currently selected ETFs"""
    # Return only the selected ETF as a list for compatibility
    if SELECTED_ETF:
        return [SELECTED_ETF]
    else:
        return []

# ============================================================================
# COMMON DATA LOADING AND PROCESSING FUNCTIONS
# ============================================================================

def load_etf_data(etf_name):
    """
    Unified data loading function with standard preprocessing
    Reads from consolidated file and extracts specific ETF data

    Args:
        etf_name: ETF name (ARKF, ARKG, ARKK, ARKQ, ARKW, ARKX)

    Returns:
        DataFrame with Date converted to datetime and Weight converted to percentage
        Filters out currency assets and problematic stocks
        Includes affiliation_check column for filtering
    """
    global _CONSOLIDATED_DATA_CACHE

    # Read consolidated file (with caching to avoid re-reading large file)
    if _CONSOLIDATED_DATA_CACHE is None:
        print("Loading consolidated data file (this may take a moment)...")
        _CONSOLIDATED_DATA_CACHE = pd.read_excel(get_data_path(etf_name), sheet_name=SHEET_NAME)
        print(f"✓ Loaded {len(_CONSOLIDATED_DATA_CACHE):,} rows")

    consolidated_df = _CONSOLIDATED_DATA_CACHE

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

    # Filter out rows where the ETF doesn't hold this position (all values are NaN)
    df = df.dropna(subset=['Position', 'Weight'], how='all').copy()

    # Filter out currency assets and problematic stocks
    if 'Bloomberg Name' in df.columns:
        # Remove currency assets (Bloomberg Name contains 'Curncy')
        df = df[~df['Bloomberg Name'].str.contains('Curncy', case=False, na=False)].copy()

        # Remove TCS LI Equity (stock split data issue)
        df = df[df['Bloomberg Name'] != 'TCS LI Equity'].copy()

    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100

    # Add backward compatibility columns
    df['Company_Name'] = df['Bloomberg Name']  # For legacy code compatibility
    df['Market Value'] = df['MV']  # For legacy code compatibility

    return df

def filter_by_weight_range(df, weight_range=None):
    """
    Filter DataFrame by weight range and exclude affiliation check positions

    Args:
        df: DataFrame with 'Weight' and 'affiliation_check' columns (in percentage format)
        weight_range: Weight range dict with 'min' and 'max' keys
                      If None, uses CURRENT_RANGE
                      If CURRENT_RANGE is also None, defaults to <1%

    Returns:
        Filtered DataFrame (excludes positions with affiliation_check == 1)
    """
    if weight_range is None:
        weight_range = CURRENT_RANGE

    # Filter by weight range
    if weight_range:
        filtered = df[(df['Weight'] >= weight_range['min']) &
                     (df['Weight'] < weight_range['max'])].copy()
    else:
        # Default fallback for backward compatibility
        filtered = df[df['Weight'] < 1].copy()

    # Exclude positions with affiliation_check == 1
    if 'affiliation_check' in filtered.columns:
        filtered = filtered[filtered['affiliation_check'] == 0].copy()

    return filtered

def calculate_yesterday_values(df):
    """
    Calculate yesterday's position, price, and values for P&L calculation

    Args:
        df: DataFrame with 'Bloomberg Name', 'Position', 'Stock_Price' columns

    Returns:
        DataFrame with added columns:
        - Yesterday_Position
        - Yesterday_Price
        - Yesterday_Value
        - Today_Value
        - Price_Changed
    """
    df = df.copy()

    # Sort by stock and date
    df = df.sort_values(['Bloomberg Name', 'Date'])

    # Calculate yesterday's values
    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)

    # Calculate value-based P&L components
    df['Yesterday_Value'] = df['Yesterday_Position'] * df['Yesterday_Price']
    df['Today_Value'] = df['Yesterday_Position'] * df['Stock_Price']

    # Track price changes (for detecting non-trading days)
    df['Price_Changed'] = df['Stock_Price'] != df['Yesterday_Price']

    return df

def aggregate_to_weekly(df, date_column='Date', value_columns=None, agg_funcs=None):
    """
    Aggregate daily data to weekly data

    Args:
        df: DataFrame with date column
        date_column: Name of the date column
        value_columns: List of columns to aggregate (if None, uses all numeric columns)
        agg_funcs: Dict of {column: function} for aggregation (default: 'last' for all)

    Returns:
        DataFrame with weekly aggregated data
    """
    df = df.copy()

    # Add week identifier
    df['Week'] = pd.to_datetime(df[date_column]).dt.to_period('W')

    # Determine columns to aggregate
    if value_columns is None:
        # Use all numeric columns except the date column
        value_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    # Set default aggregation function
    if agg_funcs is None:
        agg_funcs = {col: 'last' for col in value_columns}

    # Add date to aggregation (always use last date of week)
    agg_funcs[date_column] = 'last'

    # Group by week and aggregate
    weekly_data = df.groupby('Week').agg(agg_funcs).reset_index()

    # Convert Week back to datetime (use start of week)
    weekly_data['Week_Start'] = weekly_data['Week'].dt.to_timestamp()

    # Sort by date
    weekly_data = weekly_data.sort_values(date_column)

    return weekly_data

# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_value(x, _pos=None):
    """
    Format y-axis values with B for billions, M for millions

    Args:
        x: Value to format
        _pos: Position parameter (unused, required by matplotlib FuncFormatter)

    Returns:
        Formatted string
    """
    if abs(x) >= 1e9:
        return f'${x/1e9:.1f}B'
    elif abs(x) >= 1e6:
        return f'${x/1e6:.0f}M'
    else:
        return f'${x/1e3:.0f}K'

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_default_data_files():
    """Initialize with all available ETF files"""
    global DATA_FILES, SELECTED_ETF
    find_latest_etf_files()
    # Don't select any ETF by default - user will select in main menu

# Initialize on import
initialize_default_data_files()

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Code directory: {CODE_DIR}")
    print("\nData file locations:")
    for fund, path in DATA_FILES.items():
        exists = "✅" if path.exists() else "❌"
        print(f"  {exists} {fund}: {path}")

    print("\nVerifying all files...")
    verify_all_data_files()
