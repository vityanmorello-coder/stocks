"""
MULTI-TIMEFRAME ANALYSIS SYSTEM
Analyze market across multiple timeframes for confluence trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Timeframe(Enum):
    """Supported timeframes"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class TrendDirection(Enum):
    """Trend direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class TimeframeAnalysis:
    """Analysis for single timeframe"""
    timeframe: str
    trend: TrendDirection
    trend_strength: float
    support_levels: List[float]
    resistance_levels: List[float]
    rsi: float
    macd_signal: str
    volume_trend: str
    volatility: float
    key_level_distance: float
    
    def to_dict(self):
        return {
            'timeframe': self.timeframe,
            'trend': self.trend.value,
            'trend_strength': self.trend_strength,
            'support_levels': self.support_levels,
            'resistance_levels': self.resistance_levels,
            'rsi': self.rsi,
            'macd_signal': self.macd_signal,
            'volume_trend': self.volume_trend,
            'volatility': self.volatility,
            'key_level_distance': self.key_level_distance
        }


@dataclass
class MultiTimeframeSignal:
    """Multi-timeframe trading signal"""
    symbol: str
    direction: str
    confluence_score: float
    entry_price: float
    stop_loss: float
    take_profit: float
    timeframe_alignment: Dict[str, str]
    key_levels: Dict[str, List[float]]
    risk_reward_ratio: float
    confidence: float
    reasoning: List[str]
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'confluence_score': self.confluence_score,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'timeframe_alignment': self.timeframe_alignment,
            'key_levels': self.key_levels,
            'risk_reward_ratio': self.risk_reward_ratio,
            'confidence': self.confidence,
            'reasoning': self.reasoning
        }


class MultiTimeframeAnalyzer:
    """Analyze markets across multiple timeframes"""
    
    def __init__(self, timeframes: List[str] = None):
        self.timeframes = timeframes or ['15m', '1h', '4h', '1d']
        self.weights = {
            '1m': 0.05,
            '5m': 0.10,
            '15m': 0.15,
            '30m': 0.15,
            '1h': 0.20,
            '4h': 0.25,
            '1d': 0.30,
            '1w': 0.35
        }
    
    def analyze_symbol(self, symbol: str, data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """Analyze symbol across all timeframes"""
        
        analyses = {}
        
        for timeframe in self.timeframes:
            if timeframe in data_dict and not data_dict[timeframe].empty:
                df = data_dict[timeframe]
                analyses[timeframe] = self._analyze_timeframe(df, timeframe)
        
        if not analyses:
            return None
        
        confluence = self._calculate_confluence(analyses)
        
        signal = self._generate_signal(symbol, analyses, confluence, data_dict)
        
        return {
            'symbol': symbol,
            'analyses': {tf: analysis.to_dict() for tf, analysis in analyses.items()},
            'confluence': confluence,
            'signal': signal.to_dict() if signal else None
        }
    
    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> TimeframeAnalysis:
        """Analyze single timeframe"""
        
        if len(df) < 50:
            return self._empty_analysis(timeframe)
        
        trend, trend_strength = self._detect_trend(df)
        
        support_levels = self._find_support_levels(df)
        resistance_levels = self._find_resistance_levels(df)
        
        rsi = self._calculate_rsi(df)
        macd_signal = self._analyze_macd(df)
        volume_trend = self._analyze_volume(df)
        volatility = self._calculate_volatility(df)
        
        current_price = df['close'].iloc[-1]
        key_level_distance = self._distance_to_key_level(
            current_price, support_levels, resistance_levels
        )
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=trend,
            trend_strength=trend_strength,
            support_levels=support_levels[:3],
            resistance_levels=resistance_levels[:3],
            rsi=rsi,
            macd_signal=macd_signal,
            volume_trend=volume_trend,
            volatility=volatility,
            key_level_distance=key_level_distance
        )
    
    def _detect_trend(self, df: pd.DataFrame) -> Tuple[TrendDirection, float]:
        """Detect trend and strength"""
        
        close = df['close']
        
        ema_20 = close.ewm(span=20).mean().iloc[-1]
        ema_50 = close.ewm(span=50).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        if current_price > ema_20 > ema_50:
            trend = TrendDirection.BULLISH
            strength = min((current_price - ema_50) / ema_50 * 100, 100)
        elif current_price < ema_20 < ema_50:
            trend = TrendDirection.BEARISH
            strength = min((ema_50 - current_price) / ema_50 * 100, 100)
        else:
            trend = TrendDirection.NEUTRAL
            strength = 0
        
        adx = self._calculate_adx(df)
        strength = (strength + adx) / 2
        
        return trend, strength
    
    def _find_support_levels(self, df: pd.DataFrame, num_levels: int = 3) -> List[float]:
        """Find support levels"""
        
        lows = df['low'].values
        
        support_levels = []
        window = 10
        
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i-window:i+window+1]):
                support_levels.append(lows[i])
        
        if not support_levels:
            return [df['low'].min()]
        
        support_levels = sorted(set(support_levels))
        
        current_price = df['close'].iloc[-1]
        support_levels = [s for s in support_levels if s < current_price]
        
        return support_levels[-num_levels:] if support_levels else [df['low'].min()]
    
    def _find_resistance_levels(self, df: pd.DataFrame, num_levels: int = 3) -> List[float]:
        """Find resistance levels"""
        
        highs = df['high'].values
        
        resistance_levels = []
        window = 10
        
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                resistance_levels.append(highs[i])
        
        if not resistance_levels:
            return [df['high'].max()]
        
        resistance_levels = sorted(set(resistance_levels))
        
        current_price = df['close'].iloc[-1]
        resistance_levels = [r for r in resistance_levels if r > current_price]
        
        return resistance_levels[:num_levels] if resistance_levels else [df['high'].max()]
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI"""
        
        close = df['close']
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _analyze_macd(self, df: pd.DataFrame) -> str:
        """Analyze MACD"""
        
        close = df['close']
        
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        
        macd_current = macd.iloc[-1]
        signal_current = signal.iloc[-1]
        macd_prev = macd.iloc[-2]
        signal_prev = signal.iloc[-2]
        
        if macd_current > signal_current and macd_prev <= signal_prev:
            return "bullish_crossover"
        elif macd_current < signal_current and macd_prev >= signal_prev:
            return "bearish_crossover"
        elif macd_current > signal_current:
            return "bullish"
        elif macd_current < signal_current:
            return "bearish"
        else:
            return "neutral"
    
    def _analyze_volume(self, df: pd.DataFrame) -> str:
        """Analyze volume trend"""
        
        if 'volume' not in df.columns:
            return "unknown"
        
        volume = df['volume']
        
        if len(volume) < 20:
            return "unknown"
        
        vol_ma = volume.rolling(window=20).mean()
        current_vol = volume.iloc[-1]
        avg_vol = vol_ma.iloc[-1]
        
        if current_vol > avg_vol * 1.5:
            return "high"
        elif current_vol < avg_vol * 0.5:
            return "low"
        else:
            return "normal"
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility (ATR)"""
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0.0
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX"""
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0.0
    
    def _distance_to_key_level(self, price: float, supports: List[float], resistances: List[float]) -> float:
        """Calculate distance to nearest key level"""
        
        all_levels = supports + resistances
        
        if not all_levels:
            return 100.0
        
        distances = [abs(price - level) / price * 100 for level in all_levels]
        
        return min(distances)
    
    def _calculate_confluence(self, analyses: Dict[str, TimeframeAnalysis]) -> Dict:
        """Calculate confluence across timeframes"""
        
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for timeframe, analysis in analyses.items():
            weight = self.weights.get(timeframe, 0.1)
            
            if analysis.trend == TrendDirection.BULLISH:
                bullish_count += 1
                weighted_score += weight * analysis.trend_strength
            elif analysis.trend == TrendDirection.BEARISH:
                bearish_count += 1
                weighted_score -= weight * analysis.trend_strength
            else:
                neutral_count += 1
            
            total_weight += weight
        
        confluence_score = (weighted_score / total_weight) if total_weight > 0 else 0.0
        
        alignment_pct = max(bullish_count, bearish_count) / len(analyses) * 100
        
        return {
            'bullish_timeframes': bullish_count,
            'bearish_timeframes': bearish_count,
            'neutral_timeframes': neutral_count,
            'confluence_score': confluence_score,
            'alignment_percentage': alignment_pct,
            'is_aligned': alignment_pct >= 66.0
        }
    
    def _generate_signal(self, symbol: str, analyses: Dict[str, TimeframeAnalysis], 
                        confluence: Dict, data_dict: Dict[str, pd.DataFrame]) -> Optional[MultiTimeframeSignal]:
        """Generate trading signal from multi-timeframe analysis"""
        
        if not confluence['is_aligned']:
            return None
        
        if abs(confluence['confluence_score']) < 30:
            return None
        
        direction = 'buy' if confluence['confluence_score'] > 0 else 'sell'
        
        entry_timeframe = '15m' if '15m' in data_dict else list(data_dict.keys())[0]
        entry_df = data_dict[entry_timeframe]
        entry_price = entry_df['close'].iloc[-1]
        
        higher_tf = '4h' if '4h' in analyses else '1h' if '1h' in analyses else entry_timeframe
        higher_analysis = analyses[higher_tf]
        
        if direction == 'buy':
            stop_loss = higher_analysis.support_levels[0] if higher_analysis.support_levels else entry_price * 0.98
            take_profit = higher_analysis.resistance_levels[0] if higher_analysis.resistance_levels else entry_price * 1.04
        else:
            stop_loss = higher_analysis.resistance_levels[0] if higher_analysis.resistance_levels else entry_price * 1.02
            take_profit = higher_analysis.support_levels[0] if higher_analysis.support_levels else entry_price * 0.96
        
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        if rr_ratio < 1.5:
            return None
        
        timeframe_alignment = {
            tf: analysis.trend.value for tf, analysis in analyses.items()
        }
        
        key_levels = {
            tf: {
                'support': analysis.support_levels,
                'resistance': analysis.resistance_levels
            } for tf, analysis in analyses.items()
        }
        
        reasoning = self._build_reasoning(analyses, confluence, direction)
        
        confidence = min(confluence['alignment_percentage'] + abs(confluence['confluence_score']), 100) / 100
        
        return MultiTimeframeSignal(
            symbol=symbol,
            direction=direction,
            confluence_score=confluence['confluence_score'],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timeframe_alignment=timeframe_alignment,
            key_levels=key_levels,
            risk_reward_ratio=rr_ratio,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _build_reasoning(self, analyses: Dict[str, TimeframeAnalysis], 
                        confluence: Dict, direction: str) -> List[str]:
        """Build reasoning for signal"""
        
        reasoning = []
        
        reasoning.append(f"{confluence['alignment_percentage']:.0f}% timeframe alignment")
        
        if direction == 'buy':
            reasoning.append("Bullish trend across multiple timeframes")
        else:
            reasoning.append("Bearish trend across multiple timeframes")
        
        for tf, analysis in analyses.items():
            if analysis.trend_strength > 60:
                reasoning.append(f"Strong {analysis.trend.value} trend on {tf}")
        
        for tf, analysis in analyses.items():
            if analysis.macd_signal in ['bullish_crossover', 'bearish_crossover']:
                reasoning.append(f"MACD {analysis.macd_signal} on {tf}")
        
        return reasoning
    
    def _empty_analysis(self, timeframe: str) -> TimeframeAnalysis:
        """Return empty analysis"""
        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=TrendDirection.NEUTRAL,
            trend_strength=0.0,
            support_levels=[],
            resistance_levels=[],
            rsi=50.0,
            macd_signal="neutral",
            volume_trend="unknown",
            volatility=0.0,
            key_level_distance=100.0
        )


if __name__ == "__main__":
    print("Multi-Timeframe Analyzer Loaded")
    print("Features:")
    print("  - Multiple timeframe analysis")
    print("  - Trend confluence detection")
    print("  - Support/resistance levels")
    print("  - Signal generation with reasoning")
