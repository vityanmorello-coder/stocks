"""
ExecutionEngine v1.0 - Professional Automated Trade Execution
Handles broker API integration, smart order placement, and fail-safes.

Architecture:
1. BrokerInterface (abstract) - Swappable broker backends
2. PaperBroker - Paper trading simulator
3. MT5Broker - MetaTrader 5 integration (optional)
4. SmartOrderRouter - Decides limit vs market, handles slippage
5. PositionSizer - Confidence-based position sizing
6. ExecutionManager - Orchestrates everything with retry/error handling/kill switch

Data Flow:
Signal → QuantumScorer → AdaptiveLearner → PositionSizer → SmartOrderRouter → BrokerInterface
"""

import time
import logging
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading

logger = logging.getLogger(__name__)


# ============================================================
# DATA TYPES
# ============================================================

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class OrderRequest:
    """Request to place an order"""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence: float = 0.5
    strategy: str = ""
    comment: str = ""
    max_slippage_pips: float = 3.0


@dataclass
class OrderResult:
    """Result of an order execution"""
    success: bool = False
    order_id: str = ""
    fill_price: float = 0.0
    fill_quantity: float = 0.0
    slippage: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    error_message: str = ""
    execution_time_ms: float = 0.0
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'order_id': self.order_id,
            'fill_price': self.fill_price,
            'fill_quantity': self.fill_quantity,
            'slippage': round(self.slippage, 5),
            'status': self.status.value,
            'error': self.error_message,
            'exec_time_ms': round(self.execution_time_ms, 1),
            'timestamp': self.timestamp,
        }


@dataclass
class ExecutionStats:
    """Track execution quality"""
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    total_slippage: float = 0.0
    avg_execution_time_ms: float = 0.0
    retry_count: int = 0
    kill_switch_activations: int = 0


# ============================================================
# BROKER INTERFACE (ABSTRACT)
# ============================================================

class BrokerInterface(ABC):
    """Abstract broker interface - implement for each broker"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to broker"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from broker"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected"""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Tuple[float, float]:
        """Get current bid/ask prices"""
        pass
    
    @abstractmethod
    def place_market_order(self, symbol: str, side: str, quantity: float,
                           stop_loss: float, take_profit: float,
                           comment: str = "") -> OrderResult:
        """Place a market order"""
        pass
    
    @abstractmethod
    def place_limit_order(self, symbol: str, side: str, quantity: float,
                          price: float, stop_loss: float, take_profit: float,
                          comment: str = "") -> OrderResult:
        """Place a limit order"""
        pass
    
    @abstractmethod
    def modify_order(self, order_id: str, stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None) -> bool:
        """Modify an existing order's SL/TP"""
        pass
    
    @abstractmethod
    def close_position(self, order_id: str) -> OrderResult:
        """Close an open position"""
        pass
    
    @abstractmethod
    def get_open_positions(self) -> List[dict]:
        """Get all open positions"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> dict:
        """Get account balance/equity info"""
        pass


# ============================================================
# PAPER BROKER (SIMULATION)
# ============================================================

class PaperBroker(BrokerInterface):
    """Paper trading broker for testing"""
    
    def __init__(self, initial_balance: float = 100.0):
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions: Dict[str, dict] = {}
        self.trade_history: List[dict] = []
        self.connected = True
        self._order_counter = 0
        
        # Simulated latency and slippage
        self.latency_ms = 50  # 50ms simulated
        self.slippage_pips = 0.5
    
    def connect(self) -> bool:
        self.connected = True
        return True
    
    def disconnect(self):
        self.connected = False
    
    def is_connected(self) -> bool:
        return self.connected
    
    def get_current_price(self, symbol: str) -> Tuple[float, float]:
        """Get simulated current price"""
        import random
        
        # Use FortradeAPIClient prices if available
        try:
            from fortrade_api_client import FortradeAPIClient
            info = FortradeAPIClient.INSTRUMENT_PRICES.get(
                symbol, {'price': 1.0, 'volatility': 0.001}
            )
            base = info['price']
            vol = info['volatility']
            spread = vol * 0.1
            bid = base + random.uniform(-vol * 0.1, vol * 0.1)
            ask = bid + spread
            return bid, ask
        except:
            return 1.0850, 1.0852
    
    def place_market_order(self, symbol: str, side: str, quantity: float,
                           stop_loss: float, take_profit: float,
                           comment: str = "") -> OrderResult:
        import random
        
        start = time.time()
        time.sleep(self.latency_ms / 1000)  # Simulate latency
        
        bid, ask = self.get_current_price(symbol)
        
        # Apply slippage
        slippage = random.uniform(0, self.slippage_pips) * 0.0001
        if side == 'buy':
            fill_price = ask + slippage
        else:
            fill_price = bid - slippage
        
        self._order_counter += 1
        order_id = f"PAPER_{self._order_counter}_{int(time.time())}"
        
        self.positions[order_id] = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': fill_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'open_time': datetime.now().isoformat(),
            'comment': comment,
        }
        
        exec_time = (time.time() - start) * 1000
        
        result = OrderResult(
            success=True,
            order_id=order_id,
            fill_price=fill_price,
            fill_quantity=quantity,
            slippage=slippage,
            status=OrderStatus.FILLED,
            execution_time_ms=exec_time,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Paper {side.upper()} {symbol} @ {fill_price:.5f} qty={quantity:.4f} SL={stop_loss:.5f} TP={take_profit:.5f}")
        return result
    
    def place_limit_order(self, symbol: str, side: str, quantity: float,
                          price: float, stop_loss: float, take_profit: float,
                          comment: str = "") -> OrderResult:
        # For paper trading, just fill at limit price
        self._order_counter += 1
        order_id = f"PAPER_LMT_{self._order_counter}_{int(time.time())}"
        
        self.positions[order_id] = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'open_time': datetime.now().isoformat(),
            'comment': comment,
            'order_type': 'limit'
        }
        
        return OrderResult(
            success=True,
            order_id=order_id,
            fill_price=price,
            fill_quantity=quantity,
            slippage=0.0,
            status=OrderStatus.FILLED,
            timestamp=datetime.now().isoformat()
        )
    
    def modify_order(self, order_id: str, stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None) -> bool:
        if order_id in self.positions:
            if stop_loss is not None:
                self.positions[order_id]['stop_loss'] = stop_loss
            if take_profit is not None:
                self.positions[order_id]['take_profit'] = take_profit
            return True
        return False
    
    def close_position(self, order_id: str) -> OrderResult:
        if order_id in self.positions:
            pos = self.positions.pop(order_id)
            bid, ask = self.get_current_price(pos['symbol'])
            close_price = bid if pos['side'] == 'buy' else ask
            
            if pos['side'] == 'buy':
                pnl = (close_price - pos['entry_price']) * pos['quantity']
            else:
                pnl = (pos['entry_price'] - close_price) * pos['quantity']
            
            self.balance += pnl
            self.equity = self.balance
            
            pos['close_price'] = close_price
            pos['pnl'] = pnl
            pos['close_time'] = datetime.now().isoformat()
            self.trade_history.append(pos)
            
            return OrderResult(
                success=True,
                order_id=order_id,
                fill_price=close_price,
                status=OrderStatus.FILLED,
                timestamp=datetime.now().isoformat()
            )
        
        return OrderResult(success=False, error_message="Position not found")
    
    def get_open_positions(self) -> List[dict]:
        return list(self.positions.values())
    
    def get_account_info(self) -> dict:
        return {
            'balance': self.balance,
            'equity': self.equity,
            'margin_used': 0.0,
            'margin_free': self.balance,
            'currency': 'EUR'
        }


# ============================================================
# MT5 BROKER (METATRADER 5)
# ============================================================

class MT5Broker(BrokerInterface):
    """
    MetaTrader 5 broker integration.
    Requires: pip install MetaTrader5
    """
    
    def __init__(self, login: int = 0, password: str = "", server: str = ""):
        self.login = login
        self.password = password
        self.server = server
        self._connected = False
        self.mt5 = None
    
    def connect(self) -> bool:
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            
            if not mt5.initialize():
                logger.error(f"MT5 init failed: {mt5.last_error()}")
                return False
            
            if self.login:
                authorized = mt5.login(self.login, password=self.password, server=self.server)
                if not authorized:
                    logger.error(f"MT5 login failed: {mt5.last_error()}")
                    return False
            
            self._connected = True
            info = mt5.account_info()
            logger.info(f"Connected to MT5: {info.server}, Balance: {info.balance}")
            return True
            
        except ImportError:
            logger.error("MetaTrader5 package not installed. pip install MetaTrader5")
            return False
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False
    
    def disconnect(self):
        if self.mt5:
            self.mt5.shutdown()
        self._connected = False
    
    def is_connected(self) -> bool:
        if not self._connected or not self.mt5:
            return False
        try:
            info = self.mt5.terminal_info()
            return info is not None and info.connected
        except:
            return False
    
    def get_current_price(self, symbol: str) -> Tuple[float, float]:
        if not self.mt5:
            return 0.0, 0.0
        tick = self.mt5.symbol_info_tick(symbol)
        if tick:
            return tick.bid, tick.ask
        return 0.0, 0.0
    
    def place_market_order(self, symbol: str, side: str, quantity: float,
                           stop_loss: float, take_profit: float,
                           comment: str = "") -> OrderResult:
        if not self.mt5:
            return OrderResult(success=False, error_message="MT5 not connected")
        
        start = time.time()
        mt5 = self.mt5
        
        order_type = mt5.ORDER_TYPE_BUY if side == 'buy' else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if side == 'buy' else tick.bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": quantity,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 10,  # Max slippage in points
            "magic": 123456,
            "comment": comment or "QuantumTrade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        exec_time = (time.time() - start) * 1000
        
        if result is None:
            return OrderResult(
                success=False,
                error_message=f"MT5 error: {mt5.last_error()}",
                execution_time_ms=exec_time
            )
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                error_message=f"MT5 rejected: {result.comment} (code: {result.retcode})",
                execution_time_ms=exec_time
            )
        
        slippage = abs(result.price - price) if result.price else 0
        
        return OrderResult(
            success=True,
            order_id=str(result.order),
            fill_price=result.price,
            fill_quantity=result.volume,
            slippage=slippage,
            status=OrderStatus.FILLED,
            execution_time_ms=exec_time,
            timestamp=datetime.now().isoformat()
        )
    
    def place_limit_order(self, symbol: str, side: str, quantity: float,
                          price: float, stop_loss: float, take_profit: float,
                          comment: str = "") -> OrderResult:
        if not self.mt5:
            return OrderResult(success=False, error_message="MT5 not connected")
        
        mt5 = self.mt5
        order_type = mt5.ORDER_TYPE_BUY_LIMIT if side == 'buy' else mt5.ORDER_TYPE_SELL_LIMIT
        
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": quantity,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 5,
            "magic": 123456,
            "comment": comment or "QuantumTrade_Limit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=True,
                order_id=str(result.order),
                fill_price=price,
                fill_quantity=quantity,
                status=OrderStatus.PENDING,
                timestamp=datetime.now().isoformat()
            )
        
        return OrderResult(
            success=False,
            error_message=f"Limit order failed: {result.comment if result else 'No response'}"
        )
    
    def modify_order(self, order_id: str, stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None) -> bool:
        if not self.mt5:
            return False
        
        mt5 = self.mt5
        position_id = int(order_id)
        
        # Get current position info
        positions = mt5.positions_get(ticket=position_id)
        if not positions:
            return False
        
        pos = positions[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position_id,
            "symbol": pos.symbol,
            "sl": stop_loss if stop_loss is not None else pos.sl,
            "tp": take_profit if take_profit is not None else pos.tp,
        }
        
        result = mt5.order_send(request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
    
    def close_position(self, order_id: str) -> OrderResult:
        if not self.mt5:
            return OrderResult(success=False, error_message="MT5 not connected")
        
        mt5 = self.mt5
        position_id = int(order_id)
        
        positions = mt5.positions_get(ticket=position_id)
        if not positions:
            return OrderResult(success=False, error_message="Position not found")
        
        pos = positions[0]
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": position_id,
            "price": price,
            "deviation": 10,
            "magic": 123456,
            "comment": "QuantumTrade_Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=True,
                order_id=str(result.order),
                fill_price=result.price,
                status=OrderStatus.FILLED,
                timestamp=datetime.now().isoformat()
            )
        
        return OrderResult(success=False, error_message=f"Close failed: {result.comment if result else 'No response'}")
    
    def get_open_positions(self) -> List[dict]:
        if not self.mt5:
            return []
        
        positions = self.mt5.positions_get()
        if not positions:
            return []
        
        return [{
            'order_id': str(p.ticket),
            'symbol': p.symbol,
            'side': 'buy' if p.type == 0 else 'sell',
            'quantity': p.volume,
            'entry_price': p.price_open,
            'current_price': p.price_current,
            'stop_loss': p.sl,
            'take_profit': p.tp,
            'pnl': p.profit,
            'comment': p.comment,
        } for p in positions]
    
    def get_account_info(self) -> dict:
        if not self.mt5:
            return {}
        
        info = self.mt5.account_info()
        if not info:
            return {}
        
        return {
            'balance': info.balance,
            'equity': info.equity,
            'margin_used': info.margin,
            'margin_free': info.margin_free,
            'currency': info.currency,
            'server': info.server,
            'name': info.name,
        }


# ============================================================
# SMART ORDER ROUTER
# ============================================================

class SmartOrderRouter:
    """
    Decides how to place orders for best execution.
    - Chooses limit vs market based on volatility and urgency
    - Calculates optimal limit price
    - Handles slippage protection
    """
    
    # If price is within this many ATRs of a key level, use limit order
    LIMIT_ORDER_THRESHOLD_ATR = 0.3
    
    # Maximum acceptable slippage in ATR units
    MAX_SLIPPAGE_ATR = 0.5
    
    def decide_order_type(self, current_bid: float, current_ask: float,
                          signal_type: str, confidence: float,
                          atr: float, regime: str,
                          key_levels: List[float] = None) -> Tuple[OrderType, Optional[float]]:
        """
        Decide whether to use market or limit order.
        
        Returns:
            (order_type, limit_price_or_None)
        """
        spread = current_ask - current_bid
        
        # High confidence + trending = market order (don't miss the move)
        if confidence > 0.75 and regime == 'trending':
            return OrderType.MARKET, None
        
        # Very high confidence = always market
        if confidence > 0.85:
            return OrderType.MARKET, None
        
        # In volatile markets, use limit orders to avoid slippage
        if regime == 'volatile' and confidence < 0.75:
            if signal_type == 'buy':
                # Try to get filled at bid instead of ask
                limit_price = current_bid + spread * 0.3
            else:
                limit_price = current_ask - spread * 0.3
            return OrderType.LIMIT, limit_price
        
        # Near key levels, use limit orders
        if key_levels and atr > 0:
            price = current_ask if signal_type == 'buy' else current_bid
            for level in key_levels:
                if abs(price - level) < atr * self.LIMIT_ORDER_THRESHOLD_ATR:
                    # Place limit at the key level
                    if signal_type == 'buy' and level < price:
                        return OrderType.LIMIT, level
                    elif signal_type == 'sell' and level > price:
                        return OrderType.LIMIT, level
        
        # Default: market order for moderate+ confidence
        if confidence >= 0.55:
            return OrderType.MARKET, None
        
        # Low confidence: limit order with improvement
        if signal_type == 'buy':
            limit_price = current_bid + spread * 0.2
        else:
            limit_price = current_ask - spread * 0.2
        
        return OrderType.LIMIT, limit_price
    
    def check_slippage(self, expected_price: float, fill_price: float,
                       atr: float) -> Tuple[bool, float]:
        """
        Check if slippage is acceptable.
        Returns (acceptable, slippage_in_atr_units)
        """
        if atr == 0:
            return True, 0.0
        
        slippage = abs(fill_price - expected_price)
        slippage_atr = slippage / atr
        
        acceptable = slippage_atr <= self.MAX_SLIPPAGE_ATR
        return acceptable, slippage_atr


# ============================================================
# POSITION SIZER
# ============================================================

class PositionSizer:
    """
    Calculate position size based on confidence, risk, and account state.
    """
    
    def calculate(self, account_balance: float, risk_percent: float,
                  entry_price: float, stop_loss: float,
                  confidence: float, pip_value: float = 0.0001) -> float:
        """
        Calculate optimal position size.
        
        Args:
            account_balance: Current account balance
            risk_percent: Max risk per trade (e.g., 1.0 for 1%)
            entry_price: Entry price
            stop_loss: Stop loss price
            confidence: Signal confidence (0-1)
            pip_value: Value per pip for this instrument
        
        Returns:
            Position size (lots/units)
        """
        # Risk amount in account currency
        risk_amount = account_balance * (risk_percent / 100.0)
        
        # Distance to SL
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance == 0:
            return 0.0
        
        # Base position size
        if pip_value > 0:
            sl_pips = sl_distance / pip_value
            base_size = risk_amount / (sl_pips * 10)  # Assuming standard lot
        else:
            base_size = risk_amount / sl_distance
        
        # Apply confidence multiplier
        # 0.85+ = full size, 0.50 = half size, below 0.40 = no trade
        if confidence >= 0.85:
            conf_mult = 1.0
        elif confidence >= 0.70:
            conf_mult = 0.75
        elif confidence >= 0.55:
            conf_mult = 0.50
        elif confidence >= 0.45:
            conf_mult = 0.25
        else:
            conf_mult = 0.0  # Don't trade
        
        final_size = base_size * conf_mult
        
        # Apply minimum and maximum
        min_size = 0.01  # Minimum 0.01 lot
        max_size = account_balance * 0.1 / entry_price  # Max 10% of account
        
        final_size = max(min_size, min(max_size, final_size))
        
        return round(final_size, 4)


# ============================================================
# EXECUTION MANAGER (MAIN ORCHESTRATOR)
# ============================================================

class ExecutionManager:
    """
    Main execution orchestrator with retry logic, error handling, and kill switch.
    
    Usage:
        em = ExecutionManager(broker=PaperBroker())
        result = em.execute_signal(order_request)
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY_SEC = 1.0
    MAX_ORDERS_PER_MINUTE = 5
    COOLDOWN_AFTER_ERROR_SEC = 30
    
    def __init__(self, broker: BrokerInterface = None):
        self.broker = broker or PaperBroker()
        self.router = SmartOrderRouter()
        self.sizer = PositionSizer()
        self.stats = ExecutionStats()
        self.execution_log: List[dict] = []
        
        # Safety
        self.kill_switch = False
        self.last_error_time: Optional[datetime] = None
        self.orders_this_minute: List[datetime] = []
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        self._load_log()
    
    def _load_log(self):
        try:
            if os.path.exists('execution_log.json'):
                with open('execution_log.json', 'r') as f:
                    self.execution_log = json.load(f)
        except:
            self.execution_log = []
    
    def _save_log(self):
        try:
            with open('execution_log.json', 'w') as f:
                json.dump(self.execution_log[-500:], f, indent=2)
        except:
            pass
    
    def activate_kill_switch(self, reason: str = "Manual"):
        """Emergency stop all trading"""
        self.kill_switch = True
        self.stats.kill_switch_activations += 1
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
        
        # Close all positions
        try:
            positions = self.broker.get_open_positions()
            for pos in positions:
                self.broker.close_position(pos['order_id'])
                logger.warning(f"Emergency closed: {pos['order_id']}")
        except Exception as e:
            logger.error(f"Error closing positions during kill switch: {e}")
    
    def deactivate_kill_switch(self):
        """Re-enable trading"""
        self.kill_switch = False
        logger.info("Kill switch deactivated")
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        # Remove orders older than 1 minute
        self.orders_this_minute = [
            t for t in self.orders_this_minute 
            if (now - t).total_seconds() < 60
        ]
        return len(self.orders_this_minute) < self.MAX_ORDERS_PER_MINUTE
    
    def _check_cooldown(self) -> bool:
        """Check if we're in error cooldown"""
        if self.last_error_time is None:
            return True
        elapsed = (datetime.now() - self.last_error_time).total_seconds()
        return elapsed >= self.COOLDOWN_AFTER_ERROR_SEC
    
    def execute_signal(self, request: OrderRequest, atr: float = 0.0,
                       regime: str = 'normal',
                       key_levels: List[float] = None) -> OrderResult:
        """
        Execute a trading signal with full safety checks.
        
        Args:
            request: OrderRequest with all trade details
            atr: Current ATR for the instrument
            regime: Market regime for smart routing
            key_levels: Key price levels for limit order placement
        
        Returns:
            OrderResult with execution details
        """
        with self._lock:
            # Safety checks
            if self.kill_switch:
                return OrderResult(success=False, error_message="Kill switch is active")
            
            if not self.broker.is_connected():
                logger.warning("Broker not connected, attempting reconnect...")
                if not self.broker.connect():
                    return OrderResult(success=False, error_message="Broker connection failed")
            
            if not self._check_rate_limit():
                return OrderResult(success=False, error_message="Rate limit exceeded")
            
            if not self._check_cooldown():
                remaining = self.COOLDOWN_AFTER_ERROR_SEC - (datetime.now() - self.last_error_time).total_seconds()
                return OrderResult(success=False, error_message=f"Error cooldown ({remaining:.0f}s remaining)")
            
            # Get current price
            bid, ask = self.broker.get_current_price(request.symbol)
            if bid == 0 or ask == 0:
                return OrderResult(success=False, error_message="Could not get current price")
            
            # Smart order routing
            order_type, limit_price = self.router.decide_order_type(
                bid, ask, request.side, request.confidence,
                atr, regime, key_levels
            )
            
            # Execute with retry
            result = self._execute_with_retry(request, order_type, limit_price, atr)
            
            # Record
            self.orders_this_minute.append(datetime.now())
            self.stats.total_orders += 1
            
            if result.success:
                self.stats.successful_orders += 1
                self.stats.total_slippage += abs(result.slippage)
                
                # Update running average execution time
                n = self.stats.successful_orders
                self.stats.avg_execution_time_ms = (
                    self.stats.avg_execution_time_ms * (n-1) + result.execution_time_ms
                ) / n
            else:
                self.stats.failed_orders += 1
                self.last_error_time = datetime.now()
            
            # Log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': request.symbol,
                'side': request.side,
                'order_type': order_type.value,
                'confidence': request.confidence,
                'result': result.to_dict()
            }
            self.execution_log.append(log_entry)
            self._save_log()
            
            return result
    
    def _execute_with_retry(self, request: OrderRequest, 
                             order_type: OrderType,
                             limit_price: Optional[float],
                             atr: float) -> OrderResult:
        """Execute order with retry logic"""
        last_error = ""
        
        for attempt in range(self.MAX_RETRIES):
            try:
                if order_type == OrderType.LIMIT and limit_price:
                    result = self.broker.place_limit_order(
                        symbol=request.symbol,
                        side=request.side,
                        quantity=request.quantity,
                        price=limit_price,
                        stop_loss=request.stop_loss,
                        take_profit=request.take_profit,
                        comment=request.comment or f"QT_{request.strategy}"
                    )
                else:
                    result = self.broker.place_market_order(
                        symbol=request.symbol,
                        side=request.side,
                        quantity=request.quantity,
                        stop_loss=request.stop_loss,
                        take_profit=request.take_profit,
                        comment=request.comment or f"QT_{request.strategy}"
                    )
                
                if result.success:
                    # Check slippage
                    if atr > 0 and result.slippage > 0:
                        acceptable, slip_atr = self.router.check_slippage(
                            limit_price or (request.limit_price or result.fill_price),
                            result.fill_price, atr
                        )
                        if not acceptable:
                            logger.warning(
                                f"High slippage on {request.symbol}: "
                                f"{slip_atr:.2f} ATR units"
                            )
                    
                    return result
                
                last_error = result.error_message
                logger.warning(f"Order attempt {attempt+1} failed: {last_error}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Order attempt {attempt+1} exception: {e}")
            
            if attempt < self.MAX_RETRIES - 1:
                self.stats.retry_count += 1
                time.sleep(self.RETRY_DELAY_SEC * (attempt + 1))
        
        return OrderResult(
            success=False,
            error_message=f"Failed after {self.MAX_RETRIES} attempts: {last_error}",
            status=OrderStatus.ERROR
        )
    
    def get_execution_stats(self) -> dict:
        """Get execution quality metrics"""
        return {
            'total_orders': self.stats.total_orders,
            'success_rate': round(
                self.stats.successful_orders / max(self.stats.total_orders, 1), 3
            ),
            'avg_slippage': round(
                self.stats.total_slippage / max(self.stats.successful_orders, 1), 6
            ),
            'avg_exec_time_ms': round(self.stats.avg_execution_time_ms, 1),
            'total_retries': self.stats.retry_count,
            'kill_switch_active': self.kill_switch,
            'kill_switch_activations': self.stats.kill_switch_activations,
            'broker_connected': self.broker.is_connected(),
            'broker_type': type(self.broker).__name__,
        }
