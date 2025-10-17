"""
Calculate position market value data (weekly aggregation)
Shows the market value and percentage of AUM allocated to positions in weight range
"""

import pandas as pd
import numpy as np
import os
from config import (CURRENT_RANGE, OUTPUT_DIRS, load_etf_data,
                    filter_by_weight_range, get_selected_etfs)

def calculate_weekly_market_value(etf_name):
    """Calculate the weekly aggregated market value of positions in weight range"""

    # Load data using unified function
    df = load_etf_data(etf_name)
    
    # Add week identifier
    df['Week'] = df['Date'].dt.to_period('W')

    # Filter for positions in weight range
    df_small = filter_by_weight_range(df)
    
    # Calculate weekly total for positions in weight range (sum across all days in the week)
    weekly_small = df_small.groupby('Week').agg({
        'Market Value': 'sum'
    }).reset_index()
    weekly_small.columns = ['Week', 'Small_MV_Total']
    
    # Calculate weekly total for all positions (sum across all days in the week)
    weekly_all = df.groupby('Week').agg({
        'Market Value': 'sum'
    }).reset_index()
    weekly_all.columns = ['Week', 'Total_MV']
    
    # Merge the data
    weekly_data = weekly_small.merge(weekly_all, on='Week', how='left')
    
    # Calculate percentage
    weekly_data['Small_MV_Pct'] = (weekly_data['Small_MV_Total'] / weekly_data['Total_MV']) * 100
    
    # Convert Week back to datetime (use start of week)
    weekly_data['Date'] = weekly_data['Week'].dt.to_timestamp()
    
    # Sort by date
    weekly_data = weekly_data.sort_values('Date')
    
    return weekly_data[['Date', 'Small_MV_Total', 'Total_MV', 'Small_MV_Pct']]

def calculate_weekly_market_value_by_range(etf_name):
    """Calculate the weekly aggregated market value for all weight ranges"""

    # Load data using unified function
    df = load_etf_data(etf_name)
    
    # Add week identifier
    df['Week'] = df['Date'].dt.to_period('W')
    
    # Define weight ranges
    weight_ranges = {
        '<1%': (0, 1),
        '1-2.5%': (1, 2.5),
        '2.5-5%': (2.5, 5),
        '5-7.5%': (5, 7.5),
        '>7.5%': (7.5, 100)
    }
    
    # Calculate market value for each weight range
    weekly_results = []
    
    for week in df['Week'].unique():
        week_data = df[df['Week'] == week]
        week_result = {'Week': week}
        
        # Total market value for the week
        total_mv = week_data['Market Value'].sum()
        week_result['Total_MV'] = total_mv
        
        # Market value for each weight range
        for range_name, (min_weight, max_weight) in weight_ranges.items():
            range_data = week_data[(week_data['Weight'] >= min_weight) & (week_data['Weight'] < max_weight)]
            range_mv = range_data['Market Value'].sum()
            week_result[f'MV_{range_name}'] = range_mv
            week_result[f'MV_Pct_{range_name}'] = (range_mv / total_mv * 100) if total_mv > 0 else 0
        
        weekly_results.append(week_result)
    
    # Convert to DataFrame
    weekly_data = pd.DataFrame(weekly_results)
    
    # Convert Week back to datetime (use start of week)
    weekly_data['Date'] = weekly_data['Week'].dt.to_timestamp()
    
    # Sort by date
    weekly_data = weekly_data.sort_values('Date')
    
    return weekly_data

def save_market_value_data():
    """Calculate and save market value data to Excel"""

    etfs = get_selected_etfs()

    all_data = {}
    all_range_data = {}

    # Calculate for each ETF
    for etf in etfs:
        weekly_data = calculate_weekly_market_value(etf)
        all_data[etf] = weekly_data

        # Also calculate market value by weight range
        range_data = calculate_weekly_market_value_by_range(etf)
        all_range_data[etf] = range_data
        print(f"  ✓ {etf}: Market value")
    
    # Save data to Excel
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'under_1pct'
    output_filename = f"{folder_suffix}_Market_Value_Data.xlsx"
    output_path = f"{OUTPUT_DIRS['market_value']}/{output_filename}"
    
    with pd.ExcelWriter(output_path) as writer:
        for etf in etfs:
            data = all_data[etf].copy()
            data.to_excel(writer, sheet_name=etf, index=False)
            
            # Save range data
            range_data = all_range_data[etf].copy()
            range_data.to_excel(writer, sheet_name=f'{etf}_Ranges', index=False)
        
        # Create summary sheet
        summary_data = []
        for etf in etfs:
            data = all_data[etf]
            summary_data.append({
                'ETF': etf,
                'Latest_Date': data['Date'].max(),
                'Latest_Small_MV': data.iloc[-1]['Small_MV_Total'],
                'Latest_Total_MV': data.iloc[-1]['Total_MV'],
                'Latest_Small_MV_Pct': data.iloc[-1]['Small_MV_Pct'],
                'Avg_Small_MV': data['Small_MV_Total'].mean(),
                'Avg_Small_MV_Pct': data['Small_MV_Pct'].mean(),
                'Max_Small_MV': data['Small_MV_Total'].max(),
                'Min_Small_MV': data['Small_MV_Total'].min()
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)


    return all_data, all_range_data

def run():
    """Main function to calculate and save market value data"""
    result = save_market_value_data()
    return result

if __name__ == "__main__":
    run()