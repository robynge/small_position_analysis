"""
Calculate position counts in weight range over time and save to Excel
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE
from data_config import get_data_path

def process_etf_data(fund_name):
    """Process a single ETF's data to get daily position counts by weight ranges"""
    
    
    # Read the data using centralized path
    df = pd.read_excel(get_data_path(fund_name), sheet_name='Sheet1')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100
    
    # Group by Date to get daily counts for ALL weight ranges
    daily_data = []
    
    for date in df['Date'].unique():
        date_df = df[df['Date'] == date]
        
        # Total positions for this date
        total_positions = len(date_df)
        
        # Count positions in each weight range
        count_under_1 = len(date_df[date_df['Weight'] < 1])
        count_1_to_2_5 = len(date_df[(date_df['Weight'] >= 1) & (date_df['Weight'] < 2.5)])
        count_2_5_to_5 = len(date_df[(date_df['Weight'] >= 2.5) & (date_df['Weight'] < 5)])
        count_5_to_7_5 = len(date_df[(date_df['Weight'] >= 5) & (date_df['Weight'] < 7.5)])
        count_over_7_5 = len(date_df[date_df['Weight'] >= 7.5])
        
        # Count positions in current selected weight range
        if CURRENT_RANGE:
            selected_positions = len(date_df[(date_df['Weight'] >= CURRENT_RANGE['min']) & 
                                            (date_df['Weight'] < CURRENT_RANGE['max'])])
        else:
            selected_positions = count_under_1
        
        # Calculate percentage for selected range
        selected_percentage = (selected_positions / total_positions * 100) if total_positions > 0 else 0
        
        daily_data.append({
            'Date': date,
            '<1%': count_under_1,
            '1-2.5%': count_1_to_2_5,
            '2.5-5%': count_2_5_to_5,
            '5-7.5%': count_5_to_7_5,
            '>7.5%': count_over_7_5,
            'Total_Positions': total_positions,
            'Selected_Positions': selected_positions,
            'Selected_Percentage': selected_percentage
        })
    
    # Convert to DataFrame
    result = pd.DataFrame(daily_data)
    result = result.sort_values('Date')
    
    return result

def save_positions_data_to_excel(all_data):
    """Save position data to Excel with proper structure"""
    
    weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
    folder_suffix = CURRENT_RANGE['folder'] if CURRENT_RANGE else 'under_1pct'
    
    # Create Excel file with one sheet per ETF
    output_filename = f"{folder_suffix}_Positions_Data.xlsx"
    output_path = f"{OUTPUT_DIRS['position']}/{output_filename}"
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for etf, data in all_data.items():
            # Save raw daily data
            data.to_excel(writer, sheet_name=etf, index=False)
        
        # Create summary sheet
        summary_data = []
        for etf, data in all_data.items():
            summary_data.append({
                'ETF': etf,
                'Latest_Date': data['Date'].max(),
                'Latest_Selected_Positions': data.iloc[-1]['Selected_Positions'],
                'Latest_Total_Positions': data.iloc[-1]['Total_Positions'],
                'Latest_Selected_Percentage': data.iloc[-1]['Selected_Percentage'],
                'Avg_Selected_Positions': data['Selected_Positions'].mean(),
                'Avg_Selected_Percentage': data['Selected_Percentage'].mean(),
                'Max_Selected_Positions': data['Selected_Positions'].max(),
                'Min_Selected_Positions': data['Selected_Positions'].min()
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    

def run():
    """Main function to calculate and save position data"""
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    
    all_data = {}
    
    # Process each ETF
    for etf in etfs:
        data = process_etf_data(etf)
        all_data[etf] = data
    
    # Save data to Excel
    save_positions_data_to_excel(all_data)
    
    print("✅ Position data calculated")

if __name__ == "__main__":
    run()