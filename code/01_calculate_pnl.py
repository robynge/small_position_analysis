"""
P&L Calculation for Positions in Weight Range
Uses adjusted P&L formula accounting for inflows/outflows

Formula:
- Stock Dollar P&L = day1 stock MV - day0 stock MV
- Stock Inflows/Outflows = (day1 position - day0 position) * (day1 price + day0 price) / 2
- Stock Adjusted P&L = Stock Dollar P&L - Stock Inflows/Outflows

Special cases:
- Entry position (day0 = 0): inflow = day1 position * day1 price
- Exit position (day1 = 0): outflow = -day0 position * day0 price, adj P&L = 0
"""

import pandas as pd
import numpy as np
from config import (OUTPUT_DIRS, load_etf_data,
                    filter_by_weight_range, get_selected_etfs)

def calculate_stock_pnl(df):
    """
    Calculate stock-level P&L with inflows/outflows adjustment

    Returns DataFrame with columns:
    - Date, Bloomberg Name
    - Day0_Position, Day1_Position
    - Day0_Price, Day1_Price
    - Day0_MV, Day1_MV
    - Dollar_PnL, Inflows_Outflows, Adj_PnL
    - Position_Status (Ongoing/Entry/Exit)
    """

    # Sort by stock and date
    df = df.sort_values(['Bloomberg Name', 'Date'])

    # Calculate previous day values
    df['Day0_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Day0_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)

    # Current day (Day1) values
    df['Day1_Position'] = df['Position']
    df['Day1_Price'] = df['Stock_Price']

    # Market values
    df['Day0_MV'] = df['Day0_Position'] * df['Day0_Price']
    df['Day1_MV'] = df['Day1_Position'] * df['Day1_Price']

    # Fill NaN for first day
    df['Day0_Position'] = df['Day0_Position'].fillna(0)
    df['Day0_Price'] = df['Day0_Price'].fillna(0)
    df['Day0_MV'] = df['Day0_MV'].fillna(0)

    # Identify position status
    df['Position_Status'] = 'Ongoing'
    df.loc[(df['Day0_Position'] == 0) & (df['Day1_Position'] > 0), 'Position_Status'] = 'Entry'
    df.loc[(df['Day0_Position'] > 0) & (df['Day1_Position'] == 0), 'Position_Status'] = 'Exit'

    # Calculate Dollar P&L (simple MV change)
    df['Dollar_PnL'] = df['Day1_MV'] - df['Day0_MV']

    # Calculate Inflows/Outflows based on position status
    df['Inflows_Outflows'] = 0.0

    # Ongoing positions: (day1 pos - day0 pos) * avg(day1 price, day0 price)
    ongoing_mask = df['Position_Status'] == 'Ongoing'
    df.loc[ongoing_mask, 'Inflows_Outflows'] = (
        (df.loc[ongoing_mask, 'Day1_Position'] - df.loc[ongoing_mask, 'Day0_Position']) *
        (df.loc[ongoing_mask, 'Day1_Price'] + df.loc[ongoing_mask, 'Day0_Price']) / 2
    )

    # Entry positions: inflow = day1 position * day1 price
    entry_mask = df['Position_Status'] == 'Entry'
    df.loc[entry_mask, 'Inflows_Outflows'] = (
        df.loc[entry_mask, 'Day1_Position'] * df.loc[entry_mask, 'Day1_Price']
    )

    # Exit positions: outflow = -day0 position * day0 price
    exit_mask = df['Position_Status'] == 'Exit'
    df.loc[exit_mask, 'Inflows_Outflows'] = (
        -df.loc[exit_mask, 'Day0_Position'] * df.loc[exit_mask, 'Day0_Price']
    )

    # Calculate Adjusted P&L
    # For exit positions, adj P&L = 0 (because we're realizing the position)
    df['Adj_PnL'] = df['Dollar_PnL'] - df['Inflows_Outflows']
    df.loc[exit_mask, 'Adj_PnL'] = 0.0

    return df

def calculate_pnl(etf_name):
    """
    Calculate daily adjusted P&L for positions in current weight range

    Returns:
    - daily_summary: daily total P&L
    - stock_summary: total P&L by stock
    """

    # Load data
    df = load_etf_data(etf_name)

    # Filter out invalid prices
    df = df[(df['Stock_Price'] > 0) & (df['Stock_Price'].notna())]

    # Calculate stock-level P&L for ALL positions
    df = calculate_stock_pnl(df)

    # Filter for positions in current weight range
    df_small = filter_by_weight_range(df)

    # Remove first day (no previous day for comparison)
    df_small = df_small[df_small['Day0_Position'].notna()]

    # Skip non-trading days (where no prices changed)
    df_small['Price_Changed'] = df_small['Day1_Price'] != df_small['Day0_Price']
    dates_with_changes = df_small.groupby('Date')['Price_Changed'].any()
    valid_dates = dates_with_changes[dates_with_changes].index
    df_small = df_small[df_small['Date'].isin(valid_dates)]

    # 1. Daily Total P&L
    daily_summary = df_small.groupby('Date').agg({
        'Dollar_PnL': 'sum',
        'Inflows_Outflows': 'sum',
        'Adj_PnL': 'sum'
    }).reset_index()
    daily_summary = daily_summary.sort_values('Date')
    daily_summary['Cumulative_Adj_PnL'] = daily_summary['Adj_PnL'].cumsum()

    # 2. Stock Total P&L (aggregate by stock across all time)
    company_names = df_small.groupby('Bloomberg Name')['Company_Name'].last().to_dict()
    stock_summary = df_small.groupby('Bloomberg Name')['Adj_PnL'].sum().reset_index()
    stock_summary.columns = ['Bloomberg_Name', 'Total_Adj_PnL']
    stock_summary['Stock'] = stock_summary['Bloomberg_Name'].map(company_names)
    stock_summary['Stock'] = stock_summary['Stock'].fillna(stock_summary['Bloomberg_Name'])
    stock_summary['Stock'] = stock_summary['Stock'].astype(str).replace('nan', '')
    stock_summary = stock_summary[['Stock', 'Total_Adj_PnL']].sort_values('Total_Adj_PnL')

    return daily_summary, stock_summary


def save_pnl_data(etf_name):
    """Calculate and save P&L data with 2 sheets: Daily_Total_PnL, Stock_Total_PnL"""

    # Calculate P&L data
    daily_pnl, stock_pnl = calculate_pnl(etf_name)

    # Save to PnL folder with 2 sheets
    output_file = f"{OUTPUT_DIRS['pnl']}/{etf_name}_PnL_Data.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        daily_pnl.to_excel(writer, sheet_name='Daily_Total_PnL', index=False)
        stock_pnl.to_excel(writer, sheet_name='Stock_Total_PnL', index=False)

    return daily_pnl, stock_pnl

def run():
    """Main function to run P&L calculations"""
    etfs = get_selected_etfs()

    all_pnl_data = {}
    for etf in etfs:
        daily_pnl, stock_pnl = save_pnl_data(etf)
        all_pnl_data[etf] = {'daily': daily_pnl, 'stock': stock_pnl}
        print(f"  ✓ {etf}: P&L calculation (adjusted) with 2 sheets")

    return all_pnl_data

if __name__ == "__main__":
    run()
