# Adjusted P&L Calculation Logic

## Overview
The P&L calculation has been updated to use **Adjusted P&L** formula that accounts for inflows/outflows, providing a more accurate measure of investment performance.

## Formula

### Stock-Level Calculation

#### Basic Components
- **Day0** = Previous trading day
- **Day1** = Current trading day
- **Stock MV (Market Value)** = Position × Stock Price
- **Dollar P&L** = Day1 MV - Day0 MV
- **Inflows/Outflows** = Position change effect
- **Adjusted P&L** = Dollar P&L - Inflows/Outflows

#### Position Status Categories

**1. Ongoing Position (Day0 > 0 and Day1 > 0)**
```
Dollar P&L = Day1_MV - Day0_MV
Inflows/Outflows = (Day1_Position - Day0_Position) × (Day1_Price + Day0_Price) / 2
Adjusted P&L = Dollar P&L - Inflows/Outflows
```

**2. Entry Position (Day0 = 0, Day1 > 0)**
```
Dollar P&L = Day1_MV - 0
Inflows = Day1_Position × Day1_Price
Adjusted P&L = Dollar P&L - Inflows
```
*Note: All P&L is attributed to inflow, not investment performance*

**3. Exit Position (Day0 > 0, Day1 = 0)**
```
Dollar P&L = 0 - Day0_MV = -Day0_MV
Outflows = -Day0_Position × Day0_Price
Adjusted P&L = 0
```
*Note: Position is being closed out, no performance attribution*

### Portfolio-Level Aggregation

Daily aggregation across all positions in weight range:
```
Daily_Dollar_PnL = Sum of all stock Dollar_PnL
Daily_Inflows_Outflows = Sum of all stock Inflows_Outflows
Daily_Adj_PnL = Sum of all stock Adj_PnL
Cumulative_Adj_PnL = Cumulative sum of Daily_Adj_PnL
```

## Why Adjusted P&L?

**Problem with Simple Dollar P&L:**
- Adding/removing positions changes market value
- Price changes also change market value
- Can't distinguish between performance and capital flows

**Example:**
```
Day 0: Position = 100 shares @ $50 = $5,000 MV
Day 1: Position = 200 shares @ $52 = $10,400 MV

Simple Dollar P&L = $10,400 - $5,000 = $5,400
```

This suggests a $5,400 gain, but:
- Stock only went up 4% ($50 → $52)
- Most of the change is from adding 100 shares (inflow)

**Adjusted P&L Calculation:**
```
Dollar P&L = $5,400
Inflows = (200 - 100) × ($52 + $50) / 2 = 100 × $51 = $5,100
Adjusted P&L = $5,400 - $5,100 = $300
```

The true investment performance is $300, not $5,400.

## ARKF Results Example

For ARKF <1% positions (all time):

| Metric | Amount |
|--------|--------|
| Total Dollar P&L | -$63,038.7M |
| Total Inflows/Outflows | -$66,587.5M |
| **Total Adjusted P&L** | **+$3,548.8M** |

**Interpretation:**
- Market value decreased by $63B (Dollar P&L)
- But $66.6B was withdrawn from small positions (Outflows)
- **Actual investment performance: +$3.5B gain**

## Implementation

### Updated Files

1. **01_calculate_pnl.py**
   - `calculate_stock_pnl()`: Calculates adjusted P&L for each stock
   - `calculate_pnl()`: Aggregates to daily portfolio P&L
   - `calculate_loss_table()`: Loss attribution using adjusted P&L

2. **01_2_plot_pnl_line.py**
   - Updated to plot `Cumulative_Adj_PnL` instead of `Cumulative_PnL`
   - Shows both daily and cumulative adjusted P&L

3. **01_1_plot_pnl_pie.py**
   - Updated to use adjusted P&L for loss attribution
   - Imports `calculate_stock_pnl()` from module 01

### Output Format

**PnL_Data sheet:**
```
Date, Dollar_PnL, Inflows_Outflows, Adj_PnL, Cumulative_Adj_PnL
```

**Loss_Table sheet:**
```
Rank, Stock, Loss_Millions, Loss_Contribution_%
```
(Based on adjusted P&L losses)

## Key Insights

1. **Adjusted P&L removes capital flow effects**
   - Only measures investment performance
   - Separates trading decisions from price performance

2. **More accurate for portfolios with high turnover**
   - ARK ETFs frequently add/reduce positions
   - Simple MV change would be misleading

3. **Better for attribution analysis**
   - Loss table shows true performance contributors
   - Not distorted by position size changes

## Date: October 2025
Updated by: Claude Code Analysis System
