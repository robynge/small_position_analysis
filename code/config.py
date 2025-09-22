"""
Configuration file for output directories and weight ranges
"""
import os

# Weight range configuration
WEIGHT_RANGES = [
    {'min': 0, 'max': 1, 'label': '<1%', 'folder': 'under_1pct'},
    {'min': 1, 'max': 2.5, 'label': '1-2.5%', 'folder': '1_to_2.5pct'},
    {'min': 2.5, 'max': 5, 'label': '2.5-5%', 'folder': '2.5_to_5pct'},
    {'min': 5, 'max': 7.5, 'label': '5-7.5%', 'folder': '5_to_7.5pct'},
    {'min': 7.5, 'max': 100, 'label': '>7.5%', 'folder': 'over_7.5pct'}
]

# Current weight range (will be set dynamically)
CURRENT_RANGE = None

# Base output directory
BASE_OUTPUT_DIR = '../output'

def get_output_dirs():
    """Get output directories based on current ETF and weight range"""
    from data_config import SELECTED_ETF

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

# Initialize with None - will be set when a range is selected
OUTPUT_DIRS = None

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
    
    if CURRENT_RANGE:
        print(f"✅ All output directories created for {CURRENT_RANGE['label']} positions")
    else:
        print("✅ All output directories created successfully")

def set_current_range(weight_range):
    """Set the current weight range for analysis"""
    global CURRENT_RANGE, OUTPUT_DIRS
    CURRENT_RANGE = weight_range
    OUTPUT_DIRS = get_output_dirs()
    print(f"📊 Weight range set to: {CURRENT_RANGE['label']}")

def get_selected_etfs():
    """Get currently selected ETFs from data_config"""
    # Import here to avoid circular import
    from data_config import SELECTED_ETF
    # Return only the selected ETF as a list for compatibility
    if SELECTED_ETF:
        return [SELECTED_ETF]
    else:
        return []

def format_value(x, pos=None):
    """Format y-axis values with B for billions, M for millions"""
    if abs(x) >= 1e9:
        return f'${x/1e9:.1f}B'
    elif abs(x) >= 1e6:
        return f'${x/1e6:.0f}M'
    else:
        return f'${x/1e3:.0f}K'

# ETF list comes from data_config