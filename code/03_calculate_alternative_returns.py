"""
Calculate alternative returns if positions in weight range were excluded
Compare actual ETF returns vs returns without positions in weight range
Using weight-normalized return calculation
"""

import pandas as pd
import numpy as np
import os
from config import (OUTPUT_DIRS, CURRENT_RANGE, load_etf_data, get_selected_etfs)

def calculate_returns_comparison(etf_name):
    """
    Calculate and compare returns using weight-normalized method:
    1. Each stock return = (today_price / yesterday_price) - 1
    2. Group return = Σ(stock_return × normalized_weight)
    3. Cumulative return = sum of daily returns
    """

    # Load data
    df = load_etf_data(etf_name)
    df = df.sort_values(['Bloomberg Name', 'Date']).reset_index(drop=True)

    # Calculate yesterday's price for return calculation
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)

    # Calculate stock return
    df['Stock_Return'] = (df['Stock_Price'] - df['Yesterday_Price']) / df['Yesterday_Price']

    # Group by date to calculate daily returns
    daily_results = []

    for date in df['Date'].unique():
        date_df = df[df['Date'] == date].copy()

        # Remove rows without yesterday price (can't calculate return)
        date_df = date_df.dropna(subset=['Yesterday_Price', 'Stock_Return'])

        if len(date_df) == 0:
            continue

        # Skip non-trading days by checking if any stock had price change
        if (date_df['Stock_Price'] == date_df['Yesterday_Price']).all():
            continue

        # Filter based on current weight range
        # Exclude positions with affiliation_check == 1 from being considered small
        if CURRENT_RANGE:
            # Positions IN the current range (small positions)
            small_positions = date_df[(date_df['Weight'] >= CURRENT_RANGE['min']) &
                                     (date_df['Weight'] < CURRENT_RANGE['max']) &
                                     (date_df['affiliation_check'] == 0)].copy()
            # Positions OUTSIDE the current range (large positions)
            large_positions = date_df[(date_df['Weight'] < CURRENT_RANGE['min']) |
                                     (date_df['Weight'] >= CURRENT_RANGE['max']) |
                                     (date_df['affiliation_check'] == 1)].copy()
        else:
            # Default fallback for <1%
            small_positions = date_df[(date_df['Weight'] < 1) &
                                     (date_df['affiliation_check'] == 0)].copy()
            large_positions = date_df[(date_df['Weight'] >= 1) |
                                     (date_df['affiliation_check'] == 1)].copy()

        # Calculate return for all positions (actual ETF return)
        total_weight = date_df['Weight'].sum()
        if total_weight > 0:
            date_df['Normalized_Weight'] = date_df['Weight'] / total_weight
            return_actual = (date_df['Stock_Return'] * date_df['Normalized_Weight']).sum()
        else:
            return_actual = 0

        # Calculate return for small positions only
        small_weight = small_positions['Weight'].sum()
        if small_weight > 0 and len(small_positions) > 0:
            small_positions['Normalized_Weight'] = small_positions['Weight'] / small_weight
            return_small_only = (small_positions['Stock_Return'] * small_positions['Normalized_Weight']).sum()
        else:
            return_small_only = 0

        # Calculate return for large positions only (excluding small)
        large_weight = large_positions['Weight'].sum()
        if large_weight > 0 and len(large_positions) > 0:
            large_positions['Normalized_Weight'] = large_positions['Weight'] / large_weight
            return_exclude_small = (large_positions['Stock_Return'] * large_positions['Normalized_Weight']).sum()
        else:
            return_exclude_small = 0

        daily_results.append({
            'Date': date,
            'Return_Actual': return_actual,
            'Return_ExcludeSmall': return_exclude_small,
            'Return_SmallOnly': return_small_only
        })

    comparison = pd.DataFrame(daily_results)
    comparison = comparison.sort_values('Date').reset_index(drop=True)

    # Calculate cumulative returns (simple sum)
    comparison['Cumulative_Actual'] = comparison['Return_Actual'].fillna(0).cumsum()
    comparison['Cumulative_ExcludeSmall'] = comparison['Return_ExcludeSmall'].fillna(0).cumsum()
    comparison['Cumulative_SmallOnly'] = comparison['Return_SmallOnly'].fillna(0).cumsum()

    return comparison

def save_alternative_returns_data():
    """Calculate and save alternative returns data to Excel"""

    etfs = get_selected_etfs()

    # Store all results
    all_results = {}

    # Calculate for all ETFs
    for etf in etfs:
        daily_data = calculate_returns_comparison(etf)
        all_results[etf] = daily_data
        print(f"  ✓ {etf}: Alternative returns")

    # Save data to Excel
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'Alternative'
    output_filename = f"{folder_suffix}_Returns_Data.xlsx"
    output_path = f"{OUTPUT_DIRS['returns']}/{output_filename}"

    with pd.ExcelWriter(output_path) as writer:
        # Save daily data for each ETF
        for etf in etfs:
            daily_data = all_results[etf]
            daily_data.to_excel(writer, sheet_name=f'{etf}_Daily', index=False)

        # Create summary sheet with final results
        summary_data = []
        for etf in etfs:
            data = all_results[etf]
            final_actual = data['Cumulative_Actual'].iloc[-1] * 100
            final_small = data['Cumulative_SmallOnly'].iloc[-1] * 100
            final_exclude = data['Cumulative_ExcludeSmall'].iloc[-1] * 100

            summary_data.append({
                'ETF': etf,
                'Final_Cumulative_Return_Total_%': final_actual,
                'Final_Cumulative_Return_SmallOnly_%': final_small,
                'Final_Cumulative_Return_ExcludeSmall_%': final_exclude,
                'Small_vs_Total_Difference_%': final_small - final_actual,
                'ExcludeSmall_vs_Total_Difference_%': final_exclude - final_actual
            })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)


    return all_results, summary_df

def run():
    """Main function to calculate and save alternative returns data"""
    result = save_alternative_returns_data()
    return result

if __name__ == "__main__":
    run()
