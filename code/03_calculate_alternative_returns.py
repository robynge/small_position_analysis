"""
Calculate alternative returns if positions in weight range were excluded
Compare actual ETF returns vs returns without positions in weight range
Using position-weighted return calculation
"""

import pandas as pd
import numpy as np
import os
from config import (OUTPUT_DIRS, CURRENT_RANGE, load_etf_data,
                    calculate_yesterday_values, get_selected_etfs)

def calculate_returns_comparison(etf_name):
    """
    Calculate and compare returns using position-weighted method:
    Return = Sum(Yesterday_Position * Today_Price) / Sum(Yesterday_Position * Yesterday_Price)
    """

    # Load data using unified function
    df = load_etf_data(etf_name)

    # Calculate yesterday's values
    df = calculate_yesterday_values(df)
    
    # Group by date to calculate daily returns
    daily_results = []
    
    for date in df['Date'].unique():
        date_df = df[df['Date'] == date].copy()
        
        # Remove rows without yesterday data (first day for each stock)
        date_df = date_df.dropna(subset=['Yesterday_Value', 'Today_Value'])
        
        if len(date_df) == 0:
            continue
        
        # Skip non-trading days (holidays) where no prices changed
        # Check if ANY stock had a price change on this date
        if not date_df['Price_Changed'].any():
            continue  # Skip this date - it's a holiday with repeated data
        
        # Calculate return for positions excluding current weight range
        # Use yesterday's weight to determine which positions to include
        # Exclude new positions (where Yesterday_Position = 0 or Yesterday_Value = 0)
        date_df = date_df[date_df['Yesterday_Value'] > 0].copy()

        if len(date_df) == 0:
            continue

        total_yesterday_value = date_df['Yesterday_Value'].sum()
        total_today_value = date_df['Today_Value'].sum()

        date_df['Yesterday_Weight'] = (date_df['Yesterday_Value'] / total_yesterday_value) * 100

        # Filter based on current weight range
        # Exclude positions with affiliation_check == 1 from being considered small
        if CURRENT_RANGE:
            # Positions IN the current range (to be excluded from alternative return)
            in_range = date_df[(date_df['Yesterday_Weight'] >= CURRENT_RANGE['min']) &
                              (date_df['Yesterday_Weight'] < CURRENT_RANGE['max']) &
                              (date_df['affiliation_check'] == 0)]
            # Positions OUTSIDE the current range (to be kept for alternative return)
            out_of_range = date_df[(date_df['Yesterday_Weight'] < CURRENT_RANGE['min']) |
                                   (date_df['Yesterday_Weight'] >= CURRENT_RANGE['max']) |
                                   (date_df['affiliation_check'] == 1)]
        else:
            # Default fallback when no range specified
            in_range = date_df[(date_df['Yesterday_Weight'] < 1) & (date_df['affiliation_check'] == 0)]
            out_of_range = date_df[(date_df['Yesterday_Weight'] >= 1) | (date_df['affiliation_check'] == 1)]
        
        large_positions = out_of_range  # Positions to keep
        small_positions = in_range      # Positions to exclude
        
        large_yesterday_value = large_positions['Yesterday_Value'].sum()
        large_today_value = large_positions['Today_Value'].sum()
        
        small_yesterday_value = small_positions['Yesterday_Value'].sum()
        small_today_value = small_positions['Today_Value'].sum()
        
        # Calculate returns
        return_actual = (total_today_value / total_yesterday_value - 1) if total_yesterday_value > 0 else 0
        return_exclude_small = (large_today_value / large_yesterday_value - 1) if large_yesterday_value > 0 else 0
        return_small_only = (small_today_value / small_yesterday_value - 1) if small_yesterday_value > 0 else 0

        daily_results.append({
            'Date': date,
            'Return_Actual': return_actual,
            'Return_ExcludeSmall': return_exclude_small,
            'Return_SmallOnly': return_small_only
        })
    
    comparison = pd.DataFrame(daily_results)
    comparison = comparison.sort_values('Date').reset_index(drop=True)
    
    # Calculate cumulative returns (starting from 1)
    comparison['Cumulative_Actual'] = (1 + comparison['Return_Actual'].fillna(0)).cumprod()
    comparison['Cumulative_ExcludeSmall'] = (1 + comparison['Return_ExcludeSmall'].fillna(0)).cumprod()
    comparison['Cumulative_SmallOnly'] = (1 + comparison['Return_SmallOnly'].fillna(0)).cumprod()
    
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
            final_actual = (data['Cumulative_Actual'].iloc[-1] - 1) * 100
            final_small = (data['Cumulative_SmallOnly'].iloc[-1] - 1) * 100
            final_exclude = (data['Cumulative_ExcludeSmall'].iloc[-1] - 1) * 100

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