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
from config import OUTPUT_DIRS, CURRENT_RANGE

def plot_alternative_returns_charts():
    """Create alternative returns charts from saved Excel data"""
    
    # Load data
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'Alternative'
    input_file = f"{OUTPUT_DIRS['returns']}/{folder_suffix}_Returns_Data.xlsx"
    
    if not os.path.exists(input_file):
        print(f"❌ Alternative returns data file not found: {input_file}")
        print("   Please run step 3 first to calculate alternative returns data")
        return
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    colors = {'ARKF': '#FF6B6B', 'ARKG': '#4ECDC4', 'ARKK': '#45B7D1', 
              'ARKQ': '#96CEB4', 'ARKW': '#FECA57'}
    
    # Read summary data
    summary_df = pd.read_excel(input_file, sheet_name='Summary')
    
    # Create individual PNG for each ETF
    for etf in etfs:
        
        # Read ETF data
        daily_data = pd.read_excel(input_file, sheet_name=f'{etf}_Daily')
        weekly_data = pd.read_excel(input_file, sheet_name=f'{etf}_Weekly')
        
        daily_data['Date'] = pd.to_datetime(daily_data['Date'])
        weekly_data['Date'] = pd.to_datetime(weekly_data['Date'])
        
        # Create figure with 2 subplots (weekly returns and cumulative returns)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Weekly Returns subplot (left)
        ax1.plot(weekly_data['Date'], weekly_data['Weekly_Return_Total_%'], 
                color='black', linewidth=2, alpha=0.7, label=f'Total {etf} Return')
        ax1.plot(weekly_data['Date'], weekly_data['Weekly_Return_ExcludeSmall_%'], 
                color=colors[etf], linewidth=2, alpha=0.5, 
                label=f'Excluding {CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions')
        ax1.plot(weekly_data['Date'], weekly_data['Weekly_Return_SmallOnly_%'], 
                color='purple', linewidth=2, alpha=0.5, 
                label=f'{CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions Only')
        
        ax1.set_title(f'{etf} - Weekly Returns', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=11)
        ax1.set_ylabel('Weekly Return (%)', fontsize=11)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=10, framealpha=0.9)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Cumulative Returns subplot (right)
        ax2.plot(daily_data['Date'], daily_data['Cumulative_Actual'] * 100 - 100, 
                color='black', linewidth=2.5, label=f'Total {etf} Return', alpha=0.7)
        ax2.plot(daily_data['Date'], daily_data['Cumulative_ExcludeSmall'] * 100 - 100, 
                color=colors[etf], linewidth=2.5, 
                label=f'Excluding {CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions', alpha=0.5)
        ax2.plot(daily_data['Date'], daily_data['Cumulative_SmallOnly'] * 100 - 100, 
                color='purple', linewidth=2.5, 
                label=f'{CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions Only', alpha=0.5)
        
        # Fill between the lines
        ax2.fill_between(daily_data['Date'], 
                        daily_data['Cumulative_ExcludeSmall'] * 100 - 100,
                        daily_data['Cumulative_SmallOnly'] * 100 - 100,
                        alpha=0.1, color='gray')
        
        ax2.set_title(f'{etf} - Cumulative Returns', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=11)
        ax2.set_ylabel('Cumulative Return (%)', fontsize=11)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=10, framealpha=0.9)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}%'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Get statistics from summary
        etf_summary = summary_df[summary_df['ETF'] == etf].iloc[0]
        final_exclude = etf_summary['Final_Cumulative_Return_ExcludeSmall_%']
        final_small = etf_summary['Final_Cumulative_Return_SmallOnly_%']
        difference = etf_summary['Small_vs_Total_Difference_%']
        
        plt.suptitle(f'{etf} Alternative Returns Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save individual ETF chart
        output_file = f"{OUTPUT_DIRS['returns']}/{etf}_Alternative_Returns_Chart.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
    
    print("✅ Alternative returns charts created")

def run():
    """Main function to create alternative returns charts"""
    
    plot_alternative_returns_charts()

if __name__ == "__main__":
    run()