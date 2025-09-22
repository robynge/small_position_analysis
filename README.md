# Small Position Analysis Tool

A comprehensive analysis tool for tracking small positions in ARK ETF portfolios, designed to identify potential investment opportunities and track position graduation patterns.

## Overview

This tool analyzes ARK Invest ETF holdings across different weight ranges to identify:
- Small positions that might be scaling (< 1% weight)
- Position graduation from small to large holdings
- P&L contribution from different position sizes
- Market value allocation across weight ranges
- Alternative returns excluding small positions

## Weight Ranges

The tool analyzes positions in 5 distinct weight ranges:

| Range | Label | Description |
|-------|-------|-------------|
| 0-1% | Ultra Small | Early-stage positions, potential new ideas |
| 1-2.5% | Small | Growing conviction positions |
| 2.5-5% | Medium | Established positions |
| 5-7.5% | Large | Core holdings |
| >7.5% | Very Large | Highest conviction positions |

## Features

### 1. P&L Analysis
- Daily and cumulative profit/loss tracking
- Top contributor identification
- Pie charts showing P&L distribution
- Time series of daily and cumulative returns

### 2. Position Tracking
- Daily count of positions in each weight range
- Entry/exit tracking for positions
- Weight change analysis

### 3. Market Value Analysis
- Total capital allocated to each weight range
- Percentage of AUM in small positions
- Weekly aggregated market value trends

### 4. Alternative Returns
- Compare ETF performance with vs without small positions
- Benchmark against S&P 500 and TQQQ
- Daily and weekly return analysis

### 5. Graduation Analysis
- Track positions graduating from small to large weights
- Compare performance of graduated vs all small positions
- Identify successful scaling patterns

## Installation

### Requirements
```bash
pip install pandas numpy matplotlib openpyxl seaborn
```

### Project Structure
```
small_position_analysis/
├── input/                  # Place ETF data files here
│   ├── ARKF_Transformed_Data.xlsx
│   ├── ARKG_Transformed_Data.xlsx
│   └── ...
├── code/                   # Source code
│   ├── main.py            # Main menu system
│   ├── data_config.py     # Centralized data paths
│   ├── config.py          # Output configuration
│   └── ...
└── output/                # Analysis results
    ├── ARKF/              # ETF-specific outputs
    │   ├── 00_Starter_Residual_under_1pct/
    │   ├── 01_PnL_Analysis_under_1pct/
    │   └── ...
    └── ...
```

## Usage

### 1. Prepare Data
Place ETF data files in the `input/` folder. Files should be named:
- `ARKF_Transformed_Data.xlsx`
- `ARKG_Transformed_Data.xlsx`
- `ARKK_Transformed_Data.xlsx`
- `ARKQ_Transformed_Data.xlsx`
- `ARKW_Transformed_Data.xlsx`
- `ARKX_Transformed_Data.xlsx`

Data must be in Excel format with Sheet1 containing columns:
- Date
- Bloomberg Name
- Ticker
- Position
- Stock_Price
- Weight (in decimal format, e.g., 0.01 for 1%)

### 2. Run Analysis

```bash
cd code
python main.py
```

### 3. Menu Options

1. **Select ETF** (Press E): Choose which ETF to analyze
2. **Select Weight Range** (Press R): Choose weight range to analyze
3. **Run Analysis Steps**:
   - 0: Analyze starter & residual positions
   - 1: Calculate P&L
   - 2: Calculate position counts
   - 3: Calculate alternative returns
   - 4: Calculate graduation analysis
   - A: Run all steps for current range
   - B: Batch run all steps for all weight ranges

### 4. View Results
Results are saved in `output/[ETF_NAME]/` folders as Excel files with charts and detailed data.

## Output Files

Each analysis generates Excel files with multiple sheets:

### Starter/Residual Analysis
- Summary statistics
- List of new entries
- Position details

### P&L Analysis
- Daily P&L by position
- Top contributors
- Cumulative returns

### Market Value
- Weekly market value trends
- Percentage of AUM analysis
- Range comparisons

### Alternative Returns
- Daily/weekly returns comparison
- Performance vs benchmarks
- Statistical analysis

### Graduation Analysis
- Graduated position list
- Performance comparison
- Success rate metrics

## Example Workflow

```bash
# 1. Start the program
python main.py

# 2. Select ETF (e.g., ARKK)
Press E → Select 3 for ARKK

# 3. Select weight range (e.g., <1%)
Press R → Select 1 for <1%

# 4. Run all analyses
Press A to run all steps

# 5. Check results in output/ARKK/
```

## Key Insights Generated

1. **Entry Signals**: Identify when ARK starts accumulating new positions
2. **Scaling Patterns**: Track how positions grow from small to large
3. **Risk Contribution**: Understand P&L contribution from small vs large positions
4. **Success Rate**: Measure how many small positions successfully graduate
5. **Performance Impact**: Quantify the effect of small positions on overall returns

## Notes

- All weights are converted from decimal to percentage format internally
- Cash positions (MVRXX, DGCXX, etc.) are automatically excluded
- Analysis uses daily frequency with weekly aggregations where appropriate
- P&L calculations use position-weighted methodology

## Support

For issues or questions, please open an issue on GitHub.