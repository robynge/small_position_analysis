"""
Plot distribution of daily returns for alternative returns analysis
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE, get_selected_etfs

def plot_return_distributions():
    """Create distribution charts for daily returns"""

    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'Alternative'
    input_file = f"{OUTPUT_DIRS['returns']}/{folder_suffix}_Returns_Data.xlsx"

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Alternative returns data file not found: {input_file}\nPlease run step 3 first.")

    etfs = get_selected_etfs()
    colors = {'ARKF': '#FF6B6B', 'ARKG': '#4ECDC4', 'ARKK': '#45B7D1',
              'ARKQ': '#96CEB4', 'ARKW': '#FECA57', 'ARKX': '#9B59B6'}

    for etf in etfs:
        daily_data = pd.read_excel(input_file, sheet_name=f'{etf}_Daily')

        # Convert returns to percentage
        returns_actual = daily_data['Return_Actual'] * 100
        returns_exclude = daily_data['Return_ExcludeSmall'] * 100
        returns_small = daily_data['Return_SmallOnly'] * 100

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # Actual Returns Distribution
        axes[0].hist(returns_actual, bins=50, alpha=0.7, color='black', edgecolor='black')
        axes[0].axvline(returns_actual.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {returns_actual.mean():.2f}%')
        axes[0].axvline(returns_actual.median(), color='blue', linestyle='--', linewidth=2, label=f'Median: {returns_actual.median():.2f}%')
        axes[0].set_title(f'{etf} Total Return Distribution', fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Daily Return (%)', fontsize=10)
        axes[0].set_ylabel('Frequency', fontsize=10)
        axes[0].legend(fontsize=9)
        axes[0].grid(True, alpha=0.3)

        # Exclude Small Distribution
        axes[1].hist(returns_exclude, bins=50, alpha=0.7, color=colors[etf], edgecolor='black')
        axes[1].axvline(returns_exclude.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {returns_exclude.mean():.2f}%')
        axes[1].axvline(returns_exclude.median(), color='blue', linestyle='--', linewidth=2, label=f'Median: {returns_exclude.median():.2f}%')
        axes[1].set_title(f'Excluding {CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Distribution', fontsize=12, fontweight='bold')
        axes[1].set_xlabel('Daily Return (%)', fontsize=10)
        axes[1].set_ylabel('Frequency', fontsize=10)
        axes[1].legend(fontsize=9)
        axes[1].grid(True, alpha=0.3)

        # Small Only Distribution
        axes[2].hist(returns_small, bins=50, alpha=0.7, color='purple', edgecolor='black')
        axes[2].axvline(returns_small.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {returns_small.mean():.2f}%')
        axes[2].axvline(returns_small.median(), color='blue', linestyle='--', linewidth=2, label=f'Median: {returns_small.median():.2f}%')
        axes[2].set_title(f'{CURRENT_RANGE["label"] if CURRENT_RANGE else "<1%"} Only Distribution', fontsize=12, fontweight='bold')
        axes[2].set_xlabel('Daily Return (%)', fontsize=10)
        axes[2].set_ylabel('Frequency', fontsize=10)
        axes[2].legend(fontsize=9)
        axes[2].grid(True, alpha=0.3)

        plt.suptitle(f'{etf} - Daily Return Distributions', fontsize=16, fontweight='bold')
        plt.tight_layout()

        output_file = f"{OUTPUT_DIRS['returns']}/{etf}_Return_Distribution.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {etf}: Return distribution chart")

def run():
    """Main function to create return distribution charts"""
    plot_return_distributions()

if __name__ == "__main__":
    run()
