"""
MarketStructureAnalyzer v1.0 - Real Trading Edge
Detects market structure that lagging indicators miss:
- Higher highs / Higher lows (trend structure)
- Structure breaks (BOS / CHoCH)
- Order blocks (institutional entry zones)
- Liquidity zones (stop hunt levels)
- Supply & demand zones
- Volume-weighted levels
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SwingPoint:
    """A detected swing high or swing low"""
    index: int
    price: float
    type: str  # 'high' or 'low'
    strength: int = 1  # How many bars confirm this swing


@dataclass
class OrderBlock:
    """Institutional order block zone"""
    top: float
    bottom: float
    type: str  # 'bullish' or 'bearish'
    strength: float = 0.0  # 0-1
    tested: bool = False
    index: int = 0


@dataclass
class LiquidityZone:
    """Zone where stop losses are likely clustered"""
    price: float
    type: str  # 'buy_side' (above highs) or 'sell_side' (below lows)
    strength: float = 0.0
    swept: bool = False


@dataclass 
class SupplyDemandZone:
    """Supply or demand zone from strong price rejections"""
    top: float
    bottom: float
    type: str  # 'supply' or 'demand'
    strength: float = 0.0
    touches: int = 0


@dataclass
class StructureAnalysis:
    """Complete market structure analysis result"""
    trend: str = "neutral"  # bullish, bearish, neutral
    trend_strength: float = 0.0
    
    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)
    
    structure_break: bool = False
    break_type: str = ""  # 'BOS' (break of structure) or 'CHoCH' (change of character)
    break_direction: str = ""  # 'bullish' or 'bearish'
    
    order_blocks: List[OrderBlock] = field(default_factory=list)
    liquidity_zones: List[LiquidityZone] = field(default_factory=list)
    supply_demand_zones: List[SupplyDemandZone] = field(default_factory=list)
    
    alignment_score: float = 0.0  # -1 to +1 for QuantumScorer integration
    
    key_levels: List[Tuple[float, str]] = field(default_factory=list)
    narrative: str = ""
    
    def to_dict(self) -> dict:
        return {
            'trend': self.trend,
            'trend_strength': round(self.trend_strength, 3),
            'structure_break': self.structure_break,
            'break_type': self.break_type,
            'break_direction': self.break_direction,
            'order_blocks': len(self.order_blocks),
            'liquidity_zones': len(self.liquidity_zones),
            'sd_zones': len(self.supply_demand_zones),
            'alignment_score': round(self.alignment_score, 3),
            'narrative': self.narrative,
        }


class MarketStructureAnalyzer:
    """
    Analyzes price action for real trading edge beyond lagging indicators.
    
    Data Flow:
    1. Detect swing highs/lows from price action
    2. Determine trend structure (HH/HL or LH/LL)
    3. Detect structure breaks (BOS/CHoCH)
    4. Find order blocks (last opposite candle before impulse)
    5. Map liquidity zones (clusters of equal highs/lows)
    6. Identify supply/demand zones (strong rejection areas)
    7. Produce alignment_score for QuantumScorer integration
    """
    
    def __init__(self, swing_lookback: int = 5):
        self.swing_lookback = swing_lookback
    
    def analyze(self, df: pd.DataFrame, signal_type: str = 'buy') -> StructureAnalysis:
        """
        Full market structure analysis.
        
        Args:
            df: OHLCV DataFrame with at least 50 rows
            signal_type: 'buy' or 'sell' - to calculate alignment
        
        Returns:
            StructureAnalysis with all detected structures
        """
        result = StructureAnalysis()
        
        if df.empty or len(df) < 30:
            result.narrative = "Insufficient data for structure analysis"
            return result
        
        # Step 1: Detect swing points
        result.swing_highs = self._detect_swing_highs(df)
        result.swing_lows = self._detect_swing_lows(df)
        
        # Step 2: Determine trend structure
        trend, strength = self._analyze_trend_structure(result.swing_highs, result.swing_lows)
        result.trend = trend
        result.trend_strength = strength
        
        # Step 3: Detect structure breaks
        sb, sb_type, sb_dir = self._detect_structure_break(df, result.swing_highs, result.swing_lows)
        result.structure_break = sb
        result.break_type = sb_type
        result.break_direction = sb_dir
        
        # Step 4: Find order blocks
        result.order_blocks = self._find_order_blocks(df)
        
        # Step 5: Map liquidity zones
        result.liquidity_zones = self._find_liquidity_zones(df, result.swing_highs, result.swing_lows)
        
        # Step 6: Supply/Demand zones
        result.supply_demand_zones = self._find_supply_demand_zones(df)
        
        # Step 7: Key levels compilation
        result.key_levels = self._compile_key_levels(df, result)
        
        # Step 8: Calculate alignment score for QuantumScorer
        result.alignment_score = self._calculate_alignment(result, signal_type, df)
        
        # Step 9: Generate narrative
        result.narrative = self._generate_narrative(result, signal_type)
        
        return result
    
    def _detect_swing_highs(self, df: pd.DataFrame) -> List[SwingPoint]:
        """Detect swing highs using fractal method"""
        swings = []
        lb = self.swing_lookback
        highs = df['high'].values
        
        for i in range(lb, len(highs) - lb):
            is_swing = True
            for j in range(1, lb + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing = False
                    break
            
            if is_swing:
                # Determine strength (how many bars it's higher than)
                strength = 0
                for k in range(1, min(lb * 2, len(highs) - i)):
                    if highs[i] > highs[i - min(k, i)] and i + k < len(highs) and highs[i] > highs[i + k]:
                        strength += 1
                    else:
                        break
                
                swings.append(SwingPoint(
                    index=i,
                    price=highs[i],
                    type='high',
                    strength=max(1, strength)
                ))
        
        return swings
    
    def _detect_swing_lows(self, df: pd.DataFrame) -> List[SwingPoint]:
        """Detect swing lows using fractal method"""
        swings = []
        lb = self.swing_lookback
        lows = df['low'].values
        
        for i in range(lb, len(lows) - lb):
            is_swing = True
            for j in range(1, lb + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing = False
                    break
            
            if is_swing:
                strength = 0
                for k in range(1, min(lb * 2, len(lows) - i)):
                    if lows[i] < lows[i - min(k, i)] and i + k < len(lows) and lows[i] < lows[i + k]:
                        strength += 1
                    else:
                        break
                
                swings.append(SwingPoint(
                    index=i,
                    price=lows[i],
                    type='low',
                    strength=max(1, strength)
                ))
        
        return swings
    
    def _analyze_trend_structure(self, swing_highs: List[SwingPoint], 
                                  swing_lows: List[SwingPoint]) -> Tuple[str, float]:
        """
        Analyze trend from swing structure.
        Bullish: Higher Highs + Higher Lows
        Bearish: Lower Highs + Lower Lows
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "neutral", 0.0
        
        # Check last 4 swing points for pattern
        recent_highs = swing_highs[-4:] if len(swing_highs) >= 4 else swing_highs
        recent_lows = swing_lows[-4:] if len(swing_lows) >= 4 else swing_lows
        
        # Count higher highs
        hh_count = 0
        for i in range(1, len(recent_highs)):
            if recent_highs[i].price > recent_highs[i-1].price:
                hh_count += 1
        
        # Count higher lows
        hl_count = 0
        for i in range(1, len(recent_lows)):
            if recent_lows[i].price > recent_lows[i-1].price:
                hl_count += 1
        
        # Count lower highs
        lh_count = 0
        for i in range(1, len(recent_highs)):
            if recent_highs[i].price < recent_highs[i-1].price:
                lh_count += 1
        
        # Count lower lows
        ll_count = 0
        for i in range(1, len(recent_lows)):
            if recent_lows[i].price < recent_lows[i-1].price:
                ll_count += 1
        
        total = max(len(recent_highs) + len(recent_lows) - 2, 1)
        bullish = (hh_count + hl_count) / total
        bearish = (lh_count + ll_count) / total
        
        if bullish > 0.6:
            return "bullish", bullish
        elif bearish > 0.6:
            return "bearish", bearish
        else:
            return "neutral", max(bullish, bearish)
    
    def _detect_structure_break(self, df: pd.DataFrame,
                                 swing_highs: List[SwingPoint],
                                 swing_lows: List[SwingPoint]) -> Tuple[bool, str, str]:
        """
        Detect Break of Structure (BOS) or Change of Character (CHoCH).
        
        BOS: Price breaks the last swing in trend direction (continuation)
        CHoCH: Price breaks the last swing AGAINST trend direction (reversal)
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return False, "", ""
        
        current_price = df['close'].iloc[-1]
        last_high = swing_highs[-1].price
        prev_high = swing_highs[-2].price if len(swing_highs) >= 2 else last_high
        last_low = swing_lows[-1].price
        prev_low = swing_lows[-2].price if len(swing_lows) >= 2 else last_low
        
        # Check recent bars for break
        recent_high = df['high'].tail(3).max()
        recent_low = df['low'].tail(3).min()
        
        # Bullish BOS: price breaks above last swing high in an uptrend
        if recent_high > last_high:
            if prev_high < last_high:  # Was already trending up
                return True, "BOS", "bullish"
            else:  # Was trending down, now breaking up = CHoCH
                return True, "CHoCH", "bullish"
        
        # Bearish BOS: price breaks below last swing low in a downtrend
        if recent_low < last_low:
            if prev_low > last_low:  # Was already trending down
                return True, "BOS", "bearish"
            else:  # Was trending up, now breaking down = CHoCH
                return True, "CHoCH", "bearish"
        
        return False, "", ""
    
    def _find_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        Find order blocks: the last opposite-color candle before a strong impulse move.
        
        Bullish OB: Last bearish candle before a strong bullish move
        Bearish OB: Last bullish candle before a strong bearish move
        """
        order_blocks = []
        
        if len(df) < 20:
            return order_blocks
        
        closes = df['close'].values
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # ATR for measuring "strong" moves
        atr_vals = df['atr'].values if 'atr' in df.columns else np.full(len(df), np.std(closes) * 0.01)
        
        for i in range(5, len(df) - 3):
            atr = atr_vals[i] if not np.isnan(atr_vals[i]) else abs(closes[i] * 0.01)
            if atr == 0:
                continue
            
            # Check for strong impulse after this candle (next 3 candles)
            move = closes[min(i+3, len(closes)-1)] - closes[i]
            
            is_bearish_candle = closes[i] < opens[i]
            is_bullish_candle = closes[i] > opens[i]
            
            # Bullish Order Block: bearish candle followed by strong up move
            if is_bearish_candle and move > atr * 2.0:
                ob = OrderBlock(
                    top=opens[i],
                    bottom=closes[i],
                    type='bullish',
                    strength=min(1.0, move / (atr * 3)),
                    index=i
                )
                # Check if price has come back to test it
                for j in range(i+4, len(closes)):
                    if lows[j] <= ob.top and lows[j] >= ob.bottom:
                        ob.tested = True
                        break
                
                order_blocks.append(ob)
            
            # Bearish Order Block: bullish candle followed by strong down move
            elif is_bullish_candle and move < -atr * 2.0:
                ob = OrderBlock(
                    top=closes[i],
                    bottom=opens[i],
                    type='bearish',
                    strength=min(1.0, abs(move) / (atr * 3)),
                    index=i
                )
                for j in range(i+4, len(closes)):
                    if highs[j] >= ob.bottom and highs[j] <= ob.top:
                        ob.tested = True
                        break
                
                order_blocks.append(ob)
        
        # Keep only most recent and strongest
        order_blocks.sort(key=lambda x: (x.index, x.strength), reverse=True)
        return order_blocks[:10]
    
    def _find_liquidity_zones(self, df: pd.DataFrame,
                               swing_highs: List[SwingPoint],
                               swing_lows: List[SwingPoint]) -> List[LiquidityZone]:
        """
        Find liquidity zones where stop losses are likely clustered.
        
        Buy-side liquidity: Above equal/cluster highs (stop losses of shorts)
        Sell-side liquidity: Below equal/cluster lows (stop losses of longs)
        """
        zones = []
        current_price = df['close'].iloc[-1]
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return zones
        
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else abs(current_price * 0.01)
        if pd.isna(atr) or atr == 0:
            atr = abs(current_price * 0.01)
        
        tolerance = atr * 0.5
        
        # Find clusters of equal highs (buy-side liquidity)
        high_prices = [sh.price for sh in swing_highs]
        for i, price in enumerate(high_prices):
            cluster_count = sum(1 for p in high_prices if abs(p - price) < tolerance)
            if cluster_count >= 2:
                swept = current_price > price
                zones.append(LiquidityZone(
                    price=price,
                    type='buy_side',
                    strength=min(1.0, cluster_count / 4),
                    swept=swept
                ))
        
        # Find clusters of equal lows (sell-side liquidity)
        low_prices = [sl.price for sl in swing_lows]
        for i, price in enumerate(low_prices):
            cluster_count = sum(1 for p in low_prices if abs(p - price) < tolerance)
            if cluster_count >= 2:
                swept = current_price < price
                zones.append(LiquidityZone(
                    price=price,
                    type='sell_side',
                    strength=min(1.0, cluster_count / 4),
                    swept=swept
                ))
        
        # Deduplicate by proximity
        unique_zones = []
        for zone in zones:
            is_dup = False
            for uz in unique_zones:
                if abs(uz.price - zone.price) < tolerance and uz.type == zone.type:
                    is_dup = True
                    if zone.strength > uz.strength:
                        uz.strength = zone.strength
                    break
            if not is_dup:
                unique_zones.append(zone)
        
        return unique_zones
    
    def _find_supply_demand_zones(self, df: pd.DataFrame) -> List[SupplyDemandZone]:
        """
        Find supply and demand zones from strong price rejections.
        
        Demand zone: Area where price dropped and then reversed strongly upward
        Supply zone: Area where price rose and then reversed strongly downward
        """
        zones = []
        
        if len(df) < 20:
            return zones
        
        closes = df['close'].values
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        atr_vals = df['atr'].values if 'atr' in df.columns else np.full(len(df), np.std(closes) * 0.01)
        
        for i in range(3, len(df) - 3):
            atr = atr_vals[i] if not np.isnan(atr_vals[i]) else abs(closes[i] * 0.01)
            if atr == 0:
                continue
            
            # Look for strong rejection candles (long wicks)
            body_size = abs(closes[i] - opens[i])
            upper_wick = highs[i] - max(closes[i], opens[i])
            lower_wick = min(closes[i], opens[i]) - lows[i]
            candle_range = highs[i] - lows[i]
            
            if candle_range == 0:
                continue
            
            # Demand zone: long lower wick + bullish close + follow-through
            if lower_wick > body_size * 1.5 and closes[i] > opens[i]:
                follow_through = closes[min(i+2, len(closes)-1)] - closes[i]
                if follow_through > atr * 0.5:
                    zone = SupplyDemandZone(
                        top=min(closes[i], opens[i]),
                        bottom=lows[i],
                        type='demand',
                        strength=min(1.0, (lower_wick / candle_range) * (follow_through / atr)),
                    )
                    # Count how many times price touched this zone later
                    for j in range(i+1, len(closes)):
                        if lows[j] <= zone.top and lows[j] >= zone.bottom:
                            zone.touches += 1
                    
                    zones.append(zone)
            
            # Supply zone: long upper wick + bearish close + follow-through
            if upper_wick > body_size * 1.5 and closes[i] < opens[i]:
                follow_through = closes[i] - closes[min(i+2, len(closes)-1)]
                if follow_through > atr * 0.5:
                    zone = SupplyDemandZone(
                        top=highs[i],
                        bottom=max(closes[i], opens[i]),
                        type='supply',
                        strength=min(1.0, (upper_wick / candle_range) * (follow_through / atr)),
                    )
                    for j in range(i+1, len(closes)):
                        if highs[j] >= zone.bottom and highs[j] <= zone.top:
                            zone.touches += 1
                    
                    zones.append(zone)
        
        # Keep strongest and most recent
        zones.sort(key=lambda x: x.strength, reverse=True)
        return zones[:8]
    
    def _compile_key_levels(self, df: pd.DataFrame, result: StructureAnalysis) -> List[Tuple[float, str]]:
        """Compile all significant price levels"""
        levels = []
        
        # Swing highs/lows
        for sh in result.swing_highs[-3:]:
            levels.append((sh.price, f"Swing High (str:{sh.strength})"))
        for sl in result.swing_lows[-3:]:
            levels.append((sl.price, f"Swing Low (str:{sl.strength})"))
        
        # Order block zones
        for ob in result.order_blocks[:3]:
            mid = (ob.top + ob.bottom) / 2
            levels.append((mid, f"{'Bullish' if ob.type=='bullish' else 'Bearish'} OB"))
        
        # Liquidity zones
        for lz in result.liquidity_zones[:3]:
            levels.append((lz.price, f"{'Buy' if lz.type=='buy_side' else 'Sell'}-side Liquidity"))
        
        # S/D zones
        for sd in result.supply_demand_zones[:3]:
            mid = (sd.top + sd.bottom) / 2
            levels.append((mid, f"{'Demand' if sd.type=='demand' else 'Supply'} Zone"))
        
        levels.sort(key=lambda x: x[0])
        return levels
    
    def _calculate_alignment(self, result: StructureAnalysis, 
                              signal_type: str, df: pd.DataFrame) -> float:
        """
        Calculate how well the signal aligns with market structure.
        Returns -1.0 (strongly against) to +1.0 (strongly aligned).
        This feeds directly into QuantumScorer.
        """
        is_buy = signal_type.lower() == 'buy'
        score = 0.0
        factors = 0
        
        # 1. Trend alignment (+/- 0.3)
        if result.trend == 'bullish' and is_buy:
            score += 0.3 * result.trend_strength
        elif result.trend == 'bearish' and not is_buy:
            score += 0.3 * result.trend_strength
        elif result.trend != 'neutral':
            score -= 0.2 * result.trend_strength
        factors += 1
        
        # 2. Structure break alignment (+/- 0.25)
        if result.structure_break:
            if result.break_direction == 'bullish' and is_buy:
                score += 0.25
                if result.break_type == 'CHoCH':
                    score += 0.1  # CHoCH is a stronger signal
            elif result.break_direction == 'bearish' and not is_buy:
                score += 0.25
                if result.break_type == 'CHoCH':
                    score += 0.1
            else:
                score -= 0.15
        factors += 1
        
        # 3. Order block proximity (+/- 0.2)
        current_price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else abs(current_price * 0.01)
        if pd.isna(atr) or atr == 0:
            atr = abs(current_price * 0.01)
        
        for ob in result.order_blocks[:3]:
            if ob.type == 'bullish' and is_buy:
                if ob.bottom <= current_price <= ob.top + atr:
                    score += 0.2 * ob.strength
                    break
            elif ob.type == 'bearish' and not is_buy:
                if ob.bottom - atr <= current_price <= ob.top:
                    score += 0.2 * ob.strength
                    break
        factors += 1
        
        # 4. Liquidity consideration (+/- 0.15)
        for lz in result.liquidity_zones:
            dist = abs(current_price - lz.price) / atr
            if dist < 2:  # Near a liquidity zone
                if lz.type == 'sell_side' and is_buy and not lz.swept:
                    score -= 0.1  # Risk of stop hunt below
                elif lz.type == 'buy_side' and not is_buy and not lz.swept:
                    score -= 0.1
                elif lz.swept:
                    score += 0.1  # Liquidity already taken = good
        factors += 1
        
        # 5. Supply/Demand zone alignment (+/- 0.15)
        for sd in result.supply_demand_zones[:3]:
            if sd.type == 'demand' and is_buy:
                if sd.bottom <= current_price <= sd.top + atr:
                    score += 0.15 * sd.strength
                    break
            elif sd.type == 'supply' and not is_buy:
                if sd.bottom - atr <= current_price <= sd.top:
                    score += 0.15 * sd.strength
                    break
        factors += 1
        
        return np.clip(score, -1.0, 1.0)
    
    def _generate_narrative(self, result: StructureAnalysis, signal_type: str) -> str:
        """Generate human-readable market structure narrative"""
        parts = []
        
        is_buy = signal_type.lower() == 'buy'
        
        # Trend
        if result.trend == 'bullish':
            parts.append("Uptrend structure (HH/HL)")
        elif result.trend == 'bearish':
            parts.append("Downtrend structure (LH/LL)")
        else:
            parts.append("No clear trend structure")
        
        # Structure break
        if result.structure_break:
            parts.append(f"{result.break_type} {result.break_direction}")
        
        # Order blocks
        active_obs = [ob for ob in result.order_blocks if not ob.tested]
        if active_obs:
            types = set(ob.type for ob in active_obs[:3])
            parts.append(f"Active OBs: {', '.join(types)}")
        
        # Alignment
        if result.alignment_score > 0.3:
            parts.append("Structure SUPPORTS signal")
        elif result.alignment_score < -0.2:
            parts.append("Structure AGAINST signal")
        else:
            parts.append("Structure neutral")
        
        return " | ".join(parts)
