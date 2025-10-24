"""
Analyze graduated stocks: stocks that grew from <1% to >=1%
Calculate daily returns for two periods:
1. Before graduation (<1% period)
2. After graduation (>=1% period)
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, load_etf_data, get_selected_etfs
import os

def identify_graduated_stocks(df):
    """
    Identify stocks that graduated from <1% to >=1%

    Excludes:
    - Stocks that never reached >=1%
    - Stocks that started with >=1% (unless they later dropped <1% then went back >=1%)

    Returns:
        dict: {ticker: graduation_date}
    """
    graduated_stocks = {}

    for ticker, group in df.groupby('Bloomberg Name'):
        group = group.sort_values('Date').reset_index(drop=True)

        # Find the first valid <1% period (excluding initial >1% if exists)
        started_small = False
        small_period_start_idx = None

        for idx in range(len(group)):
            weight = group.iloc[idx]['Weight']
            affiliation = group.iloc[idx]['affiliation_check']

            # Skip if affiliated
            if affiliation != 0:
                continue

            # Track when stock first enters <1% range
            if weight < 1 and not started_small:
                started_small = True
                small_period_start_idx = idx

            # Check for graduation: moved from <1% to >=1%
            if started_small and weight >= 1:
                graduation_date = group.iloc[idx]['Date']
                graduated_stocks[ticker] = {
                    'graduation_date': graduation_date,
                    'small_start_idx': small_period_start_idx
                }
                break

    return graduated_stocks

def calculate_graduated_returns(etf_name):
    """
    Calculate daily returns for graduated stocks in two periods:
    1. <1% period (before graduation)
    2. >=1% period (after graduation)
    """

    # Load data
    df = load_etf_data(etf_name)
    df = df.sort_values(['Bloomberg Name', 'Date']).reset_index(drop=True)

    # Calculate yesterday's values for return and P&L calculation
    df['Yesterday_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Yesterday_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Yesterday_Weight'] = df.groupby('Bloomberg Name')['Weight'].shift(1)

    # Calculate daily return
    df['Daily_Return'] = (df['Stock_Price'] - df['Yesterday_Price']) / df['Yesterday_Price']

    # Calculate daily P&L
    df['Daily_PnL'] = df['Yesterday_Position'] * (df['Stock_Price'] - df['Yesterday_Price'])

    # Identify graduated stocks
    graduated_stocks = identify_graduated_stocks(df)

    if len(graduated_stocks) == 0:
        print(f"  ⚠️  {etf_name}: No graduated stocks found")
        return pd.DataFrame(), graduated_stocks

    # Collect returns for each graduated stock
    all_returns = []

    for ticker, grad_info in graduated_stocks.items():
        ticker_df = df[df['Bloomberg Name'] == ticker].copy()
        ticker_df = ticker_df.sort_values('Date').reset_index(drop=True)

        graduation_date = grad_info['graduation_date']
        small_start_idx = grad_info['small_start_idx']

        for idx in range(len(ticker_df)):
            row = ticker_df.iloc[idx]

            # Skip if no yesterday price (can't calculate return)
            if pd.isna(row['Yesterday_Price']):
                continue

            # Skip if affiliated
            if row['affiliation_check'] != 0:
                continue

            # Skip if before small period started
            if idx < small_start_idx:
                continue

            # Determine period
            if row['Date'] < graduation_date:
                period = 'Before_Graduation_<1%'
            else:
                period = 'After_Graduation_>=1%'

            all_returns.append({
                'ETF': etf_name,
                'Ticker': ticker,
                'Date': row['Date'],
                'Weight': row['Weight'],
                'Daily_Return': row['Daily_Return'],
                'Daily_PnL': row['Daily_PnL'],
                'Period': period,
                'Graduation_Date': graduation_date
            })

    returns_df = pd.DataFrame(all_returns)

    return returns_df, graduated_stocks

def calculate_all_graduated_returns():
    """Calculate graduated returns for all ETFs"""

    etfs = get_selected_etfs()

    all_results = {}
    all_graduated_stocks = {}

    for etf in etfs:
        returns_df, graduated_stocks = calculate_graduated_returns(etf)
        all_results[etf] = returns_df
        all_graduated_stocks[etf] = graduated_stocks
        print(f"  ✓ {etf}: {len(graduated_stocks)} graduated stocks, {len(returns_df)} return records")

    return all_results, all_graduated_stocks

def save_graduation_data(all_results, all_graduated_stocks):
    """Save graduation analysis data to Excel"""

    output_dir = OUTPUT_DIRS['graduation']
    os.makedirs(output_dir, exist_ok=True)

    # Use consistent naming
    output_file = f"{output_dir}/Graduation_Returns_Data.xlsx"

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = []
        for etf in all_results.keys():
            returns_df = all_results[etf]

            if len(returns_df) == 0:
                summary_data.append({
                    'ETF': etf,
                    'Num_Graduated_Stocks': 0,
                    'Total_Records_Before': 0,
                    'Total_Records_After': 0,
                    'Mean_Return_Before_%': 0,
                    'Mean_Return_After_%': 0,
                    'Median_Return_Before_%': 0,
                    'Median_Return_After_%': 0,
                    'Std_Return_Before_%': 0,
                    'Std_Return_After_%': 0,
                    'Mean_PnL_Before': 0,
                    'Mean_PnL_After': 0,
                    'Median_PnL_Before': 0,
                    'Median_PnL_After': 0,
                    'Total_PnL_Before': 0,
                    'Total_PnL_After': 0
                })
                continue

            before_df = returns_df[returns_df['Period'] == 'Before_Graduation_<1%']
            after_df = returns_df[returns_df['Period'] == 'After_Graduation_>=1%']

            before_returns = before_df['Daily_Return']
            after_returns = after_df['Daily_Return']
            before_pnl = before_df['Daily_PnL']
            after_pnl = after_df['Daily_PnL']

            summary_data.append({
                'ETF': etf,
                'Num_Graduated_Stocks': len(all_graduated_stocks[etf]),
                'Total_Records_Before': len(before_returns),
                'Total_Records_After': len(after_returns),
                'Mean_Return_Before_%': before_returns.mean() * 100 if len(before_returns) > 0 else 0,
                'Mean_Return_After_%': after_returns.mean() * 100 if len(after_returns) > 0 else 0,
                'Median_Return_Before_%': before_returns.median() * 100 if len(before_returns) > 0 else 0,
                'Median_Return_After_%': after_returns.median() * 100 if len(after_returns) > 0 else 0,
                'Std_Return_Before_%': before_returns.std() * 100 if len(before_returns) > 0 else 0,
                'Std_Return_After_%': after_returns.std() * 100 if len(after_returns) > 0 else 0,
                'Mean_PnL_Before': before_pnl.mean() if len(before_pnl) > 0 else 0,
                'Mean_PnL_After': after_pnl.mean() if len(after_pnl) > 0 else 0,
                'Median_PnL_Before': before_pnl.median() if len(before_pnl) > 0 else 0,
                'Median_PnL_After': after_pnl.median() if len(after_pnl) > 0 else 0,
                'Total_PnL_Before': before_pnl.sum() if len(before_pnl) > 0 else 0,
                'Total_PnL_After': after_pnl.sum() if len(after_pnl) > 0 else 0
            })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Detailed returns for each ETF
        for etf in all_results.keys():
            returns_df = all_results[etf].copy()

            if len(returns_df) > 0:
                # Convert return to percentage
                returns_df['Daily_Return_%'] = returns_df['Daily_Return'] * 100

                # Select columns for output
                output_data = returns_df[['Date', 'Ticker', 'Weight', 'Daily_Return_%',
                                         'Daily_PnL', 'Period', 'Graduation_Date']].copy()

                output_data.to_excel(writer, sheet_name=etf, index=False)
            else:
                # Empty DataFrame with column headers
                pd.DataFrame(columns=['Date', 'Ticker', 'Weight', 'Daily_Return_%',
                                    'Daily_PnL', 'Period', 'Graduation_Date']).to_excel(writer, sheet_name=etf, index=False)

        # List of graduated stocks
        graduated_list = []
        for etf, stocks_dict in all_graduated_stocks.items():
            for ticker, grad_info in stocks_dict.items():
                graduated_list.append({
                    'ETF': etf,
                    'Ticker': ticker,
                    'Graduation_Date': grad_info['graduation_date']
                })

        graduated_df = pd.DataFrame(graduated_list)
        if len(graduated_df) > 0:
            graduated_df = graduated_df.sort_values(['ETF', 'Graduation_Date'])
        graduated_df.to_excel(writer, sheet_name='Graduated_Stocks', index=False)

    print(f"  📊 Saved: {output_file}")
    return summary_df

def run():
    """Main function to calculate and save graduation analysis data"""

    # Calculate graduated returns
    all_results, all_graduated_stocks = calculate_all_graduated_returns()

    # Save data
    save_graduation_data(all_results, all_graduated_stocks)

    return all_results, all_graduated_stocks

if __name__ == "__main__":
    run()
