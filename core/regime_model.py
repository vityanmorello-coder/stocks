"""
Regime Model v1.0 - Market State Classification
Classifies market regimes to filter and adjust signal confidence.
Does NOT generate trade signals - only provides context.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn not available. Using rule-based regime detection.")


@dataclass
class RegimeState:
    """Current market regime state"""
    regime: str  # trending_up, trending_down, ranging, high_volatility, low_volatility, news_driven
    confidence: float  # 0-1, how confident in this regime
    stability_score: float  # 0-1, how stable is this regime
    regime_duration: int  # How many periods in this regime
    
    # Sub-classifications
    trend_strength: float  # 0-1
    volatility_level: float  # 0-1
    volume_regime: str  # high, normal, low
    
    # Regime characteristics
    is_trending: bool
    is_ranging: bool
    is_volatile: bool
    is_news_driven: bool
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class RegimeFeatureExtractor:
    """
    Extracts features for regime classification.
    
    Features:
    - ATR expansion/contraction
    - Volatility clustering
    - Trend strength (ADX-like)
    - Volume spikes
    - Price momentum
    - Range compression
    """
    
    def __init__(self, lookback: int = 50):
        self.lookback = lookback
    
    def extract(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Extract regime features from OHLCV data.
        
        Returns:
            Dictionary of features
        """
        if len(df) < self.lookback:
            return self._empty_features()
        
        recent = df.tail(self.lookback).copy()
        
        features = {}
        
        # ATR-based features
        features.update(self._extract_atr_features(recent))
        
        # Volatility features
        features.update(self._extract_volatility_features(recent))
        
        # Trend features
        features.update(self._extract_trend_features(recent))
        
        # Volume features
        features.update(self._extract_volume_features(recent))
        
        # Momentum features
        features.update(self._extract_momentum_features(recent))
        
        # Range features
        features.update(self._extract_range_features(recent))
        
        return features
    
    def _extract_atr_features(self, df: pd.DataFrame) -> Dict:
        """ATR expansion/contraction features"""
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # ATR expansion
        atr_current = atr.iloc[-1]
        atr_avg = atr.mean()
        atr_expansion = (atr_current / atr_avg) if atr_avg > 0 else 1.0
        
        # ATR trend
        atr_slope = (atr.iloc[-5:].mean() - atr.iloc[-15:-5].mean()) / (atr.iloc[-15:-5].mean() + 1e-8)
        
        return {
            'atr_expansion': atr_expansion,
            'atr_slope': atr_slope,
            'atr_percentile': self._percentile_rank(atr.values, atr_current)
        }
    
    def _extract_volatility_features(self, df: pd.DataFrame) -> Dict:
        """Volatility clustering and regime features"""
        returns = df['close'].pct_change()
        
        # Rolling volatility
        vol_short = returns.rolling(5).std()
        vol_medium = returns.rolling(20).std()
        vol_long = returns.rolling(50).std()
        
        # Volatility clustering (autocorrelation of squared returns)
        squared_returns = returns ** 2
        vol_clustering = squared_returns.rolling(20).corr(squared_returns.shift(1)).iloc[-1]
        vol_clustering = 0.0 if np.isnan(vol_clustering) else vol_clustering
        
        # Volatility regime
        vol_current = vol_short.iloc[-1]
        vol_avg = vol_long.mean()
        vol_ratio = (vol_current / vol_avg) if vol_avg > 0 else 1.0
        
        return {
            'volatility_ratio': vol_ratio,
            'volatility_clustering': vol_clustering,
            'volatility_trend': (vol_short.iloc[-5:].mean() - vol_medium.iloc[-5:].mean()) / (vol_medium.iloc[-5:].mean() + 1e-8)
        }
    
    def _extract_trend_features(self, df: pd.DataFrame) -> Dict:
        """Trend strength features (ADX-like)"""
        # Directional movement
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        # True range
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Smooth
        atr = tr.rolling(14).mean()
        plus_di = 100 * pd.Series(plus_dm).rolling(14).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(14).mean() / atr
        
        # ADX-like calculation
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)
        adx = dx.rolling(14).mean()
        
        # Trend strength
        trend_strength = adx.iloc[-1] / 100.0 if not np.isnan(adx.iloc[-1]) else 0.0
        
        # Trend direction consistency
        closes = df['close'].values
        up_moves = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
        trend_consistency = up_moves / (len(closes) - 1) if len(closes) > 1 else 0.5
        
        return {
            'trend_strength': trend_strength,
            'trend_consistency': trend_consistency,
            'trend_direction': 1.0 if trend_consistency > 0.6 else -1.0 if trend_consistency < 0.4 else 0.0
        }
    
    def _extract_volume_features(self, df: pd.DataFrame) -> Dict:
        """Volume regime features"""
        volume = df['volume'].values
        
        # Volume spikes
        vol_avg = np.mean(volume)
        vol_std = np.std(volume)
        vol_current = volume[-1]
        
        vol_spike = (vol_current - vol_avg) / (vol_std + 1e-8)
        
        # Volume trend
        vol_short = np.mean(volume[-5:])
        vol_long = np.mean(volume[-20:])
        vol_trend = (vol_short - vol_long) / (vol_long + 1e-8)
        
        # Volume consistency
        vol_cv = vol_std / (vol_avg + 1e-8)  # Coefficient of variation
        
        return {
            'volume_spike': vol_spike,
            'volume_trend': vol_trend,
            'volume_consistency': 1.0 - min(1.0, vol_cv)
        }
    
    def _extract_momentum_features(self, df: pd.DataFrame) -> Dict:
        """Price momentum features"""
        closes = df['close'].values
        
        # Rate of change
        roc_5 = (closes[-1] - closes[-6]) / (closes[-6] + 1e-8) if len(closes) > 5 else 0.0
        roc_10 = (closes[-1] - closes[-11]) / (closes[-11] + 1e-8) if len(closes) > 10 else 0.0
        roc_20 = (closes[-1] - closes[-21]) / (closes[-21] + 1e-8) if len(closes) > 20 else 0.0
        
        # Momentum acceleration
        momentum_accel = roc_5 - roc_10
        
        return {
            'momentum_short': roc_5,
            'momentum_medium': roc_10,
            'momentum_long': roc_20,
            'momentum_acceleration': momentum_accel
        }
    
    def _extract_range_features(self, df: pd.DataFrame) -> Dict:
        """Range compression/expansion features"""
        ranges = df['high'] - df['low']
        
        # Range compression
        range_current = ranges.iloc[-5:].mean()
        range_avg = ranges.mean()
        range_ratio = (range_current / range_avg) if range_avg > 0 else 1.0
        
        # Range trend
        range_short = ranges.iloc[-5:].mean()
        range_long = ranges.iloc[-20:].mean()
        range_trend = (range_short - range_long) / (range_long + 1e-8)
        
        return {
            'range_compression': 1.0 / range_ratio if range_ratio > 0 else 1.0,
            'range_trend': range_trend
        }
    
    def _percentile_rank(self, values: np.ndarray, current: float) -> float:
        """Calculate percentile rank of current value"""
        return np.sum(values <= current) / len(values)
    
    def _empty_features(self) -> Dict:
        """Return empty features"""
        return {
            'atr_expansion': 1.0, 'atr_slope': 0.0, 'atr_percentile': 0.5,
            'volatility_ratio': 1.0, 'volatility_clustering': 0.0, 'volatility_trend': 0.0,
            'trend_strength': 0.0, 'trend_consistency': 0.5, 'trend_direction': 0.0,
            'volume_spike': 0.0, 'volume_trend': 0.0, 'volume_consistency': 0.5,
            'momentum_short': 0.0, 'momentum_medium': 0.0, 'momentum_long': 0.0,
            'momentum_acceleration': 0.0, 'range_compression': 1.0, 'range_trend': 0.0
        }


class RuleBasedRegimeClassifier:
    """
    Rule-based regime classification (fallback when no ML available).
    """
    
    def classify(self, features: Dict) -> Tuple[str, float]:
        """
        Classify regime based on rules.
        
        Returns:
            (regime_label, confidence)
        """
        # High volatility regime
        if features['volatility_ratio'] > 1.5 or features['atr_expansion'] > 1.5:
            return 'high_volatility', 0.8
        
        # Low volatility regime
        if features['volatility_ratio'] < 0.6 and features['range_compression'] > 1.3:
            return 'low_volatility', 0.75
        
        # News-driven (volume spike + high volatility)
        if features['volume_spike'] > 2.0 and features['volatility_ratio'] > 1.3:
            return 'news_driven', 0.85
        
        # Trending up
        if (features['trend_strength'] > 0.5 and 
            features['trend_direction'] > 0 and 
            features['momentum_medium'] > 0.01):
            return 'trending_up', 0.7
        
        # Trending down
        if (features['trend_strength'] > 0.5 and 
            features['trend_direction'] < 0 and 
            features['momentum_medium'] < -0.01):
            return 'trending_down', 0.7
        
        # Ranging (low trend strength + range compression)
        if features['trend_strength'] < 0.3 and features['range_compression'] > 1.1:
            return 'ranging', 0.65
        
        # Default to ranging with low confidence
        return 'ranging', 0.4


class MLRegimeClassifier:
    """
    ML-based regime classification using RandomForest.
    Trained on historical labeled data.
    """
    
    def __init__(self):
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn required for ML regime classifier")
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=5,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
    
    def train(self, features_list: List[Dict], labels: List[str]):
        """
        Train regime classifier.
        
        Args:
            features_list: List of feature dictionaries
            labels: List of regime labels
        """
        # Convert to array
        self.feature_names = list(features_list[0].keys())
        X = np.array([[f[k] for k in self.feature_names] for f in features_list])
        y = np.array(labels)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        logger.info(f"Regime classifier trained on {len(labels)} samples")
    
    def predict(self, features: Dict) -> Tuple[str, float]:
        """
        Predict regime.
        
        Returns:
            (regime_label, confidence)
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained")
        
        # Convert to array
        X = np.array([[features[k] for k in self.feature_names]])
        X_scaled = self.scaler.transform(X)
        
        # Predict
        regime = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        confidence = np.max(probabilities)
        
        return regime, confidence


class RegimeModel:
    """
    Main regime classification model.
    
    Does NOT generate trade signals.
    Only classifies market state for filtering/adjusting other signals.
    
    Usage:
        regime_model = RegimeModel()
        state = regime_model.classify(df)
        
        # Use regime to adjust signal confidence
        if state.regime == 'high_volatility':
            adjusted_confidence = base_confidence * 0.7
        elif state.regime == 'trending_up' and signal_direction == 'long':
            adjusted_confidence = base_confidence * 1.2
    """
    
    def __init__(self, use_ml: bool = False):
        self.feature_extractor = RegimeFeatureExtractor()
        self.use_ml = use_ml and HAS_SKLEARN
        
        if self.use_ml:
            self.classifier = MLRegimeClassifier()
        else:
            self.classifier = RuleBasedRegimeClassifier()
        
        # Regime history for stability tracking
        self.regime_history: List[str] = []
        self.max_history = 50
    
    def classify(self, df: pd.DataFrame) -> RegimeState:
        """
        Classify current market regime.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            RegimeState
        """
        # Extract features
        features = self.feature_extractor.extract(df)
        
        # Classify regime
        regime, confidence = self.classifier.classify(features)
        
        # Update history
        self.regime_history.append(regime)
        if len(self.regime_history) > self.max_history:
            self.regime_history.pop(0)
        
        # Calculate stability
        stability = self._calculate_stability()
        
        # Calculate regime duration
        duration = self._calculate_duration(regime)
        
        # Determine characteristics
        is_trending = regime in ['trending_up', 'trending_down']
        is_ranging = regime == 'ranging'
        is_volatile = regime in ['high_volatility', 'news_driven']
        is_news_driven = regime == 'news_driven'
        
        # Volume regime
        volume_regime = self._classify_volume_regime(features)
        
        return RegimeState(
            regime=regime,
            confidence=confidence,
            stability_score=stability,
            regime_duration=duration,
            trend_strength=features['trend_strength'],
            volatility_level=features['volatility_ratio'],
            volume_regime=volume_regime,
            is_trending=is_trending,
            is_ranging=is_ranging,
            is_volatile=is_volatile,
            is_news_driven=is_news_driven
        )
    
    def get_confidence_multiplier(self, regime_state: RegimeState, signal_direction: str) -> float:
        """
        Get confidence multiplier based on regime alignment.
        
        Args:
            regime_state: Current regime state
            signal_direction: 'long' or 'short'
        
        Returns:
            Confidence multiplier (0.5 - 1.5)
        """
        multiplier = 1.0
        
        # Trending regime alignment
        if regime_state.regime == 'trending_up' and signal_direction == 'long':
            multiplier *= 1.3
        elif regime_state.regime == 'trending_down' and signal_direction == 'short':
            multiplier *= 1.3
        elif regime_state.regime == 'trending_up' and signal_direction == 'short':
            multiplier *= 0.6  # Counter-trend
        elif regime_state.regime == 'trending_down' and signal_direction == 'long':
            multiplier *= 0.6
        
        # Ranging regime (mean reversion favored)
        elif regime_state.regime == 'ranging':
            multiplier *= 0.9  # Slightly reduce confidence
        
        # High volatility (reduce confidence)
        elif regime_state.regime == 'high_volatility':
            multiplier *= 0.7
        
        # News-driven (significantly reduce)
        elif regime_state.regime == 'news_driven':
            multiplier *= 0.5
        
        # Low volatility (slightly increase)
        elif regime_state.regime == 'low_volatility':
            multiplier *= 1.1
        
        # Stability bonus
        if regime_state.stability_score > 0.7:
            multiplier *= 1.05
        
        return np.clip(multiplier, 0.5, 1.5)
    
    def _calculate_stability(self) -> float:
        """Calculate regime stability (how often it changes)"""
        if len(self.regime_history) < 10:
            return 0.5
        
        # Count regime changes
        changes = sum(1 for i in range(1, len(self.regime_history)) 
                     if self.regime_history[i] != self.regime_history[i-1])
        
        # Stability = 1 - (change_rate)
        change_rate = changes / (len(self.regime_history) - 1)
        stability = 1.0 - change_rate
        
        return stability
    
    def _calculate_duration(self, current_regime: str) -> int:
        """Calculate how long we've been in current regime"""
        if not self.regime_history:
            return 1
        
        duration = 1
        for regime in reversed(self.regime_history[:-1]):
            if regime == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _classify_volume_regime(self, features: Dict) -> str:
        """Classify volume regime"""
        vol_spike = features['volume_spike']
        
        if vol_spike > 1.5:
            return 'high'
        elif vol_spike < -0.5:
            return 'low'
        else:
            return 'normal'


# Example usage
if __name__ == "__main__":
    # Generate sample data
    np.random.seed(42)
    n = 200
    
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
    
    # Classify regime
    regime_model = RegimeModel(use_ml=False)
    state = regime_model.classify(df)
    
    print("=== Regime Classification ===")
    print(f"Regime: {state.regime}")
    print(f"Confidence: {state.confidence:.2f}")
    print(f"Stability: {state.stability_score:.2f}")
    print(f"Duration: {state.regime_duration} periods")
    print(f"Trend Strength: {state.trend_strength:.2f}")
    print(f"Volatility Level: {state.volatility_level:.2f}")
    print(f"Volume Regime: {state.volume_regime}")
    
    # Test confidence multiplier
    long_mult = regime_model.get_confidence_multiplier(state, 'long')
    short_mult = regime_model.get_confidence_multiplier(state, 'short')
    print(f"\nConfidence Multipliers:")
    print(f"  Long signals: {long_mult:.2f}x")
    print(f"  Short signals: {short_mult:.2f}x")
