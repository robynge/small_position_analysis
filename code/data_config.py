"""
Central configuration for data file paths
This ensures all modules can find the historical data files consistently
All data files will be read from 'Sheet1' in the Excel files
"""

from pathlib import Path
import glob

# Get the absolute path to the project root (1 percent v3 directory)
CODE_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = CODE_DIR.parent.absolute()

# Input and output directories
INPUT_DIR = PROJECT_ROOT / 'input'
OUTPUT_DIR = PROJECT_ROOT / 'output'

# Default sheet name for all Excel files
SHEET_NAME = 'Sheet1'

# Store the selected data files
DATA_FILES = {}
AVAILABLE_ETF_FILES = {}  # Store the latest file for each ETF
SELECTED_ETF = None  # Currently selected ETF for analysis

def find_latest_etf_files():
    """Find data files for each ETF in the input folder"""
    global AVAILABLE_ETF_FILES
    AVAILABLE_ETF_FILES = {}

    # Search in input folder
    search_path = INPUT_DIR

    if search_path.exists():
        # Find all files for each ETF
        for fund in ['ARKF', 'ARKG', 'ARKK', 'ARKQ', 'ARKW', 'ARKX']:
            # Look for files with pattern FUND_Transformed_Data.xlsx
            pattern = str(search_path / f"{fund}_Transformed_Data.xlsx")
            files = glob.glob(pattern)

            for file in files:
                # Skip temporary Excel files
                if '~$' in file:
                    continue

                file_path = Path(file)
                if file_path.exists():
                    AVAILABLE_ETF_FILES[fund] = {
                        'path': file_path,
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

# Try to find data files with pattern matching
def find_data_file(fund_name):
    """Find the most recent data file for a fund"""
    pattern = str(PROJECT_ROOT / f"{fund_name}_historical data_*.xlsx")
    files = glob.glob(pattern)
    if files:
        # Return the most recent file (sorted by filename, assuming date format YYYYMMDD)
        return Path(sorted(files)[-1])
    return None

# Build DATA_FILES dynamically with default selection
def initialize_default_data_files():
    """Initialize with all available ETF files"""
    global DATA_FILES, SELECTED_ETF
    find_latest_etf_files()

    # Don't select any ETF by default - user will select in main menu
    # Just populate the available files
    pass

# Initialize on import
initialize_default_data_files()

def get_data_path(fund_name):
    """
    Get the absolute path to a fund's historical data file
    
    Args:
        fund_name: ETF name (ARKF, ARKG, ARKK, ARKQ, ARKW)
    
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

# Test when run directly
if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Code directory: {CODE_DIR}")
    print("\nData file locations:")
    for fund, path in DATA_FILES.items():
        exists = "✅" if path.exists() else "❌"
        print(f"  {exists} {fund}: {path}")
    
    print("\nVerifying all files...")
    verify_all_data_files()