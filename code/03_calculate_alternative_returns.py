"""
Calculate alternative returns if positions in weight range were excluded
Compare actual ETF returns vs returns without positions in weight range
Using position-weighted return calculation
"""

import pandas as pd
import numpy as np
import os
from config import OUTPUT_DIRS, CURRENT_RANGE
from data_config import get_data_path

def calculate_returns_comparison(etf_name):
    """
    Calculate and compare returns using position-weighted method:
    Return = Sum(Yesterday_Position * Today_Price) / Sum(Yesterday_Position * Yesterday_Price)
    """
    
    df = pd.read_excel(get_data_path(etf_name), sheet_name='Sheet1')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100
    
    # Sort by date and stock
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    # Calculate yesterday's position and price for each stock
    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    
    # Skip non-trading days (where price equals yesterday's price for ALL stocks)
    # This happens on holidays when data is repeated from previous day
    df['Price_Changed'] = df['Stock_Price'] != df['Yesterday_Price']
    
    # Calculate position value for return calculation
    df['Yesterday_Value'] = df['Yesterday_Position'] * df['Yesterday_Price']
    df['Today_Value'] = df['Yesterday_Position'] * df['Stock_Price']
    
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
        
        # Calculate return for all positions
        total_yesterday_value = date_df['Yesterday_Value'].sum()
        total_today_value = date_df['Today_Value'].sum()
        
        # Calculate return for positions excluding current weight range
        # Use yesterday's weight to determine which positions to include
        date_df['Yesterday_Weight'] = (date_df['Yesterday_Value'] / total_yesterday_value) * 100
        
        # Filter based on current weight range
        if CURRENT_RANGE:
            # Positions IN the current range (to be excluded from alternative return)
            in_range = date_df[(date_df['Yesterday_Weight'] >= CURRENT_RANGE['min']) & 
                              (date_df['Yesterday_Weight'] < CURRENT_RANGE['max'])]
            # Positions OUTSIDE the current range (to be kept for alternative return)
            out_of_range = date_df[(date_df['Yesterday_Weight'] < CURRENT_RANGE['min']) | 
                                   (date_df['Yesterday_Weight'] >= CURRENT_RANGE['max'])]
        else:
            # Default fallback when no range specified
            in_range = date_df[date_df['Yesterday_Weight'] < 1]
            out_of_range = date_df[date_df['Yesterday_Weight'] >= 1]
        
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
            'Return_SmallOnly': return_small_only,
            'Total_Yesterday_Value': total_yesterday_value,
            'Total_Today_Value': total_today_value,
            'Large_Yesterday_Value': large_yesterday_value,
            'Large_Today_Value': large_today_value,
            'Small_Yesterday_Value': small_yesterday_value,
            'Small_Today_Value': small_today_value
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
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    
    # Store all results
    all_results = {}
    all_weekly_results = {}
    
    # Calculate for all ETFs
    for etf in etfs:
        daily_data = calculate_returns_comparison(etf)
        all_results[etf] = daily_data
        
        # Convert to weekly data
        daily_data['Week'] = pd.to_datetime(daily_data['Date']).dt.to_period('W')
        
        # Calculate weekly returns from daily cumulative returns
        weekly_data = daily_data.groupby('Week').agg({
            'Date': 'last',
            'Cumulative_Actual': 'last',
            'Cumulative_ExcludeSmall': 'last',
            'Cumulative_SmallOnly': 'last'
        }).reset_index()
        
        # Calculate weekly returns
        weekly_data['Weekly_Return_Actual'] = weekly_data['Cumulative_Actual'].pct_change()
        weekly_data['Weekly_Return_ExcludeSmall'] = weekly_data['Cumulative_ExcludeSmall'].pct_change()
        weekly_data['Weekly_Return_SmallOnly'] = weekly_data['Cumulative_SmallOnly'].pct_change()
        
        # For first week, use the cumulative return as the weekly return
        if len(weekly_data) > 0:
            weekly_data.loc[0, 'Weekly_Return_Actual'] = weekly_data.loc[0, 'Cumulative_Actual'] - 1
            weekly_data.loc[0, 'Weekly_Return_ExcludeSmall'] = weekly_data.loc[0, 'Cumulative_ExcludeSmall'] - 1
            weekly_data.loc[0, 'Weekly_Return_SmallOnly'] = weekly_data.loc[0, 'Cumulative_SmallOnly'] - 1
        
        all_weekly_results[etf] = weekly_data
    
    # Save data to Excel with weekly data
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'Alternative'
    output_filename = f"{folder_suffix}_Returns_Data.xlsx"
    output_path = f"{OUTPUT_DIRS['returns']}/{output_filename}"
    
    with pd.ExcelWriter(output_path) as writer:
        # Save daily data for each ETF
        for etf in etfs:
            daily_data = all_results[etf]
            daily_data.to_excel(writer, sheet_name=f'{etf}_Daily', index=False)
        
        # Save weekly data for each ETF
        for etf in etfs:
            weekly_data = all_weekly_results[etf].copy()
            
            # Select and rename columns for output
            output_data = pd.DataFrame({
                'Week': weekly_data['Week'].astype(str),
                'Date': weekly_data['Date'],
                'Weekly_Return_Total_%': weekly_data['Weekly_Return_Actual'] * 100,
                'Weekly_Return_SmallOnly_%': weekly_data['Weekly_Return_SmallOnly'] * 100,
                'Weekly_Return_ExcludeSmall_%': weekly_data['Weekly_Return_ExcludeSmall'] * 100,
                'Cumulative_Return_Total_%': (weekly_data['Cumulative_Actual'] - 1) * 100,
                'Cumulative_Return_SmallOnly_%': (weekly_data['Cumulative_SmallOnly'] - 1) * 100,
                'Cumulative_Return_ExcludeSmall_%': (weekly_data['Cumulative_ExcludeSmall'] - 1) * 100
            })
            
            output_data.to_excel(writer, sheet_name=f'{etf}_Weekly', index=False)
        
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
    
    
    return all_results

def run():
    """Main function to calculate and save alternative returns data"""
    result = save_alternative_returns_data()
    print("✅ Alternative returns calculated")
    return result

if __name__ == "__main__":
    run()