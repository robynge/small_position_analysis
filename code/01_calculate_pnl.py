"""
P&L Calculation for Positions in Weight Range
Formula: (Yesterday's Position × Today's Price) - (Yesterday's Position × Yesterday's Price)
This calculates the value change rather than just price difference
"""

import pandas as pd
import numpy as np
import os
from config import OUTPUT_DIRS, CURRENT_RANGE
from data_config import get_data_path

def calculate_pnl(etf_name):
    """
    Calculate P&L for positions in current weight range using value-based formula:
    Daily P&L = (Yesterday's Position × Today's Price) - (Yesterday's Position × Yesterday's Price)
    Then sum all positions in weight range for each day
    """
    
    # Read data using centralized path
    df = pd.read_excel(get_data_path(etf_name), sheet_name='Sheet1')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100
    
    # Sort by stock and date
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    # Calculate yesterday's values for ALL positions first
    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    
    # Calculate value-based P&L components
    df['Yesterday_Value'] = df['Yesterday_Position'] * df['Yesterday_Price']
    df['Today_Value'] = df['Yesterday_Position'] * df['Stock_Price']  # Note: using yesterday's position
    
    # Now filter for positions in current weight range
    if CURRENT_RANGE:
        df_small = df[(df['Weight'] >= CURRENT_RANGE['min']) & 
                     (df['Weight'] < CURRENT_RANGE['max'])].copy()
    else:
        # Default fallback for backward compatibility
        df_small = df[df['Weight'] < 1].copy()
    
    # Calculate P&L as value change
    df_small['Daily_PnL'] = df_small['Today_Value'] - df_small['Yesterday_Value']
    
    # Remove NaN values (first day has no yesterday)
    df_small = df_small.dropna(subset=['Daily_PnL'])
    
    # Skip non-trading days (where no prices changed)
    # Group by date and check if any stock had a price change
    df_small['Price_Changed'] = df_small['Stock_Price'] != df_small['Yesterday_Price']
    dates_with_changes = df_small.groupby('Date')['Price_Changed'].any()
    valid_dates = dates_with_changes[dates_with_changes].index
    df_small = df_small[df_small['Date'].isin(valid_dates)]
    
    # Aggregate daily P&L across all positions in weight range
    daily_summary = df_small.groupby('Date')['Daily_PnL'].sum().reset_index()
    daily_summary = daily_summary.sort_values('Date')
    
    # Calculate cumulative P&L
    daily_summary['Cumulative_PnL'] = daily_summary['Daily_PnL'].cumsum()
    
    return daily_summary

def calculate_loss_table(etf_name):
    """Calculate loss contribution table for positions in weight range"""
    
    # Read data
    df = pd.read_excel(get_data_path(etf_name), sheet_name='Sheet1')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert Weight from decimal to percentage
    df['Weight'] = df['Weight'] * 100
    
    # Filter out rows with zero or invalid prices
    df = df[(df['Stock_Price'] > 0) & (df['Stock_Price'].notna())]
    
    # Sort by ticker and date
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    # Calculate daily P&L for each position
    df['Prev_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Prev_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Yesterday_Value'] = df['Prev_Position'] * df['Prev_Price']
    df['Today_Value'] = df['Prev_Position'] * df['Stock_Price']
    df['Daily_PnL'] = df['Today_Value'] - df['Yesterday_Value']
    
    # Filter for positions in current weight range
    if CURRENT_RANGE:
        df_small = df[(df['Weight'] >= CURRENT_RANGE['min']) & 
                     (df['Weight'] < CURRENT_RANGE['max'])].copy()
    else:
        df_small = df[df['Weight'] < 1].copy()
    
    # Get company names
    company_names = df_small.groupby('Bloomberg Name')['Company_Name'].last().to_dict()
    
    # Aggregate P&L by stock
    stock_pnl = df_small.groupby('Bloomberg Name')['Daily_PnL'].sum().reset_index()
    stock_pnl.columns = ['Bloomberg_Name', 'Total_PnL']
    
    # Add company names
    stock_pnl['Stock'] = stock_pnl['Bloomberg_Name'].map(company_names)
    stock_pnl['Stock'] = stock_pnl['Stock'].fillna(stock_pnl['Bloomberg_Name'])
    stock_pnl['Stock'] = stock_pnl['Stock'].astype(str).replace('nan', '')
    
    # Filter only losses (negative P&L)
    stock_pnl = stock_pnl[stock_pnl['Total_PnL'] < 0].copy()
    
    # Sort by P&L (most negative first)
    stock_pnl = stock_pnl[['Stock', 'Total_PnL']].sort_values('Total_PnL')
    
    if len(stock_pnl) == 0:
        return pd.DataFrame(columns=['Rank', 'Stock', 'Loss_Millions', 'Loss_Contribution_%', 'Abs_Percentage'])
    
    # Calculate total losses
    total_losses = abs(stock_pnl['Total_PnL'].sum())
    
    # Create top 10 table
    top10 = stock_pnl.head(10).copy()
    
    # Add Others row if needed
    if len(stock_pnl) > 10:
        others_pnl = stock_pnl.iloc[10:]['Total_PnL'].sum()
        others_row = pd.DataFrame({'Stock': ['Others'], 'Total_PnL': [others_pnl]})
        table_data = pd.concat([top10, others_row], ignore_index=True)
    else:
        table_data = top10.copy()
    
    # Format table
    table_data['Rank'] = range(1, len(table_data) + 1)
    table_data['Loss_Millions'] = abs(table_data['Total_PnL']) / 1e6
    table_data['Loss_Contribution_%'] = (abs(table_data['Total_PnL']) / total_losses) * 100
    table_data['Abs_Percentage'] = abs(table_data['Loss_Contribution_%'])
    
    # Reorder columns
    table_data = table_data[['Rank', 'Stock', 'Loss_Millions', 'Loss_Contribution_%', 'Abs_Percentage']]
    
    # Round values
    table_data['Loss_Millions'] = table_data['Loss_Millions'].round(2)
    table_data['Loss_Contribution_%'] = table_data['Loss_Contribution_%'].round(1)
    table_data['Abs_Percentage'] = table_data['Abs_Percentage'].round(1)
    
    return table_data

def save_pnl_data(etf_name):
    """Calculate and save P&L data and loss table to Excel"""
    
    # Calculate P&L data
    pnl = calculate_pnl(etf_name)
    
    # Calculate loss table
    loss_table = calculate_loss_table(etf_name)
    
    # Save to PnL folder with both sheets
    output_file = f"{OUTPUT_DIRS['pnl']}/{etf_name}_PnL_Data.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        pnl.to_excel(writer, sheet_name='PnL_Data', index=False)
        loss_table.to_excel(writer, sheet_name='Loss_Table', index=False)
    
    
    return pnl

def run():
    """Main function to run P&L calculations"""
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    
    all_pnl_data = {}
    for etf in etfs:
        all_pnl_data[etf] = save_pnl_data(etf)
    
    print("✅ P&L calculation completed")
    return all_pnl_data

if __name__ == "__main__":
    run()