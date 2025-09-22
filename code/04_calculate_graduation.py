"""
Analyze cumulative returns of graduated positions (from weight range to higher)
Compare: 
1. All positions in weight range cumulative return
2. Graduated positions (those that moved from weight range to higher) cumulative return
Using position-weighted calculation method from module 07
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE
from data_config import get_data_path
import os

def calculate_graduated_returns(etf_name):
    """
    Calculate cumulative returns for:
    1. All positions in weight range
    2. Positions that graduated from weight range to higher
    Using the same method as module 07:
    Return = Sum(Yesterday_Position * Today_Price) / Sum(Yesterday_Position * Yesterday_Price)
    """
    
    # Read data
    df = pd.read_excel(get_data_path(etf_name), sheet_name='Sheet1')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100
    df['Weight_Pct'] = df['Weight']  # For compatibility
    
    # Sort by stock and date
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    # Identify graduated positions
    graduated_tickers = set()
    for ticker, group in df.groupby('Bloomberg Name'):
        group = group.sort_values('Date')
        # Check if this ticker ever graduated from weight range to higher
        was_small = False
        weight_threshold = CURRENT_RANGE['max'] if CURRENT_RANGE else 1.0
        for idx in range(len(group)):
            weight = group.iloc[idx]['Weight_Pct']
            if weight < weight_threshold:
                was_small = True
            elif was_small and weight >= weight_threshold:
                # This ticker graduated
                graduated_tickers.add(ticker)
                break
    
    
    # Calculate yesterday's position and price for each stock
    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    
    
    # Calculate position value for return calculation
    df['Yesterday_Value'] = df['Yesterday_Position'] * df['Yesterday_Price']
    df['Today_Value'] = df['Yesterday_Position'] * df['Stock_Price']
    
    # Group by date to calculate daily returns
    daily_results = []
    
    for date in df['Date'].unique():
        date_df = df[df['Date'] == date].copy()
        
        # Remove rows without yesterday data
        date_df = date_df.dropna(subset=['Yesterday_Value', 'Today_Value'])
        
        if len(date_df) == 0:
            continue
        
        # Calculate return for ALL positions in weight range
        # Use yesterday's weight to determine which positions to include
        total_yesterday_value_all = date_df['Yesterday_Value'].sum()
        date_df['Yesterday_Weight'] = (date_df['Yesterday_Value'] / total_yesterday_value_all) * 100
        
        # Small positions are those in weight range yesterday
        # Filter based on current weight range
        if CURRENT_RANGE:
            small_positions = date_df[(date_df['Yesterday_Weight'] >= CURRENT_RANGE['min']) & 
                                     (date_df['Yesterday_Weight'] < CURRENT_RANGE['max'])]
        else:
            small_positions = date_df[date_df['Yesterday_Weight'] < 1]
        
        small_yesterday_value = small_positions['Yesterday_Value'].sum()
        small_today_value = small_positions['Today_Value'].sum()
        
        # Calculate return for GRADUATED positions that are NOW above range
        # These are graduated tickers that are currently in large position state (above range)
        # Positions above the weight range
        if CURRENT_RANGE:
            large_positions = date_df[date_df['Yesterday_Weight'] >= CURRENT_RANGE['max']]
        else:
            large_positions = date_df[date_df['Yesterday_Weight'] >= 1]
        graduated_large = large_positions[large_positions['Bloomberg Name'].isin(graduated_tickers)]
        
        grad_yesterday_value = graduated_large['Yesterday_Value'].sum()
        grad_today_value = graduated_large['Today_Value'].sum()
        
        # Calculate returns
        return_small = (small_today_value / small_yesterday_value - 1) if small_yesterday_value > 0 else 0
        return_graduated = (grad_today_value / grad_yesterday_value - 1) if grad_yesterday_value > 0 else 0
        
        
        daily_results.append({
            'Date': date,
            'Return_SmallPositions': return_small,
            'Return_Graduated': return_graduated,
            'Small_Yesterday_Value': small_yesterday_value,
            'Small_Today_Value': small_today_value,
            'Graduated_Yesterday_Value': grad_yesterday_value,
            'Graduated_Today_Value': grad_today_value,
            'Num_Small_Positions': len(small_positions),
            'Num_Graduated_Large': len(graduated_large)
        })
    
    comparison = pd.DataFrame(daily_results)
    comparison = comparison.sort_values('Date').reset_index(drop=True)
    
    # Calculate cumulative returns (starting from 1)
    comparison['Cumulative_SmallPositions'] = (1 + comparison['Return_SmallPositions'].fillna(0)).cumprod()
    comparison['Cumulative_Graduated'] = (1 + comparison['Return_Graduated'].fillna(0)).cumprod()
    
    return comparison, graduated_tickers

def calculate_all_graduated_returns():
    """Calculate graduated returns for all ETFs"""
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    
    all_results = {}
    all_graduated_tickers = {}
    
    # Calculate for all ETFs
    for etf in etfs:
        data, graduated = calculate_graduated_returns(etf)
        all_results[etf] = data
        all_graduated_tickers[etf] = graduated
    
    return all_results, all_graduated_tickers

def save_graduation_data(all_results, all_graduated_tickers):
    """Save graduation analysis data to Excel"""
    
    output_dir = OUTPUT_DIRS['graduation']
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/Graduation_Returns_Data.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = []
        for etf in all_results.keys():
            data = all_results[etf]
            final_small = (data['Cumulative_SmallPositions'].iloc[-1] - 1) * 100
            final_grad = (data['Cumulative_Graduated'].iloc[-1] - 1) * 100
            
            # Calculate average number of graduated positions in large state
            avg_graduated_large = data['Num_Graduated_Large'].mean()
            
            summary_data.append({
                'ETF': etf,
                'Final_Return_AllSmall_%': round(final_small, 2),
                'Final_Return_Graduated_%': round(final_grad, 2),
                'Difference_%': round(final_grad - final_small, 2),
                'Num_Graduated_Tickers': len(all_graduated_tickers[etf]),
                'Avg_Graduated_Large': round(avg_graduated_large, 2)
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Weekly data for each ETF
        for etf in all_results.keys():
            data = all_results[etf].copy()
            
            # Convert to weekly
            data['Week'] = pd.to_datetime(data['Date']).dt.to_period('W')
            weekly = data.groupby('Week').agg({
                'Date': 'last',
                'Cumulative_SmallPositions': 'last',
                'Cumulative_Graduated': 'last',
                'Num_Small_Positions': 'mean',
                'Num_Graduated_Large': 'mean'
            }).reset_index()
            
            # Calculate weekly returns
            weekly['Weekly_Return_Small_%'] = weekly['Cumulative_SmallPositions'].pct_change() * 100
            weekly['Weekly_Return_Graduated_%'] = weekly['Cumulative_Graduated'].pct_change() * 100
            weekly['Cumulative_Return_Small_%'] = (weekly['Cumulative_SmallPositions'] - 1) * 100
            weekly['Cumulative_Return_Graduated_%'] = (weekly['Cumulative_Graduated'] - 1) * 100
            
            # Select columns for output
            output_data = weekly[['Week', 'Date', 
                                 'Weekly_Return_Small_%', 'Weekly_Return_Graduated_%',
                                 'Cumulative_Return_Small_%', 'Cumulative_Return_Graduated_%',
                                 'Num_Small_Positions', 'Num_Graduated_Large']].copy()
            output_data['Week'] = output_data['Week'].astype(str)
            
            output_data.to_excel(writer, sheet_name=etf, index=False)
        
        # List of graduated tickers
        graduated_list = []
        for etf, tickers in all_graduated_tickers.items():
            for ticker in tickers:
                graduated_list.append({'ETF': etf, 'Ticker': ticker})
        
        graduated_df = pd.DataFrame(graduated_list)
        graduated_df.to_excel(writer, sheet_name='Graduated_Tickers', index=False)
    
    
    return summary_df

def run():
    """Main function to calculate and save graduation analysis data"""
    
    # Calculate graduated returns
    all_results, all_graduated_tickers = calculate_all_graduated_returns()
    
    # Save data
    summary = save_graduation_data(all_results, all_graduated_tickers)
    
    print("✅ Graduation analysis completed")
    
    return all_results, all_graduated_tickers

if __name__ == "__main__":
    run()