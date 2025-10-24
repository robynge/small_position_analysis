"""
Plot alternative returns charts from calculated data
Reads data from Alternative_Returns_Data.xlsx and creates visualizations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE, get_selected_etfs

def plot_alternative_returns_charts():
    """Create alternative returns charts from saved Excel data"""

    # Load data
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'Alternative'
    input_file = f"{OUTPUT_DIRS['returns']}/{folder_suffix}_Returns_Data.xlsx"

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Alternative returns data file not found: {input_file}\nPlease run step 3 first to calculate alternative returns data.")

    etfs = get_selected_etfs()
    colors = {'ARKF': '#FF6B6B', 'ARKG': '#4ECDC4', 'ARKK': '#45B7D1',
              'ARKQ': '#96CEB4', 'ARKW': '#FECA57', 'ARKX': '#9B59B6'}

    # Read summary data
    summary_df = pd.read_excel(input_file, sheet_name='Summary')

    # Process data for each ETF
    for etf in etfs:
        # Read ETF data
        daily_data = pd.read_excel(input_file, sheet_name=f'{etf}_Daily')

        daily_data['Date'] = pd.to_datetime(daily_data['Date'])

        # Create figure with 1 subplot (cumulative returns only)
        fig, ax = plt.subplots(figsize=(12, 6))

        # Cumulative Returns
        ax.plot(daily_data['Date'], daily_data['Cumulative_Actual'] * 100 - 100,
                color='black', linewidth=2.5, label=f'Total {etf} Return', alpha=0.7)
        ax.plot(daily_data['Date'], daily_data['Cumulative_ExcludeSmall'] * 100 - 100,
                color=colors[etf], linewidth=2.5,
                label=f'Excluding {CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions', alpha=0.5)
        ax.plot(daily_data['Date'], daily_data['Cumulative_SmallOnly'] * 100 - 100,
                color='purple', linewidth=2.5,
                label=f'{CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions Only', alpha=0.5)

        # Fill between the lines
        ax.fill_between(daily_data['Date'],
                        daily_data['Cumulative_ExcludeSmall'] * 100 - 100,
                        daily_data['Cumulative_SmallOnly'] * 100 - 100,
                        alpha=0.1, color='gray')

        ax.set_title(f'{etf} - Cumulative Returns', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Cumulative Return (%)', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}%'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.suptitle(f'{etf} Alternative Returns Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save individual ETF chart
        output_file = f"{OUTPUT_DIRS['returns']}/{etf}_Alternative_Returns_Chart.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {etf}: Alternative returns chart")

def run():
    """Main function to create alternative returns charts"""
    
    plot_alternative_returns_charts()

if __name__ == "__main__":
    run()