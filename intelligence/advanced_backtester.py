"""
ADVANCED BACKTESTING ENGINE
Walk-forward validation, Monte Carlo simulation, and comprehensive analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    initial_capital: float = 10000.0
    commission_pct: float = 0.1
    slippage_pct: float = 0.05
    max_positions: int = 5
    risk_per_trade_pct: float = 1.0
    use_walk_forward: bool = True
    walk_forward_periods: int = 5
    in_sample_pct: float = 0.7
    monte_carlo_runs: int = 1000


@dataclass
class Trade:
    """Individual trade record"""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    size: float
    stop_loss: float
    take_profit: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    commission: float
    slippage: float
    strategy: str
    regime: str
    exit_reason: Optional[str]
    
    def to_dict(self):
        return asdict(self)


@dataclass
class BacktestResults:
    """Comprehensive backtest results"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    calmar_ratio: float
    recovery_factor: float
    avg_trade_duration: float
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int
    equity_curve: List[float]
    drawdown_curve: List[float]
    trades: List[Trade]
    
    def to_dict(self):
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'total_return_pct': self.total_return_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'expectancy': self.expectancy,
            'calmar_ratio': self.calmar_ratio,
            'recovery_factor': self.recovery_factor,
            'avg_trade_duration': self.avg_trade_duration,
            'best_trade': self.best_trade,
            'worst_trade': self.worst_trade,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses
        }


class AdvancedBacktester:
    """Advanced backtesting engine with walk-forward validation"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.current_capital = self.config.initial_capital
        self.peak_capital = self.config.initial_capital
        self.open_positions: Dict = {}
    
    def run_backtest(self, data: pd.DataFrame, strategy_func, **kwargs) -> BacktestResults:
        """Run standard backtest"""
        
        self._reset()
        
        for i in range(len(data)):
            current_bar = data.iloc[i]
            
            self._update_open_positions(current_bar)
            
            if len(self.open_positions) < self.config.max_positions:
                signal = strategy_func(data.iloc[:i+1], **kwargs)
                
                if signal:
                    self._enter_trade(signal, current_bar)
            
            self.equity_curve.append(self.current_capital)
        
        self._close_all_positions(data.iloc[-1])
        
        return self._calculate_results()
    
    def run_walk_forward(self, data: pd.DataFrame, strategy_func, **kwargs) -> Dict:
        """Run walk-forward validation"""
        
        n_periods = self.config.walk_forward_periods
        total_length = len(data)
        period_length = total_length // n_periods
        
        in_sample_length = int(period_length * self.config.in_sample_pct)
        out_sample_length = period_length - in_sample_length
        
        all_results = []
        combined_trades = []
        
        for period in range(n_periods):
            start_idx = period * period_length
            
            in_sample_start = start_idx
            in_sample_end = start_idx + in_sample_length
            out_sample_start = in_sample_end
            out_sample_end = min(out_sample_start + out_sample_length, total_length)
            
            in_sample_data = data.iloc[in_sample_start:in_sample_end]
            out_sample_data = data.iloc[out_sample_start:out_sample_end]
            
            optimized_params = self._optimize_parameters(in_sample_data, strategy_func, **kwargs)
            
            self._reset()
            out_sample_results = self.run_backtest(out_sample_data, strategy_func, **optimized_params)
            
            all_results.append({
                'period': period + 1,
                'in_sample_start': in_sample_data.index[0],
                'in_sample_end': in_sample_data.index[-1],
                'out_sample_start': out_sample_data.index[0],
                'out_sample_end': out_sample_data.index[-1],
                'results': out_sample_results.to_dict(),
                'optimized_params': optimized_params
            })
            
            combined_trades.extend(out_sample_results.trades)
        
        aggregate_results = self._aggregate_walk_forward_results(all_results, combined_trades)
        
        return {
            'walk_forward_periods': all_results,
            'aggregate_results': aggregate_results,
            'is_robust': self._check_robustness(all_results)
        }
    
    def run_monte_carlo(self, trades: List[Trade], runs: int = None) -> Dict:
        """Run Monte Carlo simulation on trade sequence"""
        
        runs = runs or self.config.monte_carlo_runs
        
        if not trades:
            return {}
        
        trade_returns = [t.pnl_pct for t in trades if t.pnl_pct is not None]
        
        if not trade_returns:
            return {}
        
        simulation_results = []
        
        for _ in range(runs):
            shuffled_returns = np.random.choice(trade_returns, size=len(trade_returns), replace=True)
            
            equity = self.config.initial_capital
            equity_curve = [equity]
            
            for ret in shuffled_returns:
                equity *= (1 + ret / 100)
                equity_curve.append(equity)
            
            final_return = (equity - self.config.initial_capital) / self.config.initial_capital * 100
            max_dd = self._calculate_max_drawdown_from_curve(equity_curve)
            
            simulation_results.append({
                'final_equity': equity,
                'final_return_pct': final_return,
                'max_drawdown_pct': max_dd
            })
        
        returns = [r['final_return_pct'] for r in simulation_results]
        drawdowns = [r['max_drawdown_pct'] for r in simulation_results]
        
        return {
            'runs': runs,
            'mean_return': np.mean(returns),
            'median_return': np.median(returns),
            'std_return': np.std(returns),
            'min_return': min(returns),
            'max_return': max(returns),
            'percentile_5': np.percentile(returns, 5),
            'percentile_95': np.percentile(returns, 95),
            'mean_drawdown': np.mean(drawdowns),
            'max_drawdown': max(drawdowns),
            'probability_profit': sum(1 for r in returns if r > 0) / runs * 100
        }
    
    def _reset(self):
        """Reset backtester state"""
        self.trades = []
        self.equity_curve = []
        self.current_capital = self.config.initial_capital
        self.peak_capital = self.config.initial_capital
        self.open_positions = {}
    
    def _enter_trade(self, signal: Dict, current_bar):
        """Enter a new trade"""
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        side = signal['side']
        
        risk_amount = self.current_capital * (self.config.risk_per_trade_pct / 100)
        
        price_risk = abs(entry_price - stop_loss)
        if price_risk == 0:
            return
        
        position_size = risk_amount / price_risk
        
        position_value = position_size * entry_price
        if position_value > self.current_capital * 0.2:
            position_size = (self.current_capital * 0.2) / entry_price
        
        commission = position_value * (self.config.commission_pct / 100)
        slippage = entry_price * (self.config.slippage_pct / 100)
        
        adjusted_entry = entry_price + slippage if side == 'buy' else entry_price - slippage
        
        trade = Trade(
            entry_time=current_bar.name,
            exit_time=None,
            symbol=signal.get('symbol', 'UNKNOWN'),
            side=side,
            entry_price=adjusted_entry,
            exit_price=None,
            size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            pnl=None,
            pnl_pct=None,
            commission=commission,
            slippage=slippage * position_size,
            strategy=signal.get('strategy', 'UNKNOWN'),
            regime=signal.get('regime', 'UNKNOWN'),
            exit_reason=None
        )
        
        self.open_positions[len(self.trades)] = trade
        self.trades.append(trade)
        self.current_capital -= (commission + trade.slippage)
    
    def _update_open_positions(self, current_bar):
        """Update and close positions if needed"""
        
        positions_to_close = []
        
        for trade_id, trade in self.open_positions.items():
            current_price = current_bar['close']
            
            exit_reason = None
            exit_price = None
            
            if trade.side == 'buy':
                if current_price >= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = 'take_profit'
                elif current_price <= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = 'stop_loss'
            else:
                if current_price <= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = 'take_profit'
                elif current_price >= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = 'stop_loss'
            
            if exit_price:
                self._close_trade(trade, exit_price, current_bar.name, exit_reason)
                positions_to_close.append(trade_id)
        
        for trade_id in positions_to_close:
            del self.open_positions[trade_id]
    
    def _close_trade(self, trade: Trade, exit_price: float, exit_time, exit_reason: str):
        """Close a trade"""
        
        slippage = exit_price * (self.config.slippage_pct / 100)
        adjusted_exit = exit_price - slippage if trade.side == 'buy' else exit_price + slippage
        
        if trade.side == 'buy':
            pnl = (adjusted_exit - trade.entry_price) * trade.size
        else:
            pnl = (trade.entry_price - adjusted_exit) * trade.size
        
        commission = adjusted_exit * trade.size * (self.config.commission_pct / 100)
        pnl -= commission
        
        trade.exit_price = adjusted_exit
        trade.exit_time = exit_time
        trade.pnl = pnl
        trade.pnl_pct = (pnl / (trade.entry_price * trade.size)) * 100
        trade.exit_reason = exit_reason
        
        self.current_capital += pnl
        
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
    
    def _close_all_positions(self, final_bar):
        """Close all remaining positions"""
        for trade in list(self.open_positions.values()):
            self._close_trade(trade, final_bar['close'], final_bar.name, 'end_of_backtest')
        self.open_positions.clear()
    
    def _calculate_results(self) -> BacktestResults:
        """Calculate comprehensive backtest results"""
        
        completed_trades = [t for t in self.trades if t.pnl is not None]
        
        if not completed_trades:
            return self._empty_results()
        
        winning_trades = [t for t in completed_trades if t.pnl > 0]
        losing_trades = [t for t in completed_trades if t.pnl <= 0]
        
        total_pnl = sum(t.pnl for t in completed_trades)
        total_return_pct = (total_pnl / self.config.initial_capital) * 100
        
        returns = [t.pnl_pct for t in completed_trades]
        sharpe = self._calculate_sharpe_ratio(returns)
        sortino = self._calculate_sortino_ratio(returns)
        
        max_dd, max_dd_pct = self._calculate_max_drawdown()
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        expectancy = (len(winning_trades) / len(completed_trades) * avg_win + 
                     len(losing_trades) / len(completed_trades) * avg_loss) if completed_trades else 0
        
        calmar = abs(total_return_pct / max_dd_pct) if max_dd_pct != 0 else 0
        recovery = abs(total_pnl / max_dd) if max_dd != 0 else 0
        
        durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 
                    for t in completed_trades if t.exit_time]
        avg_duration = np.mean(durations) if durations else 0
        
        consecutive_wins, consecutive_losses = self._calculate_consecutive_streaks(completed_trades)
        
        return BacktestResults(
            total_trades=len(completed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=(len(winning_trades) / len(completed_trades) * 100) if completed_trades else 0,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            calmar_ratio=calmar,
            recovery_factor=recovery,
            avg_trade_duration=avg_duration,
            best_trade=max([t.pnl for t in completed_trades]) if completed_trades else 0,
            worst_trade=min([t.pnl for t in completed_trades]) if completed_trades else 0,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            equity_curve=self.equity_curve,
            drawdown_curve=self._calculate_drawdown_curve(),
            trades=completed_trades
        )
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        excess_returns = [r - risk_free_rate for r in returns]
        return (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252) if np.std(excess_returns) > 0 else 0.0
    
    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        excess_returns = [r - risk_free_rate for r in returns]
        downside_returns = [r for r in excess_returns if r < 0]
        
        if not downside_returns:
            return 0.0
        
        downside_std = np.std(downside_returns)
        return (np.mean(excess_returns) / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0
    
    def _calculate_max_drawdown(self) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
        if not self.equity_curve:
            return 0.0, 0.0
        
        peak = self.equity_curve[0]
        max_dd = 0.0
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0.0
        
        return max_dd, max_dd_pct
    
    def _calculate_max_drawdown_from_curve(self, equity_curve: List[float]) -> float:
        """Calculate max drawdown percentage from equity curve"""
        peak = equity_curve[0]
        max_dd_pct = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd_pct = ((peak - equity) / peak * 100) if peak > 0 else 0.0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
        
        return max_dd_pct
    
    def _calculate_drawdown_curve(self) -> List[float]:
        """Calculate drawdown curve"""
        if not self.equity_curve:
            return []
        
        peak = self.equity_curve[0]
        drawdowns = []
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd_pct = ((peak - equity) / peak * 100) if peak > 0 else 0.0
            drawdowns.append(dd_pct)
        
        return drawdowns
    
    def _calculate_consecutive_streaks(self, trades: List[Trade]) -> Tuple[int, int]:
        """Calculate maximum consecutive wins and losses"""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def _optimize_parameters(self, data: pd.DataFrame, strategy_func, **kwargs) -> Dict:
        """Simple parameter optimization (placeholder for grid search)"""
        return kwargs
    
    def _aggregate_walk_forward_results(self, all_results: List[Dict], combined_trades: List[Trade]) -> Dict:
        """Aggregate walk-forward results"""
        
        total_return = sum(r['results']['total_return_pct'] for r in all_results)
        avg_win_rate = np.mean([r['results']['win_rate'] for r in all_results])
        avg_sharpe = np.mean([r['results']['sharpe_ratio'] for r in all_results])
        
        return {
            'total_periods': len(all_results),
            'total_return_pct': total_return,
            'avg_win_rate': avg_win_rate,
            'avg_sharpe_ratio': avg_sharpe,
            'total_trades': len(combined_trades)
        }
    
    def _check_robustness(self, all_results: List[Dict]) -> bool:
        """Check if strategy is robust across periods"""
        
        profitable_periods = sum(1 for r in all_results if r['results']['total_return_pct'] > 0)
        robustness_ratio = profitable_periods / len(all_results)
        
        return robustness_ratio >= 0.6
    
    def _empty_results(self) -> BacktestResults:
        """Return empty results"""
        return BacktestResults(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
            total_pnl=0.0, total_return_pct=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
            max_drawdown=0.0, max_drawdown_pct=0.0, avg_win=0.0, avg_loss=0.0,
            profit_factor=0.0, expectancy=0.0, calmar_ratio=0.0, recovery_factor=0.0,
            avg_trade_duration=0.0, best_trade=0.0, worst_trade=0.0,
            consecutive_wins=0, consecutive_losses=0, equity_curve=[], drawdown_curve=[], trades=[]
        )


# ─────────────────────────────────────────────────────────────────────────────
# WALK-FORWARD VALIDATION (time-based, no data leakage)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WalkForwardWindow:
    """One window of a walk-forward test."""
    period: int
    train_start: object
    train_end: object
    test_start: object
    test_end: object
    train_size: int
    test_size: int
    results: Optional['BacktestResults'] = None
    oos_sharpe: float = 0.0
    oos_return: float = 0.0
    oos_win_rate: float = 0.0
    is_profitable: bool = False


class WalkForwardValidator:
    """
    Anchored or rolling walk-forward validation with strict time ordering.
    Train/test splits are ALWAYS chronological — no random shuffling.

    Anchored:  train window grows each fold (expanding window)
    Rolling:   train window stays fixed size (sliding window)
    """

    def __init__(self,
                 n_splits: int = 5,
                 train_pct: float = 0.7,
                 mode: str = 'rolling',   # 'rolling' | 'anchored'
                 gap_bars: int = 0):       # bars to skip between train/test
        self.n_splits = n_splits
        self.train_pct = train_pct
        self.mode = mode
        self.gap = gap_bars
        self.windows: List[WalkForwardWindow] = []

    def split(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Yield (train_df, test_df) pairs in chronological order.
        Data is sorted ascending by index before splitting.
        """
        data = data.sort_index()
        n = len(data)
        if n < 50:
            raise ValueError(f"Need at least 50 bars for walk-forward, got {n}")

        total_window = n // self.n_splits
        test_size = max(1, int(total_window * (1 - self.train_pct)))
        train_size = total_window - test_size

        splits = []
        self.windows = []

        for i in range(self.n_splits):
            if self.mode == 'anchored':
                train_start = 0
                train_end = train_size + i * test_size
            else:
                train_start = i * test_size
                train_end = train_start + train_size

            test_start = train_end + self.gap
            test_end = min(test_start + test_size, n)

            if test_end <= test_start or train_end > n:
                break

            train_df = data.iloc[train_start:train_end]
            test_df = data.iloc[test_start:test_end]

            win = WalkForwardWindow(
                period=i + 1,
                train_start=train_df.index[0],
                train_end=train_df.index[-1],
                test_start=test_df.index[0],
                test_end=test_df.index[-1],
                train_size=len(train_df),
                test_size=len(test_df),
            )
            self.windows.append(win)
            splits.append((train_df, test_df))

        return splits

    def evaluate(self, data: pd.DataFrame, strategy_func,
                 config: 'BacktestConfig' = None, **strategy_kwargs) -> Dict:
        """
        Run full walk-forward evaluation and return structured results dict.
        strategy_func(df, **kwargs) -> BacktestResults or list of signals.
        """
        from advanced_backtester import AdvancedBacktester, BacktestConfig
        config = config or BacktestConfig()

        splits = self.split(data)
        oos_returns, oos_sharpes, oos_win_rates = [], [], []

        for idx, (train_df, test_df) in enumerate(splits):
            bt = AdvancedBacktester(config)
            try:
                results = bt.run_backtest(test_df, strategy_func, **strategy_kwargs)
            except Exception as e:
                logger.warning(f"[WF] Period {idx+1} failed: {e}")
                continue

            w = self.windows[idx]
            w.results = results
            w.oos_sharpe = results.sharpe_ratio
            w.oos_return = results.total_return_pct
            w.oos_win_rate = results.win_rate
            w.is_profitable = results.total_return_pct > 0

            oos_returns.append(results.total_return_pct)
            oos_sharpes.append(results.sharpe_ratio)
            oos_win_rates.append(results.win_rate)

        if not oos_returns:
            return {'error': 'No valid periods'}

        profitable = sum(1 for r in oos_returns if r > 0)
        robustness = profitable / len(oos_returns)

        return {
            'mode': self.mode,
            'n_periods': len(oos_returns),
            'oos_returns': oos_returns,
            'oos_sharpes': oos_sharpes,
            'oos_win_rates': oos_win_rates,
            'mean_oos_return': float(np.mean(oos_returns)),
            'std_oos_return': float(np.std(oos_returns)),
            'mean_oos_sharpe': float(np.mean(oos_sharpes)),
            'mean_oos_win_rate': float(np.mean(oos_win_rates)),
            'profitable_periods': profitable,
            'total_periods': len(oos_returns),
            'robustness_score': round(robustness, 3),
            'is_robust': robustness >= 0.6,
            'windows': [
                {
                    'period': w.period,
                    'train': f"{w.train_start} → {w.train_end}",
                    'test': f"{w.test_start} → {w.test_end}",
                    'oos_return_pct': round(w.oos_return, 2),
                    'oos_sharpe': round(w.oos_sharpe, 3),
                    'oos_win_rate': round(w.oos_win_rate, 1),
                    'profitable': w.is_profitable,
                }
                for w in self.windows if w.results
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE IMPORTANCE (model-agnostic + sklearn optional)
# ─────────────────────────────────────────────────────────────────────────────

class FeatureImportanceAnalyzer:
    """
    Computes feature importance for trade outcomes using:
      1. Random Forest (if sklearn available) — most reliable
      2. Permutation importance fallback
      3. Mean difference (win vs loss) as a last resort
    """

    FEATURE_COLUMNS = [
        'rsi', 'macd', 'signal_line', 'adx', 'atr_pct',
        'bb_position', 'volume_ratio', 'ma_fast', 'ma_slow',
        'price_vs_ma20', 'price_vs_ma50', 'high_low_range_pct',
        'close_vs_open_pct', 'body_ratio',
    ]

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build a feature matrix from OHLCV+indicator DataFrame.
        Returns only rows with no NaNs.
        """
        feats = pd.DataFrame(index=df.index)
        c = df['close']

        feats['rsi'] = self._rsi(c, 14)
        feats['macd'] = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        feats['signal_line'] = feats['macd'].ewm(span=9).mean()
        feats['adx'] = self._adx(df, 14)
        feats['atr_pct'] = self._atr(df, 14) / c * 100

        bb_mid = c.rolling(20).mean()
        bb_std = c.rolling(20).std()
        feats['bb_position'] = (c - (bb_mid - 2 * bb_std)) / (4 * bb_std + 1e-9)

        if 'volume' in df.columns and df['volume'].sum() > 0:
            feats['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        else:
            feats['volume_ratio'] = 1.0

        feats['ma_fast'] = c.rolling(20).mean()
        feats['ma_slow'] = c.rolling(50).mean()
        feats['price_vs_ma20'] = (c / feats['ma_fast'] - 1) * 100
        feats['price_vs_ma50'] = (c / feats['ma_slow'] - 1) * 100
        feats['high_low_range_pct'] = (df['high'] - df['low']) / c * 100
        feats['close_vs_open_pct'] = (df['close'] - df['open']) / df['open'] * 100
        feats['body_ratio'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-9)

        return feats.dropna()

    def compute(self, df: pd.DataFrame, trades: List['Trade'],
                lookahead_bars: int = 5) -> Dict[str, float]:
        """
        Label each bar as profitable (1) or not (0) based on future return,
        then fit a classifier and extract feature importances.
        """
        feats = self.extract_features(df)
        if feats.empty or len(feats) < 30:
            return {}

        # Label: 1 if close N bars later > close now
        future_ret = df['close'].shift(-lookahead_bars) / df['close'] - 1
        labels = (future_ret > 0).astype(int).reindex(feats.index).dropna()
        feats = feats.reindex(labels.index)
        X = feats.values
        y = labels.values

        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Time-based split — NO random shuffle
            split = int(len(X) * 0.7)
            X_train, X_test = X_scaled[:split], X_scaled[split:]
            y_train, y_test = y[:split], y[split:]

            clf = RandomForestClassifier(n_estimators=100, max_depth=6,
                                         random_state=42, n_jobs=-1)
            clf.fit(X_train, y_train)

            importances = dict(zip(feats.columns, clf.feature_importances_))
            # Also store test accuracy
            test_acc = clf.score(X_test, y_test)
            importances['_model_test_accuracy'] = round(test_acc, 4)
            importances['_method'] = 'random_forest'

        except ImportError:
            # Fallback: normalized mean-difference between win/loss bars
            win_mask = y == 1
            importances = {}
            for i, col in enumerate(feats.columns):
                win_mean = float(np.mean(X[win_mask, i])) if win_mask.any() else 0.0
                loss_mean = float(np.mean(X[~win_mask, i])) if (~win_mask).any() else 0.0
                denom = max(abs(win_mean), abs(loss_mean), 1e-9)
                importances[col] = round(abs(win_mean - loss_mean) / denom, 4)
            importances['_method'] = 'mean_difference_fallback'

        # Sort descending by importance (skip internal keys)
        ranked = {k: v for k, v in sorted(
            importances.items(),
            key=lambda x: x[1] if isinstance(x[1], float) else -1,
            reverse=True
        ) if not k.startswith('_')}

        ranked['_method'] = importances.get('_method', 'unknown')
        if '_model_test_accuracy' in importances:
            ranked['_model_test_accuracy'] = importances['_model_test_accuracy']

        return ranked

    # ── Technical helpers ────────────────────────────────────

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        hl = df['high'] - df['low']
        hc = (df['high'] - df['close'].shift()).abs()
        lc = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        up = df['high'].diff()
        down = -df['low'].diff()
        plus_dm = up.where((up > down) & (up > 0), 0.0)
        minus_dm = down.where((down > up) & (down > 0), 0.0)
        atr = FeatureImportanceAnalyzer._atr(df, period)
        plus_di = 100 * plus_dm.rolling(period).mean() / (atr + 1e-9)
        minus_di = 100 * minus_dm.rolling(period).mean() / (atr + 1e-9)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
        return dx.rolling(period).mean()


# ─────────────────────────────────────────────────────────────────────────────
# CONFUSION MATRIX FOR SIGNAL ACCURACY
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SignalConfusionMatrix:
    """
    Treats each signal as a binary prediction:
      Positive class = signal direction was correct (trade was profitable)
      Negative class = signal direction was wrong (trade was a loss)

    TP: Predicted BUY/SELL → price moved in predicted direction → win
    FP: Predicted BUY/SELL → price moved against → loss
    FN: Should have signalled (based on future price) → no signal fired
    TN: No signal AND no opportunity (correct abstention)
    """
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def total(self): return self.tp + self.fp + self.fn + self.tn

    @property
    def precision(self): return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self): return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self):
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self): return (self.tp + self.tn) / self.total if self.total > 0 else 0.0

    @property
    def specificity(self): return self.tn / (self.tn + self.fp) if (self.tn + self.fp) > 0 else 0.0

    def to_dict(self) -> Dict:
        return {
            'tp': self.tp, 'fp': self.fp, 'fn': self.fn, 'tn': self.tn,
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1, 4),
            'accuracy': round(self.accuracy, 4),
            'specificity': round(self.specificity, 4),
        }

    def summary_table(self) -> str:
        lines = [
            "Signal Confusion Matrix",
            "─" * 40,
            f"{'':20s} Predicted +   Predicted -",
            f"{'Actual +  (profitable)':20s}  TP={self.tp:5d}       FN={self.fn:5d}",
            f"{'Actual -  (loss)':20s}  FP={self.fp:5d}       TN={self.tn:5d}",
            "─" * 40,
            f"Precision  : {self.precision:.2%}",
            f"Recall     : {self.recall:.2%}",
            f"F1 Score   : {self.f1:.2%}",
            f"Accuracy   : {self.accuracy:.2%}",
            f"Specificity: {self.specificity:.2%}",
        ]
        return "\n".join(lines)


def build_confusion_matrix(trades: List['Trade'],
                            df: pd.DataFrame,
                            lookahead_bars: int = 5) -> SignalConfusionMatrix:
    """
    Build confusion matrix from completed trades.

    TP: trade was profitable (signal direction correct)
    FP: trade was a loss (signal direction wrong)
    FN: bars with profitable move but no trade (missed opportunities)
    TN: bars with no move and no trade (correct abstentions)
    """
    cm = SignalConfusionMatrix()

    # Signal outcomes from trades
    signalled_times = set()
    for t in trades:
        if t.pnl is None:
            continue
        correct = (t.side == 'buy' and t.pnl > 0) or (t.side == 'sell' and t.pnl > 0)
        if correct:
            cm.tp += 1
        else:
            cm.fp += 1
        if hasattr(t.entry_time, 'normalize'):
            signalled_times.add(t.entry_time)

    # FN/TN from non-signalled bars
    future_ret = df['close'].shift(-lookahead_bars) / df['close'] - 1
    non_signal_bars = [i for i, idx in enumerate(df.index) if idx not in signalled_times]

    for i in non_signal_bars:
        if i >= len(future_ret):
            continue
        ret = future_ret.iloc[i]
        if pd.isna(ret):
            continue
        if abs(ret) > 0.003:   # > 0.3% move = a tradeable opportunity existed
            cm.fn += 1
        else:
            cm.tn += 1

    return cm


def confusion_matrix_by_strategy(trades: List['Trade'],
                                   df: pd.DataFrame) -> Dict[str, Dict]:
    """Build per-strategy confusion matrices."""
    strategies = list({t.strategy for t in trades})
    result = {}
    for strat in strategies:
        strat_trades = [t for t in trades if t.strategy == strat]
        cm = build_confusion_matrix(strat_trades, df)
        result[strat] = cm.to_dict()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE METRICS (standalone, usable without full backtest)
# ─────────────────────────────────────────────────────────────────────────────

class PerformanceMetrics:
    """
    Stateless metrics calculator. All methods are class-level and accept
    either a list of Trade objects or raw return arrays.
    """

    @staticmethod
    def sharpe(returns: List[float], risk_free: float = 0.0,
               periods_per_year: int = 252) -> float:
        """Annualised Sharpe ratio."""
        r = np.array(returns)
        if len(r) < 2:
            return 0.0
        excess = r - risk_free
        std = np.std(excess, ddof=1)
        return float((np.mean(excess) / std) * np.sqrt(periods_per_year)) if std > 0 else 0.0

    @staticmethod
    def sortino(returns: List[float], risk_free: float = 0.0,
                periods_per_year: int = 252) -> float:
        """Annualised Sortino ratio (uses downside deviation)."""
        r = np.array(returns)
        if len(r) < 2:
            return 0.0
        excess = r - risk_free
        downside = excess[excess < 0]
        dstd = np.std(downside, ddof=1) if len(downside) > 1 else 0.0
        return float((np.mean(excess) / dstd) * np.sqrt(periods_per_year)) if dstd > 0 else 0.0

    @staticmethod
    def max_drawdown(equity_curve: List[float]) -> Tuple[float, float]:
        """Returns (max_drawdown_$, max_drawdown_%)."""
        eq = np.array(equity_curve)
        if len(eq) < 2:
            return 0.0, 0.0
        running_max = np.maximum.accumulate(eq)
        drawdowns = running_max - eq
        dd_pct = np.where(running_max > 0, drawdowns / running_max * 100, 0.0)
        return float(np.max(drawdowns)), float(np.max(dd_pct))

    @staticmethod
    def win_rate(trades: List['Trade']) -> float:
        """Win rate as percentage."""
        completed = [t for t in trades if t.pnl is not None]
        if not completed:
            return 0.0
        wins = sum(1 for t in completed if t.pnl > 0)
        return round(wins / len(completed) * 100, 2)

    @staticmethod
    def profit_factor(trades: List['Trade']) -> float:
        """Gross profit / gross loss."""
        completed = [t for t in trades if t.pnl is not None]
        gross_profit = sum(t.pnl for t in completed if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in completed if t.pnl <= 0))
        return round(gross_profit / gross_loss, 3) if gross_loss > 0 else 0.0

    @staticmethod
    def calmar(total_return_pct: float, max_dd_pct: float) -> float:
        """Calmar ratio = annualised return / max drawdown."""
        return round(abs(total_return_pct / max_dd_pct), 3) if max_dd_pct != 0 else 0.0

    @staticmethod
    def expectancy(trades: List['Trade']) -> float:
        """Average $ expectancy per trade."""
        completed = [t for t in trades if t.pnl is not None]
        if not completed:
            return 0.0
        return round(sum(t.pnl for t in completed) / len(completed), 4)

    @classmethod
    def all_metrics(cls, trades: List['Trade'], equity_curve: List[float],
                    initial_capital: float = 10000.0) -> Dict:
        """Compute and return all metrics as a flat dict."""
        completed = [t for t in trades if t.pnl is not None]
        returns = [t.pnl_pct for t in completed if t.pnl_pct is not None]
        total_pnl = sum(t.pnl for t in completed)
        total_ret_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0
        dd_abs, dd_pct = cls.max_drawdown(equity_curve)

        return {
            'total_trades':     len(completed),
            'winning_trades':   sum(1 for t in completed if t.pnl > 0),
            'losing_trades':    sum(1 for t in completed if t.pnl <= 0),
            'win_rate_pct':     cls.win_rate(completed),
            'profit_factor':    cls.profit_factor(completed),
            'sharpe_ratio':     round(cls.sharpe(returns), 3),
            'sortino_ratio':    round(cls.sortino(returns), 3),
            'max_drawdown_abs': round(dd_abs, 2),
            'max_drawdown_pct': round(dd_pct, 2),
            'calmar_ratio':     cls.calmar(total_ret_pct, dd_pct),
            'expectancy_per_trade': cls.expectancy(completed),
            'total_pnl':        round(total_pnl, 2),
            'total_return_pct': round(total_ret_pct, 2),
        }


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR  (JSON + printable table)
# ─────────────────────────────────────────────────────────────────────────────

class BacktestReportGenerator:
    """
    Aggregates backtest results, walk-forward output, feature importance,
    and confusion matrix into a structured report.

    Output formats:
      - to_dict()   → Python dict
      - to_json()   → JSON string
      - to_table()  → printable plain-text table
    """

    def __init__(self, symbol: str = '', timeframe: str = ''):
        self.symbol = symbol
        self.timeframe = timeframe
        self._data: Dict = {}

    def add_backtest_results(self, results: 'BacktestResults'):
        self._data['backtest'] = results.to_dict()
        self._data['backtest']['equity_curve_len'] = len(results.equity_curve)

    def add_walk_forward(self, wf: Dict):
        self._data['walk_forward'] = {
            k: v for k, v in wf.items() if k != 'windows'
        }
        self._data['walk_forward']['windows'] = wf.get('windows', [])

    def add_feature_importance(self, importance: Dict):
        self._data['feature_importance'] = importance

    def add_confusion_matrix(self, cm: SignalConfusionMatrix):
        self._data['confusion_matrix'] = cm.to_dict()

    def add_confusion_by_strategy(self, by_strat: Dict[str, Dict]):
        self._data['confusion_by_strategy'] = by_strat

    def add_monte_carlo(self, mc: Dict):
        self._data['monte_carlo'] = mc

    def add_metadata(self, **kwargs):
        self._data['metadata'] = {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }

    def to_dict(self) -> Dict:
        return self._data

    def to_json(self, indent: int = 2) -> str:
        def _serialise(obj):
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, (np.bool_,)): return bool(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            if isinstance(obj, datetime): return obj.isoformat()
            raise TypeError(f"Not serialisable: {type(obj)}")
        return json.dumps(self._data, indent=indent, default=_serialise)

    def to_table(self) -> str:
        lines = []
        W = 58

        def _h(title):
            lines.append("╔" + "═" * W + "╗")
            lines.append("║  " + title.upper().ljust(W - 2) + "║")
            lines.append("╠" + "═" * W + "╣")

        def _row(label, value, fmt=''):
            val_str = (f"{value:{fmt}}" if fmt else str(value)) if value is not None else 'N/A'
            lines.append(f"║  {label:<30s}{val_str:>{W - 33}}  ║")

        def _sep():
            lines.append("╟" + "─" * W + "╢")

        def _end():
            lines.append("╚" + "═" * W + "╝")

        # ── Metadata ─────────────────────────────────────────
        meta = self._data.get('metadata', {})
        _h(f"Backtest Report  {meta.get('symbol','')} {meta.get('timeframe','')}")
        _row("Generated", meta.get('generated_at', '')[:19])
        _end()

        # ── Core Metrics ──────────────────────────────────────
        bt = self._data.get('backtest', {})
        if bt:
            _h("Performance Metrics")
            _row("Total Trades",       bt.get('total_trades'))
            _row("Win Rate",           f"{bt.get('win_rate', 0):.1f}%")
            _row("Profit Factor",      f"{bt.get('profit_factor', 0):.3f}")
            _row("Total Return",       f"{bt.get('total_return_pct', 0):.2f}%")
            _row("Total PnL",          f"${bt.get('total_pnl', 0):.2f}")
            _sep()
            _row("Sharpe Ratio",       f"{bt.get('sharpe_ratio', 0):.3f}")
            _row("Sortino Ratio",      f"{bt.get('sortino_ratio', 0):.3f}")
            _row("Calmar Ratio",       f"{bt.get('calmar_ratio', 0):.3f}")
            _row("Max Drawdown",       f"{bt.get('max_drawdown_pct', 0):.2f}%")
            _sep()
            _row("Avg Win",            f"${bt.get('avg_win', 0):.2f}")
            _row("Avg Loss",           f"${bt.get('avg_loss', 0):.2f}")
            _row("Expectancy/Trade",   f"${bt.get('expectancy', 0):.2f}")
            _row("Best Trade",         f"${bt.get('best_trade', 0):.2f}")
            _row("Worst Trade",        f"${bt.get('worst_trade', 0):.2f}")
            _end()

        # ── Walk-Forward ──────────────────────────────────────
        wf = self._data.get('walk_forward', {})
        if wf:
            _h("Walk-Forward Validation (Out-of-Sample)")
            _row("Periods Tested",     wf.get('n_periods'))
            _row("Profitable Periods", f"{wf.get('profitable_periods')} / {wf.get('total_periods')}")
            _row("Robustness Score",   f"{wf.get('robustness_score', 0):.1%}")
            _row("Is Robust",          "✓ YES" if wf.get('is_robust') else "✗ NO")
            _sep()
            _row("Mean OOS Return",    f"{wf.get('mean_oos_return', 0):.2f}%")
            _row("Std OOS Return",     f"{wf.get('std_oos_return', 0):.2f}%")
            _row("Mean OOS Sharpe",    f"{wf.get('mean_oos_sharpe', 0):.3f}")
            _row("Mean OOS Win Rate",  f"{wf.get('mean_oos_win_rate', 0):.1f}%")
            # Period-by-period table
            _sep()
            lines.append(f"║  {'Period':<8}{'Train→Test':<28}{'Ret':>6}{'Sharpe':>8}{'WR':>6}  ║")
            _sep()
            for w in wf.get('windows', []):
                ret = f"{w['oos_return_pct']:+.1f}%"
                sh  = f"{w['oos_sharpe']:.2f}"
                wr  = f"{w['oos_win_rate']:.0f}%"
                tag = '✓' if w['profitable'] else '✗'
                date_str = str(w['test'])[:20]
                lines.append(f"║  {tag}{w['period']:<7}{date_str:<28}{ret:>6}{sh:>8}{wr:>6}  ║")
            _end()

        # ── Confusion Matrix ──────────────────────────────────
        cm = self._data.get('confusion_matrix', {})
        if cm:
            _h("Signal Confusion Matrix")
            _row("True Positives",   cm.get('tp'))
            _row("False Positives",  cm.get('fp'))
            _row("False Negatives",  cm.get('fn'))
            _row("True Negatives",   cm.get('tn'))
            _sep()
            _row("Precision",  f"{cm.get('precision', 0):.2%}")
            _row("Recall",     f"{cm.get('recall', 0):.2%}")
            _row("F1 Score",   f"{cm.get('f1_score', 0):.2%}")
            _row("Accuracy",   f"{cm.get('accuracy', 0):.2%}")
            _end()

        # ── Feature Importance ────────────────────────────────
        fi = self._data.get('feature_importance', {})
        if fi:
            _h(f"Feature Importance  [{fi.get('_method','?')}]")
            if '_model_test_accuracy' in fi:
                _row("Model Test Accuracy", f"{fi['_model_test_accuracy']:.2%}")
                _sep()
            top10 = [(k, v) for k, v in fi.items()
                     if not k.startswith('_') and isinstance(v, float)][:10]
            max_imp = max((v for _, v in top10), default=1.0)
            for feat, imp in top10:
                bar_len = int(imp / max_imp * 20) if max_imp > 0 else 0
                bar = '█' * bar_len + '░' * (20 - bar_len)
                lines.append(f"║  {feat:<22s} {bar} {imp:.3f}  ║")
            _end()

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATED RUNNER — ties all pieces together
# ─────────────────────────────────────────────────────────────────────────────

class ValidatedBacktestRunner:
    """
    One-stop class: run backtest + walk-forward + feature importance
    + confusion matrix + report in a single call.

    Example:
        runner = ValidatedBacktestRunner('EUR/USD', '15m')
        report = runner.run(df, my_strategy_func)
        print(report.to_table())
        print(report.to_json())
    """

    def __init__(self, symbol: str = '', timeframe: str = '',
                 config: 'BacktestConfig' = None):
        self.symbol = symbol
        self.timeframe = timeframe
        self.config = config or BacktestConfig()

    def run(self, df: pd.DataFrame, strategy_func,
            wf_splits: int = 5, wf_mode: str = 'rolling',
            mc_runs: int = 500, **strategy_kwargs) -> BacktestReportGenerator:

        report = BacktestReportGenerator(self.symbol, self.timeframe)
        report.add_metadata(wf_splits=wf_splits, wf_mode=wf_mode,
                            mc_runs=mc_runs, bars=len(df))

        # 1. Full in-sample backtest
        bt = AdvancedBacktester(self.config)
        bt_results = bt.run_backtest(df, strategy_func, **strategy_kwargs)
        report.add_backtest_results(bt_results)

        # 2. Walk-forward (out-of-sample)
        wfv = WalkForwardValidator(n_splits=wf_splits, mode=wf_mode)
        wf_results = wfv.evaluate(df, strategy_func, self.config, **strategy_kwargs)
        report.add_walk_forward(wf_results)

        # 3. Feature importance
        fia = FeatureImportanceAnalyzer()
        fi = fia.compute(df, bt_results.trades)
        report.add_feature_importance(fi)

        # 4. Confusion matrix (overall + by strategy)
        cm = build_confusion_matrix(bt_results.trades, df)
        report.add_confusion_matrix(cm)
        by_strat = confusion_matrix_by_strategy(bt_results.trades, df)
        report.add_confusion_by_strategy(by_strat)

        # 5. Monte Carlo
        mc = bt.run_monte_carlo(bt_results.trades, runs=mc_runs)
        report.add_monte_carlo(mc)

        return report


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  QuantumTrade — Validated Backtest Engine")
    print("=" * 60)

    # ── Build synthetic OHLCV data (replace with real data in production) ──
    np.random.seed(42)
    n_bars = 800
    dates = pd.date_range('2023-01-01', periods=n_bars, freq='15min')
    price = 1.08
    prices = [price]
    for _ in range(n_bars - 1):
        prices.append(prices[-1] * (1 + np.random.normal(0, 0.0008)))
    prices = np.array(prices)

    df_demo = pd.DataFrame({
        'open':   prices * (1 + np.random.uniform(-0.0002, 0.0002, n_bars)),
        'high':   prices * (1 + np.abs(np.random.normal(0, 0.0005, n_bars))),
        'low':    prices * (1 - np.abs(np.random.normal(0, 0.0005, n_bars))),
        'close':  prices,
        'volume': np.random.randint(500, 5000, n_bars).astype(float),
    }, index=dates)

    # ── Simple demo strategy: RSI mean-reversion ──────────────
    def demo_strategy(data: pd.DataFrame, rsi_low=35, rsi_high=65):
        if len(data) < 30:
            return None
        close = data['close']
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        cur_rsi = rsi.iloc[-1]
        cur_price = close.iloc[-1]
        atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
        if cur_rsi < rsi_low:
            return {'side': 'buy', 'entry_price': cur_price,
                    'stop_loss': cur_price - atr * 1.5,
                    'take_profit': cur_price + atr * 2.5,
                    'symbol': 'EUR/USD', 'strategy': 'rsi_reversion', 'regime': 'ranging'}
        if cur_rsi > rsi_high:
            return {'side': 'sell', 'entry_price': cur_price,
                    'stop_loss': cur_price + atr * 1.5,
                    'take_profit': cur_price - atr * 2.5,
                    'symbol': 'EUR/USD', 'strategy': 'rsi_reversion', 'regime': 'ranging'}
        return None

    # ── Run everything ────────────────────────────────────────
    runner = ValidatedBacktestRunner('EUR/USD', '15m')
    report = runner.run(df_demo, demo_strategy, wf_splits=5, mc_runs=200)

    print(report.to_table())
    print()

    # Save JSON report
    json_path = 'backtest_report.json'
    with open(json_path, 'w') as f:
        f.write(report.to_json())
    print(f"Full report saved to: {json_path}")

    # Summary stats
    d = report.to_dict()
    bt = d.get('backtest', {})
    wf = d.get('walk_forward', {})
    cm = d.get('confusion_matrix', {})
    fi = d.get('feature_importance', {})

    print("\nQuick interpretation:")
    sharpe = bt.get('sharpe_ratio', 0)
    pf     = bt.get('profit_factor', 0)
    robust = wf.get('is_robust', False)
    f1     = cm.get('f1_score', 0)
    method = fi.get('_method', '?')
    top_feat = next((k for k in fi if not k.startswith('_')), 'N/A')

    print(f"  Sharpe {sharpe:.2f}  ({'good' if sharpe > 1 else 'needs work'})")
    print(f"  Profit factor {pf:.2f}  ({'edge present' if pf > 1.2 else 'marginal'})")
    print(f"  Walk-forward robust: {robust}")
    print(f"  Signal F1 score: {f1:.2%}")
    print(f"  Top feature: {top_feat}  (method: {method})")
