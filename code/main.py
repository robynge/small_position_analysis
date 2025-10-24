"""
Main Script - Run all analysis steps with dynamic weight ranges
You can run for a single weight range or batch process all ranges
"""

import sys
import os
import importlib

# Set the working directory to code folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config import (create_directories, WEIGHT_RANGES, set_current_range, CURRENT_RANGE,
                    get_selected_etfs, set_selected_etf, get_available_etf_files)
import config

# Global flag for all ranges mode
ALL_RANGES_MODE = False

# Analysis modules with new numbering system
modules = {
    '0': ('00_starter_residual_analysis', 'Analyze starter & residual positions'),
    '1': ('01_calculate_pnl', 'Calculate P&L for positions'),
    '1.1': ('01_1_plot_pnl_pie', 'Plot P&L pie charts (top contributors)'),
    '1.2': ('01_2_plot_pnl_line', 'Plot P&L line charts (daily & cumulative)'),
    '2': ('02_calculate_positions', 'Calculate position counts in weight range'),
    '2.2': ('02_2_calculate_market_value', 'Calculate market value data'),
    '2.3': ('02_3_plot_market_value', 'Plot market value charts'),
    '3': ('03_calculate_alternative_returns', 'Calculate alternative returns data'),
    '3.1': ('03_1_plot_alternative_returns', 'Plot alternative returns charts'),
    '3.2': ('03_2_plot_distribution', 'Plot return distribution charts'),
    '4': ('04_calculate_graduation', 'Calculate graduation analysis data'),
    '4.1': ('04_1_plot_graduation', 'Plot graduation analysis charts')
}

def print_menu():
    """Print menu options"""
    # Check if we're in all ranges mode
    if globals().get('ALL_RANGES_MODE', False):
        current_label = 'ALL RANGES MODE'
    elif CURRENT_RANGE:
        current_label = CURRENT_RANGE['label']
    else:
        current_label = '<1%'

    # Show current selected ETF
    if config.SELECTED_ETF and config.DATA_FILES:
        data_info = f"Selected ETF: {config.SELECTED_ETF}"
    else:
        data_info = "No ETF selected - Please select an ETF first (option E)"

    print("\n" + "="*60)
    print(f"ARK ETF Position Analysis - {current_label}")
    print(f"{data_info}")
    print("="*60)
    print("\nAvailable steps:")
    
    # Group modules by major number
    last_major = None
    for key in sorted(modules.keys()):
        _, desc = modules[key]  # Using _ to indicate module name not used here
        major = key.split('.')[0]
        if major != last_major and '.' not in key:
            if last_major is not None:
                print()  # Add spacing between groups
            last_major = major
        indent = "    " if '.' in key else "  "
        print(f"{indent}{key}. {desc}")
    print("  A. Run all steps for current range")
    print("  B. Batch run all steps for ALL weight ranges")
    print("  R. Select weight range")
    print("  E. Select ETF for analysis")
    print("  Q. Quit")
    print("-"*60)

def select_weight_range():
    """Let user select a weight range"""
    print("\n" + "="*40)
    print("Select Weight Range:")
    print("="*40)
    for i, range_config in enumerate(WEIGHT_RANGES):
        print(f"  {i+1}. {range_config['label']}")
    print("  0. All ranges (select step after)")
    print("-"*40)
    
    choice = input("Select range (0-5): ").strip()
    
    if choice == '0':
        return 'ALL_RANGES'  # Special marker for all ranges
    elif choice in ['1', '2', '3', '4', '5']:
        selected = WEIGHT_RANGES[int(choice)-1]
        set_current_range(selected)
        create_directories()
        return selected
    else:
        print("Invalid choice")
        return False

def select_etf():
    """Let user select which ETF to analyze"""
    print("\n" + "="*60)
    print("Select ETF for Analysis")
    print("="*60)

    # Get all available ETF files
    available = get_available_etf_files()

    if not available:
        print("❌ No data files found in input folder!")
        return False

    # Show available ETF files
    print("\nAvailable ETF data files:")
    print("-"*60)

    etf_list = []
    for i, etf in enumerate(['ARKF', 'ARKG', 'ARKK', 'ARKQ', 'ARKW', 'ARKX'], 1):
        if etf in available:
            selected = '►' if etf == config.SELECTED_ETF else ' '
            etf_list.append(etf)
            print(f"  [{selected}] {i}. {etf}: {available[etf]['path'].name}")
        else:
            print(f"  [ ] {i}. {etf}: Not found")

    if not etf_list:
        print("\n❌ No ETF files found!")
        return False

    print("-"*60)
    print("  0. Cancel")
    print("-"*60)

    choice = input("\nSelect ETF (1-6, or 0 to cancel): ").strip()

    if choice == '0':
        print("Selection cancelled")
        return False

    etf_map = {'1': 'ARKF', '2': 'ARKG', '3': 'ARKK', '4': 'ARKQ', '5': 'ARKW', '6': 'ARKX'}

    if choice in etf_map:
        selected_etf = etf_map[choice]
        if selected_etf in available:
            set_selected_etf(selected_etf)
            create_directories()  # Create directories for this ETF
            print(f"\n✅ Selected ETF: {selected_etf}")
            print(f"   File: {available[selected_etf]['path'].name}")
            return True
        else:
            print(f"❌ {selected_etf} file not available")
            return False
    else:
        print("Invalid choice")
        return False

def run_module(module_name, description):
    """Run a specific module"""
    weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else 'All'
    print(f"\n▶ {description} [{weight_label}]")
    try:
        # Clear module cache to ensure fresh import
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        # Import and run
        module = importlib.import_module(module_name)
        if hasattr(module, 'run'):
            module.run()
        elif hasattr(module, 'main'):
            module.main()
        else:
            print(f"  ⚠️  Module {module_name} has no run() or main() function")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()

def run_all_modules():
    """Run all analysis modules for current weight range"""
    # Ensure directories exist
    create_directories()

    weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
    print(f"\n{'='*60}")
    print(f"Running All Steps [{weight_label}]")
    print(f"{'='*60}")

    for key in sorted(modules.keys()):
        module_name, description = modules[key]
        run_module(module_name, description)

    print(f"\n{'='*60}")
    print(f"✅ Completed")
    print(f"{'='*60}")

def batch_run_all_ranges():
    """Run all modules for all weight ranges"""
    print("\n" + "="*60)
    print("Batch Mode: All Weight Ranges")
    print("="*60)

    for range_config in WEIGHT_RANGES:
        print(f"\n{'='*60}")
        print(f"Range: {range_config['label']}")
        print(f"{'='*60}")

        # Set current range
        set_current_range(range_config)
        create_directories()

        # Run all modules for this range
        for key in sorted(modules.keys()):
            module_name, description = modules[key]
            run_module(module_name, description)

    print(f"\n{'='*60}")
    print("✅ All Ranges Completed")
    print(f"{'='*60}")

def run_specific_module_all_ranges(module_key):
    """Run a specific module for all weight ranges"""
    module_name, description = modules[module_key]

    print(f"\n{'='*60}")
    print(f"{description} - All Ranges")
    print(f"{'='*60}")

    for range_config in WEIGHT_RANGES:
        print(f"\n▶ Range: {range_config['label']}")

        # Set current range
        set_current_range(range_config)
        create_directories()

        # Run the specific module
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, 'run'):
                module.run()
            elif hasattr(module, 'main'):
                module.main()
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n{'='*60}")
    print(f"✅ Completed")
    print(f"{'='*60}")

def select_multiple_etfs():
    """Let user select multiple ETFs"""
    print("\n" + "="*60)
    print("Select ETFs for Analysis (enter numbers separated by comma)")
    print("="*60)

    # Get all available ETF files
    available = get_available_etf_files()

    if not available:
        print("❌ No data files found in input folder!")
        return []

    # Show available ETF files
    print("\nAvailable ETFs:")
    print("-"*60)

    etf_list = ['ARKF', 'ARKG', 'ARKK', 'ARKQ', 'ARKW', 'ARKX']
    for i, etf in enumerate(etf_list, 1):
        if etf in available:
            print(f"  {i}. {etf}")
        else:
            print(f"  {i}. {etf} (NOT FOUND)")

    print("-"*60)
    print("Examples: '1,3,5' or '1-6' for all")
    print("-"*60)

    choice = input("\nSelect ETFs (e.g., 1,2,3): ").strip()

    # Parse input
    selected_etfs = []
    if '-' in choice:
        # Handle range like '1-6'
        parts = choice.split('-')
        if len(parts) == 2:
            try:
                start = int(parts[0])
                end = int(parts[1])
                for i in range(start, end + 1):
                    if 1 <= i <= len(etf_list):
                        etf = etf_list[i-1]
                        if etf in available:
                            selected_etfs.append(etf)
            except:
                print("Invalid range format")
                return []
    else:
        # Handle comma-separated like '1,3,5'
        numbers = [n.strip() for n in choice.split(',')]
        for n in numbers:
            try:
                idx = int(n)
                if 1 <= idx <= len(etf_list):
                    etf = etf_list[idx-1]
                    if etf in available:
                        selected_etfs.append(etf)
            except:
                print(f"Invalid number: {n}")

    if selected_etfs:
        print(f"\n✅ Selected ETFs: {', '.join(selected_etfs)}")
    else:
        print("❌ No valid ETFs selected")

    return selected_etfs

def select_multiple_ranges():
    """Let user select multiple weight ranges"""
    print("\n" + "="*60)
    print("Select Weight Ranges (enter numbers separated by comma)")
    print("="*60)

    for i, range_config in enumerate(WEIGHT_RANGES, 1):
        print(f"  {i}. {range_config['label']}")

    print("-"*60)
    print("Examples: '1,3,5' or '1-5' for all")
    print("-"*60)

    choice = input("\nSelect ranges (e.g., 1,2,3): ").strip()

    # Parse input
    selected_ranges = []
    if '-' in choice:
        # Handle range like '1-5'
        parts = choice.split('-')
        if len(parts) == 2:
            try:
                start = int(parts[0])
                end = int(parts[1])
                for i in range(start, end + 1):
                    if 1 <= i <= len(WEIGHT_RANGES):
                        selected_ranges.append(WEIGHT_RANGES[i-1])
            except:
                print("Invalid range format")
                return []
    else:
        # Handle comma-separated like '1,3,5'
        numbers = [n.strip() for n in choice.split(',')]
        for n in numbers:
            try:
                idx = int(n)
                if 1 <= idx <= len(WEIGHT_RANGES):
                    selected_ranges.append(WEIGHT_RANGES[idx-1])
            except:
                print(f"Invalid number: {n}")

    if selected_ranges:
        labels = [r['label'] for r in selected_ranges]
        print(f"\n✅ Selected ranges: {', '.join(labels)}")
    else:
        print("❌ No valid ranges selected")

    return selected_ranges

def select_multiple_steps():
    """Let user select multiple analysis steps"""
    print("\n" + "="*60)
    print("Select Analysis Steps (enter numbers separated by comma)")
    print("="*60)

    # Show all available steps
    step_list = []
    for key in sorted(modules.keys()):
        _, desc = modules[key]
        step_list.append(key)
        indent = "    " if '.' in key else "  "
        print(f"{indent}{key}. {desc}")

    print("\n  A. Run ALL steps")
    print("-"*60)
    print("Examples: '0,1,2' or 'A' for all")
    print("-"*60)

    choice = input("\nSelect steps (e.g., 1,3,4.1): ").strip().upper()

    # Parse input
    selected_steps = []
    if choice == 'A':
        # Select all steps
        selected_steps = list(modules.keys())
    else:
        # Handle comma-separated
        step_inputs = [s.strip() for s in choice.split(',')]
        for s in step_inputs:
            if s in modules:
                selected_steps.append(s)
            else:
                print(f"Invalid step: {s}")

    if selected_steps:
        print(f"\n✅ Selected {len(selected_steps)} steps")
    else:
        print("❌ No valid steps selected")

    return selected_steps

def main():
    """Main batch selection system"""
    print("\n" + "="*60)
    print("ARK ETF Position Analysis - Batch Mode")
    print("="*60)

    # Step 1: Select ETFs
    selected_etfs = select_multiple_etfs()
    if not selected_etfs:
        print("\n❌ No ETFs selected. Exiting.")
        return

    # Step 2: Select ranges
    selected_ranges = select_multiple_ranges()
    if not selected_ranges:
        print("\n❌ No ranges selected. Exiting.")
        return

    # Step 3: Select steps
    selected_steps = select_multiple_steps()
    if not selected_steps:
        print("\n❌ No steps selected. Exiting.")
        return

    # Confirm before running
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"ETFs:   {', '.join(selected_etfs)}")
    print(f"Ranges: {', '.join([r['label'] for r in selected_ranges])}")
    print(f"Steps:  {len(selected_steps)} steps")
    print("-"*60)

    confirm = input("\nProceed with analysis? (Y/N): ").strip().upper()
    if confirm != 'Y':
        print("\n❌ Cancelled.")
        return

    # Run analysis
    print("\n" + "="*60)
    print("RUNNING ANALYSIS")
    print("="*60)

    total_runs = len(selected_etfs) * len(selected_ranges) * len(selected_steps)
    current_run = 0

    for etf in selected_etfs:
        # Set current ETF
        set_selected_etf(etf)

        for range_config in selected_ranges:
            # Set current range
            set_current_range(range_config)
            create_directories()

            print(f"\n{'='*60}")
            print(f"ETF: {etf} | Range: {range_config['label']}")
            print(f"{'='*60}")

            for step_key in selected_steps:
                current_run += 1
                module_name, description = modules[step_key]
                print(f"\n[{current_run}/{total_runs}] {description}")
                run_module(module_name, description)

    print(f"\n{'='*60}")
    print("✅ ALL ANALYSIS COMPLETED")
    print(f"{'='*60}")

def quick_run_all():
    """Quick function to run all steps without menu"""
    # Check if we should run for all ranges
    if '--batch' in sys.argv:
        batch_run_all_ranges()
    else:
        # Run for default first range
        if not CURRENT_RANGE:
            set_current_range(WEIGHT_RANGES[0])
            create_directories()
        run_all_modules()

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            quick_run_all()
        elif sys.argv[1] == '--batch':
            batch_run_all_ranges()
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --all to run all steps for default range")
            print("Use --batch to run all steps for ALL weight ranges")
    else:
        main()