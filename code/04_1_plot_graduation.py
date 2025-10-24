"""
Plot graduation analysis charts from calculated data
Reads data from Graduation_Returns_Data.xlsx and creates visualizations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE

def plot_graduation_charts():
    """Create graduation analysis charts from saved Excel data"""

    # Load data
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'under_1pct'
    input_file = f"{OUTPUT_DIRS['graduation']}/{folder_suffix}_Graduation_Returns_Data.xlsx"

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Graduation data file not found: {input_file}\nPlease run step 4 first to calculate graduation data.")

    from config import get_selected_etfs
    etfs = get_selected_etfs()
    colors = {'ARKF': '#FF6B6B', 'ARKG': '#4ECDC4', 'ARKK': '#45B7D1',
              'ARKQ': '#96CEB4', 'ARKW': '#FECA57', 'ARKX': '#9B59B6'}

    # Read summary data
    summary_df = pd.read_excel(input_file, sheet_name='Summary')

    # Process data for each ETF
    for etf in etfs:
        # Read ETF data
        daily_data = pd.read_excel(input_file, sheet_name=etf)
        daily_data['Date'] = pd.to_datetime(daily_data['Date'])

        # Create figure with 1 subplot
        fig, ax = plt.subplots(figsize=(12, 6))

        # Cumulative returns comparison
        ax.plot(daily_data['Date'], daily_data['Cumulative_Return_Small_%'],
                color='blue', linewidth=2,
                label=f'Current {CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions', alpha=0.8)
        ax.plot(daily_data['Date'], daily_data['Cumulative_Return_Graduated_%'],
                color='orangered', linewidth=2,
                label=f'Graduated (Now >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%)', alpha=0.8)

        ax.fill_between(daily_data['Date'],
                        daily_data['Cumulative_Return_Small_%'],
                        daily_data['Cumulative_Return_Graduated_%'],
                        alpha=0.1, color='gray')

        ax.set_title(f'{etf} - Cumulative Returns Comparison', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Cumulative Return (%)', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}%'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # Add statistics from summary
        etf_summary = summary_df[summary_df['ETF'] == etf].iloc[0]
        stats_text = (f"Final Returns: Small={etf_summary['Final_Return_AllSmall_%']:.1f}%, "
                     f"Graduated={etf_summary['Final_Return_Graduated_%']:.1f}%\n"
                     f"Graduated Tickers: {int(etf_summary['Num_Graduated_Tickers'])}")

        # Add text box with stats
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                verticalalignment='top', fontsize=9)
        
        plt.suptitle(f'{etf} - Graduated Positions Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save individual chart
        output_file = f"{OUTPUT_DIRS['graduation']}/{etf}_Graduated_Analysis_Chart.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {etf}: Graduation chart")

def run():
    """Main function to create graduation analysis charts"""
    
    plot_graduation_charts()

if __name__ == "__main__":
    run()