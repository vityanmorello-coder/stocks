"""
Alpha Engine v1.0 - Real Market Microstructure Intelligence
Detects order flow imbalances, liquidity sweeps, and market inefficiencies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrderFlowSignal:
    """Order flow analysis result"""
    buying_pressure: float  # 0-1, higher = more buying
    selling_pressure: float  # 0-1, higher = more selling
    pressure_imbalance: float  # -1 to +1, positive = bullish
    volume_delta_proxy: float  # Approximation of buy vs sell volume
    absorption_detected: bool  # Large volume with small price move
    momentum_continuation: bool  # Strong move with follow-through
    confidence: float  # 0-1


@dataclass
class LiquiditySweep:
    """Liquidity sweep detection result"""
    sweep_detected: bool
    sweep_score: float  # 0-1, confidence of sweep
    direction: str  # 'bullish_sweep', 'bearish_sweep', 'none'
    sweep_type: str  # 'stop_hunt', 'false_breakout', 'wick_reversal'
    price_level: float  # Price where sweep occurred
    displacement_strength: float  # How strong was the reversal
    confidence_adjustment: float  # Multiplier for signal confidence


@dataclass
class MarketInefficiency:
    """Market inefficiency detection result"""
    inefficiency_detected: bool
    inefficiency_score: float  # 0-1
    trade_bias: str  # 'long', 'short', 'none'
    inefficiency_type: str  # 'imbalance', 'fast_displacement', 'fair_value_gap'
    price_zone_start: float
    price_zone_end: float
    expected_fill: bool  # Whether price likely to return to fill gap


class OrderFlowAnalyzer:
    """
    Analyzes order flow to detect buying/selling pressure imbalances.
    
    Uses candle microstructure:
    - Wick analysis (rejection vs absorption)
    - Volume distribution
    - Price action momentum
    """
    
    def __init__(self):
        self.lookback = 20
    
    def analyze(self, df: pd.DataFrame) -> OrderFlowSignal:
        """
        Analyze order flow from OHLCV data.
        
        Args:
            df: DataFrame with OHLC + volume
        
        Returns:
            OrderFlowSignal
        """
        if len(df) < self.lookback:
            return self._empty_signal()
        
        recent = df.tail(self.lookback).copy()
        
        # Calculate buying vs selling pressure
        buying_pressure = self._calculate_buying_pressure(recent)
        selling_pressure = self._calculate_selling_pressure(recent)
        
        # Volume delta proxy (buy volume - sell volume approximation)
        volume_delta = self._calculate_volume_delta_proxy(recent)
        
        # Pressure imbalance
        imbalance = buying_pressure - selling_pressure
        
        # Detect absorption (large volume, small price move)
        absorption = self._detect_absorption(recent)
        
        # Detect momentum continuation
        momentum_cont = self._detect_momentum_continuation(recent)
        
        # Calculate confidence
        confidence = self._calculate_flow_confidence(
            buying_pressure, selling_pressure, volume_delta, absorption, momentum_cont
        )
        
        return OrderFlowSignal(
            buying_pressure=buying_pressure,
            selling_pressure=selling_pressure,
            pressure_imbalance=imbalance,
            volume_delta_proxy=volume_delta,
            absorption_detected=absorption,
            momentum_continuation=momentum_cont,
            confidence=confidence
        )
    
    def _calculate_buying_pressure(self, df: pd.DataFrame) -> float:
        """Calculate buying pressure from candle structure"""
        # Bullish candles (close > open)
        bullish = df['close'] > df['open']
        
        # Upper wick rejection strength (buyers pushed price up)
        body_size = abs(df['close'] - df['open'])
        upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
        lower_wick = df[['open', 'close']].min(axis=1) - df['low']
        
        # Buying pressure indicators
        bullish_ratio = bullish.sum() / len(df)
        
        # Strong closes near high (buyers in control)
        close_position = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
        avg_close_position = close_position.mean()
        
        # Volume on bullish candles
        vol_on_bullish = df.loc[bullish, 'volume'].sum() / (df['volume'].sum() + 1e-8)
        
        # Combine indicators
        buying_pressure = (bullish_ratio * 0.3 + avg_close_position * 0.4 + vol_on_bullish * 0.3)
        
        return np.clip(buying_pressure, 0, 1)
    
    def _calculate_selling_pressure(self, df: pd.DataFrame) -> float:
        """Calculate selling pressure from candle structure"""
        # Bearish candles (close < open)
        bearish = df['close'] < df['open']
        
        bearish_ratio = bearish.sum() / len(df)
        
        # Strong closes near low (sellers in control)
        close_position = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
        avg_close_position = 1 - close_position.mean()  # Invert for selling
        
        # Volume on bearish candles
        vol_on_bearish = df.loc[bearish, 'volume'].sum() / (df['volume'].sum() + 1e-8)
        
        selling_pressure = (bearish_ratio * 0.3 + avg_close_position * 0.4 + vol_on_bearish * 0.3)
        
        return np.clip(selling_pressure, 0, 1)
    
    def _calculate_volume_delta_proxy(self, df: pd.DataFrame) -> float:
        """Approximate buy volume - sell volume"""
        # Proxy: volume on up moves vs down moves
        price_change = df['close'].diff()
        
        up_volume = df.loc[price_change > 0, 'volume'].sum()
        down_volume = df.loc[price_change < 0, 'volume'].sum()
        
        total_volume = up_volume + down_volume
        if total_volume == 0:
            return 0.0
        
        # Normalize to -1 to +1
        delta = (up_volume - down_volume) / total_volume
        
        return np.clip(delta, -1, 1)
    
    def _detect_absorption(self, df: pd.DataFrame) -> bool:
        """Detect absorption: large volume but small price move"""
        last_candle = df.iloc[-1]
        avg_volume = df['volume'].mean()
        
        # High volume
        high_volume = last_candle['volume'] > avg_volume * 1.5
        
        # Small body (price didn't move much despite volume)
        body_size = abs(last_candle['close'] - last_candle['open'])
        candle_range = last_candle['high'] - last_candle['low']
        small_body = body_size < candle_range * 0.3
        
        return high_volume and small_body
    
    def _detect_momentum_continuation(self, df: pd.DataFrame) -> bool:
        """Detect strong momentum with follow-through"""
        if len(df) < 3:
            return False
        
        last_3 = df.tail(3)
        
        # Check for 3 consecutive candles in same direction
        closes = last_3['close'].values
        
        # All up or all down
        all_up = all(closes[i] > closes[i-1] for i in range(1, len(closes)))
        all_down = all(closes[i] < closes[i-1] for i in range(1, len(closes)))
        
        # Increasing volume
        volumes = last_3['volume'].values
        increasing_vol = volumes[-1] > volumes[0]
        
        return (all_up or all_down) and increasing_vol
    
    def _calculate_flow_confidence(
        self, buying: float, selling: float, delta: float, 
        absorption: bool, momentum: bool
    ) -> float:
        """Calculate overall order flow confidence"""
        # Strong imbalance = high confidence
        imbalance_strength = abs(buying - selling)
        
        # Volume delta confirmation
        delta_strength = abs(delta)
        
        # Bonus for special patterns
        pattern_bonus = 0.0
        if absorption:
            pattern_bonus += 0.1
        if momentum:
            pattern_bonus += 0.15
        
        confidence = (imbalance_strength * 0.5 + delta_strength * 0.5 + pattern_bonus)
        
        return np.clip(confidence, 0, 1)
    
    def _empty_signal(self) -> OrderFlowSignal:
        """Return empty signal when not enough data"""
        return OrderFlowSignal(
            buying_pressure=0.5, selling_pressure=0.5, pressure_imbalance=0.0,
            volume_delta_proxy=0.0, absorption_detected=False,
            momentum_continuation=False, confidence=0.0
        )


class LiquiditySweepDetector:
    """
    Detects liquidity sweeps (stop hunts, false breakouts).
    
    Patterns:
    1. Price breaks key level (resistance/support)
    2. Sharp wick forms (stops triggered)
    3. Immediate reversal (liquidity grabbed)
    4. Strong displacement in opposite direction
    """
    
    def __init__(self, wick_threshold: float = 0.6, displacement_threshold: float = 0.5):
        self.wick_threshold = wick_threshold
        self.displacement_threshold = displacement_threshold
        self.lookback = 50
    
    def detect(self, df: pd.DataFrame, key_levels: Optional[Dict] = None) -> LiquiditySweep:
        """
        Detect liquidity sweeps.
        
        Args:
            df: OHLCV DataFrame
            key_levels: Optional dict with 'resistance' and 'support' levels
        
        Returns:
            LiquiditySweep
        """
        if len(df) < 10:
            return self._empty_sweep()
        
        recent = df.tail(self.lookback).copy()
        last_candle = recent.iloc[-1]
        
        # Identify key levels if not provided
        if key_levels is None:
            key_levels = self._identify_key_levels(recent)
        
        # Check for sweep patterns
        bullish_sweep = self._detect_bullish_sweep(recent, last_candle, key_levels)
        bearish_sweep = self._detect_bearish_sweep(recent, last_candle, key_levels)
        
        if bullish_sweep['detected']:
            return bullish_sweep['result']
        elif bearish_sweep['detected']:
            return bearish_sweep['result']
        else:
            return self._empty_sweep()
    
    def _identify_key_levels(self, df: pd.DataFrame) -> Dict:
        """Identify support and resistance levels"""
        highs = df['high'].values
        lows = df['low'].values
        
        # Recent swing high/low
        resistance = np.percentile(highs, 95)
        support = np.percentile(lows, 5)
        
        return {'resistance': resistance, 'support': support}
    
    def _detect_bullish_sweep(
        self, df: pd.DataFrame, last_candle: pd.Series, levels: Dict
    ) -> Dict:
        """Detect bullish liquidity sweep (sweep below support, then rally)"""
        support = levels.get('support', df['low'].min())
        
        # Check if price swept below support
        swept_below = last_candle['low'] < support
        
        if not swept_below:
            return {'detected': False}
        
        # Check for long lower wick (rejection)
        body_low = min(last_candle['open'], last_candle['close'])
        lower_wick = body_low - last_candle['low']
        candle_range = last_candle['high'] - last_candle['low']
        
        wick_ratio = lower_wick / (candle_range + 1e-8)
        strong_wick = wick_ratio > self.wick_threshold
        
        # Check for bullish close (reversal)
        bullish_close = last_candle['close'] > last_candle['open']
        
        # Check displacement strength
        close_position = (last_candle['close'] - last_candle['low']) / (candle_range + 1e-8)
        strong_displacement = close_position > self.displacement_threshold
        
        if strong_wick and bullish_close and strong_displacement:
            sweep_score = (wick_ratio + close_position) / 2
            
            return {
                'detected': True,
                'result': LiquiditySweep(
                    sweep_detected=True,
                    sweep_score=sweep_score,
                    direction='bullish_sweep',
                    sweep_type='stop_hunt',
                    price_level=support,
                    displacement_strength=close_position,
                    confidence_adjustment=1.0 + (sweep_score * 0.3)  # Boost confidence
                )
            }
        
        return {'detected': False}
    
    def _detect_bearish_sweep(
        self, df: pd.DataFrame, last_candle: pd.Series, levels: Dict
    ) -> Dict:
        """Detect bearish liquidity sweep (sweep above resistance, then drop)"""
        resistance = levels.get('resistance', df['high'].max())
        
        # Check if price swept above resistance
        swept_above = last_candle['high'] > resistance
        
        if not swept_above:
            return {'detected': False}
        
        # Check for long upper wick (rejection)
        body_high = max(last_candle['open'], last_candle['close'])
        upper_wick = last_candle['high'] - body_high
        candle_range = last_candle['high'] - last_candle['low']
        
        wick_ratio = upper_wick / (candle_range + 1e-8)
        strong_wick = wick_ratio > self.wick_threshold
        
        # Check for bearish close (reversal)
        bearish_close = last_candle['close'] < last_candle['open']
        
        # Check displacement strength
        close_position = (last_candle['high'] - last_candle['close']) / (candle_range + 1e-8)
        strong_displacement = close_position > self.displacement_threshold
        
        if strong_wick and bearish_close and strong_displacement:
            sweep_score = (wick_ratio + close_position) / 2
            
            return {
                'detected': True,
                'result': LiquiditySweep(
                    sweep_detected=True,
                    sweep_score=sweep_score,
                    direction='bearish_sweep',
                    sweep_type='stop_hunt',
                    price_level=resistance,
                    displacement_strength=close_position,
                    confidence_adjustment=1.0 + (sweep_score * 0.3)
                )
            }
        
        return {'detected': False}
    
    def _empty_sweep(self) -> LiquiditySweep:
        """Return empty sweep result"""
        return LiquiditySweep(
            sweep_detected=False, sweep_score=0.0, direction='none',
            sweep_type='none', price_level=0.0, displacement_strength=0.0,
            confidence_adjustment=1.0
        )


class MarketInefficiencyDetector:
    """
    Detects market inefficiencies:
    - Price imbalance zones
    - Fast displacement with no retrace
    - Fair value gaps (FVG)
    """
    
    def __init__(self):
        self.lookback = 30
    
    def detect(self, df: pd.DataFrame) -> MarketInefficiency:
        """
        Detect market inefficiencies.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            MarketInefficiency
        """
        if len(df) < 10:
            return self._empty_inefficiency()
        
        recent = df.tail(self.lookback).copy()
        
        # Detect fair value gap
        fvg = self._detect_fair_value_gap(recent)
        if fvg['detected']:
            return fvg['result']
        
        # Detect fast displacement
        displacement = self._detect_fast_displacement(recent)
        if displacement['detected']:
            return displacement['result']
        
        # Detect imbalance zone
        imbalance = self._detect_imbalance_zone(recent)
        if imbalance['detected']:
            return imbalance['result']
        
        return self._empty_inefficiency()
    
    def _detect_fair_value_gap(self, df: pd.DataFrame) -> Dict:
        """
        Detect Fair Value Gap (FVG):
        - 3 candles where middle candle doesn't overlap with candles before/after
        """
        if len(df) < 3:
            return {'detected': False}
        
        last_3 = df.tail(3)
        candles = last_3.values
        
        # Bullish FVG: gap between candle 1 high and candle 3 low
        c1_high = candles[0][2]  # high of first candle
        c3_low = candles[2][3]   # low of third candle
        
        bullish_gap = c3_low > c1_high
        
        # Bearish FVG: gap between candle 1 low and candle 3 high
        c1_low = candles[0][3]
        c3_high = candles[2][2]
        
        bearish_gap = c3_high < c1_low
        
        if bullish_gap:
            gap_size = c3_low - c1_high
            avg_range = (candles[:, 2] - candles[:, 3]).mean()  # avg high-low
            inefficiency_score = min(1.0, gap_size / (avg_range + 1e-8))
            
            return {
                'detected': True,
                'result': MarketInefficiency(
                    inefficiency_detected=True,
                    inefficiency_score=inefficiency_score,
                    trade_bias='long',
                    inefficiency_type='fair_value_gap',
                    price_zone_start=c1_high,
                    price_zone_end=c3_low,
                    expected_fill=True
                )
            }
        
        elif bearish_gap:
            gap_size = c1_low - c3_high
            avg_range = (candles[:, 2] - candles[:, 3]).mean()
            inefficiency_score = min(1.0, gap_size / (avg_range + 1e-8))
            
            return {
                'detected': True,
                'result': MarketInefficiency(
                    inefficiency_detected=True,
                    inefficiency_score=inefficiency_score,
                    trade_bias='short',
                    inefficiency_type='fair_value_gap',
                    price_zone_start=c3_high,
                    price_zone_end=c1_low,
                    expected_fill=True
                )
            }
        
        return {'detected': False}
    
    def _detect_fast_displacement(self, df: pd.DataFrame) -> Dict:
        """Detect fast price move with no retrace (inefficiency)"""
        if len(df) < 5:
            return {'detected': False}
        
        last_5 = df.tail(5)
        
        # Calculate total price move
        start_price = last_5.iloc[0]['close']
        end_price = last_5.iloc[-1]['close']
        total_move = abs(end_price - start_price)
        
        # Calculate retracement
        if end_price > start_price:
            # Upward move - check for pullbacks
            max_pullback = (last_5['low'].min() - start_price)
            retracement_ratio = abs(max_pullback / (total_move + 1e-8))
        else:
            # Downward move - check for bounces
            max_bounce = (last_5['high'].max() - start_price)
            retracement_ratio = abs(max_bounce / (total_move + 1e-8))
        
        # Fast displacement = low retracement
        fast_displacement = retracement_ratio < 0.3
        
        # Strong move
        avg_range = (df['high'] - df['low']).mean()
        strong_move = total_move > avg_range * 2
        
        if fast_displacement and strong_move:
            inefficiency_score = 1.0 - retracement_ratio
            
            return {
                'detected': True,
                'result': MarketInefficiency(
                    inefficiency_detected=True,
                    inefficiency_score=inefficiency_score,
                    trade_bias='long' if end_price > start_price else 'short',
                    inefficiency_type='fast_displacement',
                    price_zone_start=start_price,
                    price_zone_end=end_price,
                    expected_fill=False  # Fast moves often don't retrace
                )
            }
        
        return {'detected': False}
    
    def _detect_imbalance_zone(self, df: pd.DataFrame) -> Dict:
        """Detect price imbalance (single direction candles)"""
        if len(df) < 5:
            return {'detected': False}
        
        last_5 = df.tail(5)
        
        # All bullish or all bearish
        all_bullish = all(last_5['close'] > last_5['open'])
        all_bearish = all(last_5['close'] < last_5['open'])
        
        if all_bullish or all_bearish:
            # Calculate imbalance strength
            total_range = last_5['high'].max() - last_5['low'].min()
            total_body = abs(last_5['close'] - last_5['open']).sum()
            
            imbalance_strength = total_body / (total_range + 1e-8)
            
            return {
                'detected': True,
                'result': MarketInefficiency(
                    inefficiency_detected=True,
                    inefficiency_score=imbalance_strength,
                    trade_bias='long' if all_bullish else 'short',
                    inefficiency_type='imbalance',
                    price_zone_start=last_5.iloc[0]['open'],
                    price_zone_end=last_5.iloc[-1]['close'],
                    expected_fill=True  # Imbalances often get filled
                )
            }
        
        return {'detected': False}
    
    def _empty_inefficiency(self) -> MarketInefficiency:
        """Return empty inefficiency result"""
        return MarketInefficiency(
            inefficiency_detected=False, inefficiency_score=0.0,
            trade_bias='none', inefficiency_type='none',
            price_zone_start=0.0, price_zone_end=0.0, expected_fill=False
        )


class AlphaEngine:
    """
    Main Alpha Engine combining all microstructure analysis.
    
    Usage:
        alpha = AlphaEngine()
        result = alpha.analyze(df, key_levels={'resistance': 1.0900, 'support': 1.0800})
        
        if result['order_flow'].confidence > 0.7:
            # Strong order flow signal
            
        if result['liquidity_sweep'].sweep_detected:
            # Liquidity sweep - high probability reversal
            
        if result['inefficiency'].inefficiency_detected:
            # Market inefficiency - potential fill opportunity
    """
    
    def __init__(self):
        self.order_flow_analyzer = OrderFlowAnalyzer()
        self.liquidity_detector = LiquiditySweepDetector()
        self.inefficiency_detector = MarketInefficiencyDetector()
    
    def analyze(
        self,
        df: pd.DataFrame,
        key_levels: Optional[Dict] = None
    ) -> Dict:
        """
        Complete alpha analysis.
        
        Args:
            df: OHLCV DataFrame
            key_levels: Optional support/resistance levels
        
        Returns:
            Dictionary with all analysis results
        """
        # Order flow analysis
        order_flow = self.order_flow_analyzer.analyze(df)
        
        # Liquidity sweep detection
        liquidity_sweep = self.liquidity_detector.detect(df, key_levels)
        
        # Market inefficiency detection
        inefficiency = self.inefficiency_detector.detect(df)
        
        # Calculate combined alpha score
        alpha_score = self._calculate_alpha_score(order_flow, liquidity_sweep, inefficiency)
        
        # Determine trade bias
        trade_bias = self._determine_trade_bias(order_flow, liquidity_sweep, inefficiency)
        
        return {
            'order_flow': order_flow,
            'liquidity_sweep': liquidity_sweep,
            'inefficiency': inefficiency,
            'alpha_score': alpha_score,
            'trade_bias': trade_bias,
            'confidence_multiplier': self._calculate_confidence_multiplier(
                order_flow, liquidity_sweep, inefficiency
            )
        }
    
    def _calculate_alpha_score(
        self, flow: OrderFlowSignal, sweep: LiquiditySweep, ineff: MarketInefficiency
    ) -> float:
        """Calculate combined alpha score (0-1)"""
        # Order flow component
        flow_score = flow.confidence * abs(flow.pressure_imbalance)
        
        # Liquidity sweep component
        sweep_score = sweep.sweep_score if sweep.sweep_detected else 0.0
        
        # Inefficiency component
        ineff_score = ineff.inefficiency_score if ineff.inefficiency_detected else 0.0
        
        # Weighted combination
        alpha = (flow_score * 0.4 + sweep_score * 0.4 + ineff_score * 0.2)
        
        return np.clip(alpha, 0, 1)
    
    def _determine_trade_bias(
        self, flow: OrderFlowSignal, sweep: LiquiditySweep, ineff: MarketInefficiency
    ) -> str:
        """Determine overall trade bias"""
        bullish_signals = 0
        bearish_signals = 0
        
        # Order flow
        if flow.pressure_imbalance > 0.2:
            bullish_signals += 1
        elif flow.pressure_imbalance < -0.2:
            bearish_signals += 1
        
        # Liquidity sweep
        if sweep.sweep_detected:
            if sweep.direction == 'bullish_sweep':
                bullish_signals += 2  # Strong signal
            elif sweep.direction == 'bearish_sweep':
                bearish_signals += 2
        
        # Inefficiency
        if ineff.inefficiency_detected:
            if ineff.trade_bias == 'long':
                bullish_signals += 1
            elif ineff.trade_bias == 'short':
                bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            return 'bullish'
        elif bearish_signals > bullish_signals:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_confidence_multiplier(
        self, flow: OrderFlowSignal, sweep: LiquiditySweep, ineff: MarketInefficiency
    ) -> float:
        """Calculate confidence adjustment multiplier"""
        multiplier = 1.0
        
        # Liquidity sweep boost
        if sweep.sweep_detected:
            multiplier *= sweep.confidence_adjustment
        
        # Strong order flow boost
        if flow.confidence > 0.7:
            multiplier *= 1.1
        
        # Inefficiency boost
        if ineff.inefficiency_detected and ineff.inefficiency_score > 0.6:
            multiplier *= 1.05
        
        return min(1.5, multiplier)  # Cap at 1.5x


# Example usage
if __name__ == "__main__":
    # Generate sample data
    np.random.seed(42)
    n = 100
    
    data = {
        'open': np.random.randn(n).cumsum() + 100,
        'high': np.random.randn(n).cumsum() + 101,
        'low': np.random.randn(n).cumsum() + 99,
        'close': np.random.randn(n).cumsum() + 100,
        'volume': np.random.randint(1000, 5000, n)
    }
    df = pd.DataFrame(data)
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    # Run alpha engine
    alpha = AlphaEngine()
    result = alpha.analyze(df)
    
    print("=== Alpha Engine Analysis ===")
    print(f"Alpha Score: {result['alpha_score']:.3f}")
    print(f"Trade Bias: {result['trade_bias']}")
    print(f"Confidence Multiplier: {result['confidence_multiplier']:.2f}")
    print(f"\nOrder Flow Imbalance: {result['order_flow'].pressure_imbalance:+.3f}")
    print(f"Liquidity Sweep: {result['liquidity_sweep'].sweep_detected}")
    print(f"Inefficiency: {result['inefficiency'].inefficiency_detected}")
