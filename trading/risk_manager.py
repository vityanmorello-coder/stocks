"""
Risk Management System
CRITICAL: This is the most important component - protects capital at all costs
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open trading position"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy: str
    entry_time: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    original_stop_loss: float = 0.0
    trailing_stop_active: bool = False
    break_even_applied: bool = False
    highest_price: float = 0.0
    lowest_price: float = 999999.0
    
    def __post_init__(self):
        self.original_stop_loss = self.stop_loss
        self.highest_price = self.entry_price
        self.lowest_price = self.entry_price
    
    def update_pnl(self, current_price: float):
        """Update unrealized P&L and track price extremes"""
        self.current_price = current_price
        if self.side == 'buy':
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
            if current_price > self.highest_price:
                self.highest_price = current_price
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity
            if current_price < self.lowest_price:
                self.lowest_price = current_price
    
    @property
    def profit_percent(self) -> float:
        """Current profit as percentage"""
        if self.entry_price == 0:
            return 0.0
        if self.side == 'buy':
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100


@dataclass
class DailyStats:
    """Track daily trading statistics"""
    date: str
    starting_balance: float
    current_balance: float
    trades_executed: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_balance: float = 0.0
    
    def __post_init__(self):
        self.peak_balance = self.starting_balance
    
    @property
    def daily_return_percent(self) -> float:
        """Calculate daily return percentage"""
        if self.starting_balance == 0:
            return 0.0
        return ((self.current_balance - self.starting_balance) / self.starting_balance) * 100
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate"""
        total = self.winning_trades + self.losing_trades
        if total == 0:
            return 0.0
        return (self.winning_trades / total) * 100


class RiskManager:
    """
    Comprehensive risk management system
    
    Responsibilities:
    - Position sizing
    - Daily loss limits
    - Maximum drawdown protection
    - Trade frequency limits
    - Kill switch activation
    """
    
    def __init__(self, config):
        self.config = config
        
        # Account state
        self.initial_capital = config.INITIAL_CAPITAL
        self.current_balance = config.INITIAL_CAPITAL
        self.peak_balance = config.INITIAL_CAPITAL
        
        # Risk limits
        self.risk_per_trade_percent = config.RISK_PER_TRADE_PERCENT
        self.max_daily_loss_percent = config.MAX_DAILY_LOSS_PERCENT
        self.max_drawdown_percent = config.MAX_TOTAL_DRAWDOWN_PERCENT
        self.max_position_size_percent = config.MAX_POSITION_SIZE_PERCENT
        self.max_concurrent_positions = config.MAX_CONCURRENT_POSITIONS
        self.max_trades_per_day = config.MAX_TRADES_PER_DAY
        self.min_time_between_trades = config.MIN_TIME_BETWEEN_TRADES
        
        # State tracking
        self.open_positions: Dict[str, Position] = {}
        self.daily_stats: Dict[str, DailyStats] = {}
        self.last_trade_time: Optional[datetime] = None
        self.kill_switch_active = config.KILL_SWITCH_ACTIVE
        
        # Strategy trade counters
        self.strategy_trade_count: Dict[str, int] = {}
        
        logger.info("Risk Manager initialized")
        logger.info(f"Risk per trade: {self.risk_per_trade_percent}%")
        logger.info(f"Max daily loss: {self.max_daily_loss_percent}%")
        logger.info(f"Max drawdown: {self.max_drawdown_percent}%")
    
    def _get_today_stats(self) -> DailyStats:
        """Get or create today's statistics"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in self.daily_stats:
            # New day - reset counters
            self.daily_stats[today] = DailyStats(
                date=today,
                starting_balance=self.current_balance,
                current_balance=self.current_balance
            )
            self.strategy_trade_count = {}
            logger.info(f"New trading day started: {today}")
        
        return self.daily_stats[today]
    
    def update_balance(self, new_balance: float):
        """Update current account balance"""
        self.current_balance = new_balance
        
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
        
        today_stats = self._get_today_stats()
        today_stats.current_balance = new_balance
        
        # Update peak balance for drawdown calculation
        if new_balance > today_stats.peak_balance:
            today_stats.peak_balance = new_balance
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                               symbol: str) -> Tuple[float, bool, str]:
        """
        Calculate position size based on risk management rules
        
        Returns:
            (position_size, is_allowed, reason)
        """
        # Calculate risk amount in currency
        risk_amount = self.current_balance * (self.risk_per_trade_percent / 100)
        
        # Calculate price difference to stop loss
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff == 0:
            return 0.0, False, "Stop loss too close to entry price"
        
        # Position size = Risk Amount / Price Difference
        position_size = risk_amount / price_diff
        
        # Check against maximum position size
        max_position_value = self.current_balance * (self.max_position_size_percent / 100)
        max_position_size = max_position_value / entry_price
        
        if position_size > max_position_size:
            position_size = max_position_size
            logger.warning(f"Position size capped at {self.max_position_size_percent}% of balance")
        
        # Round to reasonable precision
        position_size = round(position_size, 4)
        
        return position_size, True, "Position size calculated"
    
    def can_open_position(self, signal) -> Tuple[bool, str]:
        """
        Check if a new position can be opened
        
        Returns:
            (can_open, reason)
        """
        # Check kill switch
        if self.kill_switch_active:
            return False, "KILL SWITCH ACTIVE - All trading stopped"
        
        # Check concurrent positions limit
        if len(self.open_positions) >= self.max_concurrent_positions:
            return False, f"Maximum concurrent positions reached ({self.max_concurrent_positions})"
        
        # Check daily trade limit
        today_stats = self._get_today_stats()
        if today_stats.trades_executed >= self.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.max_trades_per_day})"
        
        # Check strategy-specific trade limit
        strategy_limit = self.config.STRATEGY_MAX_TRADES.get(signal.strategy, 999)
        strategy_count = self.strategy_trade_count.get(signal.strategy, 0)
        if strategy_count >= strategy_limit:
            return False, f"Strategy '{signal.strategy}' daily limit reached ({strategy_limit})"
        
        # Check time between trades
        if self.last_trade_time:
            time_since_last = (datetime.now() - self.last_trade_time).total_seconds()
            if time_since_last < self.min_time_between_trades:
                return False, f"Minimum time between trades not met ({self.min_time_between_trades}s)"
        
        # Check daily loss limit
        if today_stats.daily_return_percent <= -self.max_daily_loss_percent:
            self.activate_kill_switch(f"Daily loss limit reached ({self.max_daily_loss_percent}%)")
            return False, "Daily loss limit reached - trading stopped for today"
        
        # Check total drawdown
        drawdown_percent = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        if drawdown_percent >= self.max_drawdown_percent:
            self.activate_kill_switch(f"Maximum drawdown reached ({self.max_drawdown_percent}%)")
            return False, "Maximum drawdown reached - SYSTEM SHUTDOWN"
        
        # Check trading hours (skip in paper mode unless enforced)
        enforce_hours = getattr(self.config, 'ENFORCE_TRADING_HOURS', False)
        if enforce_hours:
            current_hour = datetime.now().hour
            if not (self.config.TRADING_HOURS_START <= current_hour < self.config.TRADING_HOURS_END):
                return False, f"Outside trading hours ({self.config.TRADING_HOURS_START}-{self.config.TRADING_HOURS_END} UTC)"
        
        # Check correlation filter
        if getattr(self.config, 'ENABLE_CORRELATION_FILTER', False):
            correlated_pairs = getattr(self.config, 'CORRELATED_PAIRS', {})
            max_corr = getattr(self.config, 'MAX_CORRELATED_SAME_DIRECTION', 1)
            signal_symbol = signal.symbol
            signal_side = signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type)
            
            corr_symbols = correlated_pairs.get(signal_symbol, [])
            same_dir_count = 0
            for pos in self.open_positions.values():
                if pos.symbol in corr_symbols and pos.side == signal_side:
                    same_dir_count += 1
            
            if same_dir_count >= max_corr:
                return False, f"Correlation filter: already have {same_dir_count} correlated {signal_side} positions"
        
        return True, "All risk checks passed"
    
    def add_position(self, order_id: str, symbol: str, side: str, quantity: float,
                    entry_price: float, stop_loss: float, take_profit: float,
                    strategy: str):
        """Add a new open position"""
        position = Position(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy,
            entry_time=datetime.now()
        )
        
        self.open_positions[order_id] = position
        
        # Update counters
        today_stats = self._get_today_stats()
        today_stats.trades_executed += 1
        
        self.strategy_trade_count[strategy] = self.strategy_trade_count.get(strategy, 0) + 1
        self.last_trade_time = datetime.now()
        
        logger.info(f"Position added: {order_id} - {symbol} {side} {quantity} @ {entry_price}")
    
    def close_position(self, order_id: str, exit_price: float, reason: str = "Manual close"):
        """Close a position and update statistics"""
        if order_id not in self.open_positions:
            logger.warning(f"Attempted to close non-existent position: {order_id}")
            return
        
        position = self.open_positions[order_id]
        
        # Calculate P&L
        if position.side == 'buy':
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Update balance
        self.update_balance(self.current_balance + pnl)
        
        # Update statistics
        today_stats = self._get_today_stats()
        today_stats.total_pnl += pnl
        
        if pnl > 0:
            today_stats.winning_trades += 1
        else:
            today_stats.losing_trades += 1
        
        # Calculate drawdown
        drawdown = today_stats.peak_balance - self.current_balance
        if drawdown > today_stats.max_drawdown:
            today_stats.max_drawdown = drawdown
        
        logger.info(f"Position closed: {order_id} - P&L: €{pnl:.2f} - Reason: {reason}")
        
        # Remove from open positions
        del self.open_positions[order_id]
    
    def update_positions(self, current_prices: Dict[str, float]):
        """Update all open positions with current prices"""
        for order_id, position in self.open_positions.items():
            if position.symbol in current_prices:
                current_price = current_prices[position.symbol]
                position.update_pnl(current_price)
    
    def check_stop_loss_take_profit(self, current_prices: Dict[str, float]) -> List[str]:
        """
        Check if any positions hit stop loss or take profit
        Also applies trailing stop and break-even stop
        
        Returns:
            List of (order_id, exit_price, reason) to close
        """
        to_close = []
        
        for order_id, position in self.open_positions.items():
            if position.symbol not in current_prices:
                continue
            
            current_price = current_prices[position.symbol]
            
            # Apply break-even stop
            self._apply_break_even_stop(position, current_price)
            
            # Apply trailing stop
            self._apply_trailing_stop(position, current_price)
            
            if position.side == 'buy':
                if current_price <= position.stop_loss:
                    reason = "Trailing stop hit" if position.trailing_stop_active else "Stop loss hit"
                    to_close.append((order_id, current_price, reason))
                elif current_price >= position.take_profit:
                    to_close.append((order_id, current_price, "Take profit hit"))
            
            else:  # sell position
                if current_price >= position.stop_loss:
                    reason = "Trailing stop hit" if position.trailing_stop_active else "Stop loss hit"
                    to_close.append((order_id, current_price, reason))
                elif current_price <= position.take_profit:
                    to_close.append((order_id, current_price, "Take profit hit"))
        
        return to_close
    
    def _apply_break_even_stop(self, position: Position, current_price: float):
        """Move stop loss to entry price after reaching profit threshold"""
        if not getattr(self.config, 'ENABLE_BREAK_EVEN_STOP', False):
            return
        if position.break_even_applied:
            return
        
        activation = getattr(self.config, 'BREAK_EVEN_ACTIVATION_PERCENT', 0.4)
        offset_pips = getattr(self.config, 'BREAK_EVEN_OFFSET_PIPS', 2)
        pip_value = 0.0001 if 'JPY' not in position.symbol else 0.01
        
        if position.profit_percent >= activation:
            if position.side == 'buy':
                new_sl = position.entry_price + (offset_pips * pip_value)
                if new_sl > position.stop_loss:
                    position.stop_loss = new_sl
                    position.break_even_applied = True
                    logger.info(f"Break-even stop applied: {position.symbol} SL moved to {new_sl:.5f}")
            else:
                new_sl = position.entry_price - (offset_pips * pip_value)
                if new_sl < position.stop_loss:
                    position.stop_loss = new_sl
                    position.break_even_applied = True
                    logger.info(f"Break-even stop applied: {position.symbol} SL moved to {new_sl:.5f}")
    
    def _apply_trailing_stop(self, position: Position, current_price: float):
        """Trail stop loss behind price to lock in profits"""
        if not getattr(self.config, 'ENABLE_TRAILING_STOP', False):
            return
        
        activation = getattr(self.config, 'TRAILING_STOP_ACTIVATION_PERCENT', 0.5)
        distance = getattr(self.config, 'TRAILING_STOP_DISTANCE_PERCENT', 0.3)
        
        if position.profit_percent < activation:
            return
        
        position.trailing_stop_active = True
        
        if position.side == 'buy':
            trail_price = position.highest_price * (1 - distance / 100)
            if trail_price > position.stop_loss:
                old_sl = position.stop_loss
                position.stop_loss = trail_price
                logger.info(f"Trailing stop updated: {position.symbol} SL {old_sl:.5f} -> {trail_price:.5f}")
        else:
            trail_price = position.lowest_price * (1 + distance / 100)
            if trail_price < position.stop_loss:
                old_sl = position.stop_loss
                position.stop_loss = trail_price
                logger.info(f"Trailing stop updated: {position.symbol} SL {old_sl:.5f} -> {trail_price:.5f}")
    
    @staticmethod
    def get_current_session() -> str:
        """Determine current trading session"""
        hour = datetime.utcnow().hour
        
        if 0 <= hour < 7:
            return 'asian'
        elif 7 <= hour < 8:
            return 'london'  # London pre-market
        elif 8 <= hour < 12:
            return 'london'
        elif 12 <= hour < 16:
            return 'overlap'  # London/NY overlap
        elif 16 <= hour < 21:
            return 'newyork'
        else:
            return 'off_hours'
    
    def get_session_confidence_multiplier(self) -> float:
        """Get confidence multiplier based on current session"""
        session = self.get_current_session()
        multipliers = getattr(self.config, 'SESSION_MULTIPLIERS', {})
        return multipliers.get(session, 1.0)
    
    def get_adaptive_position_size(self, base_size: float, volatility: float) -> float:
        """Adjust position size based on market volatility"""
        if not getattr(self.config, 'ENABLE_ADAPTIVE_PARAMS', False):
            return base_size
        
        if volatility > 0.02:  # High volatility
            multiplier = getattr(self.config, 'HIGH_VOLATILITY_SIZE_MULTIPLIER', 0.7)
            logger.info(f"High volatility detected - position size reduced by {(1-multiplier)*100:.0f}%")
        elif volatility < 0.005:  # Low volatility
            multiplier = getattr(self.config, 'LOW_VOLATILITY_SIZE_MULTIPLIER', 1.2)
            logger.info(f"Low volatility detected - position size increased by {(multiplier-1)*100:.0f}%")
        else:
            multiplier = 1.0
        
        return round(base_size * multiplier, 4)
    
    def get_spread_adjusted_entry(self, entry_price: float, symbol: str, side: str) -> float:
        """Adjust entry price to account for spread"""
        spreads = getattr(self.config, 'ESTIMATED_SPREAD_PIPS', {})
        spread_pips = spreads.get(symbol, 1.5)
        pip_value = 0.0001 if 'JPY' not in symbol else 0.01
        
        spread = spread_pips * pip_value
        
        if side == 'buy':
            return entry_price + spread / 2
        else:
            return entry_price - spread / 2
    
    def activate_kill_switch(self, reason: str):
        """Activate emergency kill switch"""
        self.kill_switch_active = True
        logger.critical(f"🚨 KILL SWITCH ACTIVATED: {reason}")
        logger.critical("All trading has been stopped. Manual intervention required.")
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch (manual intervention required)"""
        self.kill_switch_active = False
        logger.warning("Kill switch deactivated - trading resumed")
    
    def get_risk_summary(self) -> Dict:
        """Get current risk status summary"""
        today_stats = self._get_today_stats()
        
        total_exposure = sum(
            pos.quantity * pos.entry_price 
            for pos in self.open_positions.values()
        )
        
        exposure_percent = (total_exposure / self.current_balance * 100) if self.current_balance > 0 else 0
        
        drawdown_percent = ((self.peak_balance - self.current_balance) / self.peak_balance * 100) if self.peak_balance > 0 else 0
        
        return {
            'current_balance': self.current_balance,
            'daily_pnl': today_stats.total_pnl,
            'daily_return_percent': today_stats.daily_return_percent,
            'open_positions': len(self.open_positions),
            'trades_today': today_stats.trades_executed,
            'win_rate': today_stats.win_rate,
            'total_exposure': total_exposure,
            'exposure_percent': exposure_percent,
            'drawdown_percent': drawdown_percent,
            'kill_switch_active': self.kill_switch_active,
            'daily_loss_limit_remaining': self.max_daily_loss_percent + today_stats.daily_return_percent,
            'trades_remaining_today': self.max_trades_per_day - today_stats.trades_executed
        }
    
    def export_daily_stats(self) -> str:
        """Export daily statistics to JSON"""
        stats_dict = {
            date: {
                'date': stats.date,
                'starting_balance': stats.starting_balance,
                'ending_balance': stats.current_balance,
                'trades': stats.trades_executed,
                'wins': stats.winning_trades,
                'losses': stats.losing_trades,
                'total_pnl': stats.total_pnl,
                'return_percent': stats.daily_return_percent,
                'win_rate': stats.win_rate,
                'max_drawdown': stats.max_drawdown
            }
            for date, stats in self.daily_stats.items()
        }
        
        return json.dumps(stats_dict, indent=2)
