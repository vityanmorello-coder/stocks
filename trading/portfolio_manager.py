"""
Portfolio Manager v1.0 - Advanced Multi-Position Risk Management
Manages portfolio-level risk, correlation, and dynamic capital allocation.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Open position"""
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    unrealized_pnl: float = 0.0
    risk_amount: float = 0.0
    
    def update_pnl(self, current_price: float):
        """Update unrealized PnL"""
        if self.side == 'buy':
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity


@dataclass
class PortfolioState:
    """Current portfolio state"""
    total_capital: float
    available_capital: float
    total_exposure: float
    total_risk: float
    open_positions: int
    unrealized_pnl: float
    realized_pnl: float
    
    # Risk metrics
    portfolio_heat: float  # Total risk as % of capital
    max_heat_allowed: float = 6.0  # Max 6% total risk
    
    # Diversification
    asset_class_exposure: Dict[str, float] = field(default_factory=dict)
    correlation_risk: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'total_capital': round(self.total_capital, 2),
            'available_capital': round(self.available_capital, 2),
            'total_exposure': round(self.total_exposure, 2),
            'total_risk': round(self.total_risk, 2),
            'open_positions': self.open_positions,
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'realized_pnl': round(self.realized_pnl, 2),
            'portfolio_heat': round(self.portfolio_heat, 2),
            'asset_class_exposure': {k: round(v, 2) for k, v in self.asset_class_exposure.items()},
            'correlation_risk': round(self.correlation_risk, 2)
        }


class PortfolioManager:
    """
    Advanced portfolio-level risk management.
    
    Features:
    - Multi-position risk tracking
    - Correlation-based position limits
    - Dynamic capital allocation
    - Asset class diversification
    - Portfolio heat management
    - Drawdown protection
    
    Usage:
        pm = PortfolioManager(initial_capital=10000)
        can_trade, reason = pm.can_open_position(symbol, risk_amount)
        if can_trade:
            pm.add_position(symbol, side, entry_price, quantity, sl, tp)
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        max_portfolio_heat: float = 6.0,  # Max 6% total risk
        max_single_position_risk: float = 2.0,  # Max 2% per trade
        max_positions: int = 5,
        max_correlated_positions: int = 2,
        max_asset_class_exposure: float = 40.0  # Max 40% in one asset class
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_portfolio_heat = max_portfolio_heat
        self.max_single_risk = max_single_position_risk
        self.max_positions = max_positions
        self.max_correlated = max_correlated_positions
        self.max_asset_class_exp = max_asset_class_exposure
        
        self.positions: Dict[str, Position] = {}
        self.realized_pnl = 0.0
        
        # Asset class mapping
        self.asset_classes = {
            'EUR/USD': 'forex', 'GBP/USD': 'forex', 'USD/JPY': 'forex', 'AUD/USD': 'forex',
            'XAU/USD': 'commodity', 'XAG/USD': 'commodity', 'OIL/USD': 'commodity',
            'AAPL': 'stock', 'SPX500': 'index', 'BTC/USD': 'crypto'
        }
        
        # Correlation matrix (simplified - in production, calculate dynamically)
        self.correlations = {
            ('EUR/USD', 'GBP/USD'): 0.85,
            ('EUR/USD', 'AUD/USD'): 0.70,
            ('GBP/USD', 'AUD/USD'): 0.75,
            ('XAU/USD', 'XAG/USD'): 0.90,
            ('XAU/USD', 'EUR/USD'): 0.60,
            ('USD/JPY', 'EUR/USD'): -0.70,
            ('OIL/USD', 'CAD/USD'): 0.80,
        }
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols"""
        key = tuple(sorted([symbol1, symbol2]))
        return self.correlations.get(key, 0.0)
    
    def get_portfolio_state(self) -> PortfolioState:
        """Get current portfolio state"""
        total_exposure = sum(
            abs(pos.quantity * pos.entry_price)
            for pos in self.positions.values()
        )
        
        total_risk = sum(
            pos.risk_amount
            for pos in self.positions.values()
        )
        
        unrealized_pnl = sum(
            pos.unrealized_pnl
            for pos in self.positions.values()
        )
        
        portfolio_heat = (total_risk / self.current_capital) * 100
        
        # Asset class exposure
        asset_exp = {}
        for pos in self.positions.values():
            asset_class = self.asset_classes.get(pos.symbol, 'other')
            exposure = abs(pos.quantity * pos.entry_price)
            asset_exp[asset_class] = asset_exp.get(asset_class, 0) + exposure
        
        # Convert to percentages
        for ac in asset_exp:
            asset_exp[ac] = (asset_exp[ac] / self.current_capital) * 100
        
        # Correlation risk
        corr_risk = self._calculate_correlation_risk()
        
        return PortfolioState(
            total_capital=self.current_capital,
            available_capital=self.current_capital - total_exposure + unrealized_pnl,
            total_exposure=total_exposure,
            total_risk=total_risk,
            open_positions=len(self.positions),
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self.realized_pnl,
            portfolio_heat=portfolio_heat,
            max_heat_allowed=self.max_portfolio_heat,
            asset_class_exposure=asset_exp,
            correlation_risk=corr_risk
        )
    
    def _calculate_correlation_risk(self) -> float:
        """Calculate portfolio correlation risk"""
        if len(self.positions) < 2:
            return 0.0
        
        symbols = list(self.positions.keys())
        total_corr = 0.0
        pairs = 0
        
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                corr = abs(self.get_correlation(sym1, sym2))
                total_corr += corr
                pairs += 1
        
        return (total_corr / pairs) if pairs > 0 else 0.0
    
    def can_open_position(
        self,
        symbol: str,
        risk_amount: float,
        confidence: float = 0.5
    ) -> Tuple[bool, str]:
        """
        Check if new position can be opened.
        
        Args:
            symbol: Trading symbol
            risk_amount: Risk amount in currency
            confidence: Signal confidence (0-1)
        
        Returns:
            (allowed, reason)
        """
        state = self.get_portfolio_state()
        
        # Check max positions
        if len(self.positions) >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})"
        
        # Check if already have position in this symbol
        if symbol in self.positions:
            return False, f"Already have position in {symbol}"
        
        # Check single position risk
        risk_pct = (risk_amount / self.current_capital) * 100
        if risk_pct > self.max_single_risk:
            return False, f"Risk {risk_pct:.1f}% exceeds max {self.max_single_risk}%"
        
        # Check portfolio heat
        new_heat = state.portfolio_heat + risk_pct
        if new_heat > self.max_portfolio_heat:
            return False, f"Portfolio heat {new_heat:.1f}% exceeds max {self.max_portfolio_heat}%"
        
        # Check asset class exposure
        asset_class = self.asset_classes.get(symbol, 'other')
        current_exp = state.asset_class_exposure.get(asset_class, 0)
        if current_exp > self.max_asset_class_exp:
            return False, f"{asset_class} exposure {current_exp:.1f}% exceeds max {self.max_asset_class_exp}%"
        
        # Check correlation with existing positions
        correlated_count = 0
        for existing_symbol in self.positions.keys():
            corr = abs(self.get_correlation(symbol, existing_symbol))
            if corr > 0.7:  # High correlation threshold
                correlated_count += 1
        
        if correlated_count >= self.max_correlated:
            return False, f"Too many correlated positions ({correlated_count})"
        
        # Confidence-based filtering
        if confidence < 0.45:
            return False, f"Confidence {confidence:.0%} too low for portfolio entry"
        
        return True, "Position allowed"
    
    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float
    ) -> bool:
        """Add new position to portfolio"""
        # Calculate risk
        if side == 'buy':
            risk_per_unit = entry_price - stop_loss
        else:
            risk_per_unit = stop_loss - entry_price
        
        risk_amount = abs(risk_per_unit * quantity)
        
        # Check if allowed
        allowed, reason = self.can_open_position(symbol, risk_amount)
        if not allowed:
            logger.warning(f"Position rejected: {reason}")
            return False
        
        # Add position
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.now(),
            risk_amount=risk_amount
        )
        
        self.positions[symbol] = position
        logger.info(f"Position added: {symbol} {side} {quantity} @ {entry_price}")
        
        return True
    
    def close_position(
        self,
        symbol: str,
        exit_price: float
    ) -> Optional[float]:
        """Close position and return PnL"""
        if symbol not in self.positions:
            logger.warning(f"Position not found: {symbol}")
            return None
        
        pos = self.positions[symbol]
        
        # Calculate PnL
        if pos.side == 'buy':
            pnl = (exit_price - pos.entry_price) * pos.quantity
        else:
            pnl = (pos.entry_price - exit_price) * pos.quantity
        
        # Update capital
        self.current_capital += pnl
        self.realized_pnl += pnl
        
        # Remove position
        del self.positions[symbol]
        
        logger.info(f"Position closed: {symbol} @ {exit_price} | PnL: {pnl:.2f}")
        
        return pnl
    
    def update_positions(self, current_prices: Dict[str, float]):
        """Update all positions with current prices"""
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                pos.update_pnl(current_prices[symbol])
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        confidence: float,
        base_risk_pct: float = 1.0
    ) -> float:
        """
        Calculate optimal position size based on confidence and portfolio state.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            confidence: Signal confidence (0-1)
            base_risk_pct: Base risk percentage
        
        Returns:
            Position size (quantity)
        """
        state = self.get_portfolio_state()
        
        # Adjust risk based on confidence
        # High confidence (0.8+) = full risk
        # Medium confidence (0.6-0.8) = 75% risk
        # Low confidence (0.45-0.6) = 50% risk
        if confidence >= 0.8:
            risk_mult = 1.0
        elif confidence >= 0.6:
            risk_mult = 0.75
        else:
            risk_mult = 0.5
        
        # Adjust risk based on portfolio heat
        # If portfolio heat is high, reduce position size
        heat_ratio = state.portfolio_heat / self.max_portfolio_heat
        if heat_ratio > 0.8:
            risk_mult *= 0.5  # Reduce to 50% if near max heat
        elif heat_ratio > 0.6:
            risk_mult *= 0.75  # Reduce to 75%
        
        # Calculate risk amount
        adjusted_risk_pct = base_risk_pct * risk_mult
        risk_amount = self.current_capital * (adjusted_risk_pct / 100)
        
        # Calculate position size
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit == 0:
            return 0.0
        
        quantity = risk_amount / risk_per_unit
        
        return quantity
    
    def get_diversification_score(self) -> float:
        """
        Calculate portfolio diversification score (0-100).
        Higher = better diversified.
        """
        if len(self.positions) == 0:
            return 100.0
        
        state = self.get_portfolio_state()
        
        # Factor 1: Number of positions (more = better, up to a point)
        pos_score = min(100, (len(self.positions) / self.max_positions) * 100)
        
        # Factor 2: Asset class distribution (more even = better)
        if state.asset_class_exposure:
            exposures = list(state.asset_class_exposure.values())
            # Calculate coefficient of variation
            if len(exposures) > 1:
                cv = np.std(exposures) / np.mean(exposures) if np.mean(exposures) > 0 else 1.0
                dist_score = max(0, 100 * (1 - cv))
            else:
                dist_score = 50  # Single asset class
        else:
            dist_score = 100
        
        # Factor 3: Correlation risk (lower = better)
        corr_score = max(0, 100 * (1 - state.correlation_risk))
        
        # Weighted average
        diversification = (pos_score * 0.3 + dist_score * 0.4 + corr_score * 0.3)
        
        return min(100, max(0, diversification))
    
    def get_risk_metrics(self) -> Dict:
        """Get comprehensive risk metrics"""
        state = self.get_portfolio_state()
        
        return {
            'portfolio_heat': state.portfolio_heat,
            'max_heat': self.max_portfolio_heat,
            'heat_utilization': (state.portfolio_heat / self.max_portfolio_heat) * 100,
            'total_risk': state.total_risk,
            'total_exposure': state.total_exposure,
            'leverage': state.total_exposure / self.current_capital if self.current_capital > 0 else 0,
            'diversification_score': self.get_diversification_score(),
            'correlation_risk': state.correlation_risk,
            'open_positions': state.open_positions,
            'max_positions': self.max_positions,
            'position_utilization': (state.open_positions / self.max_positions) * 100,
            'unrealized_pnl': state.unrealized_pnl,
            'unrealized_pnl_pct': (state.unrealized_pnl / self.current_capital) * 100,
            'total_return': ((self.current_capital + state.unrealized_pnl - self.initial_capital) / self.initial_capital) * 100
        }


# Example usage
if __name__ == "__main__":
    pm = PortfolioManager(initial_capital=10000)
    
    # Try to add positions
    symbols = ['EUR/USD', 'GBP/USD', 'XAU/USD', 'AAPL']
    
    for symbol in symbols:
        entry = 1.0850 if 'USD' in symbol else 100.0
        sl = entry * 0.99
        tp = entry * 1.02
        quantity = pm.calculate_position_size(symbol, entry, sl, confidence=0.75)
        
        success = pm.add_position(symbol, 'buy', entry, quantity, sl, tp)
        print(f"{symbol}: {'Added' if success else 'Rejected'}")
    
    # Get portfolio state
    state = pm.get_portfolio_state()
    print(f"\nPortfolio State:")
    print(f"  Capital: ${state.total_capital:.2f}")
    print(f"  Exposure: ${state.total_exposure:.2f}")
    print(f"  Portfolio Heat: {state.portfolio_heat:.1f}%")
    print(f"  Open Positions: {state.open_positions}")
    print(f"  Diversification: {pm.get_diversification_score():.1f}/100")
    
    # Risk metrics
    metrics = pm.get_risk_metrics()
    print(f"\nRisk Metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
