"""
Plot graduation analysis charts: return and P&L distribution comparison
Shows distribution of daily returns and P&L for graduated stocks:
1. Before graduation (<1% period)
2. After graduation (>=1% period)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, get_selected_etfs
from scipy import stats

def plot_graduation_distribution():
    """Create distribution charts comparing before/after graduation returns and P&L"""

    # Load data
    input_file = f"{OUTPUT_DIRS['graduation']}/Graduation_Returns_Data.xlsx"

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Graduation data file not found: {input_file}\nPlease run step 4 first to calculate graduation data.")

    etfs = get_selected_etfs()

    # Read summary for statistics
    summary_df = pd.read_excel(input_file, sheet_name='Summary')

    # Process data for each ETF
    for etf in etfs:
        # Read ETF data
        returns_df = pd.read_excel(input_file, sheet_name=etf)

        if len(returns_df) == 0:
            print(f"  ⚠️  {etf}: No graduated stocks data")
            continue

        # Separate data by period
        before_df = returns_df[returns_df['Period'] == 'Before_Graduation_<1%']
        after_df = returns_df[returns_df['Period'] == 'After_Graduation_>=1%']

        before_returns = before_df['Daily_Return_%']
        after_returns = after_df['Daily_Return_%']
        before_pnl = before_df['Daily_PnL']
        after_pnl = after_df['Daily_PnL']

        if len(before_returns) == 0 or len(after_returns) == 0:
            print(f"  ⚠️  {etf}: Insufficient data for distribution")
            continue

        # Create figure with 2x2 subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))

        # ========== Plot 1: Before Graduation - Return Distribution ==========
        ax1.hist(before_returns, bins=50, alpha=0.7, color='steelblue',
                edgecolor='black', density=True, label='Histogram')

        # Add KDE
        kde_before_ret = stats.gaussian_kde(before_returns.dropna())
        x_range_before_ret = np.linspace(before_returns.min(), before_returns.max(), 300)
        ax1.plot(x_range_before_ret, kde_before_ret(x_range_before_ret),
                color='darkblue', linewidth=2.5, label='KDE')

        # Add vertical line for mean
        mean_before_ret = before_returns.mean()
        ax1.axvline(mean_before_ret, color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {mean_before_ret:.2f}%')

        ax1.set_title(f'{etf} - Before Graduation (<1% Period)\nDaily Return Distribution',
                     fontsize=12, fontweight='bold')
        ax1.set_xlabel('Daily Return (%)', fontsize=10)
        ax1.set_ylabel('Density', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=8)

        # Statistics text
        stats_before_ret = (
            f"n = {len(before_returns)}\n"
            f"Mean = {before_returns.mean():.2f}%\n"
            f"Median = {before_returns.median():.2f}%\n"
            f"Std = {before_returns.std():.2f}%\n"
            f"Skew = {before_returns.skew():.2f}\n"
            f"Kurt = {before_returns.kurtosis():.2f}"
        )
        ax1.text(0.02, 0.98, stats_before_ret, transform=ax1.transAxes,
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
                verticalalignment='top', fontsize=8, family='monospace')

        # ========== Plot 2: After Graduation - Return Distribution ==========
        ax2.hist(after_returns, bins=50, alpha=0.7, color='orangered',
                edgecolor='black', density=True, label='Histogram')

        # Add KDE
        kde_after_ret = stats.gaussian_kde(after_returns.dropna())
        x_range_after_ret = np.linspace(after_returns.min(), after_returns.max(), 300)
        ax2.plot(x_range_after_ret, kde_after_ret(x_range_after_ret),
                color='darkred', linewidth=2.5, label='KDE')

        # Add vertical line for mean
        mean_after_ret = after_returns.mean()
        ax2.axvline(mean_after_ret, color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {mean_after_ret:.2f}%')

        ax2.set_title(f'{etf} - After Graduation (≥1% Period)\nDaily Return Distribution',
                     fontsize=12, fontweight='bold')
        ax2.set_xlabel('Daily Return (%)', fontsize=10)
        ax2.set_ylabel('Density', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=8)

        # Statistics text
        stats_after_ret = (
            f"n = {len(after_returns)}\n"
            f"Mean = {after_returns.mean():.2f}%\n"
            f"Median = {after_returns.median():.2f}%\n"
            f"Std = {after_returns.std():.2f}%\n"
            f"Skew = {after_returns.skew():.2f}\n"
            f"Kurt = {after_returns.kurtosis():.2f}"
        )
        ax2.text(0.02, 0.98, stats_after_ret, transform=ax2.transAxes,
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7),
                verticalalignment='top', fontsize=8, family='monospace')

        # ========== Plot 3: Before Graduation - P&L Distribution ==========
        ax3.hist(before_pnl, bins=50, alpha=0.7, color='mediumseagreen',
                edgecolor='black', density=True, label='Histogram')

        # Add KDE
        kde_before_pnl = stats.gaussian_kde(before_pnl.dropna())
        x_range_before_pnl = np.linspace(before_pnl.min(), before_pnl.max(), 300)
        ax3.plot(x_range_before_pnl, kde_before_pnl(x_range_before_pnl),
                color='darkgreen', linewidth=2.5, label='KDE')

        # Add vertical line for mean
        mean_before_pnl = before_pnl.mean()
        ax3.axvline(mean_before_pnl, color='red', linestyle='--', linewidth=2,
                   label=f'Mean: ${mean_before_pnl:,.0f}')

        ax3.set_title(f'{etf} - Before Graduation (<1% Period)\nDaily P&L Distribution',
                     fontsize=12, fontweight='bold')
        ax3.set_xlabel('Daily P&L ($)', fontsize=10)
        ax3.set_ylabel('Density', fontsize=10)
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='best', fontsize=8)

        # Format x-axis for currency
        ax3.ticklabel_format(style='plain', axis='x')

        # Statistics text
        stats_before_pnl = (
            f"n = {len(before_pnl)}\n"
            f"Mean = ${before_pnl.mean():,.0f}\n"
            f"Median = ${before_pnl.median():,.0f}\n"
            f"Std = ${before_pnl.std():,.0f}\n"
            f"Total = ${before_pnl.sum():,.0f}\n"
            f"Skew = {before_pnl.skew():.2f}"
        )
        ax3.text(0.02, 0.98, stats_before_pnl, transform=ax3.transAxes,
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7),
                verticalalignment='top', fontsize=8, family='monospace')

        # ========== Plot 4: After Graduation - P&L Distribution ==========
        ax4.hist(after_pnl, bins=50, alpha=0.7, color='gold',
                edgecolor='black', density=True, label='Histogram')

        # Add KDE
        kde_after_pnl = stats.gaussian_kde(after_pnl.dropna())
        x_range_after_pnl = np.linspace(after_pnl.min(), after_pnl.max(), 300)
        ax4.plot(x_range_after_pnl, kde_after_pnl(x_range_after_pnl),
                color='darkorange', linewidth=2.5, label='KDE')

        # Add vertical line for mean
        mean_after_pnl = after_pnl.mean()
        ax4.axvline(mean_after_pnl, color='red', linestyle='--', linewidth=2,
                   label=f'Mean: ${mean_after_pnl:,.0f}')

        ax4.set_title(f'{etf} - After Graduation (≥1% Period)\nDaily P&L Distribution',
                     fontsize=12, fontweight='bold')
        ax4.set_xlabel('Daily P&L ($)', fontsize=10)
        ax4.set_ylabel('Density', fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='best', fontsize=8)

        # Format x-axis for currency
        ax4.ticklabel_format(style='plain', axis='x')

        # Statistics text
        stats_after_pnl = (
            f"n = {len(after_pnl)}\n"
            f"Mean = ${after_pnl.mean():,.0f}\n"
            f"Median = ${after_pnl.median():,.0f}\n"
            f"Std = ${after_pnl.std():,.0f}\n"
            f"Total = ${after_pnl.sum():,.0f}\n"
            f"Skew = {after_pnl.skew():.2f}"
        )
        ax4.text(0.02, 0.98, stats_after_pnl, transform=ax4.transAxes,
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7),
                verticalalignment='top', fontsize=8, family='monospace')

        # Overall title
        etf_summary = summary_df[summary_df['ETF'] == etf].iloc[0]
        num_graduated = int(etf_summary['Num_Graduated_Stocks'])

        plt.suptitle(f'{etf} - Graduated Stocks Distribution ({num_graduated} stocks)',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()

        # Save chart
        output_file = f"{OUTPUT_DIRS['graduation']}/{etf}_Graduated_Distribution.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ {etf}: Distribution chart")

def run():
    """Main function to create graduation distribution charts"""

    plot_graduation_distribution()

if __name__ == "__main__":
    run()
