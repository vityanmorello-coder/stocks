"""
COMPREHENSIVE ANALYTICS DASHBOARD
Advanced performance analytics, visualization, and reporting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    avg_trade_duration_hours: float
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int
    recovery_factor: float
    
    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class AnalyticsDashboard:
    """Comprehensive analytics and reporting system"""
    
    def __init__(self):
        self.trade_history: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.daily_stats: Dict[str, Dict] = {}
    
    def add_trade(self, trade: Dict):
        """Add trade to history"""
        self.trade_history.append(trade)
        self._update_equity_curve(trade)
        self._update_daily_stats(trade)
    
    def calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        if not self.trade_history:
            return self._empty_metrics()
        
        df = pd.DataFrame(self.trade_history)
        
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] <= 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = df['pnl'].sum()
        initial_capital = 10000
        total_return_pct = (total_pnl / initial_capital) * 100
        
        returns = df['pnl_pct'].values
        sharpe = self._calculate_sharpe(returns)
        sortino = self._calculate_sortino(returns)
        
        equity_df = pd.DataFrame(self.equity_curve)
        max_dd, max_dd_pct = self._calculate_max_drawdown(equity_df)
        
        calmar = abs(total_return_pct / max_dd_pct) if max_dd_pct != 0 else 0
        
        wins = df[df['pnl'] > 0]['pnl']
        losses = df[df['pnl'] <= 0]['pnl']
        
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        
        gross_profit = wins.sum()
        gross_loss = abs(losses.sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)
        
        if 'exit_time' in df.columns and 'entry_time' in df.columns:
            df['duration'] = pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])
            avg_duration = df['duration'].mean().total_seconds() / 3600
        else:
            avg_duration = 0
        
        best_trade = df['pnl'].max()
        worst_trade = df['pnl'].min()
        
        consecutive_wins, consecutive_losses = self._calculate_streaks(df)
        
        recovery_factor = abs(total_pnl / max_dd) if max_dd != 0 else 0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_trade_duration_hours=avg_duration,
            best_trade=best_trade,
            worst_trade=worst_trade,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            recovery_factor=recovery_factor
        )
    
    def get_strategy_breakdown(self) -> Dict:
        """Analyze performance by strategy"""
        
        if not self.trade_history:
            return {}
        
        df = pd.DataFrame(self.trade_history)
        
        if 'strategy' not in df.columns:
            return {}
        
        breakdown = {}
        
        for strategy in df['strategy'].unique():
            strategy_df = df[df['strategy'] == strategy]
            
            breakdown[strategy] = {
                'total_trades': len(strategy_df),
                'winning_trades': len(strategy_df[strategy_df['pnl'] > 0]),
                'win_rate': len(strategy_df[strategy_df['pnl'] > 0]) / len(strategy_df) * 100,
                'total_pnl': strategy_df['pnl'].sum(),
                'avg_pnl': strategy_df['pnl'].mean(),
                'best_trade': strategy_df['pnl'].max(),
                'worst_trade': strategy_df['pnl'].min()
            }
        
        return breakdown
    
    def get_symbol_breakdown(self) -> Dict:
        """Analyze performance by symbol"""
        
        if not self.trade_history:
            return {}
        
        df = pd.DataFrame(self.trade_history)
        
        if 'symbol' not in df.columns:
            return {}
        
        breakdown = {}
        
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol]
            
            breakdown[symbol] = {
                'total_trades': len(symbol_df),
                'winning_trades': len(symbol_df[symbol_df['pnl'] > 0]),
                'win_rate': len(symbol_df[symbol_df['pnl'] > 0]) / len(symbol_df) * 100,
                'total_pnl': symbol_df['pnl'].sum(),
                'avg_pnl': symbol_df['pnl'].mean()
            }
        
        return breakdown
    
    def get_time_analysis(self) -> Dict:
        """Analyze performance by time periods"""
        
        if not self.trade_history:
            return {}
        
        df = pd.DataFrame(self.trade_history)
        
        if 'entry_time' not in df.columns:
            return {}
        
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['hour'] = df['entry_time'].dt.hour
        df['day_of_week'] = df['entry_time'].dt.dayofweek
        
        hourly_stats = {}
        for hour in range(24):
            hour_df = df[df['hour'] == hour]
            if len(hour_df) > 0:
                hourly_stats[hour] = {
                    'trades': len(hour_df),
                    'win_rate': len(hour_df[hour_df['pnl'] > 0]) / len(hour_df) * 100,
                    'avg_pnl': hour_df['pnl'].mean()
                }
        
        daily_stats = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day_num in range(7):
            day_df = df[df['day_of_week'] == day_num]
            if len(day_df) > 0:
                daily_stats[days[day_num]] = {
                    'trades': len(day_df),
                    'win_rate': len(day_df[day_df['pnl'] > 0]) / len(day_df) * 100,
                    'avg_pnl': day_df['pnl'].mean()
                }
        
        return {
            'hourly': hourly_stats,
            'daily': daily_stats
        }
    
    def get_risk_metrics(self) -> Dict:
        """Calculate risk-related metrics"""
        
        if not self.trade_history:
            return {}
        
        df = pd.DataFrame(self.trade_history)
        
        returns = df['pnl_pct'].values if 'pnl_pct' in df.columns else []
        
        if len(returns) == 0:
            return {}
        
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else 0
        cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else 0
        
        return {
            'value_at_risk_95': var_95,
            'value_at_risk_99': var_99,
            'conditional_var_95': cvar_95,
            'conditional_var_99': cvar_99,
            'volatility': np.std(returns),
            'skewness': self._calculate_skewness(returns),
            'kurtosis': self._calculate_kurtosis(returns)
        }
    
    def get_monthly_performance(self) -> Dict:
        """Calculate monthly performance"""
        
        if not self.trade_history:
            return {}
        
        df = pd.DataFrame(self.trade_history)
        
        if 'entry_time' not in df.columns:
            return {}
        
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['month'] = df['entry_time'].dt.to_period('M')
        
        monthly_stats = {}
        
        for month in df['month'].unique():
            month_df = df[df['month'] == month]
            
            monthly_stats[str(month)] = {
                'trades': len(month_df),
                'winning_trades': len(month_df[month_df['pnl'] > 0]),
                'win_rate': len(month_df[month_df['pnl'] > 0]) / len(month_df) * 100,
                'total_pnl': month_df['pnl'].sum(),
                'avg_pnl': month_df['pnl'].mean(),
                'best_trade': month_df['pnl'].max(),
                'worst_trade': month_df['pnl'].min()
            }
        
        return monthly_stats
    
    def generate_report(self) -> str:
        """Generate comprehensive text report"""
        
        metrics = self.calculate_performance_metrics()
        strategy_breakdown = self.get_strategy_breakdown()
        symbol_breakdown = self.get_symbol_breakdown()
        risk_metrics = self.get_risk_metrics()
        
        report = []
        report.append("=" * 80)
        report.append("QUANTUMTRADE ENGINE - PERFORMANCE REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("OVERALL PERFORMANCE")
        report.append("-" * 80)
        report.append(f"Total Trades: {metrics.total_trades}")
        report.append(f"Winning Trades: {metrics.winning_trades}")
        report.append(f"Losing Trades: {metrics.losing_trades}")
        report.append(f"Win Rate: {metrics.win_rate:.2f}%")
        report.append(f"Total P&L: ${metrics.total_pnl:.2f}")
        report.append(f"Total Return: {metrics.total_return_pct:.2f}%")
        report.append("")
        
        report.append("RISK METRICS")
        report.append("-" * 80)
        report.append(f"Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
        report.append(f"Sortino Ratio: {metrics.sortino_ratio:.3f}")
        report.append(f"Calmar Ratio: {metrics.calmar_ratio:.3f}")
        report.append(f"Max Drawdown: ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_pct:.2f}%)")
        report.append(f"Recovery Factor: {metrics.recovery_factor:.3f}")
        report.append("")
        
        report.append("TRADE STATISTICS")
        report.append("-" * 80)
        report.append(f"Average Win: ${metrics.avg_win:.2f}")
        report.append(f"Average Loss: ${metrics.avg_loss:.2f}")
        report.append(f"Profit Factor: {metrics.profit_factor:.3f}")
        report.append(f"Expectancy: ${metrics.expectancy:.2f}")
        report.append(f"Best Trade: ${metrics.best_trade:.2f}")
        report.append(f"Worst Trade: ${metrics.worst_trade:.2f}")
        report.append(f"Max Consecutive Wins: {metrics.consecutive_wins}")
        report.append(f"Max Consecutive Losses: {metrics.consecutive_losses}")
        report.append("")
        
        if strategy_breakdown:
            report.append("STRATEGY BREAKDOWN")
            report.append("-" * 80)
            for strategy, stats in strategy_breakdown.items():
                report.append(f"{strategy}:")
                report.append(f"  Trades: {stats['total_trades']}")
                report.append(f"  Win Rate: {stats['win_rate']:.2f}%")
                report.append(f"  Total P&L: ${stats['total_pnl']:.2f}")
                report.append("")
        
        if symbol_breakdown:
            report.append("SYMBOL BREAKDOWN")
            report.append("-" * 80)
            for symbol, stats in symbol_breakdown.items():
                report.append(f"{symbol}:")
                report.append(f"  Trades: {stats['total_trades']}")
                report.append(f"  Win Rate: {stats['win_rate']:.2f}%")
                report.append(f"  Total P&L: ${stats['total_pnl']:.2f}")
                report.append("")
        
        if risk_metrics:
            report.append("ADVANCED RISK METRICS")
            report.append("-" * 80)
            report.append(f"VaR (95%): {risk_metrics.get('value_at_risk_95', 0):.2f}%")
            report.append(f"VaR (99%): {risk_metrics.get('value_at_risk_99', 0):.2f}%")
            report.append(f"CVaR (95%): {risk_metrics.get('conditional_var_95', 0):.2f}%")
            report.append(f"Volatility: {risk_metrics.get('volatility', 0):.2f}%")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def export_to_json(self, filename: str):
        """Export analytics to JSON"""
        
        data = {
            'performance_metrics': self.calculate_performance_metrics().to_dict(),
            'strategy_breakdown': self.get_strategy_breakdown(),
            'symbol_breakdown': self.get_symbol_breakdown(),
            'time_analysis': self.get_time_analysis(),
            'risk_metrics': self.get_risk_metrics(),
            'monthly_performance': self.get_monthly_performance(),
            'trade_history': self.trade_history,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Analytics exported to {filename}")
    
    def _update_equity_curve(self, trade: Dict):
        """Update equity curve"""
        
        current_equity = self.equity_curve[-1]['equity'] if self.equity_curve else 10000
        new_equity = current_equity + trade.get('pnl', 0)
        
        self.equity_curve.append({
            'timestamp': trade.get('exit_time', datetime.now()),
            'equity': new_equity,
            'pnl': trade.get('pnl', 0)
        })
    
    def _update_daily_stats(self, trade: Dict):
        """Update daily statistics"""
        
        if 'entry_time' not in trade:
            return
        
        date = pd.to_datetime(trade['entry_time']).date().isoformat()
        
        if date not in self.daily_stats:
            self.daily_stats[date] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'pnl': 0
            }
        
        self.daily_stats[date]['trades'] += 1
        self.daily_stats[date]['pnl'] += trade.get('pnl', 0)
        
        if trade.get('pnl', 0) > 0:
            self.daily_stats[date]['wins'] += 1
        else:
            self.daily_stats[date]['losses'] += 1
    
    def _calculate_sharpe(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        excess_returns = returns - risk_free_rate
        return (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252) if np.std(excess_returns) > 0 else 0.0
    
    def _calculate_sortino(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio"""
        if len(returns) < 2:
            return 0.0
        excess_returns = returns - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0:
            return 0.0
        downside_std = np.std(downside_returns)
        return (np.mean(excess_returns) / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0
    
    def _calculate_max_drawdown(self, equity_df: pd.DataFrame) -> tuple:
        """Calculate maximum drawdown"""
        if equity_df.empty or 'equity' not in equity_df.columns:
            return 0.0, 0.0
        
        equity = equity_df['equity'].values
        peak = equity[0]
        max_dd = 0.0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = peak - value
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0.0
        return max_dd, max_dd_pct
    
    def _calculate_streaks(self, df: pd.DataFrame) -> tuple:
        """Calculate consecutive win/loss streaks"""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for pnl in df['pnl'].values:
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness"""
        if len(returns) < 3:
            return 0.0
        mean = np.mean(returns)
        std = np.std(returns)
        if std == 0:
            return 0.0
        return np.mean(((returns - mean) / std) ** 3)
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate kurtosis"""
        if len(returns) < 4:
            return 0.0
        mean = np.mean(returns)
        std = np.std(returns)
        if std == 0:
            return 0.0
        return np.mean(((returns - mean) / std) ** 4) - 3
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics"""
        return PerformanceMetrics(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
            total_pnl=0.0, total_return_pct=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
            calmar_ratio=0.0, max_drawdown=0.0, max_drawdown_pct=0.0, avg_win=0.0,
            avg_loss=0.0, profit_factor=0.0, expectancy=0.0, avg_trade_duration_hours=0.0,
            best_trade=0.0, worst_trade=0.0, consecutive_wins=0, consecutive_losses=0,
            recovery_factor=0.0
        )


if __name__ == "__main__":
    print("Analytics Dashboard Loaded")
    print("Features:")
    print("  - Comprehensive performance metrics")
    print("  - Strategy & symbol breakdown")
    print("  - Time-based analysis")
    print("  - Risk metrics (VaR, CVaR)")
    print("  - Report generation")
