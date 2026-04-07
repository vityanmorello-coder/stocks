"""
Portfolio Performance Analytics System
Comprehensive portfolio analysis, risk metrics, and performance attribution
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import logging
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int


@dataclass
class RiskMetrics:
    """Risk analysis metrics"""
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    cvar_95: float  # Conditional VaR 95%
    beta: float
    alpha: float
    information_ratio: float
    tracking_error: float
    downside_deviation: float
    upside_capture: float
    downside_capture: float


@dataclass
class AttributionData:
    """Performance attribution data"""
    source: str  # "asset_allocation", "security_selection", "timing"
    contribution: float
    contribution_pct: float
    details: Dict[str, Any]


class PortfolioAnalyzer:
    """Advanced portfolio performance analyzer"""
    
    def __init__(self, benchmark_returns: Optional[pd.Series] = None):
        self.benchmark_returns = benchmark_returns
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        
    def calculate_performance_metrics(self, 
                                    returns: pd.Series,
                                    trades: Optional[List[Dict]] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        # Basic returns calculations
        total_return = (1 + returns).prod() - 1
        n_periods = len(returns)
        annualized_return = (1 + total_return) ** (252 / n_periods) - 1
        volatility = returns.std() * np.sqrt(252)
        
        # Risk-adjusted returns
        excess_returns = returns - self.risk_free_rate / 252
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)
        sortino_ratio = annualized_return / downside_deviation if downside_deviation > 0 else 0
        
        # Drawdown analysis
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Find max drawdown duration
        drawdown_periods = []
        in_drawdown = False
        start_date = None
        
        for date, dd in drawdown.items():
            if dd < 0 and not in_drawdown:
                in_drawdown = True
                start_date = date
            elif dd >= 0 and in_drawdown:
                in_drawdown = False
                duration = (date - start_date).days
                drawdown_periods.append(duration)
        
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Trade-based metrics
        if trades:
            trade_metrics = self._calculate_trade_metrics(trades)
        else:
            trade_metrics = {
                'win_rate': 0, 'profit_factor': 0, 'avg_win': 0, 'avg_loss': 0,
                'largest_win': 0, 'largest_loss': 0, 'total_trades': 0,
                'winning_trades': 0, 'losing_trades': 0
            }
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            calmar_ratio=calmar_ratio,
            **trade_metrics
        )
    
    def _calculate_trade_metrics(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate trade-based performance metrics"""
        if not trades:
            return {
                'win_rate': 0, 'profit_factor': 0, 'avg_win': 0, 'avg_loss': 0,
                'largest_win': 0, 'largest_loss': 0, 'total_trades': 0,
                'winning_trades': 0, 'losing_trades': 0
            }
        
        # Extract P&L from trades
        trade_pnl = [trade.get('pnl', 0) for trade in trades]
        
        winning_trades = [pnl for pnl in trade_pnl if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnl if pnl < 0]
        
        win_rate = len(winning_trades) / len(trade_pnl) if trade_pnl else 0
        
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        
        largest_win = max(winning_trades) if winning_trades else 0
        largest_loss = min(losing_trades) if losing_trades else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'total_trades': len(trade_pnl),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }
    
    def calculate_risk_metrics(self, returns: pd.Series) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        
        # Value at Risk calculations
        var_95 = returns.quantile(0.05)
        var_99 = returns.quantile(0.01)
        
        # Conditional VaR (Expected Shortfall)
        cvar_95 = returns[returns <= var_95].mean()
        
        # Beta and Alpha (if benchmark available)
        if self.benchmark_returns is not None:
            # Align returns series
            common_index = returns.index.intersection(self.benchmark_returns.index)
            if len(common_index) > 30:  # Need sufficient data points
                portfolio_aligned = returns.loc[common_index]
                benchmark_aligned = self.benchmark_returns.loc[common_index]
                
                # Calculate beta using regression
                X = sm.add_constant(benchmark_aligned)
                model = sm.OLS(portfolio_aligned, X).fit()
                beta = model.params[1]
                alpha = model.params[0] * 252  # Annualize alpha
                
                # Information Ratio
                excess_returns = portfolio_aligned - benchmark_aligned
                tracking_error = excess_returns.std() * np.sqrt(252)
                information_ratio = excess_returns.mean() * 252 / tracking_error if tracking_error > 0 else 0
            else:
                beta = alpha = information_ratio = tracking_error = 0
        else:
            beta = alpha = information_ratio = tracking_error = 0
        
        # Downside/Upside capture
        downside_returns = returns[returns < 0]
        upside_returns = returns[returns > 0]
        
        downside_deviation = downside_returns.std() * np.sqrt(252)
        upside_deviation = upside_returns.std() * np.sqrt(252)
        
        total_deviation = returns.std() * np.sqrt(252)
        downside_capture = downside_deviation / total_deviation if total_deviation > 0 else 0
        upside_capture = upside_deviation / total_deviation if total_deviation > 0 else 0
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            beta=beta,
            alpha=alpha,
            information_ratio=information_ratio,
            tracking_error=tracking_error,
            downside_deviation=downside_deviation,
            upside_capture=upside_capture,
            downside_capture=downside_capture
        )
    
    def calculate_attribution(self, 
                            portfolio_returns: pd.Series,
                            benchmark_returns: pd.Series,
                            portfolio_weights: Dict[str, float],
                            benchmark_weights: Dict[str, float]) -> List[AttributionData]:
        """Calculate performance attribution"""
        
        attribution_results = []
        
        # Asset allocation effect
        allocation_effect = self._calculate_allocation_effect(
            portfolio_weights, benchmark_weights, benchmark_returns
        )
        attribution_results.append(allocation_effect)
        
        # Security selection effect
        selection_effect = self._calculate_selection_effect(
            portfolio_returns, benchmark_returns, portfolio_weights
        )
        attribution_results.append(selection_effect)
        
        # Timing effect (if intra-period data available)
        # This would require more granular data
        
        return attribution_results
    
    def _calculate_allocation_effect(self, 
                                   portfolio_weights: Dict[str, float],
                                   benchmark_weights: Dict[str, float],
                                   benchmark_returns: pd.Series) -> AttributionData:
        """Calculate asset allocation attribution"""
        
        # Simplified allocation effect calculation
        total_return = benchmark_returns.mean()
        allocation_contribution = 0
        
        for asset, portfolio_weight in portfolio_weights.items():
            benchmark_weight = benchmark_weights.get(asset, 0)
            asset_return = benchmark_returns.mean()  # Simplified
            weight_diff = portfolio_weight - benchmark_weight
            allocation_contribution += weight_diff * asset_return
        
        return AttributionData(
            source="asset_allocation",
            contribution=allocation_contribution,
            contribution_pct=allocation_contribution / total_return if total_return != 0 else 0,
            details={
                "weight_differences": {
                    asset: portfolio_weights.get(asset, 0) - benchmark_weights.get(asset, 0)
                    for asset in set(portfolio_weights.keys()) | set(benchmark_weights.keys())
                }
            }
        )
    
    def _calculate_selection_effect(self,
                                  portfolio_returns: pd.Series,
                                  benchmark_returns: pd.Series,
                                  portfolio_weights: Dict[str, float]) -> AttributionData:
        """Calculate security selection attribution"""
        
        # Simplified selection effect
        excess_return = portfolio_returns.mean() - benchmark_returns.mean()
        
        return AttributionData(
            source="security_selection",
            contribution=excess_return,
            contribution_pct=excess_return / benchmark_returns.mean() if benchmark_returns.mean() != 0 else 0,
            details={
                "excess_return": excess_return,
                "portfolio_return": portfolio_returns.mean(),
                "benchmark_return": benchmark_returns.mean()
            }
        )
    
    def generate_performance_report(self, 
                                  returns: pd.Series,
                                  trades: Optional[List[Dict]] = None,
                                  period: str = "1M") -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        # Calculate metrics
        performance_metrics = self.calculate_performance_metrics(returns, trades)
        risk_metrics = self.calculate_risk_metrics(returns)
        
        # Generate rolling metrics
        rolling_metrics = self._calculate_rolling_metrics(returns)
        
        # Create report
        report = {
            "period": period,
            "start_date": returns.index[0].strftime("%Y-%m-%d"),
            "end_date": returns.index[-1].strftime("%Y-%m-%d"),
            "performance_metrics": asdict(performance_metrics),
            "risk_metrics": asdict(risk_metrics),
            "rolling_metrics": rolling_metrics,
            "monthly_returns": self._calculate_monthly_returns(returns),
            "yearly_returns": self._calculate_yearly_returns(returns),
            "correlation_matrix": self._calculate_correlation_matrix(returns) if len(returns.shape) > 1 else None
        }
        
        return report
    
    def _calculate_rolling_metrics(self, returns: pd.Series, window: int = 30) -> Dict[str, List]:
        """Calculate rolling performance metrics"""
        
        rolling_sharpe = returns.rolling(window).apply(
            lambda x: (x.mean() * 252) / (x.std() * np.sqrt(252)) if x.std() > 0 else 0
        )
        
        rolling_returns = returns.rolling(window).apply(lambda x: (1 + x).prod() - 1)
        
        return {
            "rolling_sharpe": rolling_sharpe.dropna().tolist(),
            "rolling_returns": rolling_returns.dropna().tolist(),
            "dates": rolling_sharpe.dropna().index.strftime("%Y-%m-%d").tolist()
        }
    
    def _calculate_monthly_returns(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate monthly returns"""
        monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        return {date.strftime("%Y-%m"): value for date, value in monthly_returns.items()}
    
    def _calculate_yearly_returns(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate yearly returns"""
        yearly_returns = returns.resample('Y').apply(lambda x: (1 + x).prod() - 1)
        return {date.strftime("%Y"): value for date, value in yearly_returns.items()}
    
    def _calculate_correlation_matrix(self, returns: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix for multiple assets"""
        correlation_matrix = returns.corr()
        return correlation_matrix.to_dict()
    
    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """Save performance report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"portfolio_performance_{timestamp}.json"
        
        Path("data").mkdir(exist_ok=True)
        filepath = Path("data") / filename
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Performance report saved to {filepath}")
        return filepath


# Import for beta calculation
try:
    import statsmodels.api as sm
except ImportError:
    logger.warning("statsmodels not available - beta calculation will be limited")
    sm = None
