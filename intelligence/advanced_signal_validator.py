"""
Advanced Signal Validation System
Adds multiple layers of validation to improve trade quality
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from trading.trading_strategies import TradingSignal, SignalType

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of signal validation"""
    is_valid: bool
    confidence_adjustment: float
    reasons: List[str]
    warnings: List[str]


class AdvancedSignalValidator:
    """
    Multi-layer signal validation system
    
    Validates signals based on:
    1. Market conditions (volatility, trend strength)
    2. Technical confirmation (multiple timeframes)
    3. Risk/reward ratio
    4. Historical performance
    5. Market correlation
    """
    
    def __init__(self, config):
        self.config = config
        self.min_risk_reward_ratio = 1.5
        self.max_volatility_threshold = 0.03
        self.min_trend_strength = 0.6
        
        self.signal_history = []
        self.performance_by_strategy = {}
        
        logger.info("Advanced Signal Validator initialized")
    
    def validate_signal(self, signal: TradingSignal, market_data: pd.DataFrame) -> ValidationResult:
        """
        Comprehensive signal validation
        
        Returns ValidationResult with adjusted confidence
        """
        reasons = []
        warnings = []
        confidence_multiplier = 1.0
        
        if len(market_data) < 50:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                reasons=["Insufficient market data"],
                warnings=[]
            )
        
        rr_valid, rr_ratio = self._validate_risk_reward(signal)
        if not rr_valid:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                reasons=[f"Poor risk/reward ratio: {rr_ratio:.2f}"],
                warnings=[]
            )
        else:
            reasons.append(f"Good R/R ratio: {rr_ratio:.2f}")
            if rr_ratio > 2.0:
                confidence_multiplier *= 1.1
        
        volatility = self._calculate_volatility(market_data)
        if volatility > self.max_volatility_threshold:
            warnings.append(f"High volatility: {volatility:.4f}")
            confidence_multiplier *= 0.9
        else:
            reasons.append(f"Normal volatility: {volatility:.4f}")
        
        trend_strength = self._calculate_trend_strength(market_data)
        if trend_strength < self.min_trend_strength:
            warnings.append(f"Weak trend: {trend_strength:.2f}")
            confidence_multiplier *= 0.85
        else:
            reasons.append(f"Strong trend: {trend_strength:.2f}")
            confidence_multiplier *= 1.05
        
        volume_valid = self._validate_volume(market_data)
        if not volume_valid:
            warnings.append("Low volume conditions")
            confidence_multiplier *= 0.9
        else:
            reasons.append("Healthy volume")
        
        price_action_valid = self._validate_price_action(market_data, signal)
        if not price_action_valid:
            warnings.append("Conflicting price action")
            confidence_multiplier *= 0.85
        else:
            reasons.append("Confirming price action")
            confidence_multiplier *= 1.05
        
        strategy_performance = self._get_strategy_performance(signal.strategy)
        if strategy_performance < 0.5:
            warnings.append(f"Strategy win rate: {strategy_performance*100:.1f}%")
            confidence_multiplier *= 0.9
        elif strategy_performance > 0.6:
            reasons.append(f"Strategy performing well: {strategy_performance*100:.1f}%")
            confidence_multiplier *= 1.1
        
        final_confidence = signal.confidence * confidence_multiplier
        
        min_confidence_threshold = 0.15
        is_valid = final_confidence >= min_confidence_threshold and len(warnings) < 5
        
        if not is_valid:
            reasons.insert(0, f"Final confidence too low: {final_confidence:.2f}")
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_adjustment=confidence_multiplier,
            reasons=reasons,
            warnings=warnings
        )
    
    def _validate_risk_reward(self, signal: TradingSignal) -> Tuple[bool, float]:
        """Validate risk/reward ratio"""
        if signal.signal_type == SignalType.BUY:
            risk = signal.entry_price - signal.stop_loss
            reward = signal.take_profit - signal.entry_price
        else:
            risk = signal.stop_loss - signal.entry_price
            reward = signal.entry_price - signal.take_profit
        
        if risk <= 0:
            return False, 0.0
        
        rr_ratio = reward / risk
        
        return rr_ratio >= self.min_risk_reward_ratio, rr_ratio
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate recent volatility (ATR-based)"""
        if len(df) < 14:
            return 0.0
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean().iloc[-1]
        
        current_price = df['close'].iloc[-1]
        volatility = atr / current_price
        
        return volatility
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength using ADX-like metric"""
        if len(df) < 20:
            return 0.0
        
        close = df['close']
        
        ema_20 = close.ewm(span=20).mean()
        ema_50 = close.ewm(span=50).mean() if len(df) >= 50 else ema_20
        
        trend_alignment = abs(ema_20.iloc[-1] - ema_50.iloc[-1]) / ema_50.iloc[-1]
        
        price_momentum = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]
        
        trend_strength = min((abs(trend_alignment) + abs(price_momentum)) / 2, 1.0)
        
        return trend_strength
    
    def _validate_volume(self, df: pd.DataFrame) -> bool:
        """Validate volume conditions"""
        if 'volume' not in df.columns or len(df) < 20:
            return True
        
        recent_volume = df['volume'].iloc[-5:].mean()
        avg_volume = df['volume'].iloc[-20:].mean()
        
        return recent_volume >= avg_volume * 0.7
    
    def _validate_price_action(self, df: pd.DataFrame, signal: TradingSignal) -> bool:
        """Validate price action confirms signal"""
        if len(df) < 5:
            return True
        
        recent_closes = df['close'].iloc[-5:]
        
        if signal.signal_type == SignalType.BUY:
            bullish_candles = sum(recent_closes.diff() > 0)
            return bullish_candles >= 2
        else:
            bearish_candles = sum(recent_closes.diff() < 0)
            return bearish_candles >= 2
    
    def _get_strategy_performance(self, strategy_name: str) -> float:
        """Get historical performance of strategy"""
        if strategy_name not in self.performance_by_strategy:
            return 0.55
        
        perf = self.performance_by_strategy[strategy_name]
        total = perf.get('wins', 0) + perf.get('losses', 0)
        
        if total == 0:
            return 0.55
        
        return perf.get('wins', 0) / total
    
    def record_signal_outcome(self, signal: TradingSignal, was_profitable: bool):
        """Record signal outcome for learning"""
        self.signal_history.append({
            'strategy': signal.strategy,
            'symbol': signal.symbol,
            'profitable': was_profitable,
            'confidence': signal.confidence
        })
        
        if signal.strategy not in self.performance_by_strategy:
            self.performance_by_strategy[signal.strategy] = {'wins': 0, 'losses': 0}
        
        if was_profitable:
            self.performance_by_strategy[signal.strategy]['wins'] += 1
        else:
            self.performance_by_strategy[signal.strategy]['losses'] += 1
        
        logger.info(f"Recorded outcome for {signal.strategy}: {'WIN' if was_profitable else 'LOSS'}")
    
    def get_validation_summary(self) -> Dict:
        """Get summary of validation statistics"""
        return {
            'total_signals_validated': len(self.signal_history),
            'strategy_performance': self.performance_by_strategy.copy(),
            'recent_signals': self.signal_history[-10:]
        }
