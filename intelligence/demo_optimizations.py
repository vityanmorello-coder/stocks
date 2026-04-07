"""
QUANTUMTRADE ENGINE - OPTIMIZATION DEMO
Demonstrates all new optimization features
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

print("=" * 80)
print("QUANTUMTRADE ENGINE v3.0 - OPTIMIZATION DEMO")
print("=" * 80)
print()

# ============================================================
# 1. PERFORMANCE OPTIMIZATION DEMO
# ============================================================
print("1️⃣  PERFORMANCE OPTIMIZATION")
print("-" * 80)

from performance_optimizer import (
    DataCache, DataPipelineOptimizer, PerformanceMonitor,
    cached_market_data, MemoryOptimizer
)

# Initialize
optimizer = DataPipelineOptimizer()
monitor = PerformanceMonitor()

# Fetch sample data
print("Fetching market data...")
monitor.start_timer('data_fetch')
df = yf.download('EURUSD=X', period='1mo', interval='15m', progress=False)
# Normalize column names to lowercase
df.columns = [col.lower() if isinstance(col, str) else col for col in df.columns]
monitor.end_timer('data_fetch')

# Optimize DataFrame memory
print(f"Original memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
monitor.start_timer('memory_optimization')
df_optimized = optimizer.optimize_dataframe(df)
monitor.end_timer('memory_optimization')
print(f"Optimized memory usage: {df_optimized.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

# Batch calculate indicators
print("Calculating indicators in batch...")
monitor.start_timer('indicator_calculation')
indicators = ['ema_20', 'ema_50', 'rsi', 'macd', 'bollinger', 'atr']
df_optimized = optimizer.batch_indicator_calculation(df_optimized, indicators)
monitor.end_timer('indicator_calculation')

print(f"✅ Calculated {len(indicators)} indicators")
print()

# ============================================================
# 2. BACKTESTING DEMO
# ============================================================
print("2️⃣  ADVANCED BACKTESTING")
print("-" * 80)

from advanced_backtester import AdvancedBacktester, BacktestConfig, Trade

# Configure backtester
config = BacktestConfig(
    initial_capital=10000,
    commission_pct=0.1,
    slippage_pct=0.05,
    max_positions=3,
    risk_per_trade_pct=1.0
)

backtester = AdvancedBacktester(config)

# Simple strategy function (demo)
def simple_strategy(data, **params):
    """Simple EMA crossover strategy"""
    if len(data) < 50:
        return None
    
    last_row = data.iloc[-1]
    prev_row = data.iloc[-2]
    
    # Buy signal: fast EMA crosses above slow EMA
    if prev_row['ema_20'] <= prev_row['ema_50'] and last_row['ema_20'] > last_row['ema_50']:
        return {
            'side': 'buy',
            'entry_price': last_row['close'],
            'stop_loss': last_row['close'] * 0.98,
            'take_profit': last_row['close'] * 1.04,
            'symbol': 'EURUSD',
            'strategy': 'EMA_Crossover'
        }
    
    return None

# Run backtest
print("Running backtest...")
results = backtester.run_backtest(df_optimized, simple_strategy)

print(f"Total Trades: {results.total_trades}")
print(f"Win Rate: {results.win_rate:.2f}%")
print(f"Total Return: {results.total_return_pct:.2f}%")
print(f"Sharpe Ratio: {results.sharpe_ratio:.3f}")
print(f"Max Drawdown: {results.max_drawdown_pct:.2f}%")
print(f"Profit Factor: {results.profit_factor:.3f}")
print()

# Monte Carlo simulation
if results.trades:
    print("Running Monte Carlo simulation (100 runs)...")
    mc_results = backtester.run_monte_carlo(results.trades, runs=100)
    print(f"Mean Return: {mc_results['mean_return']:.2f}%")
    print(f"Probability of Profit: {mc_results['probability_profit']:.1f}%")
    print(f"95th Percentile: {mc_results['percentile_95']:.2f}%")
    print()

# ============================================================
# 3. MULTI-TIMEFRAME ANALYSIS DEMO
# ============================================================
print("3️⃣  MULTI-TIMEFRAME ANALYSIS")
print("-" * 80)

from multi_timeframe_analyzer import MultiTimeframeAnalyzer

# Initialize analyzer
mtf_analyzer = MultiTimeframeAnalyzer(timeframes=['15m', '1h', '4h'])

# Fetch data for multiple timeframes
print("Fetching multi-timeframe data...")
data_dict = {
    '15m': yf.download('EURUSD=X', period='5d', interval='15m', progress=False),
    '1h': yf.download('EURUSD=X', period='1mo', interval='1h', progress=False),
    '4h': yf.download('EURUSD=X', period='3mo', interval='1d', progress=False)  # Using 1d as proxy
}

# Prepare data
for tf in data_dict:
    df = data_dict[tf]
    df.columns = [col.lower() for col in df.columns]
    df = optimizer.batch_indicator_calculation(df, ['ema_20', 'ema_50', 'rsi', 'macd'])
    data_dict[tf] = df

# Analyze
analysis = mtf_analyzer.analyze_symbol('EURUSD', data_dict)

if analysis:
    print(f"Confluence Score: {analysis['confluence']['confluence_score']:.1f}")
    print(f"Alignment: {analysis['confluence']['alignment_percentage']:.0f}%")
    print(f"Is Aligned: {analysis['confluence']['is_aligned']}")
    
    if analysis['signal']:
        signal = analysis['signal']
        print(f"\n🎯 SIGNAL DETECTED:")
        print(f"  Direction: {signal['direction'].upper()}")
        print(f"  Confidence: {signal['confidence']:.1%}")
        print(f"  Entry: {signal['entry_price']:.5f}")
        print(f"  Stop Loss: {signal['stop_loss']:.5f}")
        print(f"  Take Profit: {signal['take_profit']:.5f}")
        print(f"  R:R Ratio: {signal['risk_reward_ratio']:.2f}")
        print(f"  Reasoning: {', '.join(signal['reasoning'][:3])}")
    else:
        print("No high-confidence signal at this time")
print()

# ============================================================
# 4. ALERT SYSTEM DEMO
# ============================================================
print("4️⃣  ALERT SYSTEM")
print("-" * 80)

from alert_system import AlertManager, AlertPriority, AlertType

# Initialize (without actual credentials for demo)
alert_config = {
    'email_enabled': False,
    'telegram_enabled': False,
    'discord_enabled': False,
    'alert_log_file': 'demo_alerts.json'
}

alert_manager = AlertManager(alert_config)

# Create sample alerts
alert_manager.create_signal_alert({
    'symbol': 'EURUSD',
    'direction': 'buy',
    'confidence': 0.85,
    'entry_price': 1.0850,
    'stop_loss': 1.0820,
    'take_profit': 1.0910,
    'risk_reward': 2.0
})

alert_manager.create_risk_warning(
    'Drawdown Alert',
    'Portfolio drawdown reached 8%',
    {'current_dd': 8.0, 'max_dd': 10.0}
)

print(f"✅ Created {len(alert_manager.alert_history)} alerts")
print(f"Active alerts: {len(alert_manager.active_alerts)}")
print()

# ============================================================
# 5. STRATEGY OPTIMIZER DEMO
# ============================================================
print("5️⃣  STRATEGY OPTIMIZER")
print("-" * 80)

from strategy_optimizer import ParameterSpace, GeneticOptimizer

# Define parameter space
param_spaces = [
    ParameterSpace('ema_fast', 10, 30, is_integer=True),
    ParameterSpace('ema_slow', 40, 100, is_integer=True),
    ParameterSpace('rsi_period', 10, 20, is_integer=True)
]

# Initialize optimizer (small population for demo)
optimizer_ga = GeneticOptimizer(
    parameter_spaces=param_spaces,
    population_size=10,
    generations=5,
    mutation_rate=0.2,
    crossover_rate=0.7
)

# Simple fitness function
def demo_fitness(params):
    """Demo fitness function"""
    # In real use, this would run a backtest
    score = (params['ema_fast'] / params['ema_slow']) * params['rsi_period']
    return score

print("Running genetic optimization (5 generations, 10 population)...")
opt_results = optimizer_ga.optimize(demo_fitness)

print(f"✅ Optimization complete")
print(f"Best Parameters: {opt_results['best_parameters']}")
print(f"Best Fitness: {opt_results['best_fitness']:.4f}")
print()

# ============================================================
# 6. ANALYTICS DASHBOARD DEMO
# ============================================================
print("6️⃣  ANALYTICS DASHBOARD")
print("-" * 80)

from analytics_dashboard import AnalyticsDashboard

# Initialize dashboard
analytics = AnalyticsDashboard()

# Add sample trades
sample_trades = [
    {'symbol': 'EURUSD', 'pnl': 150, 'pnl_pct': 1.5, 'strategy': 'EMA_Cross', 'entry_time': datetime.now() - timedelta(days=5)},
    {'symbol': 'GBPUSD', 'pnl': -50, 'pnl_pct': -0.5, 'strategy': 'RSI_Reversal', 'entry_time': datetime.now() - timedelta(days=4)},
    {'symbol': 'EURUSD', 'pnl': 200, 'pnl_pct': 2.0, 'strategy': 'EMA_Cross', 'entry_time': datetime.now() - timedelta(days=3)},
    {'symbol': 'USDJPY', 'pnl': 100, 'pnl_pct': 1.0, 'strategy': 'Breakout', 'entry_time': datetime.now() - timedelta(days=2)},
    {'symbol': 'GBPUSD', 'pnl': -30, 'pnl_pct': -0.3, 'strategy': 'RSI_Reversal', 'entry_time': datetime.now() - timedelta(days=1)},
]

for trade in sample_trades:
    analytics.add_trade(trade)

# Calculate metrics
metrics = analytics.calculate_performance_metrics()

print(f"Total Trades: {metrics.total_trades}")
print(f"Win Rate: {metrics.win_rate:.2f}%")
print(f"Total P&L: ${metrics.total_pnl:.2f}")
print(f"Profit Factor: {metrics.profit_factor:.3f}")
print(f"Expectancy: ${metrics.expectancy:.2f}")

# Strategy breakdown
strategy_stats = analytics.get_strategy_breakdown()
print(f"\nStrategy Breakdown:")
for strategy, stats in strategy_stats.items():
    print(f"  {strategy}: {stats['win_rate']:.1f}% WR, ${stats['total_pnl']:.2f} P&L")

# Export report
analytics.export_to_json('demo_analytics.json')
print(f"\n✅ Analytics exported to demo_analytics.json")
print()

# ============================================================
# PERFORMANCE SUMMARY
# ============================================================
print("=" * 80)
print("PERFORMANCE SUMMARY")
print("=" * 80)
monitor.print_report()

print()
print("=" * 80)
print("🚀 OPTIMIZATION DEMO COMPLETE")
print("=" * 80)
print()
print("Next Steps:")
print("  1. Configure alert channels (Telegram/Discord)")
print("  2. Run full backtests with walk-forward validation")
print("  3. Optimize your strategy parameters")
print("  4. Enable multi-timeframe analysis in live trading")
print("  5. Monitor performance with analytics dashboard")
print()
print("See OPTIMIZATION_GUIDE.md for detailed documentation")
print()
