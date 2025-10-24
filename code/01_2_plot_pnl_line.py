import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE, format_value, get_selected_etfs

def load_pnl_data(etf_name):
    """Load P&L data from Excel file (calculated by step 1)"""

    # Read the already calculated P&L data
    file_path = f"{OUTPUT_DIRS['pnl']}/{etf_name}_PnL_Data.xlsx"

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"P&L data file not found: {file_path}\nPlease run step 1 first to calculate P&L data.")

    pnl_data = pd.read_excel(file_path, sheet_name='Daily_Total_PnL')
    pnl_data['Date'] = pd.to_datetime(pnl_data['Date'])

    return pnl_data

def plot_pnl_charts():
    """Create individual P&L charts for each ETF with both daily and cumulative adjusted P&L"""

    from config import get_selected_etfs
    etfs = get_selected_etfs()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    # Create individual charts for each ETF
    for i, etf in enumerate(etfs):
        # Load pre-calculated P&L data
        pnl_data = load_pnl_data(etf)

        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot cumulative adjusted P&L on primary axis
        ax.plot(pnl_data['Date'], pnl_data['Cumulative_Adj_PnL'],
                color=colors[i], linewidth=2.5, label='Cumulative Adjusted P&L')

        # Create secondary axis for daily adjusted P&L
        ax2 = ax.twinx()
        ax2.plot(pnl_data['Date'], pnl_data['Adj_PnL'],
                color=colors[i], linewidth=0.8, alpha=0.4, label='Daily Adjusted P&L')

        weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
        ax.set_title(f'{etf} - P&L from {weight_label} Positions', fontsize=18, fontweight='bold')
        ax.set_xlabel('Date', fontsize=14)
        ax.set_ylabel('Cumulative P&L', color=colors[i], fontsize=15)
        ax2.set_ylabel('Daily P&L', color=colors[i], fontsize=15)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)

        # Get actual data min/max for both axes
        cum_data_min = pnl_data['Cumulative_Adj_PnL'].min()
        cum_data_max = pnl_data['Cumulative_Adj_PnL'].max()
        daily_data_min = pnl_data['Adj_PnL'].min()
        daily_data_max = pnl_data['Adj_PnL'].max()

        # Add 5% padding to data ranges
        cum_padding = (cum_data_max - cum_data_min) * 0.05
        daily_padding = (daily_data_max - daily_data_min) * 0.05

        cum_min = cum_data_min - cum_padding
        cum_max = cum_data_max + cum_padding
        daily_min = daily_data_min - daily_padding
        daily_max = daily_data_max + daily_padding

        # Set daily axis range based on daily data (user requirement)
        ax2.set_ylim(daily_min, daily_max)

        # Align zero lines: adjust cumulative range to match daily's zero position
        if cum_min < 0 and cum_max > 0 and daily_min < 0 and daily_max > 0:
            # Calculate where 0 appears in daily range (as fraction from bottom)
            zero_position = abs(daily_min) / (daily_max - daily_min)

            # Calculate how cumulative range should be adjusted
            # Target: abs(cum_min) / (cum_max - cum_min) = zero_position
            # This means: below_zero / above_zero = zero_position / (1 - zero_position)
            cum_below_zero = abs(cum_min)
            cum_above_zero = cum_max
            target_ratio = zero_position / (1 - zero_position)
            current_ratio = cum_below_zero / cum_above_zero

            if current_ratio < target_ratio:
                # Need to expand below zero (make cum_min more negative)
                new_cum_min = -cum_above_zero * target_ratio
                new_cum_max = cum_max
            else:
                # Need to expand above zero (make cum_max larger)
                new_cum_max = cum_below_zero / target_ratio
                new_cum_min = cum_min

            # Ensure original data range is still visible
            new_cum_min = min(new_cum_min, cum_min)
            new_cum_max = max(new_cum_max, cum_max)

            ax.set_ylim(new_cum_min, new_cum_max)
        else:
            # If not both crossing zero, just use data ranges
            ax.set_ylim(cum_min, cum_max)

        # Format y-axes
        ax.yaxis.set_major_formatter(plt.FuncFormatter(format_value))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(format_value))
        
        # Color the tick labels and increase size
        ax.tick_params(axis='y', labelcolor=colors[i], labelsize=13)
        ax2.tick_params(axis='y', labelcolor=colors[i], labelsize=13)
        ax.tick_params(axis='x', labelsize=12)
        
        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add legend
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=13)
        
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIRS['pnl']}/{etf}_Small_Position_PnL.png", dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {etf}: P&L line chart")


def run():
    """Run function for main.py integration"""
    plot_pnl_charts()

if __name__ == "__main__":
    plot_pnl_charts()