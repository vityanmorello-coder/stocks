"""
Portfolio Optimizer v1.0 - Advanced Position Sizing
Risk parity, volatility targeting, and correlation-aware allocation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptimalAllocation:
    """Optimal position allocation result"""
    symbol: str
    optimal_size: float  # Position size in lots/units
    risk_contribution: float  # % of total portfolio risk
    volatility_adjusted_size: float
    correlation_penalty: float  # Reduction due to correlation
    final_size: float  # After all adjustments
    allocation_confidence: float  # 0-1


@dataclass
class PortfolioRiskMetrics:
    """Portfolio-level risk metrics"""
    total_risk: float  # Total portfolio risk in currency
    risk_parity_score: float  # 0-1, how well risk is distributed
    volatility_target_met: bool
    current_volatility: float
    target_volatility: float
    correlation_risk: float  # Average correlation
    diversification_ratio: float  # Higher = better diversified
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class RiskParityEngine:
    """
    Risk Parity allocation: distribute risk equally across positions.
    
    Traditional: allocate equal capital to each position
    Risk Parity: allocate so each position contributes equal risk
    
    Lower volatility assets get larger allocation.
    Higher volatility assets get smaller allocation.
    """
    
    def __init__(self):
        pass
    
    def calculate_allocation(
        self,
        symbols: List[str],
        volatilities: Dict[str, float],
        total_capital: float,
        target_risk_per_position: float = 1.0  # % of capital
    ) -> Dict[str, float]:
        """
        Calculate risk parity allocation.
        
        Args:
            symbols: List of symbols
            volatilities: Dict of symbol -> realized volatility
            total_capital: Total capital
            target_risk_per_position: Target risk per position (% of capital)
        
        Returns:
            Dict of symbol -> position size
        """
        allocations = {}
        
        for symbol in symbols:
            vol = volatilities.get(symbol, 0.01)
            
            # Risk parity: size inversely proportional to volatility
            # risk = size * volatility
            # target_risk = size * vol
            # size = target_risk / vol
            
            target_risk_amount = total_capital * (target_risk_per_position / 100)
            position_size = target_risk_amount / vol if vol > 0 else 0.0
            
            allocations[symbol] = position_size
        
        return allocations
    
    def calculate_risk_contribution(
        self,
        positions: Dict[str, float],
        volatilities: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate each position's contribution to total portfolio risk.
        
        Returns:
            Dict of symbol -> risk contribution (%)
        """
        risk_contributions = {}
        total_risk = 0.0
        
        # Calculate individual risks
        for symbol, size in positions.items():
            vol = volatilities.get(symbol, 0.01)
            risk = size * vol
            risk_contributions[symbol] = risk
            total_risk += risk
        
        # Normalize to percentages
        if total_risk > 0:
            for symbol in risk_contributions:
                risk_contributions[symbol] = (risk_contributions[symbol] / total_risk) * 100
        
        return risk_contributions
    
    def calculate_risk_parity_score(self, risk_contributions: Dict[str, float]) -> float:
        """
        Calculate how well risk is distributed (0-1).
        
        Perfect risk parity = all positions contribute equally
        Score = 1 - coefficient_of_variation
        """
        if not risk_contributions:
            return 0.0
        
        contributions = list(risk_contributions.values())
        
        # Perfect parity = all equal
        target = 100.0 / len(contributions)
        
        # Calculate deviation from perfect parity
        deviations = [abs(c - target) for c in contributions]
        avg_deviation = np.mean(deviations)
        
        # Score: lower deviation = higher score
        score = 1.0 - (avg_deviation / target)
        
        return max(0.0, min(1.0, score))


class VolatilityTargeter:
    """
    Volatility targeting: adjust position sizes to maintain target portfolio volatility.
    
    If realized volatility is high -> reduce position sizes
    If realized volatility is low -> increase position sizes
    """
    
    def __init__(self, target_volatility: float = 0.15):
        """
        Args:
            target_volatility: Target annualized volatility (e.g., 0.15 = 15%)
        """
        self.target_volatility = target_volatility
    
    def calculate_volatility_scalar(
        self,
        current_volatility: float,
        lookback_volatility: float
    ) -> float:
        """
        Calculate position size scalar based on volatility.
        
        Args:
            current_volatility: Recent realized volatility
            lookback_volatility: Longer-term average volatility
        
        Returns:
            Scalar multiplier (0.5 - 2.0)
        """
        if current_volatility == 0:
            return 1.0
        
        # Target / Current
        scalar = self.target_volatility / current_volatility
        
        # Cap at reasonable bounds
        scalar = np.clip(scalar, 0.5, 2.0)
        
        return scalar
    
    def adjust_positions(
        self,
        positions: Dict[str, float],
        current_volatility: float
    ) -> Dict[str, float]:
        """
        Adjust position sizes based on current volatility.
        
        Returns:
            Adjusted positions
        """
        scalar = self.calculate_volatility_scalar(current_volatility, self.target_volatility)
        
        adjusted = {symbol: size * scalar for symbol, size in positions.items()}
        
        return adjusted
    
    def calculate_portfolio_volatility(
        self,
        positions: Dict[str, float],
        volatilities: Dict[str, float],
        correlations: Optional[Dict[Tuple[str, str], float]] = None
    ) -> float:
        """
        Calculate portfolio volatility considering correlations.
        
        If no correlations provided, assumes independent (conservative).
        """
        symbols = list(positions.keys())
        
        if not symbols:
            return 0.0
        
        # Simple case: no correlations (independent assets)
        if correlations is None:
            # Portfolio variance = sum of individual variances
            total_variance = 0.0
            for symbol in symbols:
                size = positions[symbol]
                vol = volatilities.get(symbol, 0.01)
                variance = (size * vol) ** 2
                total_variance += variance
            
            portfolio_vol = np.sqrt(total_variance)
            return portfolio_vol
        
        # Complex case: with correlations
        # Build covariance matrix
        n = len(symbols)
        cov_matrix = np.zeros((n, n))
        
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                vol1 = volatilities.get(sym1, 0.01)
                vol2 = volatilities.get(sym2, 0.01)
                
                if i == j:
                    corr = 1.0
                else:
                    corr = correlations.get((sym1, sym2), 0.0)
                    if corr == 0.0:
                        corr = correlations.get((sym2, sym1), 0.0)
                
                cov_matrix[i, j] = corr * vol1 * vol2
        
        # Position weights
        weights = np.array([positions[sym] for sym in symbols])
        
        # Portfolio variance = w^T * Cov * w
        portfolio_variance = weights.T @ cov_matrix @ weights
        portfolio_vol = np.sqrt(portfolio_variance)
        
        return portfolio_vol


class CorrelationAdjuster:
    """
    Adjust position sizes based on correlation with existing positions.
    
    High correlation = reduce size to avoid concentration risk
    Low correlation = maintain or increase size for diversification
    """
    
    def __init__(self, correlation_threshold: float = 0.7):
        """
        Args:
            correlation_threshold: Above this, apply penalty
        """
        self.correlation_threshold = correlation_threshold
    
    def calculate_correlation_penalty(
        self,
        symbol: str,
        existing_positions: Dict[str, float],
        correlations: Dict[Tuple[str, str], float]
    ) -> float:
        """
        Calculate penalty for adding this symbol given existing positions.
        
        Returns:
            Penalty multiplier (0.5 - 1.0)
        """
        if not existing_positions:
            return 1.0  # No penalty if no existing positions
        
        penalties = []
        
        for existing_symbol in existing_positions.keys():
            if existing_symbol == symbol:
                continue
            
            # Get correlation
            corr = correlations.get((symbol, existing_symbol), 0.0)
            if corr == 0.0:
                corr = correlations.get((existing_symbol, symbol), 0.0)
            
            corr = abs(corr)  # Use absolute correlation
            
            # Apply penalty if highly correlated
            if corr > self.correlation_threshold:
                # Linear penalty: 0.7 corr = 0.85x, 0.9 corr = 0.65x
                penalty = 1.0 - (corr - self.correlation_threshold) / (1.0 - self.correlation_threshold) * 0.5
                penalties.append(penalty)
        
        if not penalties:
            return 1.0
        
        # Use minimum penalty (most restrictive)
        return min(penalties)
    
    def adjust_for_correlation(
        self,
        new_positions: Dict[str, float],
        existing_positions: Dict[str, float],
        correlations: Dict[Tuple[str, str], float]
    ) -> Dict[str, float]:
        """
        Adjust new position sizes based on correlation with existing positions.
        
        Returns:
            Adjusted positions
        """
        adjusted = {}
        
        for symbol, size in new_positions.items():
            penalty = self.calculate_correlation_penalty(symbol, existing_positions, correlations)
            adjusted[symbol] = size * penalty
        
        return adjusted


class PortfolioOptimizer:
    """
    Main portfolio optimizer combining risk parity, volatility targeting, and correlation adjustment.
    
    Usage:
        optimizer = PortfolioOptimizer(target_volatility=0.15)
        
        allocations = optimizer.optimize(
            symbols=['EUR/USD', 'GBP/USD', 'XAU/USD'],
            volatilities={'EUR/USD': 0.12, 'GBP/USD': 0.14, 'XAU/USD': 0.18},
            correlations={('EUR/USD', 'GBP/USD'): 0.85},
            total_capital=10000,
            existing_positions={'EUR/USD': 0.5}
        )
    """
    
    def __init__(
        self,
        target_volatility: float = 0.15,
        target_risk_per_position: float = 1.0,
        correlation_threshold: float = 0.7
    ):
        self.risk_parity = RiskParityEngine()
        self.vol_targeter = VolatilityTargeter(target_volatility)
        self.corr_adjuster = CorrelationAdjuster(correlation_threshold)
        
        self.target_volatility = target_volatility
        self.target_risk_per_position = target_risk_per_position
    
    def optimize(
        self,
        symbols: List[str],
        volatilities: Dict[str, float],
        correlations: Dict[Tuple[str, str], float],
        total_capital: float,
        existing_positions: Optional[Dict[str, float]] = None,
        signal_confidences: Optional[Dict[str, float]] = None
    ) -> List[OptimalAllocation]:
        """
        Calculate optimal position sizes.
        
        Args:
            symbols: Symbols to allocate
            volatilities: Realized volatility for each symbol
            correlations: Pairwise correlations
            total_capital: Total capital
            existing_positions: Current positions (for correlation adjustment)
            signal_confidences: Signal confidence for each symbol (0-1)
        
        Returns:
            List of OptimalAllocation
        """
        if existing_positions is None:
            existing_positions = {}
        
        if signal_confidences is None:
            signal_confidences = {s: 0.7 for s in symbols}
        
        # Step 1: Risk parity allocation
        base_allocations = self.risk_parity.calculate_allocation(
            symbols, volatilities, total_capital, self.target_risk_per_position
        )
        
        # Step 2: Volatility targeting
        current_vol = self._estimate_current_volatility(volatilities)
        vol_adjusted = self.vol_targeter.adjust_positions(base_allocations, current_vol)
        
        # Step 3: Correlation adjustment
        corr_adjusted = self.corr_adjuster.adjust_for_correlation(
            vol_adjusted, existing_positions, correlations
        )
        
        # Step 4: Confidence adjustment
        final_allocations = {}
        for symbol in symbols:
            confidence = signal_confidences.get(symbol, 0.7)
            # Scale by confidence: 0.5 conf = 0.75x size, 0.9 conf = 1.1x size
            conf_scalar = 0.5 + confidence
            final_allocations[symbol] = corr_adjusted[symbol] * conf_scalar
        
        # Step 5: Calculate risk contributions
        risk_contributions = self.risk_parity.calculate_risk_contribution(
            final_allocations, volatilities
        )
        
        # Build results
        results = []
        for symbol in symbols:
            corr_penalty = self.corr_adjuster.calculate_correlation_penalty(
                symbol, existing_positions, correlations
            )
            
            results.append(OptimalAllocation(
                symbol=symbol,
                optimal_size=base_allocations[symbol],
                risk_contribution=risk_contributions.get(symbol, 0.0),
                volatility_adjusted_size=vol_adjusted[symbol],
                correlation_penalty=corr_penalty,
                final_size=final_allocations[symbol],
                allocation_confidence=signal_confidences.get(symbol, 0.7)
            ))
        
        return results
    
    def calculate_portfolio_metrics(
        self,
        positions: Dict[str, float],
        volatilities: Dict[str, float],
        correlations: Dict[Tuple[str, str], float]
    ) -> PortfolioRiskMetrics:
        """
        Calculate portfolio-level risk metrics.
        
        Returns:
            PortfolioRiskMetrics
        """
        # Risk contributions
        risk_contributions = self.risk_parity.calculate_risk_contribution(positions, volatilities)
        
        # Risk parity score
        rp_score = self.risk_parity.calculate_risk_parity_score(risk_contributions)
        
        # Portfolio volatility
        portfolio_vol = self.vol_targeter.calculate_portfolio_volatility(
            positions, volatilities, correlations
        )
        
        # Volatility target met
        vol_target_met = abs(portfolio_vol - self.target_volatility) < 0.03  # Within 3%
        
        # Correlation risk
        corr_risk = self._calculate_avg_correlation(positions, correlations)
        
        # Diversification ratio
        div_ratio = self._calculate_diversification_ratio(positions, volatilities, portfolio_vol)
        
        # Total risk
        total_risk = sum(positions[s] * volatilities.get(s, 0.01) for s in positions)
        
        return PortfolioRiskMetrics(
            total_risk=total_risk,
            risk_parity_score=rp_score,
            volatility_target_met=vol_target_met,
            current_volatility=portfolio_vol,
            target_volatility=self.target_volatility,
            correlation_risk=corr_risk,
            diversification_ratio=div_ratio
        )
    
    def _estimate_current_volatility(self, volatilities: Dict[str, float]) -> float:
        """Estimate current market volatility (average across assets)"""
        if not volatilities:
            return 0.15
        return np.mean(list(volatilities.values()))
    
    def _calculate_avg_correlation(
        self,
        positions: Dict[str, float],
        correlations: Dict[Tuple[str, str], float]
    ) -> float:
        """Calculate average correlation among positions"""
        symbols = list(positions.keys())
        
        if len(symbols) < 2:
            return 0.0
        
        corrs = []
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                corr = correlations.get((sym1, sym2), 0.0)
                if corr == 0.0:
                    corr = correlations.get((sym2, sym1), 0.0)
                corrs.append(abs(corr))
        
        return np.mean(corrs) if corrs else 0.0
    
    def _calculate_diversification_ratio(
        self,
        positions: Dict[str, float],
        volatilities: Dict[str, float],
        portfolio_vol: float
    ) -> float:
        """
        Diversification ratio = weighted avg vol / portfolio vol
        Higher = better diversified
        """
        if portfolio_vol == 0:
            return 1.0
        
        # Weighted average volatility
        total_size = sum(positions.values())
        if total_size == 0:
            return 1.0
        
        weighted_vol = sum(
            positions[s] * volatilities.get(s, 0.01) for s in positions
        ) / total_size
        
        div_ratio = weighted_vol / portfolio_vol
        
        return div_ratio


# Example usage
if __name__ == "__main__":
    optimizer = PortfolioOptimizer(
        target_volatility=0.15,
        target_risk_per_position=1.0,
        correlation_threshold=0.7
    )
    
    # Sample data
    symbols = ['EUR/USD', 'GBP/USD', 'XAU/USD', 'AAPL']
    volatilities = {
        'EUR/USD': 0.12,
        'GBP/USD': 0.14,
        'XAU/USD': 0.18,
        'AAPL': 0.25
    }
    correlations = {
        ('EUR/USD', 'GBP/USD'): 0.85,
        ('EUR/USD', 'XAU/USD'): 0.60,
        ('GBP/USD', 'XAU/USD'): 0.55,
    }
    signal_confidences = {
        'EUR/USD': 0.75,
        'GBP/USD': 0.65,
        'XAU/USD': 0.80,
        'AAPL': 0.70
    }
    
    # Optimize
    allocations = optimizer.optimize(
        symbols=symbols,
        volatilities=volatilities,
        correlations=correlations,
        total_capital=10000,
        existing_positions={'EUR/USD': 0.3},
        signal_confidences=signal_confidences
    )
    
    print("=== Portfolio Optimization ===")
    for alloc in allocations:
        print(f"\n{alloc.symbol}:")
        print(f"  Final Size: {alloc.final_size:.4f}")
        print(f"  Risk Contribution: {alloc.risk_contribution:.1f}%")
        print(f"  Correlation Penalty: {alloc.correlation_penalty:.2f}x")
        print(f"  Confidence: {alloc.allocation_confidence:.0%}")
    
    # Portfolio metrics
    positions = {a.symbol: a.final_size for a in allocations}
    metrics = optimizer.calculate_portfolio_metrics(positions, volatilities, correlations)
    
    print(f"\n=== Portfolio Metrics ===")
    print(f"Total Risk: {metrics.total_risk:.2f}")
    print(f"Risk Parity Score: {metrics.risk_parity_score:.2f}")
    print(f"Current Volatility: {metrics.current_volatility:.2%}")
    print(f"Target Volatility: {metrics.target_volatility:.2%}")
    print(f"Volatility Target Met: {metrics.volatility_target_met}")
    print(f"Correlation Risk: {metrics.correlation_risk:.2f}")
    print(f"Diversification Ratio: {metrics.diversification_ratio:.2f}")
