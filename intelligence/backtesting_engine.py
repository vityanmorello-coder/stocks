"""
Automated Strategy Backtesting Engine
Comprehensive backtesting with parameter optimization and walk-forward analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Backtest result with comprehensive metrics"""
    strategy_name: str
    parameters: Dict[str, Any]
    start_date: str
    end_date: str
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    calmar_ratio: float
    sortino_ratio: float
    trades: List[Dict[str, Any]]
    equity_curve: List[Tuple[str, float]]
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None


@dataclass
class OptimizationResult:
    """Parameter optimization result"""
    best_parameters: Dict[str, Any]
    best_score: float
    all_results: List[Dict[str, Any]]
    optimization_method: str
    total_iterations: int
    computation_time: float


class Strategy:
    """Base strategy class for backtesting"""
    
    def __init__(self, name: str, parameters: Dict[str, Any]):
        self.name = name
        self.parameters = parameters
        self.positions = {}
        self.cash = 100000  # Starting capital
        self.equity = []
        self.trades = []
        
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement generate_signals")
    
    def execute_trades(self, signals: pd.Series, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Execute trades based on signals"""
        trades = []
        
        for date, signal in signals.items():
            if signal != 0:  # Signal to trade
                price = data.loc[date, 'close']
                
                if signal > 0:  # Long signal
                    trade = {
                        'date': date,
                        'type': 'long',
                        'entry_price': price,
                        'quantity': self.cash * 0.1 / price,  # 10% of capital per trade
                        'stop_loss': price * 0.95,  # 5% stop loss
                        'take_profit': price * 1.1  # 10% take profit
                    }
                else:  # Short signal
                    trade = {
                        'date': date,
                        'type': 'short',
                        'entry_price': price,
                        'quantity': self.cash * 0.1 / price,
                        'stop_loss': price * 1.05,  # 5% stop loss
                        'take_profit': price * 0.9  # 10% take profit
                    }
                
                trades.append(trade)
                self.positions[date] = trade
                
        return trades
    
    def manage_positions(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Manage open positions with stop loss and take profit"""
        closed_trades = []
        
        for entry_date, position in list(self.positions.items()):
            current_date = entry_date
            entry_price = position['entry_price']
            current_price = data.loc[current_date, 'close']
            
            # Check stop loss and take profit
            if position['type'] == 'long':
                if current_price <= position['stop_loss'] or current_price >= position['take_profit']:
                    # Close position
                    pnl = (current_price - entry_price) * position['quantity']
                    closed_trade = {
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'type': 'long',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'return': pnl / (entry_price * position['quantity']),
                        'duration': (current_date - entry_date).days
                    }
                    closed_trades.append(closed_trade)
                    del self.positions[entry_date]
                    
            else:  # short position
                if current_price >= position['stop_loss'] or current_price <= position['take_profit']:
                    # Close position
                    pnl = (entry_price - current_price) * position['quantity']
                    closed_trade = {
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'type': 'short',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'return': pnl / (entry_price * position['quantity']),
                        'duration': (current_date - entry_date).days
                    }
                    closed_trades.append(closed_trade)
                    del self.positions[entry_date]
        
        return closed_trades


class MovingAverageStrategy(Strategy):
    """Moving average crossover strategy"""
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on MA crossover"""
        short_window = self.parameters.get('short_window', 10)
        long_window = self.parameters.get('long_window', 30)
        
        data['ma_short'] = data['close'].rolling(window=short_window).mean()
        data['ma_long'] = data['close'].rolling(window=long_window).mean()
        
        signals = pd.Series(0, index=data.index)
        
        # Generate crossover signals
        for i in range(1, len(data)):
            if (data['ma_short'].iloc[i-1] <= data['ma_long'].iloc[i-1] and 
                data['ma_short'].iloc[i] > data['ma_long'].iloc[i]):
                signals.iloc[i] = 1  # Buy signal
            elif (data['ma_short'].iloc[i-1] >= data['ma_long'].iloc[i-1] and 
                  data['ma_short'].iloc[i] < data['ma_long'].iloc[i]):
                signals.iloc[i] = -1  # Sell signal
        
        return signals


class RSIStrategy(Strategy):
    """RSI mean reversion strategy"""
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on RSI"""
        rsi_period = self.parameters.get('rsi_period', 14)
        oversold = self.parameters.get('oversold', 30)
        overbought = self.parameters.get('overbought', 70)
        
        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        signals = pd.Series(0, index=data.index)
        
        # Generate mean reversion signals
        for i in range(rsi_period, len(data)):
            if rsi.iloc[i-1] >= oversold and rsi.iloc[i] < oversold:
                signals.iloc[i] = 1  # Buy signal (oversold)
            elif rsi.iloc[i-1] <= overbought and rsi.iloc[i] > overbought:
                signals.iloc[i] = -1  # Sell signal (overbought)
        
        return signals


class BacktestEngine:
    """Advanced backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.commission = 0.001  # 0.1% commission
        self.slippage = 0.0001  # 0.01% slippage
        
    def run_backtest(self, 
                    strategy: Strategy, 
                    data: pd.DataFrame,
                    benchmark_data: Optional[pd.DataFrame] = None) -> BacktestResult:
        """Run single strategy backtest"""
        
        logger.info(f"Running backtest for {strategy.name}")
        
        # Generate signals
        signals = strategy.generate_signals(data)
        
        # Execute trades
        all_trades = []
        equity_curve = []
        
        # Simulate trading
        cash = self.initial_capital
        positions = {}
        
        for date, row in data.iterrows():
            current_equity = cash
            
            # Update position values
            for pos_date, position in list(positions.items()):
                current_price = row['close']
                position_value = position['quantity'] * current_price
                current_equity += position_value
                
                # Check exit conditions
                should_exit = False
                exit_price = current_price
                
                if position['type'] == 'long':
                    if current_price <= position['stop_loss'] or current_price >= position['take_profit']:
                        should_exit = True
                        exit_price = min(current_price, position['take_profit'])
                else:  # short
                    if current_price >= position['stop_loss'] or current_price <= position['take_profit']:
                        should_exit = True
                        exit_price = max(current_price, position['take_profit'])
                
                if should_exit:
                    # Close position
                    pnl = (exit_price - position['entry_price']) * position['quantity']
                    if position['type'] == 'short':
                        pnl = -pnl
                    
                    # Apply commission and slippage
                    commission_cost = (position['entry_price'] + exit_price) * position['quantity'] * self.commission
                    slippage_cost = abs(exit_price - position['entry_price']) * position['quantity'] * self.slippage
                    
                    net_pnl = pnl - commission_cost - slippage_cost
                    cash += position['entry_price'] * position['quantity'] + net_pnl
                    
                    trade = {
                        'entry_date': pos_date,
                        'exit_date': date,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'pnl': net_pnl,
                        'return': net_pnl / (position['entry_price'] * position['quantity']),
                        'duration': (date - pos_date).days
                    }
                    all_trades.append(trade)
                    del positions[pos_date]
            
            # Check for new signals
            if date in signals.index:
                signal = signals.loc[date]
                if signal != 0 and cash > self.initial_capital * 0.1:  # Minimum capital requirement
                    price = row['close'] * (1 + self.slippage)  # Apply slippage
                    position_size = min(cash * 0.1, cash)  # Max 10% per trade
                    quantity = position_size / price
                    
                    if signal > 0:  # Long
                        positions[date] = {
                            'type': 'long',
                            'entry_price': price,
                            'quantity': quantity,
                            'stop_loss': price * 0.95,
                            'take_profit': price * 1.1
                        }
                        cash -= position_size
                    else:  # Short
                        positions[date] = {
                            'type': 'short',
                            'entry_price': price,
                            'quantity': quantity,
                            'stop_loss': price * 1.05,
                            'take_profit': price * 0.9
                        }
                        cash -= position_size
            
            equity_curve.append((date.strftime('%Y-%m-%d'), current_equity))
        
        # Calculate metrics
        returns = pd.Series([eq[1] for eq in equity_curve], 
                           index=[pd.to_datetime(eq[0]) for eq in equity_curve]).pct_change().dropna()
        
        total_return = (current_equity - self.initial_capital) / self.initial_capital
        n_periods = len(returns)
        annualized_return = (1 + total_return) ** (252 / n_periods) - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Drawdown
        equity_values = [eq[1] for eq in equity_curve]
        running_max = pd.Series(equity_values).expanding().max()
        drawdown = (pd.Series(equity_values) - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Trade metrics
        if all_trades:
            win_rate = len([t for t in all_trades if t['pnl'] > 0]) / len(all_trades)
            gross_profit = sum([t['pnl'] for t in all_trades if t['pnl'] > 0])
            gross_loss = abs(sum([t['pnl'] for t in all_trades if t['pnl'] < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            avg_duration = np.mean([t['duration'] for t in all_trades])
        else:
            win_rate = profit_factor = avg_duration = 0
        
        # Benchmark comparison
        benchmark_return = None
        alpha = beta = None
        
        if benchmark_data is not None:
            benchmark_returns = benchmark_data['close'].pct_change().dropna()
            benchmark_return = (benchmark_data['close'].iloc[-1] / benchmark_data['close'].iloc[0]) - 1
            
            # Align returns for alpha/beta calculation
            common_dates = returns.index.intersection(benchmark_returns.index)
            if len(common_dates) > 30:
                portfolio_aligned = returns.loc[common_dates]
                benchmark_aligned = benchmark_returns.loc[common_dates]
                
                # Simple beta calculation
                covariance = np.cov(portfolio_aligned, benchmark_aligned)[0][1]
                benchmark_variance = np.var(benchmark_aligned)
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
                alpha = annualized_return - (0.02 + beta * 0.08)  # Assuming 2% risk-free, 8% market return
        
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return BacktestResult(
            strategy_name=strategy.name,
            parameters=strategy.parameters,
            start_date=data.index[0].strftime('%Y-%m-%d'),
            end_date=data.index[-1].strftime('%Y-%m-%d'),
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(all_trades),
            avg_trade_duration=avg_duration,
            calmar_ratio=calmar_ratio,
            sortino_ratio=self._calculate_sortino_ratio(returns),
            trades=all_trades,
            equity_curve=equity_curve,
            benchmark_return=benchmark_return,
            alpha=alpha,
            beta=beta
        )
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio"""
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return 0
        
        downside_deviation = downside_returns.std() * np.sqrt(252)
        annualized_return = returns.mean() * 252
        return annualized_return / downside_deviation if downside_deviation > 0 else 0
    
    def optimize_parameters(self,
                           strategy_class: type,
                           param_grid: Dict[str, List],
                           data: pd.DataFrame,
                           optimization_metric: str = 'sharpe_ratio',
                           method: str = 'grid_search') -> OptimizationResult:
        """Optimize strategy parameters"""
        
        logger.info(f"Starting parameter optimization using {method}")
        start_time = datetime.now()
        
        if method == 'grid_search':
            results = self._grid_search_optimization(strategy_class, param_grid, data, optimization_metric)
        elif method == 'random_search':
            results = self._random_search_optimization(strategy_class, param_grid, data, optimization_metric)
        else:
            raise ValueError(f"Unknown optimization method: {method}")
        
        computation_time = (datetime.now() - start_time).total_seconds()
        
        # Find best result
        best_result = max(results, key=lambda x: x[optimization_metric])
        
        return OptimizationResult(
            best_parameters=best_result['parameters'],
            best_score=best_result[optimization_metric],
            all_results=results,
            optimization_method=method,
            total_iterations=len(results),
            computation_time=computation_time
        )
    
    def _grid_search_optimization(self,
                                strategy_class: type,
                                param_grid: Dict[str, List],
                                data: pd.DataFrame,
                                optimization_metric: str) -> List[Dict]:
        """Grid search optimization"""
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        results = []
        
        for i, combination in enumerate(combinations):
            parameters = dict(zip(param_names, combination))
            
            try:
                strategy = strategy_class(f"{strategy_class.__name__}_opt", parameters)
                result = self.run_backtest(strategy, data)
                
                results.append({
                    'parameters': parameters,
                    optimization_metric: getattr(result, optimization_metric),
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate
                })
                
                if i % 10 == 0:
                    logger.info(f"Completed {i+1}/{len(combinations)} combinations")
                    
            except Exception as e:
                logger.error(f"Error testing parameters {parameters}: {e}")
                continue
        
        return results
    
    def _random_search_optimization(self,
                                  strategy_class: type,
                                  param_grid: Dict[str, List],
                                  data: pd.DataFrame,
                                  optimization_metric: str,
                                  n_iterations: int = 100) -> List[Dict]:
        """Random search optimization"""
        
        results = []
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for i in range(n_iterations):
            # Random parameter combination
            combination = [np.random.choice(values) for values in param_values]
            parameters = dict(zip(param_names, combination))
            
            try:
                strategy = strategy_class(f"{strategy_class.__name__}_rand", parameters)
                result = self.run_backtest(strategy, data)
                
                results.append({
                    'parameters': parameters,
                    optimization_metric: getattr(result, optimization_metric),
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate
                })
                
                if i % 10 == 0:
                    logger.info(f"Completed {i+1}/{n_iterations} random iterations")
                    
            except Exception as e:
                logger.error(f"Error testing parameters {parameters}: {e}")
                continue
        
        return results
    
    def walk_forward_analysis(self,
                            strategy_class: type,
                            parameters: Dict[str, Any],
                            data: pd.DataFrame,
                            train_period_months: int = 12,
                            test_period_months: int = 3) -> List[BacktestResult]:
        """Walk-forward analysis"""
        
        logger.info("Starting walk-forward analysis")
        
        results = []
        current_date = data.index[0]
        end_date = data.index[-1]
        
        while current_date + timedelta(days=train_period_months * 30) < end_date:
            # Define training and testing periods
            train_start = current_date
            train_end = current_date + timedelta(days=train_period_months * 30)
            test_start = train_end
            test_end = test_start + timedelta(days=test_period_months * 30)
            
            if test_end > end_date:
                break
            
            # Split data
            train_data = data.loc[train_start:train_end]
            test_data = data.loc[test_start:test_end]
            
            # Optimize parameters on training data
            param_grid = {
                'short_window': [5, 10, 15, 20],
                'long_window': [20, 30, 40, 50]
            }  # Example for MA strategy
            
            optimization_result = self.optimize_parameters(
                strategy_class, param_grid, train_data, method='grid_search'
            )
            
            # Test on out-of-sample data
            best_strategy = strategy_class(
                f"{strategy_class.__name__}_walkforward",
                optimization_result.best_parameters
            )
            
            result = self.run_backtest(best_strategy, test_data)
            results.append(result)
            
            # Move to next period
            current_date = test_end
        
        return results
    
    def monte_carlo_simulation(self,
                             strategy: Strategy,
                             data: pd.DataFrame,
                             n_simulations: int = 1000) -> Dict[str, Any]:
        """Monte Carlo simulation of strategy performance"""
        
        logger.info(f"Running Monte Carlo simulation with {n_simulations} iterations")
        
        results = []
        
        for i in range(n_simulations):
            # Randomly sample data with replacement
            sampled_data = data.sample(frac=1, replace=True).sort_index()
            
            try:
                result = self.run_backtest(strategy, sampled_data)
                results.append({
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate
                })
                
                if i % 100 == 0:
                    logger.info(f"Completed {i+1}/{n_simulations} simulations")
                    
            except Exception as e:
                logger.error(f"Error in simulation {i}: {e}")
                continue
        
        # Calculate statistics
        returns = [r['total_return'] for r in results]
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        max_drawdowns = [r['max_drawdown'] for r in results]
        
        return {
            'mean_return': np.mean(returns),
            'std_return': np.std(returns),
            'percentile_5': np.percentile(returns, 5),
            'percentile_95': np.percentile(returns, 95),
            'probability_positive': len([r for r in returns if r > 0]) / len(returns),
            'mean_sharpe': np.mean(sharpe_ratios),
            'mean_max_drawdown': np.mean(max_drawdowns),
            'worst_drawdown': min(max_drawdowns),
            'n_simulations': len(results)
        }
    
    def save_results(self, results: List[BacktestResult], filename: Optional[str] = None):
        """Save backtest results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{timestamp}.json"
        
        Path("data").mkdir(exist_ok=True)
        filepath = Path("data") / filename
        
        # Convert results to serializable format
        serializable_results = []
        for result in results:
            result_dict = asdict(result)
            result_dict['trades'] = [
                {k: str(v) if isinstance(v, (datetime, pd.Timestamp)) else v 
                 for k, v in trade.items()}
                for trade in result.trades
            ]
            serializable_results.append(result_dict)
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Backtest results saved to {filepath}")
        return filepath
