"""
STRATEGY COMPARISON BACKTEST

Tests all available intraday trading strategies against the same portfolio
and generates detailed comparative analysis.

Usage:
    python backtest_all_strategies.py
    
Output:
    - Console: Performance rankings and comparisons
    - CSV: strategy_comparison_results.csv (detailed metrics)
    - Plots: Market performance over time
"""

import pandas as pd
import numpy as np
from data.smartapi_data import SmartAPIDataProvider
from backtest.portfolio_backtest_v2_ranked import PortfolioBacktestEngineV2
from strategies.multi_signal_hybrid import MultiSignalHybrid
from strategies.intraday_strategies import (
    VWAPMeanReversion,
    RSIOverbought,
    BreakoutStrategy,
    TrendFollowingWithFilter
)
from strategies.vwap_scalper import VWAPScalper
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# API Credentials
API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

# Backtest Parameters
CONFIG = {
    "TOTAL_CAPITAL": 100000,
    "MAX_POSITIONS": 5,
    "MAX_TRADES_PER_DAY": 15,
    "MIN_TRADE_VALUE": 3000.0,
    "WARMUP_CANDLES": 20,
    "LOOKBACK_DAYS": 15,
    "INTERVAL": "5m"
}

# Stock Pool
STOCK_POOL = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "MARUTI", "BAJAJFINSV", "LT", "ITC", "WIPRO",
    "HDFC", "SUNPHARMA", "ASIANPAINT", "DRREDDY", "HEROMOTOCO",
    "SBIN", "AXISBANK", "KOTAKBANK", "INDUSIND", "BAJAJFINSV"
]

# Strategy Definitions
STRATEGIES = [
    {
        "name": "MultiSignalHybrid",
        "cls": MultiSignalHybrid,
        "description": "Multi-signal confirmation (SMA + RSI + VWAP + Volume)",
        "config": {
            "fast_sma": 8,
            "slow_sma": 20,
            "rsi_period": 14,
            "rsi_oversold": 35,
            "rsi_overbought": 65,
            "volume_lookback": 20,
            "vwap_deviation": 2.5
        }
    },
    {
        "name": "TrendFollowingWithFilter",
        "cls": TrendFollowingWithFilter,
        "description": "Trend following with RSI confirmation (SMA + RSI)",
        "config": {
            "fast_sma": 8,
            "slow_sma": 20,
            "rsi_period": 14,
            "rsi_threshold": 40
        }
    },
    {
        "name": "VWAPMeanReversion",
        "cls": VWAPMeanReversion,
        "description": "Mean reversion around VWAP",
        "config": {
            "deviation_pct": 2.0,
            "lookback": 100
        }
    },
    {
        "name": "RSIOverbought",
        "cls": RSIOverbought,
        "description": "Counter-trend on RSI extremes",
        "config": {
            "period": 14,
            "overbought": 70,
            "oversold": 30
        }
    },
    {
        "name": "BreakoutStrategy",
        "cls": BreakoutStrategy,
        "description": "Breakout above/below recent range",
        "config": {
            "lookback": 20
        }
    },
    {
        "name": "VWAPScalper",
        "cls": VWAPScalper,
        "description": "Scalping with VWAP deviation",
        "config": {
            "threshold": 0.25,
            "window": 300
        }
    }
]

# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_market_data(stocks, interval, lookback_days):
    """
    Fetch OHLCV data for all stocks.
    
    Returns:
        Dict: symbol -> DataFrame
        int: Count of successfully fetched stocks
    """
    print("\n" + "="*80)
    print("FETCHING MARKET DATA")
    print("="*80)
    print(f"Interval: {interval}, Lookback: {lookback_days} days\n")
    
    try:
        data_provider = SmartAPIDataProvider(API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET)
    except Exception as e:
        print(f"✗ SmartAPI connection failed: {e}")
        exit(1)
    
    data = {}
    failed = []
    
    for symbol in stocks:
        try:
            print(f"  {symbol:<12}", end=" ", flush=True)
            df = data_provider.get_candles(symbol, interval=interval, lookback_days=lookback_days)
            
            if df.empty:
                print("✗ no data")
                failed.append(symbol)
                continue
            
            data[symbol] = df
            print(f"✓ {len(df):>5} candles")
        
        except Exception as e:
            print(f"✗ {str(e)[:35]}")
            failed.append(symbol)
    
    print(f"\n✓ Loaded {len(data)}/{len(stocks)} stocks")
    if failed:
        print(f"✗ Failed: {', '.join(failed)}")
    
    return data, len(data)

# ============================================================================
# BACKTEST EXECUTION
# ============================================================================

def run_strategy_backtest(strategy_info, market_data, config):
    """
    Run a single strategy backtest.
    
    Returns:
        Dict: Results or None if failed
    """
    strategy_name = strategy_info["name"]
    strategy_cls = strategy_info["cls"]
    strategy_config = strategy_info["config"]
    
    try:
        engine = PortfolioBacktestEngineV2(
            strategy_cls=strategy_cls,
            strategy_config=strategy_config,
            total_capital=config["TOTAL_CAPITAL"],
            max_positions=config["MAX_POSITIONS"],
            max_trades_per_day=config["MAX_TRADES_PER_DAY"],
            min_trade_value=config["MIN_TRADE_VALUE"],
            warmup_candles=config["WARMUP_CANDLES"],
            intraday_only=True,
            dynamic_slippage=True
        )
        
        result = engine.run(market_data)
        
        return {
            "strategy": strategy_name,
            "description": strategy_info["description"],
            "result": result,
            "error": None
        }
    
    except Exception as e:
        return {
            "strategy": strategy_name,
            "description": strategy_info["description"],
            "result": None,
            "error": str(e)
        }

def execute_backtests(strategies, market_data, config):
    """
    Run all strategy backtests.
    
    Returns:
        List: Results for each strategy
    """
    print("\n" + "="*80)
    print("RUNNING BACKTESTS")
    print("="*80 + "\n")
    
    results = []
    success_count = 0
    
    for i, strategy_info in enumerate(strategies, 1):
        name = strategy_info["name"]
        desc = strategy_info["description"]
        
        print(f"[{i}/{len(strategies)}] {name:<25}", end=" ", flush=True)
        
        backtest_result = run_strategy_backtest(strategy_info, market_data, config)
        
        if backtest_result["error"]:
            print(f"✗ {backtest_result['error'][:40]}")
        else:
            result = backtest_result["result"]
            ret = result['total_return'] * 100
            pf = result['profit_factor']
            wr = result['win_rate'] * 100
            print(f"✓ {ret:+.2f}% | PF: {pf:.2f}x | WR: {wr:.1f}%")
            success_count += 1
        
        results.append(backtest_result)
    
    print(f"\n✓ Completed: {success_count}/{len(strategies)} successful\n")
    
    return results

# ============================================================================
# RESULTS PROCESSING
# ============================================================================

def process_results(backtest_results):
    """
    Convert backtest results into structured DataFrame for analysis.
    
    Returns:
        DataFrame: Performance metrics for all strategies
    """
    rows = []
    
    for item in backtest_results:
        if item["error"]:
            continue
        
        result = item["result"]
        
        rows.append({
            "Strategy": item["strategy"],
            "Description": item["description"],
            
            # Capital
            "Initial Capital": 100000,
            "Final Capital": result['final_cash'],
            "Net P&L": result['net_pnl'],
            
            # Returns
            "Return %": result['total_return'] * 100,
            "Total Trades": result['total_trades'],
            "Closed Trades": result['total_trades'],
            "Winning Trades": result['winning_trades'],
            "Losing Trades": result['losing_trades'],
            "Breakeven Trades": result['breakeven_trades'],
            
            # Win Rate & Profitability
            "Win Rate %": result['win_rate'] * 100,
            "Avg Win ₹": result['avg_win'],
            "Avg Loss ₹": result['avg_loss'],
            "Largest Win ₹": result['largest_win'],
            "Largest Loss ₹": result['largest_loss'],
            "Profit Factor": result['profit_factor'],
            
            # Risk
            "Max Drawdown %": result['max_drawdown'] * 100,
            "Sharpe Ratio": result['sharpe_ratio'],
            "Total Brokerage": result['total_brokerage']
        })
    
    return pd.DataFrame(rows)

# ============================================================================
# REPORTING
# ============================================================================

def print_summary_table(df):
    """Print high-level performance summary."""
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    
    summary = df[[
        "Strategy",
        "Return %",
        "Net P&L",
        "Total Trades",
        "Win Rate %",
        "Profit Factor",
        "Sharpe Ratio",
        "Max Drawdown %"
    ]].copy()
    
    print(summary.to_string(index=False))

def print_rankings(df):
    """Print best performers by different metrics."""
    print("\n" + "="*80)
    print("STRATEGY RANKINGS")
    print("="*80)
    
    # Best return
    best_ret = df.loc[df['Return %'].idxmax()]
    print(f"\n🏆 BEST RETURN")
    print(f"   {best_ret['Strategy']:<30} {best_ret['Return %']:+.2f}%")
    
    # Best win rate
    best_wr = df.loc[df['Win Rate %'].idxmax()]
    print(f"\n🎯 BEST WIN RATE")
    print(f"   {best_wr['Strategy']:<30} {best_wr['Win Rate %']:.1f}%")
    
    # Best Sharpe
    best_sharpe = df.loc[df['Sharpe Ratio'].idxmax()]
    print(f"\n📊 BEST RISK-ADJUSTED (Sharpe)")
    print(f"   {best_sharpe['Strategy']:<30} {best_sharpe['Sharpe Ratio']:.2f}")
    
    # Best Profit Factor
    best_pf = df.loc[df['Profit Factor'].idxmax()]
    print(f"\n💰 BEST PROFIT FACTOR")
    print(f"   {best_pf['Strategy']:<30} {best_pf['Profit Factor']:.2f}x")
    
    # Lowest drawdown
    best_dd = df.loc[df['Max Drawdown %'].idxmax()]  # Least negative
    print(f"\n📉 LOWEST MAX DRAWDOWN")
    print(f"   {best_dd['Strategy']:<30} {best_dd['Max Drawdown %']:.2f}%")

def print_detailed_results(df, top_n=3):
    """Print detailed breakdown of top N strategies."""
    print("\n" + "="*80)
    print(f"DETAILED RESULTS (Top {top_n} by Return)")
    print("="*80)
    
    top_strategies = df.nlargest(top_n, 'Return %')
    
    for rank, (_, row) in enumerate(top_strategies.iterrows(), 1):
        print(f"\n{rank}. {row['Strategy']}")
        print(f"   {row['Description']}")
        print(f"\n   Capital Performance:")
        print(f"     Initial:       ₹{row['Initial Capital']:>10,.0f}")
        print(f"     Final:         ₹{row['Final Capital']:>10,.2f}")
        print(f"     Net P&L:       ₹{row['Net P&L']:>10,.2f}")
        print(f"     Return:        {row['Return %']:>10.2f}%")
        
        print(f"\n   Trade Statistics:")
        print(f"     Total Trades:  {int(row['Total Trades']):>10}")
        print(f"     Winning:       {int(row['Winning Trades']):>10} ({row['Win Rate %']:5.1f}%)")
        print(f"     Losing:        {int(row['Losing Trades']):>10}")
        print(f"     Breakeven:     {int(row['Breakeven Trades']):>10}")
        
        print(f"\n   Profitability:")
        print(f"     Avg Win:       ₹{row['Avg Win ₹']:>10,.0f}")
        print(f"     Avg Loss:      ₹{row['Avg Loss ₹']:>10,.0f}")
        print(f"     Max Win:       ₹{row['Largest Win ₹']:>10,.0f}")
        print(f"     Max Loss:      ₹{row['Largest Loss ₹']:>10,.0f}")
        print(f"     Profit Factor: {row['Profit Factor']:>10.2f}x")
        
        print(f"\n   Risk Metrics:")
        print(f"     Max Drawdown:  {row['Max Drawdown %']:>10.2f}%")
        print(f"     Sharpe Ratio:  {row['Sharpe Ratio']:>10.2f}")
        print(f"     Total Costs:   ₹{row['Total Brokerage']:>10,.0f}")

def print_comparison_analysis(df):
    """Print comparative analysis across all strategies."""
    print("\n" + "="*80)
    print("COMPARATIVE ANALYSIS")
    print("="*80)
    
    num_strategies = len(df)
    avg_return = df['Return %'].mean()
    avg_win_rate = df['Win Rate %'].mean()
    avg_pf = df['Profit Factor'].mean()
    
    print(f"\nAcross {num_strategies} strategies:")
    print(f"\n  Average Return:        {avg_return:>8.2f}%")
    print(f"  Average Win Rate:      {avg_win_rate:>8.1f}%")
    print(f"  Average Profit Factor: {avg_pf:>8.2f}x")
    
    # Consistency
    std_return = df['Return %'].std()
    std_wr = df['Win Rate %'].std()
    
    print(f"\n  Return Std Dev:        {std_return:>8.2f}%  (consistency)")
    print(f"  Win Rate Std Dev:      {std_wr:>8.1f}%  (consistency)")
    
    profitable = (df['Return %'] > 0).sum()
    print(f"\n  Profitable Strategies: {profitable}/{num_strategies}")
    
    # High quality (>30% win rate AND >1.0 pf)
    quality = ((df['Win Rate %'] > 30) & (df['Profit Factor'] > 1)).sum()
    print(f"  High Quality:          {quality}/{num_strategies} (WR>30% AND PF>1.0x)")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Execute full backtest comparison workflow."""
    
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "INTRADAY STRATEGY COMPARISON BACKTEST".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    # Fetch data
    data, stock_count = fetch_market_data(
        STOCK_POOL,
        CONFIG["INTERVAL"],
        CONFIG["LOOKBACK_DAYS"]
    )
    
    if not data:
        print("\n✗ No data fetched. Exiting.")
        exit(1)
    
    # Run backtests
    backtest_results = execute_backtests(STRATEGIES, data, CONFIG)
    
    # Process results
    df_results = process_results(backtest_results)
    
    if df_results.empty:
        print("\n✗ No successful backtests. Exiting.")
        exit(1)
    
    # Print reports
    print_summary_table(df_results)
    print_rankings(df_results)
    print_detailed_results(df_results, top_n=3)
    print_comparison_analysis(df_results)
    
    # Save results
    csv_filename = f"strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_results.to_csv(csv_filename, index=False)
    print(f"\n✓ Results saved to: {csv_filename}")
    
    print("\n" + "="*80)
    print("✓ Backtest complete")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
