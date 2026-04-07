"""
Drift Detector v1.0 - Live Performance Monitoring
Detects when the model is degrading in live markets.
Critical for preventing losses from model decay.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class DriftAlert:
    """Drift detection alert"""
    drift_detected: bool
    drift_score: float  # 0-1, higher = more drift
    drift_type: str  # 'performance', 'data', 'execution', 'mixed'
    alert_level: str  # 'green', 'yellow', 'red'
    
    # Specific drift metrics
    performance_drift: float
    data_drift: float
    execution_drift: float
    
    # Recommendations
    recommended_action: str
    position_size_multiplier: float  # Reduce size if drift detected
    
    # Details
    details: Dict
    timestamp: str
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class PerformanceDriftDetector:
    """
    Detects performance degradation in live trading.
    
    Monitors:
    - Rolling win rate drop
    - Profit factor decay
    - Sharpe ratio degradation
    - Drawdown increase
    """
    
    def __init__(
        self,
        baseline_window: int = 100,
        monitor_window: int = 30,
        win_rate_threshold: float = 0.10,  # 10% drop triggers alert
        sharpe_threshold: float = 0.30  # 30% drop triggers alert
    ):
        self.baseline_window = baseline_window
        self.monitor_window = monitor_window
        self.win_rate_threshold = win_rate_threshold
        self.sharpe_threshold = sharpe_threshold
        
        self.trade_history = deque(maxlen=baseline_window)
    
    def add_trade(self, pnl: float, win: bool):
        """Add completed trade to history"""
        self.trade_history.append({'pnl': pnl, 'win': win, 'timestamp': datetime.now()})
    
    def detect(self) -> Tuple[float, Dict]:
        """
        Detect performance drift.
        
        Returns:
            (drift_score, details)
        """
        if len(self.trade_history) < self.baseline_window:
            return 0.0, {'status': 'insufficient_data', 'trades': len(self.trade_history)}
        
        # Split into baseline and recent
        baseline_trades = list(self.trade_history)[:-self.monitor_window]
        recent_trades = list(self.trade_history)[-self.monitor_window:]
        
        # Calculate metrics
        baseline_metrics = self._calculate_metrics(baseline_trades)
        recent_metrics = self._calculate_metrics(recent_trades)
        
        # Detect drift
        win_rate_drift = self._calculate_win_rate_drift(baseline_metrics, recent_metrics)
        sharpe_drift = self._calculate_sharpe_drift(baseline_metrics, recent_metrics)
        profit_factor_drift = self._calculate_pf_drift(baseline_metrics, recent_metrics)
        drawdown_drift = self._calculate_drawdown_drift(baseline_metrics, recent_metrics)
        
        # Combined drift score
        drift_score = max(win_rate_drift, sharpe_drift, profit_factor_drift, drawdown_drift)
        
        details = {
            'baseline_win_rate': baseline_metrics['win_rate'],
            'recent_win_rate': recent_metrics['win_rate'],
            'win_rate_drift': win_rate_drift,
            'baseline_sharpe': baseline_metrics['sharpe'],
            'recent_sharpe': recent_metrics['sharpe'],
            'sharpe_drift': sharpe_drift,
            'baseline_pf': baseline_metrics['profit_factor'],
            'recent_pf': recent_metrics['profit_factor'],
            'pf_drift': profit_factor_drift,
            'drawdown_drift': drawdown_drift
        }
        
        return drift_score, details
    
    def _calculate_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate performance metrics"""
        if not trades:
            return {'win_rate': 0.0, 'sharpe': 0.0, 'profit_factor': 0.0, 'max_dd': 0.0}
        
        wins = [t for t in trades if t['win']]
        losses = [t for t in trades if not t['win']]
        
        win_rate = len(wins) / len(trades)
        
        # Sharpe
        pnls = [t['pnl'] for t in trades]
        if len(pnls) > 1 and np.std(pnls) > 0:
            sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252)
        else:
            sharpe = 0.0
        
        # Profit factor
        total_wins = sum(t['pnl'] for t in wins) if wins else 0.0
        total_losses = abs(sum(t['pnl'] for t in losses)) if losses else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        # Max drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0.0
        
        return {
            'win_rate': win_rate,
            'sharpe': sharpe,
            'profit_factor': profit_factor,
            'max_dd': max_dd
        }
    
    def _calculate_win_rate_drift(self, baseline: Dict, recent: Dict) -> float:
        """Calculate win rate drift score"""
        baseline_wr = baseline['win_rate']
        recent_wr = recent['win_rate']
        
        if baseline_wr == 0:
            return 0.0
        
        drop = (baseline_wr - recent_wr) / baseline_wr
        
        if drop > self.win_rate_threshold:
            return min(1.0, drop / 0.3)  # Normalize to 0-1
        
        return 0.0
    
    def _calculate_sharpe_drift(self, baseline: Dict, recent: Dict) -> float:
        """Calculate Sharpe drift score"""
        baseline_sharpe = baseline['sharpe']
        recent_sharpe = recent['sharpe']
        
        if baseline_sharpe <= 0:
            return 0.0
        
        drop = (baseline_sharpe - recent_sharpe) / baseline_sharpe
        
        if drop > self.sharpe_threshold:
            return min(1.0, drop / 0.5)
        
        return 0.0
    
    def _calculate_pf_drift(self, baseline: Dict, recent: Dict) -> float:
        """Calculate profit factor drift"""
        baseline_pf = baseline['profit_factor']
        recent_pf = recent['profit_factor']
        
        if baseline_pf <= 1.0:
            return 0.0
        
        drop = (baseline_pf - recent_pf) / baseline_pf
        
        if drop > 0.2:  # 20% drop in PF
            return min(1.0, drop / 0.4)
        
        return 0.0
    
    def _calculate_drawdown_drift(self, baseline: Dict, recent: Dict) -> float:
        """Calculate drawdown increase"""
        baseline_dd = baseline['max_dd']
        recent_dd = recent['max_dd']
        
        if baseline_dd == 0:
            return 0.0
        
        increase = (recent_dd - baseline_dd) / baseline_dd
        
        if increase > 0.5:  # 50% increase in drawdown
            return min(1.0, increase / 1.0)
        
        return 0.0


class DataDriftDetector:
    """
    Detects distribution shift in input features.
    
    Uses statistical distance measures to detect when current data
    differs significantly from training data.
    """
    
    def __init__(self, baseline_window: int = 500, monitor_window: int = 50):
        self.baseline_window = baseline_window
        self.monitor_window = monitor_window
        
        self.feature_history = deque(maxlen=baseline_window)
    
    def add_features(self, features: Dict[str, float]):
        """Add feature observation"""
        self.feature_history.append(features)
    
    def detect(self) -> Tuple[float, Dict]:
        """
        Detect data drift using statistical distance.
        
        Returns:
            (drift_score, details)
        """
        if len(self.feature_history) < self.baseline_window:
            return 0.0, {'status': 'insufficient_data'}
        
        # Split into baseline and recent
        baseline_data = list(self.feature_history)[:-self.monitor_window]
        recent_data = list(self.feature_history)[-self.monitor_window:]
        
        # Calculate drift for each feature
        feature_names = baseline_data[0].keys()
        feature_drifts = {}
        
        for feature in feature_names:
            baseline_values = [d[feature] for d in baseline_data]
            recent_values = [d[feature] for d in recent_data]
            
            drift = self._calculate_feature_drift(baseline_values, recent_values)
            feature_drifts[feature] = drift
        
        # Overall drift score (max drift across features)
        drift_score = max(feature_drifts.values()) if feature_drifts else 0.0
        
        # Identify drifted features
        drifted_features = {k: v for k, v in feature_drifts.items() if v > 0.3}
        
        details = {
            'feature_drifts': feature_drifts,
            'drifted_features': drifted_features,
            'num_drifted': len(drifted_features)
        }
        
        return drift_score, details
    
    def _calculate_feature_drift(self, baseline: List[float], recent: List[float]) -> float:
        """
        Calculate drift for a single feature using KL divergence approximation.
        
        Simplified: compare mean and std deviation
        """
        baseline_mean = np.mean(baseline)
        baseline_std = np.std(baseline)
        recent_mean = np.mean(recent)
        recent_std = np.std(recent)
        
        # Mean shift
        if baseline_std > 0:
            mean_shift = abs(recent_mean - baseline_mean) / baseline_std
        else:
            mean_shift = 0.0
        
        # Variance shift
        if baseline_std > 0:
            var_shift = abs(recent_std - baseline_std) / baseline_std
        else:
            var_shift = 0.0
        
        # Combined drift (normalized to 0-1)
        drift = (mean_shift + var_shift) / 2
        drift = min(1.0, drift / 2.0)  # Normalize
        
        return drift


class ExecutionDriftDetector:
    """
    Detects execution quality degradation.
    
    Monitors:
    - Slippage increase
    - Fill quality degradation
    - Latency increase
    """
    
    def __init__(self, baseline_window: int = 100, monitor_window: int = 20):
        self.baseline_window = baseline_window
        self.monitor_window = monitor_window
        
        self.execution_history = deque(maxlen=baseline_window)
    
    def add_execution(self, slippage_pips: float, fill_quality: str, latency_ms: float):
        """Add execution record"""
        quality_score = {'excellent': 1.0, 'good': 0.75, 'fair': 0.5, 'poor': 0.25}.get(fill_quality, 0.5)
        
        self.execution_history.append({
            'slippage': slippage_pips,
            'quality': quality_score,
            'latency': latency_ms,
            'timestamp': datetime.now()
        })
    
    def detect(self) -> Tuple[float, Dict]:
        """
        Detect execution drift.
        
        Returns:
            (drift_score, details)
        """
        if len(self.execution_history) < self.baseline_window:
            return 0.0, {'status': 'insufficient_data'}
        
        baseline_execs = list(self.execution_history)[:-self.monitor_window]
        recent_execs = list(self.execution_history)[-self.monitor_window:]
        
        # Calculate metrics
        baseline_metrics = self._calculate_exec_metrics(baseline_execs)
        recent_metrics = self._calculate_exec_metrics(recent_execs)
        
        # Detect drift
        slippage_drift = self._calculate_slippage_drift(baseline_metrics, recent_metrics)
        quality_drift = self._calculate_quality_drift(baseline_metrics, recent_metrics)
        latency_drift = self._calculate_latency_drift(baseline_metrics, recent_metrics)
        
        drift_score = max(slippage_drift, quality_drift, latency_drift)
        
        details = {
            'baseline_slippage': baseline_metrics['avg_slippage'],
            'recent_slippage': recent_metrics['avg_slippage'],
            'slippage_drift': slippage_drift,
            'baseline_quality': baseline_metrics['avg_quality'],
            'recent_quality': recent_metrics['avg_quality'],
            'quality_drift': quality_drift,
            'baseline_latency': baseline_metrics['avg_latency'],
            'recent_latency': recent_metrics['avg_latency'],
            'latency_drift': latency_drift
        }
        
        return drift_score, details
    
    def _calculate_exec_metrics(self, executions: List[Dict]) -> Dict:
        """Calculate execution metrics"""
        if not executions:
            return {'avg_slippage': 0.0, 'avg_quality': 0.0, 'avg_latency': 0.0}
        
        return {
            'avg_slippage': np.mean([e['slippage'] for e in executions]),
            'avg_quality': np.mean([e['quality'] for e in executions]),
            'avg_latency': np.mean([e['latency'] for e in executions])
        }
    
    def _calculate_slippage_drift(self, baseline: Dict, recent: Dict) -> float:
        """Calculate slippage drift"""
        baseline_slip = baseline['avg_slippage']
        recent_slip = recent['avg_slippage']
        
        if baseline_slip == 0:
            return 0.0
        
        increase = (recent_slip - baseline_slip) / baseline_slip
        
        if increase > 0.3:  # 30% increase in slippage
            return min(1.0, increase / 0.5)
        
        return 0.0
    
    def _calculate_quality_drift(self, baseline: Dict, recent: Dict) -> float:
        """Calculate fill quality drift"""
        baseline_qual = baseline['avg_quality']
        recent_qual = recent['avg_quality']
        
        if baseline_qual == 0:
            return 0.0
        
        drop = (baseline_qual - recent_qual) / baseline_qual
        
        if drop > 0.2:  # 20% quality drop
            return min(1.0, drop / 0.3)
        
        return 0.0
    
    def _calculate_latency_drift(self, baseline: Dict, recent: Dict) -> float:
        """Calculate latency drift"""
        baseline_lat = baseline['avg_latency']
        recent_lat = recent['avg_latency']
        
        if baseline_lat == 0:
            return 0.0
        
        increase = (recent_lat - baseline_lat) / baseline_lat
        
        if increase > 0.5:  # 50% latency increase
            return min(1.0, increase / 1.0)
        
        return 0.0


class DriftDetector:
    """
    Main drift detector combining all drift types.
    
    Monitors model degradation in real-time and triggers alerts.
    
    Usage:
        detector = DriftDetector()
        
        # After each trade
        detector.log_trade(pnl=50, win=True, features={...}, slippage=0.5, quality='good', latency=60)
        
        # Check for drift
        alert = detector.check_drift()
        
        if alert.alert_level == 'red':
            # Stop trading or reduce position sizes
            position_multiplier = alert.position_size_multiplier
    """
    
    def __init__(
        self,
        performance_baseline: int = 100,
        data_baseline: int = 500,
        execution_baseline: int = 100
    ):
        self.performance_detector = PerformanceDriftDetector(baseline_window=performance_baseline)
        self.data_detector = DataDriftDetector(baseline_window=data_baseline)
        self.execution_detector = ExecutionDriftDetector(baseline_window=execution_baseline)
        
        self.last_alert: Optional[DriftAlert] = None
    
    def log_trade(
        self,
        pnl: float,
        win: bool,
        features: Dict[str, float],
        slippage_pips: float,
        fill_quality: str,
        latency_ms: float
    ):
        """Log completed trade with all data"""
        self.performance_detector.add_trade(pnl, win)
        self.data_detector.add_features(features)
        self.execution_detector.add_execution(slippage_pips, fill_quality, latency_ms)
    
    def check_drift(self) -> DriftAlert:
        """
        Check for drift across all dimensions.
        
        Returns:
            DriftAlert with recommendations
        """
        # Detect drift in each dimension
        perf_drift, perf_details = self.performance_detector.detect()
        data_drift, data_details = self.data_detector.detect()
        exec_drift, exec_details = self.execution_detector.detect()
        
        # Overall drift score (weighted)
        drift_score = (perf_drift * 0.5 + data_drift * 0.3 + exec_drift * 0.2)
        
        # Determine drift type
        drift_types = []
        if perf_drift > 0.3:
            drift_types.append('performance')
        if data_drift > 0.3:
            drift_types.append('data')
        if exec_drift > 0.3:
            drift_types.append('execution')
        
        if len(drift_types) > 1:
            drift_type = 'mixed'
        elif drift_types:
            drift_type = drift_types[0]
        else:
            drift_type = 'none'
        
        # Determine alert level
        if drift_score > 0.7:
            alert_level = 'red'
            recommended_action = 'STOP TRADING - Model degraded significantly'
            position_multiplier = 0.0
        elif drift_score > 0.4:
            alert_level = 'yellow'
            recommended_action = 'REDUCE POSITION SIZES - Model showing drift'
            position_multiplier = 0.5
        else:
            alert_level = 'green'
            recommended_action = 'Continue normal trading'
            position_multiplier = 1.0
        
        # Build alert
        alert = DriftAlert(
            drift_detected=drift_score > 0.4,
            drift_score=drift_score,
            drift_type=drift_type,
            alert_level=alert_level,
            performance_drift=perf_drift,
            data_drift=data_drift,
            execution_drift=exec_drift,
            recommended_action=recommended_action,
            position_size_multiplier=position_multiplier,
            details={
                'performance': perf_details,
                'data': data_details,
                'execution': exec_details
            },
            timestamp=datetime.now().isoformat()
        )
        
        self.last_alert = alert
        
        # Log alert
        if alert.drift_detected:
            logger.warning(
                f"DRIFT DETECTED: {alert.alert_level.upper()} - "
                f"Score: {alert.drift_score:.2f} - Type: {alert.drift_type} - "
                f"Action: {alert.recommended_action}"
            )
        
        return alert
    
    def get_status_summary(self) -> Dict:
        """Get current drift monitoring status"""
        if self.last_alert is None:
            return {'status': 'monitoring', 'drift_detected': False}
        
        return {
            'status': 'active',
            'drift_detected': self.last_alert.drift_detected,
            'alert_level': self.last_alert.alert_level,
            'drift_score': self.last_alert.drift_score,
            'drift_type': self.last_alert.drift_type,
            'position_multiplier': self.last_alert.position_size_multiplier,
            'last_check': self.last_alert.timestamp
        }


# Example usage
if __name__ == "__main__":
    detector = DriftDetector()
    
    # Simulate trades
    np.random.seed(42)
    
    # Good performance period
    for i in range(120):
        win = np.random.random() > 0.4  # 60% win rate
        pnl = np.random.uniform(10, 50) if win else np.random.uniform(-30, -10)
        
        features = {
            'rsi': np.random.uniform(30, 70),
            'macd': np.random.uniform(-0.01, 0.01),
            'atr': np.random.uniform(0.001, 0.002)
        }
        
        detector.log_trade(
            pnl=pnl, win=win, features=features,
            slippage_pips=np.random.uniform(0.3, 0.8),
            fill_quality='good', latency_ms=np.random.uniform(40, 80)
        )
    
    # Check drift (should be green)
    alert = detector.check_drift()
    print("=== After Good Period ===")
    print(f"Alert Level: {alert.alert_level}")
    print(f"Drift Score: {alert.drift_score:.3f}")
    print(f"Recommended Action: {alert.recommended_action}")
    
    # Degraded performance period
    for i in range(40):
        win = np.random.random() > 0.65  # 35% win rate (degraded)
        pnl = np.random.uniform(5, 30) if win else np.random.uniform(-40, -15)
        
        features = {
            'rsi': np.random.uniform(20, 80),  # Wider distribution (drift)
            'macd': np.random.uniform(-0.02, 0.02),
            'atr': np.random.uniform(0.002, 0.004)  # Higher volatility
        }
        
        detector.log_trade(
            pnl=pnl, win=win, features=features,
            slippage_pips=np.random.uniform(1.0, 2.0),  # Worse slippage
            fill_quality='fair', latency_ms=np.random.uniform(100, 150)
        )
    
    # Check drift (should be yellow or red)
    alert = detector.check_drift()
    print("\n=== After Degraded Period ===")
    print(f"Alert Level: {alert.alert_level}")
    print(f"Drift Score: {alert.drift_score:.3f}")
    print(f"Drift Type: {alert.drift_type}")
    print(f"Performance Drift: {alert.performance_drift:.3f}")
    print(f"Data Drift: {alert.data_drift:.3f}")
    print(f"Execution Drift: {alert.execution_drift:.3f}")
    print(f"Position Multiplier: {alert.position_size_multiplier:.1f}x")
    print(f"Recommended Action: {alert.recommended_action}")
