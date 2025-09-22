import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
import warnings
warnings.filterwarnings('ignore')
from config import OUTPUT_DIRS, CURRENT_RANGE
from data_config import get_data_path

def calculate_stock_pnl(file_path, etf_name):
    """Calculate P&L contribution by individual stocks for positions in weight range"""
    
    # Read data
    df = pd.read_excel(file_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert Weight from decimal to percentage (0.04 -> 4.0)
    df['Weight'] = df['Weight'] * 100
    
    # Filter out rows with zero or invalid prices
    df = df[(df['Stock_Price'] > 0) & (df['Stock_Price'].notna())]
    
    # Sort by ticker and date
    df = df.sort_values(['Bloomberg Name', 'Date'])
    
    # Calculate daily P&L for each position using value-based method
    df['Prev_Position'] = df.groupby('Bloomberg Name')['Position'].shift(1)
    df['Prev_Price'] = df.groupby('Bloomberg Name')['Stock_Price'].shift(1)
    df['Yesterday_Value'] = df['Prev_Position'] * df['Prev_Price']
    df['Today_Value'] = df['Prev_Position'] * df['Stock_Price']
    df['Daily_PnL'] = df['Today_Value'] - df['Yesterday_Value']
    
    # Filter for positions in weight range only
    # Filter for positions in current weight range
    if CURRENT_RANGE:
        df_small = df[(df['Weight'] >= CURRENT_RANGE['min']) & 
                     (df['Weight'] < CURRENT_RANGE['max'])].copy()
    else:
        df_small = df[df['Weight'] < 1].copy()
    
    # Remove extreme P&L outliers
    pnl_threshold = df_small['Daily_PnL'].abs().quantile(0.999)
    df_small = df_small[df_small['Daily_PnL'].abs() <= pnl_threshold]
    
    # Get company names - use the most recent company name for each Bloomberg Name
    company_names = df_small.groupby('Bloomberg Name')['Company_Name'].last().to_dict()
    
    # Aggregate P&L by stock
    stock_pnl = df_small.groupby('Bloomberg Name')['Daily_PnL'].sum().reset_index()
    stock_pnl.columns = ['Bloomberg_Name', 'Total_PnL']
    
    # Add company names
    stock_pnl['Stock'] = stock_pnl['Bloomberg_Name'].map(company_names)
    # Use Bloomberg Name if Company name is missing or NaN
    stock_pnl['Stock'] = stock_pnl['Stock'].fillna(stock_pnl['Bloomberg_Name'])
    # Clean up any NaN values
    stock_pnl['Stock'] = stock_pnl['Stock'].astype(str).replace('nan', '')
    
    # Filter only losses (negative P&L)
    stock_pnl = stock_pnl[stock_pnl['Total_PnL'] < 0].copy()
    
    # Sort by P&L (most negative first)
    stock_pnl = stock_pnl[['Stock', 'Total_PnL']].sort_values('Total_PnL')
    
    return stock_pnl

def create_pnl_pie_chart(stock_pnl, etf_name):
    """Create pie chart for loss contributors, grouping <5% into Others"""
    
    # Check if we have any losses
    if len(stock_pnl) == 0:
        return None
    
    # Calculate total losses for percentage calculation
    total_losses = abs(stock_pnl['Total_PnL'].sum())
    
    # Calculate percentage contribution for each stock
    stock_pnl['Loss_Pct'] = (abs(stock_pnl['Total_PnL']) / total_losses) * 100
    
    # Separate stocks >= 5% and < 5%
    significant_stocks = stock_pnl[stock_pnl['Loss_Pct'] >= 5.0].copy()
    small_stocks = stock_pnl[stock_pnl['Loss_Pct'] < 5.0].copy()
    
    # If we have small stocks, create Others category
    if len(small_stocks) > 0:
        others_pnl = small_stocks['Total_PnL'].sum()
        others_row = pd.DataFrame({'Stock': ['Others'], 'Total_PnL': [others_pnl], 'Loss_Pct': [(abs(others_pnl) / total_losses) * 100]})
        chart_data = pd.concat([significant_stocks[['Stock', 'Total_PnL']], others_row[['Stock', 'Total_PnL']]], ignore_index=True)
    else:
        chart_data = significant_stocks[['Stock', 'Total_PnL']].copy()
    
    # Sort by P&L (most negative first) to maintain order
    chart_data = chart_data.sort_values('Total_PnL').reset_index(drop=True)
    
    # Convert to positive values for pie chart (since they're all losses)
    chart_data['Abs_PnL'] = abs(chart_data['Total_PnL'])
    
    # Create color gradient from dark to light
    base_color = {
        'ARKF': '#FF6B6B',  # Red
        'ARKG': '#4ECDC4',  # Teal
        'ARKK': '#45B7D1',  # Blue
        'ARKQ': '#96CEB4',  # Green
        'ARKW': '#FECA57'   # Yellow
    }
    
    # Generate red gradient for losses with better contrast
    num_slices = len(chart_data)
    colors = []
    for i in range(num_slices):
        # Create a wider range of red shades from dark to very light
        # Start from dark red (0.4, 0.0, 0.0) to light pink (1.0, 0.8, 0.8)
        progress = i / max(num_slices-1, 1)
        
        # Red channel: stays high
        r = 0.4 + (0.6 * progress)
        # Green and blue channels: increase more for lighter shades
        g = 0.0 + (0.8 * progress)
        b = 0.0 + (0.8 * progress)
        
        colors.append((r, g, b))
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        chart_data['Abs_PnL'], 
        labels=chart_data['Stock'],
        colors=colors,
        autopct=lambda pct: f'{pct:.1f}%\n(${abs(pct * total_losses / 100)/1e6:.1f}M)',
        startangle=90,
        counterclock=False,
        pctdistance=0.85,
        labeldistance=1.15
    )
    
    # Enhance text
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
        autotext.set_weight('bold')
    
    # Add title
    weight_label = CURRENT_RANGE['label'] if CURRENT_RANGE else '<1%'
    plt.title(f'{etf_name} - Loss Contribution from {weight_label} Positions\nTotal Losses: ${total_losses/1e6:.1f}M', 
              fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # Save figure
    # Directory creation handled by config.py
    output_file = f"{OUTPUT_DIRS['pnl']}/{etf_name}_PnL_Pie_Chart.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_file


def main():
    """Generate P&L pie charts for all ETFs"""
    
    from config import get_selected_etfs
    etfs = get_selected_etfs()
    
    # Create individual charts
    for etf in etfs:
        file_path = get_data_path(etf)
        
        # Calculate stock P&L
        stock_pnl = calculate_stock_pnl(file_path, etf)
        
        # Create pie chart
        output_file = create_pnl_pie_chart(stock_pnl, etf)
    
    print("✅ P&L pie charts created")

if __name__ == "__main__":
    main()