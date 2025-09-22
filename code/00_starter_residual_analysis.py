"""
Starter and Residual Position Analysis
Identifies and tracks positions in weight range in ARK ETFs
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE
from data_config import get_data_path

def identify_starter_positions(df):
    """
    Identify starter positions: stocks that enter portfolio in weight range
    """
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    # Find first appearance of each stock
    first_appearance = df.groupby('Bloomberg Name').first().reset_index()
    
    # Starter positions are those that first appear in weight range
    # Filter for positions that start in weight range
    if CURRENT_RANGE:
        starters = first_appearance[(first_appearance['Weight'] >= CURRENT_RANGE['min']) & 
                                   (first_appearance['Weight'] < CURRENT_RANGE['max'])][['Bloomberg Name']].copy()
    else:
        starters = first_appearance[first_appearance['Weight'] < 1][['Bloomberg Name']].copy()
    starters['Type'] = 'Starter'
    
    # Get detailed history for starter positions
    starter_details = []
    
    # Process each starter ticker if any exist
    if len(starters) > 0:
        for ticker in starters['Bloomberg Name'].unique():
            ticker_data = df[df['Bloomberg Name'] == ticker].copy()
            
            # Entry info
            entry_date = ticker_data['Date'].min()
            entry_weight = ticker_data['Weight'].iloc[0]
            
            # Track outcome
            max_weight = ticker_data['Weight'].max()
            final_weight = ticker_data['Weight'].iloc[-1]
            final_date = ticker_data['Date'].max()
            
            # Determine outcome
            threshold = CURRENT_RANGE['max'] if CURRENT_RANGE else 1
            if max_weight >= threshold:
                outcome = 'Graduated to Large'
                days_to_outcome = (ticker_data[ticker_data['Weight'] >= threshold]['Date'].min() - entry_date).days
            elif final_weight == 0 or pd.isna(final_weight):
                outcome = 'Dropped'
                # Find last non-zero date
                non_zero = ticker_data[ticker_data['Weight'] > 0]
                if len(non_zero) > 0:
                    days_to_outcome = (non_zero['Date'].max() - entry_date).days
                else:
                    days_to_outcome = 0
            else:
                outcome = 'Still Small'
                days_to_outcome = (final_date - entry_date).days
            
            starter_details.append({
                'Bloomberg Name': ticker,
                'Entry Date': entry_date,
                'Entry Weight %': entry_weight,
                'Max Weight Achieved %': max_weight,
                'Final Weight %': final_weight,
                'Outcome': outcome,
                'Days to Outcome': days_to_outcome,
                'Days as Small Position': days_to_outcome
            })
    
    # Return DataFrame with proper columns even if empty
    if len(starter_details) == 0:
        return pd.DataFrame(columns=['Bloomberg Name', 'Entry Date', 'Entry Weight %', 
                                    'Max Weight Achieved %', 'Final Weight %', 'Outcome', 
                                    'Days to Outcome', 'Days as Small Position'])
    else:
        return pd.DataFrame(starter_details)

def identify_residual_positions(df):
    """
    Identify residual positions: stocks that fell into weight range
    """
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    residual_details = []
    
    for ticker in df['Bloomberg Name'].unique():
        ticker_data = df[df['Bloomberg Name'] == ticker].copy()
        ticker_data = ticker_data.sort_values('Date')
        
        # Find transitions into weight range
        if CURRENT_RANGE:
            ticker_data['Was_Large'] = ticker_data['Weight'].shift(1) >= CURRENT_RANGE['max']
            ticker_data['Is_Small'] = (ticker_data['Weight'] >= CURRENT_RANGE['min']) & (ticker_data['Weight'] < CURRENT_RANGE['max'])
        else:
            ticker_data['Was_Large'] = ticker_data['Weight'].shift(1) >= 1
            ticker_data['Is_Small'] = ticker_data['Weight'] < 1
        ticker_data['Transition'] = ticker_data['Was_Large'] & ticker_data['Is_Small']
        
        transitions = ticker_data[ticker_data['Transition']]
        
        for _, trans in transitions.iterrows():
            # Get history before and after transition
            trans_date = trans['Date']
            before = ticker_data[ticker_data['Date'] < trans_date]
            after = ticker_data[ticker_data['Date'] >= trans_date]
            
            if len(before) > 0 and len(after) > 0:
                # Peak weight before falling
                peak_weight = before['Weight'].max()
                
                # Weight at transition
                trans_weight = trans['Weight']
                
                # Track outcome after becoming residual
                future_max = after['Weight'].max()
                final_weight = after['Weight'].iloc[-1]
                
                # Determine outcome
                threshold = CURRENT_RANGE['max'] if CURRENT_RANGE else 1
                if future_max >= threshold:
                    outcome = 'Recovered to Large'
                    recovery_date = after[after['Weight'] >= threshold]['Date'].min()
                    days_as_residual = (recovery_date - trans_date).days
                elif final_weight == 0 or pd.isna(final_weight):
                    outcome = 'Dropped'
                    last_date = after[after['Weight'] > 0]['Date'].max() if len(after[after['Weight'] > 0]) > 0 else trans_date
                    days_as_residual = (last_date - trans_date).days
                else:
                    outcome = 'Still Residual'
                    days_as_residual = (after['Date'].max() - trans_date).days
                
                residual_details.append({
                    'Bloomberg Name': ticker,
                    'Transition Date': trans_date,
                    'Peak Weight Before %': peak_weight,
                    'Weight at Transition %': trans_weight,
                    'Weight Drawdown %': peak_weight - trans_weight,
                    'Max Weight After %': future_max,
                    'Final Weight %': final_weight,
                    'Outcome': outcome,
                    'Days as Residual': days_as_residual
                })
    
    # Return DataFrame with proper columns even if empty
    if len(residual_details) == 0:
        return pd.DataFrame(columns=['Bloomberg Name', 'Transition Date', 'Peak Weight Before %',
                                    'Weight at Transition %', 'Weight Drawdown %', 'Max Weight After %',
                                    'Final Weight %', 'Outcome', 'Days as Residual'])
    else:
        return pd.DataFrame(residual_details)

def identify_reappeared_positions(df):
    """
    Identify positions that left and came back
    """
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    reappeared = []
    
    for ticker in df['Bloomberg Name'].unique():
        ticker_data = df[df['Bloomberg Name'] == ticker].copy()
        ticker_data = ticker_data.sort_values('Date')
        
        # Find gaps in holdings (weight = 0 or missing dates)
        ticker_data['Date_Diff'] = ticker_data['Date'].diff().dt.days
        
        # Find reappearances (gap > 30 days)
        gaps = ticker_data[ticker_data['Date_Diff'] > 30]
        
        for _, gap in gaps.iterrows():
            gap_date = gap['Date']
            before_gap = ticker_data[ticker_data['Date'] < gap_date]['Date'].max()
            
            reappeared.append({
                'Bloomberg Name': ticker,
                'Exit Date': before_gap,
                'Re-entry Date': gap_date,
                'Days Absent': gap['Date_Diff'],
                'Re-entry Weight %': gap['Weight']
            })
    
    return pd.DataFrame(reappeared)

def analyze_etf(etf_name):
    """
    Complete analysis for one ETF
    """
    
    # Load data
    df = pd.read_excel(get_data_path(etf_name), sheet_name='Sheet1')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100
    
    # Run analyses
    starters = identify_starter_positions(df)
    residuals = identify_residual_positions(df)
    reappeared = identify_reappeared_positions(df)
    
    # Create summary
    summary = pd.DataFrame([{
        'ETF': etf_name,
        'Total Starter Positions': len(starters),
        f'Graduated to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%': len(starters[starters['Outcome'] == 'Graduated to Large']),
        'Still in Range': len(starters[starters['Outcome'] == 'Still Small']),
        'Dropped': len(starters[starters['Outcome'] == 'Dropped']),
        'Starter Success Rate %': len(starters[starters['Outcome'] == 'Graduated to Large']) / len(starters) * 100 if len(starters) > 0 else 0,
        'Avg Days as Starter': starters['Days as Small Position'].mean() if len(starters) > 0 else 0,
        'Total Residual Positions': len(residuals),
        f'Recovered to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%': len(residuals[residuals['Outcome'] == 'Recovered to Large']),
        'Still Residual': len(residuals[residuals['Outcome'] == 'Still Residual']),
        'Residual Dropped': len(residuals[residuals['Outcome'] == 'Dropped']),
        'Residual Recovery Rate %': len(residuals[residuals['Outcome'] == 'Recovered to Large']) / len(residuals) * 100 if len(residuals) > 0 else 0,
        'Avg Days as Residual': residuals['Days as Residual'].mean() if len(residuals) > 0 else 0,
        'Total Reappeared': len(reappeared),
        'Avg Days Absent': reappeared['Days Absent'].mean() if len(reappeared) > 0 else 0
    }])
    
    # Save results to starter folder
    output_file = f"{OUTPUT_DIRS['starter']}/{etf_name}_starter_residual_analysis.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        summary.to_excel(writer, sheet_name='Summary', index=False)
        starters.to_excel(writer, sheet_name='Starter_Positions', index=False)
        residuals.to_excel(writer, sheet_name='Residual_Positions', index=False)
        reappeared.to_excel(writer, sheet_name='Reappeared_Positions', index=False)
    
    
    return summary, starters, residuals, reappeared

def run():
    """Main function to run starter/residual analysis"""
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    all_summaries = []
    
    for etf in etfs:
        summary, starters, residuals, reappeared = analyze_etf(etf)
        all_summaries.append(summary)
    
    # Combine summaries
    combined_summary = pd.concat(all_summaries, ignore_index=True)
    
    # Add totals row
    totals = pd.DataFrame([{
        'ETF': 'TOTAL',
        'Total Starter Positions': combined_summary['Total Starter Positions'].sum(),
        f'Graduated to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%': combined_summary[f'Graduated to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%'].sum(),
        'Still in Range': combined_summary['Still in Range'].sum(),
        'Dropped': combined_summary['Dropped'].sum(),
        'Starter Success Rate %': combined_summary[f'Graduated to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%'].sum() / combined_summary['Total Starter Positions'].sum() * 100,
        'Avg Days as Starter': combined_summary['Avg Days as Starter'].mean(),
        'Total Residual Positions': combined_summary['Total Residual Positions'].sum(),
        f'Recovered to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%': combined_summary[f'Recovered to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%'].sum(),
        'Still Residual': combined_summary['Still Residual'].sum(),
        'Residual Dropped': combined_summary['Residual Dropped'].sum(),
        'Residual Recovery Rate %': combined_summary[f'Recovered to >{CURRENT_RANGE["max"] if CURRENT_RANGE else "1"}%'].sum() / combined_summary['Total Residual Positions'].sum() * 100,
        'Avg Days as Residual': combined_summary['Avg Days as Residual'].mean(),
        'Total Reappeared': combined_summary['Total Reappeared'].sum(),
        'Avg Days Absent': combined_summary['Avg Days Absent'].mean()
    }])
    
    combined_summary = pd.concat([combined_summary, totals], ignore_index=True)
    
    print("✅ Starter/Residual analysis completed")
    
    return combined_summary

if __name__ == "__main__":
    run()