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
    input_file = f"{OUTPUT_DIRS['graduation']}/Graduation_Returns_Data.xlsx"
    
    if not os.path.exists(input_file):
        print(f"❌ Graduation analysis data file not found: {input_file}")
        print("   Please run step 4 first to calculate graduation analysis data")
        return
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    colors = {'ARKF': '#FF6B6B', 'ARKG': '#4ECDC4', 'ARKK': '#45B7D1', 
              'ARKQ': '#96CEB4', 'ARKW': '#FECA57'}
    
    # Read summary data
    summary_df = pd.read_excel(input_file, sheet_name='Summary')
    
    # Create individual charts for each ETF
    for etf in etfs:
        
        # Read ETF weekly data
        weekly_data = pd.read_excel(input_file, sheet_name=etf)
        weekly_data['Date'] = pd.to_datetime(weekly_data['Date'])
        
        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Weekly returns comparison (left)
        ax1.plot(weekly_data['Date'], weekly_data['Weekly_Return_Small_%'], 
                color='blue', linewidth=1.5, alpha=0.8, 
                label=f'Current {CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions')
        ax1.plot(weekly_data['Date'], weekly_data['Weekly_Return_Graduated_%'], 
                color='orangered', linewidth=1.5, alpha=0.8, 
                label=f'Graduated (Now >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%)')
        
        ax1.set_title(f'{etf} - Weekly Returns Comparison', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=11)
        ax1.set_ylabel('Weekly Return (%)', fontsize=11)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Cumulative returns comparison (right)
        ax2.plot(weekly_data['Date'], weekly_data['Cumulative_Return_Small_%'], 
                color='blue', linewidth=2, 
                label=f'Current {CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Positions', alpha=0.8)
        ax2.plot(weekly_data['Date'], weekly_data['Cumulative_Return_Graduated_%'], 
                color='orangered', linewidth=2, 
                label=f'Graduated (Now >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%)', alpha=0.8)
        
        ax2.fill_between(weekly_data['Date'], 
                        weekly_data['Cumulative_Return_Small_%'],
                        weekly_data['Cumulative_Return_Graduated_%'],
                        alpha=0.1, color='gray')
        
        ax2.set_title(f'{etf} - Cumulative Returns Comparison', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=11)
        ax2.set_ylabel('Cumulative Return (%)', fontsize=11)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=10, framealpha=0.9)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}%'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add statistics from summary
        etf_summary = summary_df[summary_df['ETF'] == etf].iloc[0]
        stats_text = (f"Final Returns: Small={etf_summary['Final_Return_AllSmall_%']:.1f}%, "
                     f"Graduated={etf_summary['Final_Return_Graduated_%']:.1f}%\n"
                     f"Graduated Tickers: {int(etf_summary['Num_Graduated_Tickers'])}")
        
        # Add text box with stats
        ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                verticalalignment='top', fontsize=9)
        
        plt.suptitle(f'{etf} - Graduated Positions Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save individual chart
        output_file = f"{OUTPUT_DIRS['graduation']}/{etf}_Graduated_Analysis_Chart.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
    
    print("✅ Graduation charts created")

def run():
    """Main function to create graduation analysis charts"""
    
    plot_graduation_charts()

if __name__ == "__main__":
    run()