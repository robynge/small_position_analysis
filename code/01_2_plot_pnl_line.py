import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE, format_value

def load_pnl_data(etf_name):
    """Load pre-calculated P&L data from module 01"""
    
    # Read the already calculated P&L data
    file_path = f"{OUTPUT_DIRS['pnl']}/{etf_name}_PnL_Data.xlsx"
    pnl_data = pd.read_excel(file_path)
    pnl_data['Date'] = pd.to_datetime(pnl_data['Date'])
    
    return pnl_data

def plot_pnl_charts():
    """Create individual P&L charts for each ETF with both daily and cumulative P&L"""
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Create individual charts for each ETF
    for i, etf in enumerate(etfs):
        # Load pre-calculated P&L data
        pnl_data = load_pnl_data(etf)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot cumulative P&L on primary axis
        ax.plot(pnl_data['Date'], pnl_data['Cumulative_PnL'], 
                color=colors[i], linewidth=2.5, label='Cumulative P&L')
        
        # Create secondary axis for daily P&L
        ax2 = ax.twinx()
        ax2.plot(pnl_data['Date'], pnl_data['Daily_PnL'], 
                color=colors[i], linewidth=0.8, alpha=0.4, label='Daily P&L')
        
        weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
        ax.set_title(f'{etf} - P&L from {weight_label} Positions', fontsize=18, fontweight='bold')
        ax.set_xlabel('Date', fontsize=14)
        ax.set_ylabel('Cumulative P&L', color=colors[i], fontsize=15)
        ax2.set_ylabel('Daily P&L', color=colors[i], fontsize=15)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
        
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
        

def run():
    """Run function for main.py integration"""
    plot_pnl_charts()
    print("✅ P&L line charts created")

if __name__ == "__main__":
    plot_pnl_charts()