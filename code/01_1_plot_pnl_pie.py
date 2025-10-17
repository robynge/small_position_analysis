import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE, get_data_path, get_selected_etfs

def load_stock_pnl(etf_name):
    """Load Stock_Total_PnL from Excel file (calculated by step 1)"""

    file_path = f"{OUTPUT_DIRS['pnl']}/{etf_name}_PnL_Data.xlsx"

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"P&L data file not found: {file_path}\nPlease run step 1 first to calculate P&L data.")

    stock_pnl = pd.read_excel(file_path, sheet_name='Stock_Total_PnL')

    return stock_pnl

def create_pnl_pie_chart(stock_pnl, etf_name):
    """Create pie chart for P&L contributors (both losses and gains), grouping <5% into Others"""

    # Check if we have any data
    if len(stock_pnl) == 0:
        return None

    # Calculate total absolute P&L for percentage calculation
    total_abs_pnl = abs(stock_pnl['Total_Adj_PnL']).sum()

    # Calculate percentage contribution for each stock (based on absolute value)
    stock_pnl = stock_pnl.copy()
    stock_pnl['PnL_Pct'] = (abs(stock_pnl['Total_Adj_PnL']) / total_abs_pnl) * 100

    # Separate stocks >= 5% and < 5%
    significant_stocks = stock_pnl[stock_pnl['PnL_Pct'] >= 5.0].copy()
    small_stocks = stock_pnl[stock_pnl['PnL_Pct'] < 5.0].copy()

    # If we have small stocks, create Others category
    if len(small_stocks) > 0:
        others_pnl = small_stocks['Total_Adj_PnL'].sum()
        others_row = pd.DataFrame({'Stock': ['Others'], 'Total_Adj_PnL': [others_pnl]})
        chart_data = pd.concat([significant_stocks[['Stock', 'Total_Adj_PnL']], others_row], ignore_index=True)
    else:
        chart_data = significant_stocks[['Stock', 'Total_Adj_PnL']].copy()

    # Sort by P&L (most negative first, then positive)
    chart_data = chart_data.sort_values('Total_Adj_PnL').reset_index(drop=True)

    # Use absolute values for pie chart sizing
    chart_data['Abs_PnL'] = abs(chart_data['Total_Adj_PnL'])
    
    # Generate color gradient from dark to light
    num_slices = len(chart_data)
    colors = []
    for i in range(num_slices):
        # Create a wider range of shades from dark to very light
        # Start from dark (0.4, 0.0, 0.0) to light (1.0, 0.8, 0.8)
        progress = i / max(num_slices-1, 1)

        # Red channel: stays high
        r = 0.4 + (0.6 * progress)
        # Green and blue channels: increase more for lighter shades
        g = 0.0 + (0.8 * progress)
        b = 0.0 + (0.8 * progress)

        colors.append((r, g, b))
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Create pie chart with custom formatting
    def format_autopct(pct):
        abs_value = pct * total_abs_pnl / 100
        return f'{pct:.1f}%\n(${abs_value/1e6:.1f}M)'

    wedges, texts, autotexts = ax.pie(
        chart_data['Abs_PnL'],
        labels=chart_data['Stock'],
        colors=colors,
        autopct=format_autopct,
        startangle=90,
        counterclock=False,
        pctdistance=0.85,
        labeldistance=1.15
    )

    # Enhance text
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
        autotext.set_weight('bold')

    # Add title
    weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
    net_pnl = chart_data['Total_Adj_PnL'].sum()
    plt.title(f'{etf_name} - P&L Contribution from {weight_label} Positions\nNet P&L: ${net_pnl/1e6:.1f}M',
              fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # Save figure
    # Directory creation handled by config.py
    output_file = f"{OUTPUT_DIRS['pnl']}/{etf_name}_PnL_Pie_Chart.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_file


def run():
    """Generate P&L pie charts for all ETFs"""
    etfs = get_selected_etfs()

    # Create individual charts
    for etf in etfs:
        # Load stock P&L data from Excel
        stock_pnl = load_stock_pnl(etf)

        # Create pie chart
        output_file = create_pnl_pie_chart(stock_pnl, etf)
        print(f"  ✓ {etf}: P&L pie chart")

def main():
    """Alias for run() for backward compatibility"""
    run()

if __name__ == "__main__":
    main()