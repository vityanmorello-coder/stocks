"""
Trading Strategies Implementation
Three conservative strategies focused on capital preservation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


@dataclass
class TradingSignal:
    """Trading signal with metadata"""
    signal_type: SignalType
    strategy: str
    symbol: str
    confidence: float  # 0.0 to 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    timestamp: str


class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, 
                      signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram"""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, 
                                 std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def find_support_resistance(data: pd.Series, window: int = 20) -> Tuple[float, float]:
        """Find recent support and resistance levels"""
        recent_data = data.tail(window)
        support = recent_data.min()
        resistance = recent_data.max()
        return support, resistance


class TrendFollowingStrategy:
    """
    Strategy 1: Trend Following with Moving Averages
    Conservative approach using multiple EMA confirmation
    """
    
    def __init__(self, config: Dict):
        self.name = "trend_following"
        self.ma_fast = config.get('MA_FAST', 20)
        self.ma_medium = config.get('MA_MEDIUM', 50)
        self.ma_slow = config.get('MA_SLOW', 200)
        self.tp_percent = config['STRATEGY_TP_SL'][self.name]['tp']
        self.sl_percent = config['STRATEGY_TP_SL'][self.name]['sl']
        
        logger.info(f"Initialized {self.name} strategy")
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze market data and generate signal
        
        Entry Rules:
        - BUY: Price crosses above 20 EMA AND 50 EMA > 200 EMA (strong uptrend)
        - SELL: Price crosses below 20 EMA AND 50 EMA < 200 EMA (strong downtrend)
        
        Exit Rules:
        - Price crosses back through 20 EMA
        - Take profit or stop loss hit
        """
        if len(df) < self.ma_slow:
            return None
        
        close = df['close']
        
        ema_20 = TechnicalIndicators.calculate_ema(close, self.ma_fast)
        ema_50 = TechnicalIndicators.calculate_ema(close, self.ma_medium)
        ema_200 = TechnicalIndicators.calculate_ema(close, self.ma_slow)
        
        current_price = close.iloc[-1]
        prev_price = close.iloc[-2]
        
        current_ema20 = ema_20.iloc[-1]
        prev_ema20 = ema_20.iloc[-2]
        current_ema50 = ema_50.iloc[-1]
        current_ema200 = ema_200.iloc[-1]
        
        # Check for bullish crossover
        if (prev_price <= prev_ema20 and current_price > current_ema20 and 
            current_ema50 > current_ema200):
            
            stop_loss = current_price * (1 - self.sl_percent / 100)
            take_profit = current_price * (1 + self.tp_percent / 100)
            
            confidence = min(
                (current_ema50 - current_ema200) / current_ema200 * 100,
                1.0
            )
            
            return TradingSignal(
                signal_type=SignalType.BUY,
                strategy=self.name,
                symbol=symbol,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Price crossed above 20 EMA, 50 EMA > 200 EMA (uptrend)",
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        # Check for bearish crossover
        elif (prev_price >= prev_ema20 and current_price < current_ema20 and 
              current_ema50 < current_ema200):
            
            stop_loss = current_price * (1 + self.sl_percent / 100)
            take_profit = current_price * (1 - self.tp_percent / 100)
            
            confidence = min(
                (current_ema200 - current_ema50) / current_ema200 * 100,
                1.0
            )
            
            return TradingSignal(
                signal_type=SignalType.SELL,
                strategy=self.name,
                symbol=symbol,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Price crossed below 20 EMA, 50 EMA < 200 EMA (downtrend)",
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        return None


class RSIMeanReversionStrategy:
    """
    Strategy 2: RSI Mean Reversion
    Buy oversold conditions, sell overbought conditions
    """
    
    def __init__(self, config: Dict):
        self.name = "rsi_mean_reversion"
        self.rsi_period = config.get('RSI_PERIOD', 14)
        self.rsi_oversold = config.get('RSI_OVERSOLD', 30)
        self.rsi_overbought = config.get('RSI_OVERBOUGHT', 70)
        self.rsi_neutral = config.get('RSI_NEUTRAL', 50)
        self.tp_percent = config['STRATEGY_TP_SL'][self.name]['tp']
        self.sl_percent = config['STRATEGY_TP_SL'][self.name]['sl']
        
        logger.info(f"Initialized {self.name} strategy")
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze market data and generate signal
        
        Entry Rules:
        - BUY: RSI < 30 (oversold) AND price near support
        - SELL: RSI > 70 (overbought) AND price near resistance
        
        Exit Rules:
        - RSI crosses back to neutral (50)
        - Take profit or stop loss hit
        """
        if len(df) < self.rsi_period + 20:
            return None
        
        close = df['close']
        rsi = TechnicalIndicators.calculate_rsi(close, self.rsi_period)
        support, resistance = TechnicalIndicators.find_support_resistance(close)
        
        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        # Check for oversold condition (buy signal)
        if current_rsi < self.rsi_oversold and prev_rsi >= self.rsi_oversold:
            # Additional confirmation: price near support
            if current_price <= support * 1.01:  # Within 1% of support
                
                stop_loss = current_price * (1 - self.sl_percent / 100)
                take_profit = current_price * (1 + self.tp_percent / 100)
                
                confidence = (self.rsi_oversold - current_rsi) / self.rsi_oversold
                
                return TradingSignal(
                    signal_type=SignalType.BUY,
                    strategy=self.name,
                    symbol=symbol,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason=f"RSI oversold ({current_rsi:.1f}) near support",
                    timestamp=pd.Timestamp.now().isoformat()
                )
        
        # Check for overbought condition (sell signal)
        elif current_rsi > self.rsi_overbought and prev_rsi <= self.rsi_overbought:
            # Additional confirmation: price near resistance
            if current_price >= resistance * 0.99:  # Within 1% of resistance
                
                stop_loss = current_price * (1 + self.sl_percent / 100)
                take_profit = current_price * (1 - self.tp_percent / 100)
                
                confidence = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
                
                return TradingSignal(
                    signal_type=SignalType.SELL,
                    strategy=self.name,
                    symbol=symbol,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason=f"RSI overbought ({current_rsi:.1f}) near resistance",
                    timestamp=pd.Timestamp.now().isoformat()
                )
        
        return None


class MACDMomentumStrategy:
    """
    Strategy 3: MACD Momentum
    Trade momentum shifts with MACD crossovers
    """
    
    def __init__(self, config: Dict):
        self.name = "macd_momentum"
        self.macd_fast = config.get('MACD_FAST', 12)
        self.macd_slow = config.get('MACD_SLOW', 26)
        self.macd_signal = config.get('MACD_SIGNAL', 9)
        self.tp_percent = config['STRATEGY_TP_SL'][self.name]['tp']
        self.sl_percent = config['STRATEGY_TP_SL'][self.name]['sl']
        
        logger.info(f"Initialized {self.name} strategy")
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze market data and generate signal
        
        Entry Rules:
        - BUY: MACD crosses above signal line AND histogram increasing
        - SELL: MACD crosses below signal line AND histogram decreasing
        
        Exit Rules:
        - MACD crosses back
        - Take profit or stop loss hit
        """
        if len(df) < self.macd_slow + self.macd_signal:
            return None
        
        close = df['close']
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(
            close, self.macd_fast, self.macd_slow, self.macd_signal
        )
        
        current_price = close.iloc[-1]
        
        current_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        current_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        
        # Check for bullish crossover
        if (prev_macd <= prev_signal and current_macd > current_signal and 
            current_hist > prev_hist):
            
            stop_loss = current_price * (1 - self.sl_percent / 100)
            take_profit = current_price * (1 + self.tp_percent / 100)
            
            confidence = min(abs(current_hist) / abs(current_macd) if current_macd != 0 else 0, 1.0)
            
            return TradingSignal(
                signal_type=SignalType.BUY,
                strategy=self.name,
                symbol=symbol,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"MACD bullish crossover, histogram increasing",
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        # Check for bearish crossover
        elif (prev_macd >= prev_signal and current_macd < current_signal and 
              current_hist < prev_hist):
            
            stop_loss = current_price * (1 + self.sl_percent / 100)
            take_profit = current_price * (1 - self.tp_percent / 100)
            
            confidence = min(abs(current_hist) / abs(current_macd) if current_macd != 0 else 0, 1.0)
            
            return TradingSignal(
                signal_type=SignalType.SELL,
                strategy=self.name,
                symbol=symbol,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"MACD bearish crossover, histogram decreasing",
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        return None


class StrategyManager:
    """Manage multiple trading strategies"""
    
    def __init__(self, config):
        self.config = config
        self.strategies = []
        
        if config.STRATEGIES_ENABLED.get('trend_following'):
            self.strategies.append(TrendFollowingStrategy(config.__dict__))
        
        if config.STRATEGIES_ENABLED.get('rsi_mean_reversion'):
            self.strategies.append(RSIMeanReversionStrategy(config.__dict__))
        
        if config.STRATEGIES_ENABLED.get('macd_momentum'):
            self.strategies.append(MACDMomentumStrategy(config.__dict__))
        
        logger.info(f"Strategy Manager initialized with {len(self.strategies)} strategies")
    
    def get_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Get trading signals from all strategies
        
        Args:
            market_data: Dict of {symbol: DataFrame} with OHLCV data
        
        Returns:
            List of trading signals
        """
        signals = []
        
        for symbol, df in market_data.items():
            for strategy in self.strategies:
                try:
                    signal = strategy.analyze(df, symbol)
                    if signal:
                        signals.append(signal)
                        logger.info(f"Signal generated: {signal}")
                except Exception as e:
                    logger.error(f"Error in {strategy.name} for {symbol}: {e}")
        
        return signals
    
    def filter_signals(self, signals: List[TradingSignal], 
                      min_confidence: float = 0.3) -> List[TradingSignal]:
        """Filter signals by confidence threshold"""
        filtered = [s for s in signals if s.confidence >= min_confidence]
        logger.info(f"Filtered {len(signals)} signals to {len(filtered)} (min confidence: {min_confidence})")
        return filtered
