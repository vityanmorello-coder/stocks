"""
AdaptiveLearner v1.0 - Lightweight AI That Learns From Past Trades
Supervised classification of winning vs losing trades.
Adjusts signal confidence based on historical performance patterns.

Architecture:
1. TradeLogger: Records every trade with full feature set
2. FeatureExtractor: Builds ML features from market conditions at trade time
3. PerformanceTracker: Tracks win rate per strategy/instrument/session
4. ConfidenceAdjuster: ML model that predicts P(win) and adjusts confidence
5. OnlineLearner: Incremental updates without retraining from scratch
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
import logging
import pickle

logger = logging.getLogger(__name__)

# Use sklearn if available, otherwise fall back to simple model
try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn not installed. Using built-in simple model.")


@dataclass
class TradeRecord:
    """Complete record of a trade for learning"""
    trade_id: str = ""
    timestamp: str = ""
    symbol: str = ""
    strategy: str = ""
    signal_type: str = ""  # buy/sell
    
    # Entry conditions
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    # Market conditions at entry
    rsi: float = 50.0
    macd_hist: float = 0.0
    adx: float = 0.0
    atr_ratio: float = 1.0  # ATR / avg ATR
    bb_position: float = 0.5  # 0=lower band, 1=upper band
    ema_alignment: float = 0.0  # EMA20 vs EMA50 normalized
    momentum: float = 0.0
    volume_ratio: float = 1.0  # Volume / avg volume
    trend_structure: float = 0.0  # From market structure
    structure_alignment: float = 0.0  # From market structure
    regime: str = "normal"  # trending/ranging/volatile/normal
    session: str = "london"
    day_of_week: int = 0
    hour_of_day: int = 12
    
    # Quantum scorer output
    quantum_score: float = 0.5
    risk_reward_ratio: float = 1.5
    confirmation_count: int = 0
    
    # Outcome (filled after trade closes)
    outcome: str = ""  # 'win', 'loss', 'breakeven'
    pnl: float = 0.0
    pnl_percent: float = 0.0
    duration_minutes: float = 0.0
    max_favorable_excursion: float = 0.0  # Best point during trade
    max_adverse_excursion: float = 0.0  # Worst point during trade
    exit_reason: str = ""  # 'tp_hit', 'sl_hit', 'trailing', 'manual'
    
    def to_features(self) -> List[float]:
        """Convert to feature vector for ML model"""
        return [
            self.rsi / 100.0,
            np.tanh(self.macd_hist * 10),
            self.adx / 50.0,
            self.atr_ratio,
            self.bb_position,
            self.ema_alignment,
            self.momentum,
            self.volume_ratio,
            self.trend_structure,
            self.structure_alignment,
            self.quantum_score,
            self.risk_reward_ratio / 5.0,
            self.confirmation_count / 14.0,
            1.0 if self.signal_type == 'buy' else 0.0,
            self._encode_regime(),
            self._encode_session(),
            self.day_of_week / 6.0,
            self.hour_of_day / 23.0,
        ]
    
    def _encode_regime(self) -> float:
        return {'trending': 0.0, 'ranging': 0.33, 'volatile': 0.67, 'normal': 1.0}.get(self.regime, 0.5)
    
    def _encode_session(self) -> float:
        return {'asian': 0.0, 'london': 0.25, 'newyork': 0.5, 'overlap': 0.75, 'off_hours': 1.0}.get(self.session, 0.5)
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, d: dict) -> 'TradeRecord':
        tr = cls()
        for k, v in d.items():
            if hasattr(tr, k):
                setattr(tr, k, v)
        return tr


FEATURE_NAMES = [
    'rsi', 'macd_hist', 'adx', 'atr_ratio', 'bb_position',
    'ema_alignment', 'momentum', 'volume_ratio', 'trend_structure',
    'structure_alignment', 'quantum_score', 'risk_reward',
    'confirmations', 'is_buy', 'regime', 'session', 'day_of_week', 'hour'
]


class SimpleModel:
    """Fallback model when sklearn is not available. Weighted k-NN approach."""
    
    def __init__(self):
        self.X = []
        self.y = []
        self.is_fitted = False
    
    def fit(self, X, y):
        self.X = np.array(X)
        self.y = np.array(y)
        self.is_fitted = True
    
    def predict_proba(self, X):
        X = np.array(X)
        if not self.is_fitted or len(self.X) < 5:
            return np.full((len(X), 2), 0.5)
        
        results = []
        for x in X:
            # Distance-weighted average of outcomes
            distances = np.sqrt(np.sum((self.X - x) ** 2, axis=1))
            distances = np.maximum(distances, 1e-10)
            weights = 1.0 / distances
            
            # Use top-k nearest neighbors
            k = min(10, len(self.X))
            top_k_idx = np.argsort(distances)[:k]
            
            win_weight = sum(weights[i] for i in top_k_idx if self.y[i] == 1)
            total_weight = sum(weights[i] for i in top_k_idx)
            
            win_prob = win_weight / max(total_weight, 1e-10)
            results.append([1 - win_prob, win_prob])
        
        return np.array(results)


class PerformanceTracker:
    """Tracks win rates and performance by strategy/instrument/session"""
    
    def __init__(self):
        self.stats: Dict[str, Dict] = {}
    
    def update(self, record: TradeRecord):
        """Update performance stats with a completed trade"""
        keys = [
            f"strategy:{record.strategy}",
            f"symbol:{record.symbol}",
            f"session:{record.session}",
            f"regime:{record.regime}",
            f"{record.strategy}:{record.symbol}",
            f"{record.symbol}:{record.session}",
            "overall"
        ]
        
        is_win = record.outcome == 'win'
        
        for key in keys:
            if key not in self.stats:
                self.stats[key] = {
                    'wins': 0, 'losses': 0, 'total': 0,
                    'total_pnl': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0,
                    'streak': 0, 'max_streak': 0,
                    'recent_outcomes': []
                }
            
            s = self.stats[key]
            s['total'] += 1
            s['total_pnl'] += record.pnl
            
            if is_win:
                s['wins'] += 1
                s['avg_win'] = (s['avg_win'] * (s['wins'] - 1) + record.pnl) / s['wins']
                s['streak'] = max(0, s['streak']) + 1
            else:
                s['losses'] += 1
                if s['losses'] > 0:
                    s['avg_loss'] = (s['avg_loss'] * (s['losses'] - 1) + record.pnl) / s['losses']
                s['streak'] = min(0, s['streak']) - 1
            
            s['max_streak'] = max(s['max_streak'], abs(s['streak']))
            s['recent_outcomes'] = (s['recent_outcomes'] + [1 if is_win else 0])[-20:]
    
    def get_win_rate(self, key: str) -> float:
        """Get win rate for a specific category"""
        if key not in self.stats or self.stats[key]['total'] == 0:
            return 0.5  # No data = assume 50%
        s = self.stats[key]
        return s['wins'] / s['total']
    
    def get_recent_win_rate(self, key: str, n: int = 10) -> float:
        """Get win rate of last N trades for a category"""
        if key not in self.stats:
            return 0.5
        recent = self.stats[key]['recent_outcomes']
        if not recent:
            return 0.5
        recent = recent[-n:]
        return sum(recent) / len(recent)
    
    def get_confidence_adjustment(self, symbol: str, strategy: str, session: str) -> float:
        """
        Get confidence adjustment multiplier based on historical performance.
        Returns 0.5-1.5 (0.5 = halve confidence, 1.5 = 50% boost).
        """
        adjustments = []
        
        # Strategy performance
        strat_wr = self.get_recent_win_rate(f"strategy:{strategy}")
        adjustments.append(strat_wr / 0.5)  # Normalize to 1.0 at 50% WR
        
        # Symbol performance
        sym_wr = self.get_recent_win_rate(f"symbol:{symbol}")
        adjustments.append(sym_wr / 0.5)
        
        # Session performance
        sess_wr = self.get_recent_win_rate(f"session:{session}")
        adjustments.append(sess_wr / 0.5)
        
        # Combined symbol:strategy
        combo_wr = self.get_recent_win_rate(f"{strategy}:{symbol}")
        adjustments.append(combo_wr / 0.5)
        
        # Weighted average (combo is most specific = highest weight)
        weights = [0.2, 0.2, 0.15, 0.45]
        avg = sum(a * w for a, w in zip(adjustments, weights))
        
        # Clamp to 0.5-1.5
        return max(0.5, min(1.5, avg))
    
    def get_summary(self) -> dict:
        """Get full performance summary"""
        return {
            k: {
                'win_rate': round(v['wins'] / max(v['total'], 1), 3),
                'total': v['total'],
                'pnl': round(v['total_pnl'], 2),
                'recent_wr': round(sum(v['recent_outcomes'][-10:]) / max(len(v['recent_outcomes'][-10:]), 1), 3)
            }
            for k, v in self.stats.items()
        }


class AdaptiveLearner:
    """
    Main AI layer that learns from past trades and adjusts confidence.
    
    Data Flow:
    1. On signal: extract features → predict P(win) → adjust confidence
    2. On trade close: log trade → update performance tracker → retrain model
    3. Model retrains automatically every N trades
    
    Storage:
    - trade_history.json: All trade records
    - ml_model.pkl: Trained model (if sklearn available)
    - performance_stats.json: Performance tracker state
    """
    
    TRADE_DB = 'trade_history.json'
    MODEL_FILE = 'ml_model.pkl'
    STATS_FILE = 'performance_stats.json'
    RETRAIN_INTERVAL = 10  # Retrain every N new trades
    MIN_TRADES_FOR_ML = 30  # Minimum trades before using ML predictions
    
    def __init__(self):
        self.trade_history: List[TradeRecord] = []
        self.performance = PerformanceTracker()
        self.model = None
        self.scaler = None
        self.trades_since_retrain = 0
        self.model_accuracy = 0.0
        
        self._load_state()
        self._init_model()
    
    def _load_state(self):
        """Load trade history and performance from disk"""
        # Load trade history
        try:
            if os.path.exists(self.TRADE_DB):
                with open(self.TRADE_DB, 'r') as f:
                    data = json.load(f)
                    self.trade_history = [TradeRecord.from_dict(d) for d in data]
                    logger.info(f"Loaded {len(self.trade_history)} trade records")
        except Exception as e:
            logger.warning(f"Could not load trade history: {e}")
            self.trade_history = []
        
        # Load performance stats
        try:
            if os.path.exists(self.STATS_FILE):
                with open(self.STATS_FILE, 'r') as f:
                    self.performance.stats = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load performance stats: {e}")
        
        # Rebuild performance from trade history if stats are empty
        if not self.performance.stats and self.trade_history:
            for record in self.trade_history:
                if record.outcome:
                    self.performance.update(record)
    
    def _save_state(self):
        """Persist all state to disk"""
        try:
            # Save trade history
            with open(self.TRADE_DB, 'w') as f:
                json.dump([tr.to_dict() for tr in self.trade_history[-5000:]], f, indent=2)
            
            # Save performance stats
            with open(self.STATS_FILE, 'w') as f:
                json.dump(self.performance.stats, f, indent=2)
            
            # Save model
            if self.model and HAS_SKLEARN:
                with open(self.MODEL_FILE, 'wb') as f:
                    pickle.dump({'model': self.model, 'scaler': self.scaler}, f)
        except Exception as e:
            logger.warning(f"Could not save learner state: {e}")
    
    def _init_model(self):
        """Initialize or load the ML model"""
        # Try to load saved model
        if HAS_SKLEARN and os.path.exists(self.MODEL_FILE):
            try:
                with open(self.MODEL_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.scaler = data['scaler']
                    logger.info("Loaded pre-trained ML model")
                    return
            except Exception:
                pass
        
        # Create new model
        if HAS_SKLEARN:
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                min_samples_leaf=5,
                subsample=0.8,
                random_state=42
            )
            self.scaler = StandardScaler()
        else:
            self.model = SimpleModel()
            self.scaler = None
        
        # Train on existing data if available
        self._retrain()
    
    def _retrain(self):
        """Retrain the model on all completed trades"""
        completed = [tr for tr in self.trade_history if tr.outcome in ('win', 'loss')]
        
        if len(completed) < self.MIN_TRADES_FOR_ML:
            logger.info(f"Need {self.MIN_TRADES_FOR_ML} trades for ML, have {len(completed)}")
            return
        
        X = np.array([tr.to_features() for tr in completed])
        y = np.array([1 if tr.outcome == 'win' else 0 for tr in completed])
        
        # Replace any NaN/inf
        X = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=-1.0)
        
        try:
            if HAS_SKLEARN:
                self.scaler.fit(X)
                X_scaled = self.scaler.transform(X)
                self.model.fit(X_scaled, y)
                
                # Cross-validation score
                if len(completed) >= 50:
                    scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(completed) // 10), scoring='accuracy')
                    self.model_accuracy = scores.mean()
                    logger.info(f"ML model retrained. CV Accuracy: {self.model_accuracy:.3f}")
                else:
                    self.model_accuracy = 0.0
                    logger.info(f"ML model retrained on {len(completed)} trades")
            else:
                self.model.fit(X, y)
                logger.info(f"Simple model trained on {len(completed)} trades")
            
            self.trades_since_retrain = 0
            self._save_state()
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
    
    def extract_features(self, df: pd.DataFrame, signal_type: str,
                         entry_price: float, stop_loss: float, take_profit: float,
                         symbol: str, strategy: str,
                         quantum_score: float = 0.5,
                         structure_alignment: float = 0.0,
                         session: str = 'london',
                         regime: str = 'normal') -> TradeRecord:
        """
        Extract features from current market conditions for ML prediction.
        Returns a TradeRecord ready for prediction or logging.
        """
        record = TradeRecord()
        record.timestamp = datetime.now().isoformat()
        record.symbol = symbol
        record.strategy = strategy
        record.signal_type = signal_type
        record.entry_price = entry_price
        record.stop_loss = stop_loss
        record.take_profit = take_profit
        
        if not df.empty:
            last = df.iloc[-1]
            
            record.rsi = float(last.get('rsi', 50))
            if pd.isna(record.rsi): record.rsi = 50.0
            
            macd = float(last.get('macd', 0))
            macd_sig = float(last.get('macd_signal', 0))
            record.macd_hist = macd - macd_sig if not pd.isna(macd) and not pd.isna(macd_sig) else 0.0
            
            record.adx = float(last.get('adx', 0))
            if pd.isna(record.adx): record.adx = 0.0
            
            # ATR ratio
            atr = float(last.get('atr', 0))
            if pd.isna(atr): atr = 0
            avg_atr = df['atr'].rolling(50).mean().iloc[-1] if 'atr' in df.columns else atr
            if pd.isna(avg_atr) or avg_atr == 0:
                record.atr_ratio = 1.0
            else:
                record.atr_ratio = atr / avg_atr
            
            # BB position
            bb_upper = float(last.get('bb_upper', 0))
            bb_lower = float(last.get('bb_lower', 0))
            if not pd.isna(bb_upper) and not pd.isna(bb_lower) and bb_upper != bb_lower:
                record.bb_position = (last['close'] - bb_lower) / (bb_upper - bb_lower)
            else:
                record.bb_position = 0.5
            
            # EMA alignment
            ema20 = float(last.get('ema_20', 0))
            ema50 = float(last.get('ema_50', 0))
            if not pd.isna(ema20) and not pd.isna(ema50) and ema50 != 0:
                record.ema_alignment = (ema20 - ema50) / ema50
            
            record.momentum = float(last.get('momentum', 0))
            if pd.isna(record.momentum): record.momentum = 0.0
            
            # Volume ratio
            vol = float(last.get('volume', 0))
            vol_ma = float(last.get('volume_ma', 0))
            if not pd.isna(vol) and not pd.isna(vol_ma) and vol_ma > 0:
                record.volume_ratio = vol / vol_ma
            else:
                record.volume_ratio = 1.0
            
            # Trend structure from recent price action
            if len(df) >= 20:
                recent = df.tail(20)
                highs = recent['high'].values
                lows = recent['low'].values
                hh = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
                hl = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
                total = len(highs) - 1
                if total > 0:
                    record.trend_structure = (hh + hl) / (2 * total) - 0.5
        
        record.structure_alignment = structure_alignment
        record.quantum_score = quantum_score
        record.regime = regime
        record.session = session
        
        # Risk/reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        record.risk_reward_ratio = reward / risk if risk > 0 else 1.5
        
        # Time features
        now = datetime.now()
        record.day_of_week = now.weekday()
        record.hour_of_day = now.hour
        
        return record
    
    def predict_win_probability(self, record: TradeRecord) -> Tuple[float, str]:
        """
        Predict probability of trade being a winner.
        
        Returns:
            (probability, source) - probability 0-1, source = 'ml' or 'stats' or 'default'
        """
        completed = [tr for tr in self.trade_history if tr.outcome in ('win', 'loss')]
        
        # If we have enough data for ML
        if len(completed) >= self.MIN_TRADES_FOR_ML and self.model:
            try:
                features = np.array([record.to_features()])
                features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)
                
                if HAS_SKLEARN and self.scaler:
                    features = self.scaler.transform(features)
                
                proba = self.model.predict_proba(features)[0]
                win_prob = proba[1] if len(proba) > 1 else proba[0]
                
                return float(win_prob), 'ml'
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
        
        # Fall back to performance tracker
        perf_adj = self.performance.get_confidence_adjustment(
            record.symbol, record.strategy, record.session
        )
        # Convert adjustment (0.5-1.5) to probability (0.25-0.75)
        prob = 0.25 + (perf_adj - 0.5) * 0.5
        
        if len(completed) >= 5:
            return float(prob), 'stats'
        
        # No data at all - return quantum score as proxy
        return record.quantum_score, 'default'
    
    def adjust_confidence(self, quantum_score: float, record: TradeRecord) -> Tuple[float, dict]:
        """
        Adjust QuantumScorer confidence using ML prediction and performance tracking.
        
        Returns:
            (adjusted_score, details_dict)
        """
        ml_prob, source = self.predict_win_probability(record)
        
        # Performance adjustment
        perf_adj = self.performance.get_confidence_adjustment(
            record.symbol, record.strategy, record.session
        )
        
        # Blend: 40% quantum score, 40% ML prediction, 20% performance history
        completed_count = len([tr for tr in self.trade_history if tr.outcome in ('win', 'loss')])
        
        if completed_count >= self.MIN_TRADES_FOR_ML and source == 'ml':
            # Full ML mode
            blended = quantum_score * 0.4 + ml_prob * 0.4 + (perf_adj / 1.5) * 0.2
        elif completed_count >= 5:
            # Stats mode - lean more on quantum score
            blended = quantum_score * 0.6 + ml_prob * 0.2 + (perf_adj / 1.5) * 0.2
        else:
            # No history - use quantum score directly
            blended = quantum_score
        
        # Ensure 0-1 range
        adjusted = max(0.0, min(1.0, blended))
        
        details = {
            'quantum_score': round(quantum_score, 4),
            'ml_probability': round(ml_prob, 4),
            'ml_source': source,
            'performance_adj': round(perf_adj, 3),
            'adjusted_score': round(adjusted, 4),
            'model_accuracy': round(self.model_accuracy, 3),
            'total_trades_learned': completed_count,
            'blend_mode': 'ml' if source == 'ml' else 'stats' if completed_count >= 5 else 'cold_start'
        }
        
        return adjusted, details
    
    def log_trade_open(self, record: TradeRecord) -> str:
        """Log a trade when it opens. Returns trade_id."""
        import time
        record.trade_id = f"QT_{int(time.time() * 1000)}"
        record.timestamp = datetime.now().isoformat()
        self.trade_history.append(record)
        self._save_state()
        return record.trade_id
    
    def log_trade_close(self, trade_id: str, outcome: str, pnl: float, 
                         pnl_percent: float = 0.0, duration_minutes: float = 0.0,
                         exit_reason: str = '', max_favorable: float = 0.0,
                         max_adverse: float = 0.0):
        """
        Log trade outcome when it closes.
        Triggers performance update and potential model retrain.
        """
        for record in self.trade_history:
            if record.trade_id == trade_id:
                record.outcome = outcome
                record.pnl = pnl
                record.pnl_percent = pnl_percent
                record.duration_minutes = duration_minutes
                record.exit_reason = exit_reason
                record.max_favorable_excursion = max_favorable
                record.max_adverse_excursion = max_adverse
                
                # Update performance tracker
                self.performance.update(record)
                
                # Check if retrain needed
                self.trades_since_retrain += 1
                if self.trades_since_retrain >= self.RETRAIN_INTERVAL:
                    logger.info("Triggering model retrain...")
                    self._retrain()
                
                self._save_state()
                
                logger.info(
                    f"Trade {trade_id} closed: {outcome} | PnL: {pnl:.2f} | "
                    f"Duration: {duration_minutes:.0f}min | Exit: {exit_reason}"
                )
                return
        
        logger.warning(f"Trade {trade_id} not found in history")
    
    def get_learning_status(self) -> dict:
        """Get current learning system status"""
        completed = [tr for tr in self.trade_history if tr.outcome in ('win', 'loss')]
        wins = sum(1 for tr in completed if tr.outcome == 'win')
        
        return {
            'total_trades': len(self.trade_history),
            'completed_trades': len(completed),
            'wins': wins,
            'losses': len(completed) - wins,
            'overall_win_rate': round(wins / max(len(completed), 1), 3),
            'ml_active': len(completed) >= self.MIN_TRADES_FOR_ML,
            'ml_accuracy': round(self.model_accuracy, 3),
            'trades_until_ml': max(0, self.MIN_TRADES_FOR_ML - len(completed)),
            'has_sklearn': HAS_SKLEARN,
            'performance_summary': self.performance.get_summary()
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the ML model (if sklearn)"""
        if HAS_SKLEARN and hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            return {name: round(float(imp), 4) for name, imp in zip(FEATURE_NAMES, importances)}
        return {}
