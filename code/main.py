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
from config import create_directories, WEIGHT_RANGES, set_current_range, CURRENT_RANGE

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
    from data_config import DATA_FILES, SELECTED_ETF

    if SELECTED_ETF and DATA_FILES:
        data_info = f"Selected ETF: {SELECTED_ETF}"
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
    from data_config import get_available_etf_files, set_selected_etf, SELECTED_ETF

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
            selected = '►' if etf == SELECTED_ETF else ' '
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
    print(f"\n▶ Running: {description} [{weight_label}]")
    print("-"*40)
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
            print(f"⚠️  Module {module_name} has no run() or main() function")
    except Exception as e:
        print(f"❌ Error running {module_name}: {e}")
        import traceback
        traceback.print_exc()

def run_all_modules():
    """Run all analysis modules for current weight range"""
    weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
    print(f"\n🚀 Running all analysis steps for {weight_label} positions...")
    
    for key in sorted(modules.keys()):
        module_name, description = modules[key]
        run_module(module_name, description)
    
    print(f"\n✅ All steps completed for {weight_label}!")

def batch_run_all_ranges():
    """Run all modules for all weight ranges"""
    print("\n" + "="*60)
    print("BATCH PROCESSING ALL WEIGHT RANGES")
    print("="*60)
    
    for range_config in WEIGHT_RANGES:
        print(f"\n\n{'='*60}")
        print(f"Processing Range: {range_config['label']}")
        print(f"{'='*60}")
        
        # Set current range
        set_current_range(range_config)
        create_directories()
        
        # Run all modules for this range
        run_all_modules()
    
    print("\n" + "="*60)
    print("✅ ALL WEIGHT RANGES PROCESSED SUCCESSFULLY!")
    print("="*60)
    
    # Summary
    print("\nGenerated folders:")
    for range_config in WEIGHT_RANGES:
        print(f"  - analysis_results_{range_config['folder']}/")

def run_specific_module_all_ranges(module_key):
    """Run a specific module for all weight ranges"""
    module_name, description = modules[module_key]
    
    print("\n" + "="*60)
    print(f"Running '{description}' for ALL WEIGHT RANGES")
    print("="*60)
    
    for range_config in WEIGHT_RANGES:
        print(f"\n{'='*40}")
        print(f"Range: {range_config['label']}")
        print(f"{'='*40}")
        
        # Set current range
        set_current_range(range_config)
        create_directories()
        
        # Run the specific module
        run_module(module_name, description)
    
    print("\n" + "="*60)
    print(f"✅ Module '{description}' completed for all ranges!")
    print("="*60)

def main():
    """Main menu system"""
    from data_config import SELECTED_ETF

    # Set default to first weight range initially
    if not CURRENT_RANGE:
        set_current_range(WEIGHT_RANGES[0])  # Default to first range

    while True:
        print_menu()
        choice = input("\nSelect option: ").strip().upper()
        
        if choice == 'Q':
            print("\n👋 Goodbye!")
            break
            
        elif choice == 'A':
            # Check if ETF is selected
            from data_config import SELECTED_ETF
            if not SELECTED_ETF:
                print("❌ Please select an ETF first (option E)")
                continue
            # Run all steps for current range
            run_all_modules()

        elif choice == 'B':
            # Check if ETF is selected
            from data_config import SELECTED_ETF
            if not SELECTED_ETF:
                print("❌ Please select an ETF first (option E)")
                continue
            # Batch run for all ranges
            batch_run_all_ranges()
            
        elif choice == 'R':
            # Select weight range
            result = select_weight_range()
            if result == 'ALL_RANGES':
                # Set a special marker for all ranges mode
                # We'll use a global variable to track this without modifying CURRENT_RANGE
                globals()['ALL_RANGES_MODE'] = True
                print("✅ Set to ALL RANGES mode - now select which step(s) to run")
            elif result and result != False:
                globals()['ALL_RANGES_MODE'] = False  # Clear all ranges mode
                print(f"✅ Weight range set to: {result['label']}")
        
        elif choice == 'E':
            # Select ETF for analysis
            select_etf()
                
        elif choice in modules:
            # Check if ETF is selected
            from data_config import SELECTED_ETF
            if not SELECTED_ETF:
                print("❌ Please select an ETF first (option E)")
                continue
            # Check if we're in all ranges mode
            if globals().get('ALL_RANGES_MODE', False):
                # In all ranges mode, directly run for all ranges
                run_specific_module_all_ranges(choice)
                # Clear the all ranges mode flag
                globals()['ALL_RANGES_MODE'] = False
            else:
                # Ask if user wants to run for current range or all ranges
                print(f"\nRun '{modules[choice][1]}' for:")
                print("  1. Current range only")
                print("  2. All ranges")
                sub_choice = input("Select (1-2): ").strip()
                
                if sub_choice == '1':
                    # Run for current range only
                    module_name, description = modules[choice]
                    run_module(module_name, description)
                    print("\n✅ Module completed!")
                elif sub_choice == '2':
                    # Run for all ranges
                    run_specific_module_all_ranges(choice)
                else:
                    print("Invalid choice")
            
        else:
            # Parse multiple choices
            choices = [c.strip() for c in choice.split(',')]
            valid_choices = []
            
            for c in choices:
                if c in modules:
                    valid_choices.append(c)
                else:
                    print(f"⚠️  Invalid choice: {c}")
            
            if valid_choices:
                # Check if we're in all ranges mode
                if globals().get('ALL_RANGES_MODE', False):
                    # In all ranges mode, directly run for all ranges
                    for c in valid_choices:
                        run_specific_module_all_ranges(c)
                    print("\n✅ Selected steps completed for all ranges!")
                    # Clear the all ranges mode flag
                    globals()['ALL_RANGES_MODE'] = False
                else:
                    # Ask if user wants to run for current range or all ranges
                    print(f"\nRun selected modules for:")
                    print("  1. Current range only")
                    print("  2. All ranges")
                    sub_choice = input("Select (1-2): ").strip()
                    
                    if sub_choice == '1':
                        # Run for current range
                        for c in valid_choices:
                            module_name, description = modules[c]
                            run_module(module_name, description)
                        print("\n✅ Selected steps completed!")
                    elif sub_choice == '2':
                        # Run for all ranges
                        for c in valid_choices:
                            run_specific_module_all_ranges(c)
                        print("\n✅ Selected steps completed for all ranges!")
                    else:
                        print("Invalid choice")

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