"""
QuantumScorer v1.0 - Probabilistic Weighted Confidence System
No hard cutoffs. Sigmoid-based scoring with dynamic weighting.
Outputs normalized probability (0-1) of trade success.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class ScoringBreakdown:
    """Detailed breakdown of how a score was calculated"""
    final_score: float = 0.0
    raw_scores: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    weighted_scores: Dict[str, float] = field(default_factory=dict)
    risk_reward_ratio: float = 0.0
    volatility_regime: str = "normal"
    trend_alignment: float = 0.0
    confirmation_count: int = 0
    total_factors: int = 0
    edge_description: str = ""
    
    def to_dict(self) -> dict:
        return {
            'final_score': round(self.final_score, 4),
            'risk_reward_ratio': round(self.risk_reward_ratio, 2),
            'volatility_regime': self.volatility_regime,
            'trend_alignment': round(self.trend_alignment, 4),
            'confirmations': f"{self.confirmation_count}/{self.total_factors}",
            'edge': self.edge_description,
            'top_factors': sorted(
                self.weighted_scores.items(), key=lambda x: abs(x[1]), reverse=True
            )[:5]
        }


class QuantumScorer:
    """
    Probabilistic confidence scoring engine.
    
    Architecture:
    1. Each factor produces a raw score [-1, +1] (bearish to bullish)
    2. Factors are weighted dynamically based on market regime
    3. Weighted scores are combined using sigmoid normalization
    4. Risk/reward and volatility apply final multipliers
    5. Output: probability 0.0 to 1.0 (0.5 = neutral)
    
    No hard cutoffs anywhere. Every signal gets a score.
    """
    
    # Base weights for each scoring factor (sum to ~1.0)
    BASE_WEIGHTS = {
        # Trend factors (40%)
        'ema_alignment': 0.10,
        'trend_structure': 0.12,
        'adx_strength': 0.08,
        'sma200_position': 0.10,
        
        # Momentum factors (30%)
        'rsi_signal': 0.08,
        'macd_signal': 0.08,
        'stochastic': 0.06,
        'momentum_roc': 0.08,
        
        # Volatility & Volume factors (15%)
        'bollinger_position': 0.06,
        'volatility_regime': 0.05,
        'volume_confirmation': 0.04,
        
        # Structure factors (15%)
        'support_resistance': 0.06,
        'fibonacci_proximity': 0.04,
        'risk_reward': 0.05,
    }
    
    # Dynamic weight adjustments per market regime
    REGIME_WEIGHT_ADJUSTMENTS = {
        'trending': {
            'ema_alignment': 1.5,
            'trend_structure': 1.5,
            'adx_strength': 1.3,
            'rsi_signal': 0.7,  # RSI less useful in trends
            'bollinger_position': 0.6,
        },
        'ranging': {
            'ema_alignment': 0.6,
            'trend_structure': 0.7,
            'rsi_signal': 1.5,  # RSI great in ranges
            'bollinger_position': 1.4,
            'stochastic': 1.3,
            'support_resistance': 1.5,
        },
        'volatile': {
            'volatility_regime': 1.5,
            'risk_reward': 1.4,
            'adx_strength': 1.2,
            'bollinger_position': 0.7,
        },
        'normal': {}  # Use base weights
    }
    
    def __init__(self):
        self.scoring_history: List[dict] = []
        self._load_history()
    
    def _load_history(self):
        """Load scoring history from disk"""
        try:
            if os.path.exists('scoring_history.json'):
                with open('scoring_history.json', 'r') as f:
                    self.scoring_history = json.load(f)
        except Exception:
            self.scoring_history = []
    
    def _save_history(self):
        """Persist scoring history"""
        try:
            # Keep last 1000 scores
            history = self.scoring_history[-1000:]
            with open('scoring_history.json', 'w') as f:
                json.dump(history, f)
        except Exception as e:
            logger.warning(f"Could not save scoring history: {e}")
    
    @staticmethod
    def _sigmoid(x: float, steepness: float = 4.0) -> float:
        """Smooth sigmoid: maps any value to (0, 1). steepness controls curve shape."""
        return 1.0 / (1.0 + np.exp(-steepness * x))
    
    @staticmethod
    def _soft_score(value: float, center: float, width: float, direction: str = 'lower_better') -> float:
        """
        Soft scoring function. No hard cutoffs.
        Returns -1 to +1 based on how far value is from center.
        direction: 'lower_better' (e.g., RSI for buy) or 'higher_better'
        """
        deviation = (value - center) / max(width, 0.001)
        if direction == 'lower_better':
            return -np.tanh(deviation)
        else:
            return np.tanh(deviation)
    
    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detect current market regime: trending, ranging, volatile, normal"""
        if len(df) < 50:
            return 'normal'
        
        close = df['close']
        
        # ADX for trend strength
        adx = df['adx'].iloc[-1] if 'adx' in df.columns else 0
        if pd.isna(adx):
            adx = 0
        
        # Volatility via ATR ratio
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else 0
        avg_atr = df['atr'].rolling(50).mean().iloc[-1] if 'atr' in df.columns else 0
        if pd.isna(avg_atr) or avg_atr == 0:
            vol_ratio = 1.0
        else:
            vol_ratio = atr / avg_atr
        
        # Price range compression (Bollinger Band width)
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            bb_width = (df['bb_upper'].iloc[-1] - df['bb_lower'].iloc[-1]) / close.iloc[-1]
            avg_bb_width = ((df['bb_upper'] - df['bb_lower']) / close).rolling(50).mean().iloc[-1]
            if pd.isna(avg_bb_width) or avg_bb_width == 0:
                bb_ratio = 1.0
            else:
                bb_ratio = bb_width / avg_bb_width
        else:
            bb_ratio = 1.0
        
        # Classification
        if adx > 25 and vol_ratio < 1.5:
            return 'trending'
        elif adx < 20 and bb_ratio < 0.8:
            return 'ranging'
        elif vol_ratio > 1.5 or bb_ratio > 1.5:
            return 'volatile'
        else:
            return 'normal'
    
    def _get_dynamic_weights(self, regime: str) -> Dict[str, float]:
        """Get dynamically adjusted weights based on market regime"""
        weights = dict(self.BASE_WEIGHTS)
        adjustments = self.REGIME_WEIGHT_ADJUSTMENTS.get(regime, {})
        
        for factor, mult in adjustments.items():
            if factor in weights:
                weights[factor] *= mult
        
        # Normalize so weights sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def score_signal(self, df: pd.DataFrame, signal_type: str, 
                     entry_price: float, stop_loss: float, take_profit: float,
                     symbol: str = '', strategy: str = '',
                     market_structure: Optional[dict] = None) -> ScoringBreakdown:
        """
        Score a trading signal with probabilistic weighted confidence.
        
        Args:
            df: DataFrame with indicators computed
            signal_type: 'buy' or 'sell'
            entry_price, stop_loss, take_profit: Trade levels
            symbol: Instrument name
            strategy: Strategy that generated the signal
            market_structure: Optional dict from MarketStructureAnalyzer
        
        Returns:
            ScoringBreakdown with final_score (0-1) and full details
        """
        breakdown = ScoringBreakdown()
        
        if df.empty or len(df) < 30:
            breakdown.final_score = 0.5
            breakdown.edge_description = "Insufficient data"
            return breakdown
        
        last = df.iloc[-1]
        is_buy = signal_type.lower() == 'buy'
        direction = 1.0 if is_buy else -1.0
        
        # Detect regime and get weights
        regime = self.detect_market_regime(df)
        breakdown.volatility_regime = regime
        weights = self._get_dynamic_weights(regime)
        breakdown.weights = weights
        
        raw_scores = {}
        
        # ===== TREND FACTORS =====
        
        # 1. EMA Alignment
        if 'ema_20' in df.columns and 'ema_50' in df.columns:
            ema20, ema50 = last['ema_20'], last['ema_50']
            if not pd.isna(ema20) and not pd.isna(ema50) and ema50 != 0:
                ema_diff = (ema20 - ema50) / ema50
                raw_scores['ema_alignment'] = np.tanh(ema_diff * 500) * direction
            else:
                raw_scores['ema_alignment'] = 0.0
        else:
            raw_scores['ema_alignment'] = 0.0
        
        # 2. Trend Structure (higher highs/lows or lower highs/lows)
        if len(df) >= 20:
            recent = df.tail(20)
            highs = recent['high'].values
            lows = recent['low'].values
            
            # Count higher highs and higher lows
            hh_count = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
            hl_count = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
            ll_count = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
            lh_count = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i-1])
            
            total_bars = len(highs) - 1
            if total_bars > 0:
                bullish_structure = (hh_count + hl_count) / (2 * total_bars)
                bearish_structure = (ll_count + lh_count) / (2 * total_bars)
                structure_score = (bullish_structure - bearish_structure) * direction * 2
                raw_scores['trend_structure'] = np.clip(structure_score, -1, 1)
            else:
                raw_scores['trend_structure'] = 0.0
        else:
            raw_scores['trend_structure'] = 0.0
        
        # 3. ADX Strength
        adx = last.get('adx', 0)
        if pd.isna(adx):
            adx = 0
        # ADX > 25 = strong trend (good for trend trades)
        # If we're trend-following, high ADX is good regardless of direction
        adx_score = np.tanh((adx - 20) / 15)  # Centered at 20, positive above
        # But only positive if trend direction matches signal direction
        if 'plus_di' in df.columns and 'minus_di' in df.columns:
            plus_di = last.get('plus_di', 0)
            minus_di = last.get('minus_di', 0)
            if pd.isna(plus_di): plus_di = 0
            if pd.isna(minus_di): minus_di = 0
            di_direction = 1.0 if plus_di > minus_di else -1.0
            raw_scores['adx_strength'] = adx_score * di_direction * direction
        else:
            raw_scores['adx_strength'] = adx_score * 0.5  # Reduced if no DI info
        
        # 4. SMA 200 Position
        sma200 = last.get('sma_200', None)
        if sma200 is not None and not pd.isna(sma200) and sma200 != 0:
            price_vs_sma = (last['close'] - sma200) / sma200
            raw_scores['sma200_position'] = np.tanh(price_vs_sma * 100) * direction
        else:
            raw_scores['sma200_position'] = 0.0
        
        # ===== MOMENTUM FACTORS =====
        
        # 5. RSI Signal
        rsi = last.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        if is_buy:
            # For buy: RSI < 30 = strong buy, RSI > 70 = bad for buy
            raw_scores['rsi_signal'] = self._soft_score(rsi, 50, 25, 'lower_better')
        else:
            # For sell: RSI > 70 = strong sell, RSI < 30 = bad for sell
            raw_scores['rsi_signal'] = self._soft_score(rsi, 50, 25, 'higher_better')
        
        # 6. MACD Signal
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd = last.get('macd', 0)
            macd_sig = last.get('macd_signal', 0)
            if pd.isna(macd): macd = 0
            if pd.isna(macd_sig): macd_sig = 0
            
            macd_diff = macd - macd_sig
            # Normalize by ATR for cross-instrument comparison
            atr = last.get('atr', 1)
            if pd.isna(atr) or atr == 0:
                atr = abs(last['close'] * 0.01)
            
            normalized_macd = macd_diff / atr
            raw_scores['macd_signal'] = np.tanh(normalized_macd * 5) * direction
            
            # Bonus for fresh crossover
            if len(df) >= 2:
                prev = df.iloc[-2]
                prev_macd = prev.get('macd', 0)
                prev_sig = prev.get('macd_signal', 0)
                if pd.isna(prev_macd): prev_macd = 0
                if pd.isna(prev_sig): prev_sig = 0
                
                if is_buy and macd > macd_sig and prev_macd <= prev_sig:
                    raw_scores['macd_signal'] = min(1.0, raw_scores['macd_signal'] + 0.3)
                elif not is_buy and macd < macd_sig and prev_macd >= prev_sig:
                    raw_scores['macd_signal'] = min(1.0, raw_scores['macd_signal'] + 0.3)
        else:
            raw_scores['macd_signal'] = 0.0
        
        # 7. Stochastic
        stoch_k = last.get('stoch_k', 50)
        stoch_d = last.get('stoch_d', 50)
        if pd.isna(stoch_k): stoch_k = 50
        if pd.isna(stoch_d): stoch_d = 50
        
        if is_buy:
            raw_scores['stochastic'] = self._soft_score(stoch_k, 50, 30, 'lower_better')
        else:
            raw_scores['stochastic'] = self._soft_score(stoch_k, 50, 30, 'higher_better')
        
        # 8. Momentum (Rate of Change)
        mom = last.get('momentum', 0)
        if pd.isna(mom):
            mom = 0
        raw_scores['momentum_roc'] = np.tanh(mom * 2) * direction
        
        # ===== VOLATILITY & VOLUME FACTORS =====
        
        # 9. Bollinger Band Position
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            bb_upper = last.get('bb_upper', 0)
            bb_lower = last.get('bb_lower', 0)
            if not pd.isna(bb_upper) and not pd.isna(bb_lower) and bb_upper != bb_lower:
                bb_pos = (last['close'] - bb_lower) / (bb_upper - bb_lower)
                if is_buy:
                    # Buy near lower band = good
                    raw_scores['bollinger_position'] = self._soft_score(bb_pos, 0.5, 0.4, 'lower_better')
                else:
                    raw_scores['bollinger_position'] = self._soft_score(bb_pos, 0.5, 0.4, 'higher_better')
            else:
                raw_scores['bollinger_position'] = 0.0
        else:
            raw_scores['bollinger_position'] = 0.0
        
        # 10. Volatility Regime
        atr_val = last.get('atr', 0)
        if pd.isna(atr_val):
            atr_val = 0
        avg_atr = df['atr'].rolling(50).mean().iloc[-1] if 'atr' in df.columns else atr_val
        if pd.isna(avg_atr) or avg_atr == 0:
            vol_score = 0.0
        else:
            vol_ratio = atr_val / avg_atr
            # Normal volatility is best. Too high or too low reduces score
            vol_score = 1.0 - abs(vol_ratio - 1.0)
            vol_score = np.clip(vol_score, -0.5, 1.0)
        raw_scores['volatility_regime'] = vol_score
        
        # 11. Volume Confirmation
        if 'volume' in df.columns and 'volume_ma' in df.columns:
            vol = last.get('volume', 0)
            vol_ma = last.get('volume_ma', 0)
            if not pd.isna(vol) and not pd.isna(vol_ma) and vol_ma > 0:
                vol_ratio = vol / vol_ma
                # Above average volume = confirmation
                raw_scores['volume_confirmation'] = np.tanh((vol_ratio - 1.0) * 2)
            else:
                raw_scores['volume_confirmation'] = 0.0
        else:
            raw_scores['volume_confirmation'] = 0.0
        
        # ===== STRUCTURE FACTORS =====
        
        # 12. Support/Resistance Proximity
        recent = df.tail(50)
        support = recent['low'].min()
        resistance = recent['high'].max()
        price = last['close']
        price_range = resistance - support
        
        if price_range > 0:
            position_in_range = (price - support) / price_range
            if is_buy:
                # Buy near support = good
                raw_scores['support_resistance'] = self._soft_score(position_in_range, 0.5, 0.4, 'lower_better')
            else:
                raw_scores['support_resistance'] = self._soft_score(position_in_range, 0.5, 0.4, 'higher_better')
        else:
            raw_scores['support_resistance'] = 0.0
        
        # 13. Fibonacci Proximity
        fib_618 = last.get('fib_618', None)
        fib_382 = last.get('fib_382', None)
        fib_score = 0.0
        
        if fib_618 is not None and not pd.isna(fib_618):
            dist_618 = abs(price - fib_618) / price
            if dist_618 < 0.005:  # Within 0.5% of 61.8 fib
                fib_score = 0.6
        
        if fib_382 is not None and not pd.isna(fib_382):
            dist_382 = abs(price - fib_382) / price
            if dist_382 < 0.005:
                fib_score = max(fib_score, 0.5)
        
        raw_scores['fibonacci_proximity'] = fib_score
        
        # 14. Risk/Reward Ratio
        if stop_loss > 0 and take_profit > 0 and entry_price > 0:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            
            if risk > 0:
                rr_ratio = reward / risk
                breakdown.risk_reward_ratio = rr_ratio
                # R:R of 2:1 = score of ~0.7, 3:1 = ~0.9, 1:1 = ~0.0
                raw_scores['risk_reward'] = np.tanh((rr_ratio - 1.0) / 1.5)
            else:
                raw_scores['risk_reward'] = 0.0
        else:
            raw_scores['risk_reward'] = 0.0
        
        # ===== MARKET STRUCTURE BONUS =====
        if market_structure:
            # Apply bonuses from MarketStructureAnalyzer
            structure_bonus = market_structure.get('alignment_score', 0)
            # Blend into trend_structure score
            raw_scores['trend_structure'] = np.clip(
                raw_scores['trend_structure'] + structure_bonus * 0.3, -1, 1
            )
        
        breakdown.raw_scores = raw_scores
        
        # ===== COMPUTE WEIGHTED SCORE =====
        total_weighted = 0.0
        weighted_scores = {}
        
        for factor, raw in raw_scores.items():
            w = weights.get(factor, 0.0)
            ws = raw * w
            weighted_scores[factor] = ws
            total_weighted += ws
        
        breakdown.weighted_scores = weighted_scores
        
        # Count confirmations (factors agreeing with signal direction)
        confirmations = sum(1 for v in raw_scores.values() if v > 0.1)
        total_factors = len(raw_scores)
        breakdown.confirmation_count = confirmations
        breakdown.total_factors = total_factors
        
        # Confirmation bonus: more agreement = higher confidence
        confirmation_ratio = confirmations / max(total_factors, 1)
        confirmation_bonus = (confirmation_ratio - 0.5) * 0.2
        
        # ===== SIGMOID NORMALIZATION =====
        # Map weighted sum to 0-1 probability
        combined = total_weighted + confirmation_bonus
        
        # Sigmoid with steepness of 6: maps ~[-0.5, +0.5] to ~[0.05, 0.95]
        final_score = self._sigmoid(combined, steepness=6.0)
        
        # Trend alignment
        breakdown.trend_alignment = raw_scores.get('ema_alignment', 0) + raw_scores.get('trend_structure', 0)
        
        # Build edge description
        top_positive = sorted(
            [(k, v) for k, v in raw_scores.items() if v > 0.2],
            key=lambda x: x[1], reverse=True
        )[:3]
        top_negative = sorted(
            [(k, v) for k, v in raw_scores.items() if v < -0.2],
            key=lambda x: x[1]
        )[:2]
        
        edge_parts = []
        if top_positive:
            edge_parts.append(f"Strengths: {', '.join(f[0].replace('_',' ').title() for f in top_positive)}")
        if top_negative:
            edge_parts.append(f"Risks: {', '.join(f[0].replace('_',' ').title() for f in top_negative)}")
        edge_parts.append(f"Regime: {regime}")
        edge_parts.append(f"R:R {breakdown.risk_reward_ratio:.1f}:1")
        breakdown.edge_description = " | ".join(edge_parts)
        
        breakdown.final_score = final_score
        
        # Save to history
        self.scoring_history.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'strategy': strategy,
            'signal_type': signal_type,
            'final_score': round(final_score, 4),
            'regime': regime,
            'rr_ratio': round(breakdown.risk_reward_ratio, 2),
            'confirmations': confirmations,
            'total_factors': total_factors,
        })
        
        if len(self.scoring_history) % 10 == 0:
            self._save_history()
        
        return breakdown
    
    def get_trade_recommendation(self, score: float) -> Tuple[str, str]:
        """
        Convert score to human-readable recommendation.
        No hard cutoffs - returns recommendation with confidence level.
        """
        if score >= 0.85:
            return "STRONG ENTRY", "High probability setup. Multiple confirmations aligned."
        elif score >= 0.70:
            return "GOOD ENTRY", "Solid setup with good risk/reward."
        elif score >= 0.60:
            return "MODERATE ENTRY", "Decent setup but watch for confirmation."
        elif score >= 0.50:
            return "WEAK ENTRY", "Marginal edge. Consider reducing size."
        elif score >= 0.40:
            return "CAUTION", "Weak signal. High risk of failure."
        elif score >= 0.25:
            return "AVOID", "Poor probability. Multiple factors against."
        else:
            return "NO TRADE", "Strong counter-signal detected."
    
    def get_position_size_multiplier(self, score: float) -> float:
        """
        Dynamic position sizing based on confidence.
        Higher confidence = larger position (up to 1.0x base size).
        Lower confidence = smaller position.
        """
        if score >= 0.80:
            return 1.0
        elif score >= 0.65:
            return 0.75
        elif score >= 0.55:
            return 0.50
        elif score >= 0.45:
            return 0.25
        else:
            return 0.0  # Don't trade
