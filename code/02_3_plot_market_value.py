"""
Plot market value charts from calculated data
Reads data from Market_Value_Data.xlsx and creates visualizations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')
from config import CURRENT_RANGE, format_value, set_current_range, WEIGHT_RANGES, create_directories

# Initialize configuration if not already set
if CURRENT_RANGE is None:
    set_current_range(WEIGHT_RANGES[0])  # Default to <1%
    create_directories()

# Import OUTPUT_DIRS after initialization
from config import OUTPUT_DIRS

def plot_market_value_charts():
    """Create market value charts from saved Excel data"""
    
    # Load data
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'under_1pct'
    input_file = f"{OUTPUT_DIRS['market_value']}/{folder_suffix}_Market_Value_Data.xlsx"
    
    if not os.path.exists(input_file):
        print(f"❌ Market value data file not found: {input_file}")
        print("   Please run step 2.2 first to calculate market value data")
        return
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Read data for each ETF
    for i, etf in enumerate(etfs):
        
        # Read ETF sheet
        weekly_data = pd.read_excel(input_file, sheet_name=etf)
        weekly_data['Date'] = pd.to_datetime(weekly_data['Date'])
        
        # Rename columns for compatibility
        weekly_data.columns = ['Date', 'Small_MV_Total', 'Total_MV', 'Small_MV_Pct']
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create dual axis
        ax2 = ax.twinx()
        
        # Plot market value on primary axis
        line1 = ax.plot(weekly_data['Date'], weekly_data['Small_MV_Total'], 
                       color=colors[i], linewidth=2.5, label='Market Value')
        
        # Plot percentage on secondary axis
        line2 = ax2.plot(weekly_data['Date'], weekly_data['Small_MV_Pct'], 
                        color=colors[i], linewidth=1.5, alpha=0.6, 
                        label='% of AUM')
        
        # Formatting
        weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
        ax.set_title(f'{etf} - {weight_label} Positions Weekly Trends', fontsize=18, fontweight='bold')
        ax.set_xlabel('Date', fontsize=14)
        ax.set_ylabel('Market Value', color=colors[i], fontsize=15)
        ax2.set_ylabel('% of AUM', color=colors[i], fontsize=15)
        
        # Format y-axes
        ax.yaxis.set_major_formatter(plt.FuncFormatter(format_value))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
        
        # Grid
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
        
        # Color the tick labels and increase size
        ax.tick_params(axis='y', labelcolor=colors[i], labelsize=13)
        ax2.tick_params(axis='y', labelcolor=colors[i], labelsize=13)
        ax.tick_params(axis='x', labelsize=12)
        
        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Legend
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='best', fontsize=13)
        
        plt.tight_layout()
        
        # Save chart
        output_file = f"{OUTPUT_DIRS['market_value']}/{etf}_Market_Value_Chart.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create stacked market value percentage chart
        create_stacked_mv_percentage_chart(etf, input_file)
    
    print("✅ Market value charts created")

def create_stacked_mv_percentage_chart(etf, input_file):
    """Create a stacked area chart showing market value percentage distribution by weight range"""
    
    # Read range data
    range_data = pd.read_excel(input_file, sheet_name=f'{etf}_Ranges')
    range_data['Date'] = pd.to_datetime(range_data['Date'])
    
    # Define colors (same as position distribution chart)
    colors = ['#e8f4fd', '#b3d9f2', '#5fa8d3', '#1e6ba8', '#05445e']
    weight_columns = ['<1%', '1-2.5%', '2.5-5%', '5-7.5%', '>7.5%']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Prepare data for stacking
    percentages = []
    for col in weight_columns:
        percentages.append(range_data[f'MV_Pct_{col}'].values)
    
    # Create stacked area chart
    ax.stackplot(range_data['Date'], 
                 *percentages,
                 labels=weight_columns,
                 colors=colors,
                 alpha=0.85)
    
    # Formatting
    ax.set_title(f'{etf} - Market Value Distribution by Weight Range (Percentage)', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('Percentage of Total Market Value (%)', fontsize=11)
    ax.set_ylim(0, 100)
    
    # Format y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}%'))
    
    # Grid
    ax.grid(True, alpha=0.3)
    
    # Legend with background and border
    legend = ax.legend(loc='lower left', fontsize=10, framealpha=0.9)
    legend.get_frame().set_facecolor('white')
    legend.get_frame().set_edgecolor('black')
    legend.get_frame().set_linewidth(0.5)
    
    # Rotate x-axis labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save chart
    output_file = f"{OUTPUT_DIRS['market_value']}/{etf}_Market_Value_Stacked.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

def run():
    """Main function to create market value charts"""
    
    plot_market_value_charts()

if __name__ == "__main__":
    run()