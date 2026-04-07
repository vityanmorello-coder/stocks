"""
QUANTUMTRADE ENGINE v3.0
Enterprise-Grade Trading Dashboard
Professional charting, signal analysis, and position tracking
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
from datetime import datetime, timedelta, timezone
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.fortrade_config import TradingConfig
from trading.fortrade_api_client import FortradeAPIClient
from trading.trading_strategies import StrategyManager, TradingSignal, SignalType, TechnicalIndicators
from trading.risk_manager import RiskManager
from intelligence.advanced_signal_validator import AdvancedSignalValidator
from core.quantum_scorer import QuantumScorer, ScoringBreakdown
from core.market_structure import MarketStructureAnalyzer, StructureAnalysis
from core.adaptive_learner import AdaptiveLearner
from trading.execution_engine import ExecutionManager, PaperBroker, OrderRequest, OrderType
from auth.database import get_database
from auth.auth import check_auth, logout, render_user_sidebar, render_admin_panel, LOGIN_CSS

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="QuantumTrade Engine | Trading Terminal",
    page_icon="https://img.icons8.com/fluency/48/combo-chart.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# PREMIUM CSS STYLING
# ============================================================
PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

@keyframes pulse {
    0% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
    50% { opacity: 0.95; box-shadow: 0 0 20px 5px rgba(16, 185, 129, 0.2); }
    100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
}

:root {
    --bg-primary: #0a0e17;
    --bg-secondary: #111827;
    --bg-card: #1a1f2e;
    --bg-card-hover: #1e2538;
    --border-color: #2a3042;
    --accent-blue: #3b82f6;
    --accent-green: #10b981;
    --accent-red: #ef4444;
    --accent-yellow: #f59e0b;
    --accent-purple: #8b5cf6;
    --accent-cyan: #06b6d4;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --gradient-green: linear-gradient(135deg, #10b981, #059669);
    --gradient-red: linear-gradient(135deg, #ef4444, #dc2626);
    --gradient-blue: linear-gradient(135deg, #3b82f6, #2563eb);
    --gradient-purple: linear-gradient(135deg, #8b5cf6, #7c3aed);
}

/* Main background */
.stApp {
    background: var(--bg-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* Hide Streamlit branding but keep sidebar toggle */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Force sidebar toggle button visible */
[data-testid="stSidebarCollapsedControl"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
}

button[kind="header"] {
    display: block !important;
    visibility: visible !important;
}

section[data-testid="stSidebarContent"] {
    display: block !important;
}

[data-testid="collapsedControl"] {
    display: block !important;
    visibility: visible !important;
}

/* User badge styles */
.user-badge {
    display: inline-block;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: white !important;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.admin-badge {
    display: inline-block;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    color: white !important;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-blue); }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-color);
}

[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* Top header bar */
.pro-header {
    background: linear-gradient(135deg, #111827 0%, #1a1f2e 100%);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.pro-header-title {
    font-size: 22px;
    font-weight: 800;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
    font-family: 'Inter', sans-serif;
}

.pro-header-subtitle {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 2px;
}

.pro-header-live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    color: var(--accent-green);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.live-dot {
    width: 8px;
    height: 8px;
    background: var(--accent-green);
    border-radius: 50%;
    display: inline-block;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { opacity: 1; box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
    50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(16,185,129,0); }
    100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16,185,129,0); }
}

/* Metric cards */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.metric-card:hover {
    border-color: var(--accent-blue);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.1);
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}

.metric-card.blue::before { background: var(--gradient-blue); }
.metric-card.green::before { background: var(--gradient-green); }
.metric-card.red::before { background: var(--gradient-red); }
.metric-card.purple::before { background: var(--gradient-purple); }

.metric-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
    margin-bottom: 8px;
}

.metric-value {
    font-size: 28px;
    font-weight: 800;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -1px;
}

.metric-value.positive { color: var(--accent-green); }
.metric-value.negative { color: var(--accent-red); }

.metric-change {
    font-size: 12px;
    font-weight: 600;
    margin-top: 4px;
}

.metric-change.up { color: var(--accent-green); }
.metric-change.down { color: var(--accent-red); }

/* Signal cards */
.signal-card-pro {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    margin: 12px 0;
    transition: all 0.3s ease;
    position: relative;
}

.signal-card-pro:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.signal-card-pro.buy {
    border-left: 4px solid var(--accent-green);
}

.signal-card-pro.sell {
    border-left: 4px solid var(--accent-red);
}

.signal-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.signal-badge.buy { background: rgba(16,185,129,0.15); color: var(--accent-green); }
.signal-badge.sell { background: rgba(239,68,68,0.15); color: var(--accent-red); }
.signal-badge.high { background: rgba(16,185,129,0.15); color: var(--accent-green); }
.signal-badge.medium { background: rgba(245,158,11,0.15); color: var(--accent-yellow); }
.signal-badge.low { background: rgba(239,68,68,0.15); color: var(--accent-red); }

/* Position tracker */
.position-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px 20px;
    margin: 8px 0;
}

.position-card.profit { border-left: 4px solid var(--accent-green); }
.position-card.loss { border-left: 4px solid var(--accent-red); }

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 4px;
    border: 1px solid var(--border-color);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.3px;
    padding: 8px 20px;
    color: var(--text-secondary) !important;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-blue) !important;
    color: white !important;
}

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.3px !important;
    transition: all 0.2s ease !important;
    border: none !important;
}

.stButton > button[kind="primary"] {
    background: var(--gradient-blue) !important;
    color: white !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 15px rgba(59,130,246,0.4) !important;
    transform: translateY(-1px) !important;
}

/* Analysis section */
.analysis-box {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
}

.analysis-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}

/* Separator */
.pro-separator {
    height: 1px;
    background: var(--border-color);
    margin: 20px 0;
}

/* Active position tracker */
.tracker-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid rgba(42,48,66,0.5);
}

.tracker-symbol {
    font-weight: 700;
    font-size: 15px;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
}

/* Chart annotations */
.chart-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 12px;
    margin: 8px 0;
}
</style>
"""


# ============================================================
# DATA ENGINE
# ============================================================
class TradingDataEngine:
    """Handles all data fetching, analysis, and signal generation"""
    
    def __init__(self):
        self.api_client = FortradeAPIClient(
            api_key=TradingConfig.FORTRADE_API_KEY,
            api_secret=TradingConfig.FORTRADE_API_SECRET,
            account_id=TradingConfig.FORTRADE_ACCOUNT_ID,
            base_url=TradingConfig.API_BASE_URL,
            paper_trading=(TradingConfig.TRADING_MODE == "PAPER")
        )
        self.strategy_manager = StrategyManager(TradingConfig)
        self.risk_manager = RiskManager(TradingConfig)
        self.signal_validator = AdvancedSignalValidator(TradingConfig)
        
        # Core quantum systems
        self.quantum_scorer = QuantumScorer()
        self.structure_analyzer = MarketStructureAnalyzer()
        self.adaptive_learner = AdaptiveLearner()
        self.execution_manager = ExecutionManager(broker=PaperBroker(initial_balance=TradingConfig.INITIAL_CAPITAL))
        
        # Advanced intelligence layers (hedge-fund grade)
        try:
            from core.alpha_engine import AlphaEngine
            from core.regime_model import RegimeModel
            from core.portfolio_optimizer import PortfolioOptimizer
            from core.drift_detector import DriftDetector
            
            self.alpha_engine = AlphaEngine()
            self.regime_model = RegimeModel(use_ml=False)
            self.portfolio_optimizer = PortfolioOptimizer(
                target_volatility=0.15,
                target_risk_per_position=1.0,
                correlation_threshold=0.7
            )
            self.drift_detector = DriftDetector()
            self.advanced_intelligence_enabled = True
            print("✅ Advanced intelligence layers loaded successfully")
        except ImportError as e:
            self.advanced_intelligence_enabled = False
            print(f"⚠️ Advanced intelligence layers not available: {e}")
    
    def get_market_data(self, symbol: str, periods: int = 200) -> pd.DataFrame:
        """Fetch and prepare market data with indicators"""
        candles = self.api_client.get_historical_data(
            symbol=symbol, timeframe='15m', limit=periods
        )
        
        if not candles:
            return pd.DataFrame()
        
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        # Convert to Macedonia time (UTC+2)
        df['timestamp'] = df['timestamp'].dt.tz_convert('Europe/Skopje')
        df.set_index('timestamp', inplace=True)
        df = df.sort_index()
        
        # Calculate all indicators
        df = self._add_indicators(df)
        
        return df
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators to dataframe"""
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Moving Averages
        df['ema_20'] = close.ewm(span=20).mean()
        df['ema_50'] = close.ewm(span=50).mean()
        df['sma_200'] = close.rolling(window=min(200, len(df))).mean()
        
        # Bollinger Bands
        df['bb_middle'] = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        
        # Volume MA
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        # Stochastic
        low_14 = low.rolling(window=14).min()
        high_14 = high.rolling(window=14).max()
        df['stoch_k'] = ((close - low_14) / (high_14 - low_14)) * 100
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        # Fibonacci Retracement Levels
        swing_high = df['high'].rolling(window=50).max()
        swing_low = df['low'].rolling(window=50).min()
        diff = swing_high - swing_low
        df['fib_0'] = swing_high
        df['fib_236'] = swing_high - (diff * 0.236)
        df['fib_382'] = swing_high - (diff * 0.382)
        df['fib_500'] = swing_high - (diff * 0.500)
        df['fib_618'] = swing_high - (diff * 0.618)
        df['fib_786'] = swing_high - (diff * 0.786)
        df['fib_1'] = swing_low
        
        # ADX - Trend Strength
        plus_dm = high.diff()
        minus_dm = (-low).diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        atr_14 = df['atr'].copy()
        atr_14 = atr_14.replace(0, np.nan)
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr_14)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr_14)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
        df['adx'] = dx.rolling(14).mean()
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        
        # Momentum
        df['momentum'] = close.pct_change(periods=10) * 100
        
        # VWAP approximation
        if 'volume' in df.columns:
            df['vwap'] = (df['volume'] * (high + low + close) / 3).cumsum() / df['volume'].cumsum()
        
        return df
    
    def get_signals(self):
        """Get all current signals with full quantum scoring pipeline"""
        market_data = {}
        strategy_data = {}
        
        for symbol in TradingConfig.INSTRUMENTS:
            df = self.get_market_data(symbol)
            if not df.empty:
                market_data[symbol] = df
                strategy_data[symbol] = df
        
        signals = self.strategy_manager.get_signals(strategy_data)
        
        result = []
        session = self.risk_manager.get_current_session()
        
        for signal in signals:
            if signal.symbol not in market_data:
                continue
            
            df = market_data[signal.symbol]
            sig_type = signal.signal_type.value  # 'buy' or 'sell'
            
            # Step 1: Basic validation
            validation = self.signal_validator.validate_signal(signal, df)
            
            # Step 2: Market structure analysis
            try:
                structure = self.structure_analyzer.analyze(df, sig_type)
            except Exception:
                structure = StructureAnalysis()
            
            # Step 3: Quantum probabilistic scoring (replaces hard cutoffs)
            try:
                scoring = self.quantum_scorer.score_signal(
                    df=df,
                    signal_type=sig_type,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    symbol=signal.symbol,
                    strategy=signal.strategy,
                    market_structure=structure.to_dict() if structure else None
                )
            except Exception:
                scoring = ScoringBreakdown(final_score=0.5)
            
            # Step 4: AI confidence adjustment
            try:
                regime = scoring.volatility_regime
                record = self.adaptive_learner.extract_features(
                    df=df, signal_type=sig_type,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    symbol=signal.symbol,
                    strategy=signal.strategy,
                    quantum_score=scoring.final_score,
                    structure_alignment=structure.alignment_score if structure else 0,
                    session=session,
                    regime=regime
                )
                adjusted_score, ai_details = self.adaptive_learner.adjust_confidence(
                    scoring.final_score, record
                )
            except Exception:
                adjusted_score = scoring.final_score
                ai_details = {'blend_mode': 'error'}
            
            # Use quantum score as the primary confidence
            signal.confidence = adjusted_score
            
            # Get recommendation
            recommendation, rec_detail = self.quantum_scorer.get_trade_recommendation(adjusted_score)
            
            result.append({
                'signal': signal,
                'validation': validation,
                'is_validated': validation.is_valid,
                'session': session,
                'quantum_score': scoring.final_score,
                'adjusted_score': adjusted_score,
                'scoring': scoring,
                'structure': structure,
                'ai_details': ai_details,
                'recommendation': recommendation,
                'rec_detail': rec_detail,
                'regime': scoring.volatility_regime,
                'rr_ratio': scoring.risk_reward_ratio,
            })
        
        result.sort(key=lambda x: x['adjusted_score'], reverse=True)
        return result, market_data
    
    def get_full_analysis(self, df: pd.DataFrame, symbol: str) -> dict:
        """Complete technical analysis of a symbol"""
        if df.empty or len(df) < 20:
            return {}
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = last['close']
        
        # Trend Analysis
        trend = "BULLISH" if last['ema_20'] > last['ema_50'] else "BEARISH"
        trend_strength = abs(last['ema_20'] - last['ema_50']) / last['ema_50'] * 100
        
        # RSI Analysis
        rsi = last['rsi']
        rsi_status = "OVERSOLD" if rsi < 30 else "OVERBOUGHT" if rsi > 70 else "NEUTRAL"
        
        # MACD Analysis
        macd_trend = "BULLISH" if last['macd'] > last['macd_signal'] else "BEARISH"
        macd_crossover = (
            (last['macd'] > last['macd_signal'] and prev['macd'] <= prev['macd_signal']) or
            (last['macd'] < last['macd_signal'] and prev['macd'] >= prev['macd_signal'])
        )
        
        # Bollinger Analysis
        bb_position = (close - last['bb_lower']) / (last['bb_upper'] - last['bb_lower']) * 100 if (last['bb_upper'] - last['bb_lower']) > 0 else 50
        bb_status = "UPPER BAND" if bb_position > 80 else "LOWER BAND" if bb_position < 20 else "MIDDLE"
        
        # Stochastic
        stoch_status = "OVERSOLD" if last['stoch_k'] < 20 else "OVERBOUGHT" if last['stoch_k'] > 80 else "NEUTRAL"
        
        # Volatility
        volatility = last['atr'] / close * 100
        vol_status = "HIGH" if volatility > 1.5 else "LOW" if volatility < 0.5 else "NORMAL"
        
        # Support / Resistance
        recent = df.tail(50)
        support = recent['low'].min()
        resistance = recent['high'].max()
        
        # ADX Trend Strength
        adx = last.get('adx', 0)
        if pd.isna(adx): adx = 0
        adx_status = "STRONG TREND" if adx > 25 else "WEAK/NO TREND"
        
        # Momentum
        momentum = last.get('momentum', 0)
        if pd.isna(momentum): momentum = 0
        mom_status = "BULLISH" if momentum > 0.5 else "BEARISH" if momentum < -0.5 else "FLAT"
        
        # Fibonacci proximity
        fib_levels = {}
        for fib_name in ['fib_0', 'fib_236', 'fib_382', 'fib_500', 'fib_618', 'fib_786', 'fib_1']:
            val = last.get(fib_name, 0)
            if not pd.isna(val):
                fib_levels[fib_name] = val
        
        nearest_fib = ''
        nearest_fib_dist = float('inf')
        for name, val in fib_levels.items():
            dist = abs(close - val)
            if dist < nearest_fib_dist:
                nearest_fib_dist = dist
                nearest_fib = name.replace('fib_', '').replace('_', '.')
        
        # VWAP
        vwap = last.get('vwap', close)
        if pd.isna(vwap): vwap = close
        vwap_status = "ABOVE VWAP" if close > vwap else "BELOW VWAP"
        
        # Comprehensive scoring (10-point system)
        bullish_score = 0
        bearish_score = 0
        
        # 1. EMA alignment
        if last['ema_20'] > last['ema_50']:
            bullish_score += 1
        else:
            bearish_score += 1
        
        # 2. RSI
        if rsi < 35:
            bullish_score += 1
        elif rsi > 65:
            bearish_score += 1
        
        # 3. MACD
        if last['macd'] > last['macd_signal']:
            bullish_score += 1
        else:
            bearish_score += 1
        
        # 4. Bollinger
        if bb_position < 25:
            bullish_score += 1
        elif bb_position > 75:
            bearish_score += 1
        
        # 5. Stochastic
        if last['stoch_k'] < 25:
            bullish_score += 1
        elif last['stoch_k'] > 75:
            bearish_score += 1
        
        # 6. ADX confirms trend
        if adx > 25:
            if last.get('plus_di', 0) > last.get('minus_di', 0):
                bullish_score += 1
            else:
                bearish_score += 1
        
        # 7. Momentum
        if momentum > 0.3:
            bullish_score += 1
        elif momentum < -0.3:
            bearish_score += 1
        
        # 8. VWAP
        if close > vwap:
            bullish_score += 1
        else:
            bearish_score += 1
        
        # 9. Price relative to SMA 200
        sma200 = last.get('sma_200', close)
        if not pd.isna(sma200) and close > sma200:
            bullish_score += 1
        else:
            bearish_score += 1
        
        # 10. MACD crossover bonus
        if macd_crossover:
            if last['macd'] > last['macd_signal']:
                bullish_score += 1
            else:
                bearish_score += 1
        
        total_score = bullish_score - bearish_score
        
        if total_score >= 5:
            overall = "STRONG BUY"
        elif total_score >= 3:
            overall = "BUY"
        elif total_score >= 1:
            overall = "WEAK BUY"
        elif total_score <= -5:
            overall = "STRONG SELL"
        elif total_score <= -3:
            overall = "SELL"
        elif total_score <= -1:
            overall = "WEAK SELL"
        else:
            overall = "NEUTRAL"
        
        # Market Structure Analysis
        try:
            structure = self.structure_analyzer.analyze(df, 'buy' if total_score > 0 else 'sell')
            struct_trend = structure.trend
            struct_break = structure.structure_break
            struct_break_type = structure.break_type
            struct_break_dir = structure.break_direction
            struct_alignment = structure.alignment_score
            struct_narrative = structure.narrative
            order_blocks = len(structure.order_blocks)
            liquidity_zones = len(structure.liquidity_zones)
            sd_zones = len(structure.supply_demand_zones)
            key_levels = structure.key_levels
        except Exception:
            struct_trend = "N/A"
            struct_break = False
            struct_break_type = ""
            struct_break_dir = ""
            struct_alignment = 0
            struct_narrative = ""
            order_blocks = 0
            liquidity_zones = 0
            sd_zones = 0
            key_levels = []
        
        # Quantum Score (quick)
        try:
            q_scoring = self.quantum_scorer.score_signal(
                df=df, signal_type='buy' if total_score > 0 else 'sell',
                entry_price=close, stop_loss=support, take_profit=resistance,
                symbol=symbol
            )
            quantum_prob = q_scoring.final_score
            regime = q_scoring.volatility_regime
        except Exception:
            quantum_prob = 0.5
            regime = 'normal'
        
        return {
            'symbol': symbol,
            'price': close,
            'trend': trend,
            'trend_strength': trend_strength,
            'rsi': rsi,
            'rsi_status': rsi_status,
            'macd_trend': macd_trend,
            'macd_crossover': macd_crossover,
            'bb_position': bb_position,
            'bb_status': bb_status,
            'stoch_k': last['stoch_k'],
            'stoch_d': last['stoch_d'],
            'stoch_status': stoch_status,
            'atr': last['atr'],
            'volatility': volatility,
            'vol_status': vol_status,
            'support': support,
            'resistance': resistance,
            'ema_20': last['ema_20'],
            'ema_50': last['ema_50'],
            'overall': overall,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'total_score': total_score,
            'adx': adx,
            'adx_status': adx_status,
            'momentum': momentum,
            'mom_status': mom_status,
            'vwap': vwap,
            'vwap_status': vwap_status,
            'nearest_fib': nearest_fib,
            'fib_levels': fib_levels,
            # New quantum fields
            'quantum_prob': quantum_prob,
            'regime': regime,
            'struct_trend': struct_trend,
            'struct_break': struct_break,
            'struct_break_type': struct_break_type,
            'struct_break_dir': struct_break_dir,
            'struct_alignment': struct_alignment,
            'struct_narrative': struct_narrative,
            'order_blocks': order_blocks,
            'liquidity_zones': liquidity_zones,
            'sd_zones': sd_zones,
            'key_levels': key_levels,
        }
    
    def execute_trade(self, signal_data):
        """Execute trade from signal"""
        signal = signal_data['signal']
        
        can_trade, reason = self.risk_manager.can_open_position(signal)
        if not can_trade:
            return False, reason
        
        position_size, allowed, size_reason = self.risk_manager.calculate_position_size(
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            symbol=signal.symbol
        )
        
        if not allowed:
            return False, size_reason
        
        order_response = self.api_client.place_order(
            symbol=signal.symbol,
            side=signal.signal_type.value,
            quantity=position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            order_type='market'
        )
        
        if order_response and 'order_id' in order_response:
            self.risk_manager.add_position(
                order_id=order_response['order_id'],
                symbol=signal.symbol,
                side=signal.signal_type.value,
                quantity=position_size,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy=signal.strategy
            )
            return True, order_response['order_id']
        
        return False, "Order execution failed"
    
    def close_position(self, order_id):
        """Close a position"""
        try:
            position = self.risk_manager.open_positions.get(order_id)
            self.api_client.close_position(order_id)
            
            if position:
                market_data = self.api_client.get_market_data(position.symbol)
                exit_price = market_data.get('bid', position.entry_price)
                self.risk_manager.close_position(order_id, exit_price, "Manual close from dashboard")
            
            return True
        except Exception as e:
            return False


# ============================================================
# CHART BUILDER
# ============================================================
class ProChartBuilder:
    """Creates professional trading charts"""
    
    CHART_COLORS = {
        'bg': '#0a0e17',
        'grid': '#1a1f2e',
        'text': '#94a3b8',
        'candle_up': '#10b981',
        'candle_down': '#ef4444',
        'ema_20': '#3b82f6',
        'ema_50': '#f59e0b',
        'sma_200': '#8b5cf6',
        'bb_fill': 'rgba(59,130,246,0.08)',
        'bb_line': 'rgba(59,130,246,0.3)',
        'volume_up': 'rgba(16,185,129,0.4)',
        'volume_down': 'rgba(239,68,68,0.4)',
        'buy_marker': '#10b981',
        'sell_marker': '#ef4444',
        'support': '#06b6d4',
        'resistance': '#f59e0b',
    }
    
    @staticmethod
    def create_main_chart(df: pd.DataFrame, symbol: str, 
                          signals=None, positions=None,
                          show_bb=True, show_ema=True, show_volume=True,
                          show_rsi=True, show_macd=True) -> go.Figure:
        """Create full professional trading chart"""
        
        if df.empty:
            return go.Figure()
        
        colors = ProChartBuilder.CHART_COLORS
        
        # Determine subplot count
        rows = 1
        row_heights = [0.5]
        
        if show_volume:
            rows += 1
            row_heights.append(0.1)
        if show_rsi:
            rows += 1
            row_heights.append(0.15)
        if show_macd:
            rows += 1
            row_heights.append(0.15)
        
        # Normalize heights
        total = sum(row_heights)
        row_heights = [h/total for h in row_heights]
        
        subplot_titles = [f'{symbol} - 15min']
        if show_volume: subplot_titles.append('Volume')
        if show_rsi: subplot_titles.append('RSI (14)')
        if show_macd: subplot_titles.append('MACD (12,26,9)')
        
        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=row_heights,
            subplot_titles=subplot_titles
        )
        
        # === ROW 1: Candlestick ===
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing=dict(line=dict(color=colors['candle_up'], width=1), fillcolor=colors['candle_up']),
            decreasing=dict(line=dict(color=colors['candle_down'], width=1), fillcolor=colors['candle_down']),
            name='Price',
            showlegend=False
        ), row=1, col=1)
        
        # Bollinger Bands
        if show_bb and 'bb_upper' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['bb_upper'],
                mode='lines',
                line=dict(color=colors['bb_line'], width=1, dash='dot'),
                name='BB Upper',
                showlegend=False
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df.index, y=df['bb_lower'],
                mode='lines',
                line=dict(color=colors['bb_line'], width=1, dash='dot'),
                fill='tonexty',
                fillcolor=colors['bb_fill'],
                name='BB Lower',
                showlegend=False
            ), row=1, col=1)
        
        # EMAs
        if show_ema:
            if 'ema_20' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df['ema_20'],
                    mode='lines',
                    line=dict(color=colors['ema_20'], width=1.5),
                    name='EMA 20'
                ), row=1, col=1)
            
            if 'ema_50' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df['ema_50'],
                    mode='lines',
                    line=dict(color=colors['ema_50'], width=1.5),
                    name='EMA 50'
                ), row=1, col=1)
            
            if 'sma_200' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df['sma_200'],
                    mode='lines',
                    line=dict(color=colors['sma_200'], width=1, dash='dash'),
                    name='SMA 200'
                ), row=1, col=1)
        
        # Support / Resistance lines
        recent = df.tail(50)
        support = recent['low'].min()
        resistance = recent['high'].max()
        
        fig.add_hline(y=support, line=dict(color=colors['support'], width=1, dash='dash'),
                      annotation_text=f"Support: {support:.5f}",
                      annotation_position="bottom right",
                      annotation_font_color=colors['support'],
                      row=1, col=1)
        
        fig.add_hline(y=resistance, line=dict(color=colors['resistance'], width=1, dash='dash'),
                      annotation_text=f"Resistance: {resistance:.5f}",
                      annotation_position="top right",
                      annotation_font_color=colors['resistance'],
                      row=1, col=1)
        
        # Fibonacci Retracement Levels
        if 'fib_236' in df.columns:
            last = df.iloc[-1]
            fib_data = [
                ('0%', last.get('fib_0', 0), 'rgba(139,92,246,0.6)'),
                ('23.6%', last.get('fib_236', 0), 'rgba(139,92,246,0.4)'),
                ('38.2%', last.get('fib_382', 0), 'rgba(139,92,246,0.4)'),
                ('50%', last.get('fib_500', 0), 'rgba(245,158,11,0.5)'),
                ('61.8%', last.get('fib_618', 0), 'rgba(16,185,129,0.5)'),
                ('78.6%', last.get('fib_786', 0), 'rgba(139,92,246,0.4)'),
                ('100%', last.get('fib_1', 0), 'rgba(239,68,68,0.4)'),
            ]
            for label, level, color in fib_data:
                if not pd.isna(level) and level > 0:
                    fig.add_hline(
                        y=level,
                        line=dict(color=color, width=0.8, dash='dot'),
                        annotation_text=f"Fib {label}",
                        annotation_position="left",
                        annotation_font_color=color,
                        annotation_font_size=9,
                        row=1, col=1
                    )
        
        # BUY/SELL Signal markers
        if signals:
            for sig_data in signals:
                sig = sig_data['signal']
                if sig.symbol == symbol:
                    marker_color = colors['buy_marker'] if sig.signal_type == SignalType.BUY else colors['sell_marker']
                    marker_symbol = 'triangle-up' if sig.signal_type == SignalType.BUY else 'triangle-down'
                    action = "BUY" if sig.signal_type == SignalType.BUY else "SELL"
                    
                    fig.add_trace(go.Scatter(
                        x=[df.index[-1]],
                        y=[sig.entry_price],
                        mode='markers+text',
                        marker=dict(
                            symbol=marker_symbol,
                            size=18,
                            color=marker_color,
                            line=dict(color='white', width=1)
                        ),
                        text=[f" {action} {sig.confidence*100:.0f}%"],
                        textposition='middle right',
                        textfont=dict(color=marker_color, size=12, family='JetBrains Mono'),
                        name=f'{action} Signal',
                        showlegend=True
                    ), row=1, col=1)
                    
                    # SL/TP lines
                    fig.add_hline(y=sig.take_profit, 
                                  line=dict(color=colors['buy_marker'], width=1, dash='dot'),
                                  annotation_text=f"TP: {sig.take_profit:.5f}",
                                  annotation_font_color=colors['buy_marker'],
                                  annotation_position="bottom right",
                                  row=1, col=1)
                    
                    fig.add_hline(y=sig.stop_loss,
                                  line=dict(color=colors['sell_marker'], width=1, dash='dot'),
                                  annotation_text=f"SL: {sig.stop_loss:.5f}",
                                  annotation_font_color=colors['sell_marker'],
                                  annotation_position="top right",
                                  row=1, col=1)
        
        # Position markers
        if positions:
            for pos in positions:
                if hasattr(pos, 'symbol') and pos.symbol == symbol:
                    pos_color = colors['buy_marker'] if pos.side == 'buy' else colors['sell_marker']
                    fig.add_hline(y=pos.entry_price,
                                  line=dict(color=pos_color, width=2),
                                  annotation_text=f"Entry: {pos.entry_price:.5f} ({pos.side.upper()})",
                                  annotation_font_color=pos_color,
                                  row=1, col=1)
        
        current_row = 2
        
        # === Volume ===
        if show_volume and 'volume' in df.columns:
            vol_colors = [colors['volume_up'] if df['close'].iloc[i] >= df['open'].iloc[i] 
                         else colors['volume_down'] for i in range(len(df))]
            
            fig.add_trace(go.Bar(
                x=df.index, y=df['volume'],
                marker_color=vol_colors,
                name='Volume',
                showlegend=False
            ), row=current_row, col=1)
            
            if 'volume_ma' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df['volume_ma'],
                    mode='lines',
                    line=dict(color=colors['ema_20'], width=1),
                    name='Vol MA',
                    showlegend=False
                ), row=current_row, col=1)
            
            current_row += 1
        
        # === RSI ===
        if show_rsi and 'rsi' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['rsi'],
                mode='lines',
                line=dict(color=colors['ema_20'], width=1.5),
                name='RSI',
                showlegend=False
            ), row=current_row, col=1)
            
            fig.add_hline(y=70, line=dict(color=colors['sell_marker'], width=0.5, dash='dash'),
                          row=current_row, col=1)
            fig.add_hline(y=30, line=dict(color=colors['buy_marker'], width=0.5, dash='dash'),
                          row=current_row, col=1)
            fig.add_hline(y=50, line=dict(color=colors['text'], width=0.3, dash='dot'),
                          row=current_row, col=1)
            
            # RSI fill zones
            fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.05)", 
                         line_width=0, row=current_row, col=1)
            fig.add_hrect(y0=0, y1=30, fillcolor="rgba(16,185,129,0.05)",
                         line_width=0, row=current_row, col=1)
            
            current_row += 1
        
        # === MACD ===
        if show_macd and 'macd' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['macd'],
                mode='lines',
                line=dict(color=colors['ema_20'], width=1.5),
                name='MACD',
                showlegend=False
            ), row=current_row, col=1)
            
            fig.add_trace(go.Scatter(
                x=df.index, y=df['macd_signal'],
                mode='lines',
                line=dict(color=colors['sell_marker'], width=1),
                name='Signal',
                showlegend=False
            ), row=current_row, col=1)
            
            macd_colors = [colors['candle_up'] if v >= 0 else colors['candle_down'] 
                          for v in df['macd_hist']]
            
            fig.add_trace(go.Bar(
                x=df.index, y=df['macd_hist'],
                marker_color=macd_colors,
                name='MACD Hist',
                showlegend=False,
                opacity=0.6
            ), row=current_row, col=1)
        
        # Layout
        fig.update_layout(
            height=700,
            template='plotly_dark',
            paper_bgcolor=colors['bg'],
            plot_bgcolor=colors['bg'],
            font=dict(family='Inter, sans-serif', color=colors['text'], size=11),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                bgcolor='rgba(0,0,0,0)',
                font=dict(size=10)
            ),
            margin=dict(l=60, r=20, t=40, b=20),
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )
        
        # Grid styling
        for i in range(1, rows + 1):
            fig.update_xaxes(
                gridcolor='rgba(42,48,66,0.3)',
                zeroline=False,
                row=i, col=1
            )
            fig.update_yaxes(
                gridcolor='rgba(42,48,66,0.3)',
                zeroline=False,
                side='right',
                row=i, col=1
            )
        
        return fig


# ============================================================
# MAIN DASHBOARD
# ============================================================
def render_header():
    """Render premium header"""
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="pro-header">
        <div>
            <div class="pro-header-title">QUANTUMTRADE ENGINE</div>
            <div class="pro-header-subtitle">Advanced Trading Terminal v3.0</div>
        </div>
        <div style="display: flex; align-items: center; gap: 16px;">
            <div class="pro-header-live">
                <span class="live-dot"></span>
                {TradingConfig.TRADING_MODE} MODE
            </div>
            <div style="color: var(--text-muted); font-size: 12px; font-family: 'JetBrains Mono', monospace;">
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC+2
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_metrics(engine: TradingDataEngine):
    """Render top metric cards"""
    balance = float(st.session_state.get('initial_capital', TradingConfig.INITIAL_CAPITAL))
    risk_summary = engine.risk_manager.get_risk_summary()
    daily_pnl = risk_summary['daily_pnl']
    daily_return = risk_summary['daily_return_percent']
    positions = risk_summary['open_positions']
    trades = risk_summary['trades_today']
    win_rate = risk_summary.get('win_rate', 0)
    
    session = engine.risk_manager.get_current_session()
    session_mult = engine.risk_manager.get_session_confidence_multiplier()
    
    pnl_class = 'positive' if daily_pnl >= 0 else 'negative'
    pnl_arrow = '+' if daily_pnl >= 0 else ''
    change_class = 'up' if daily_pnl >= 0 else 'down'
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card blue">
            <div class="metric-label">Portfolio Value</div>
            <div class="metric-value">EUR {balance:.2f}</div>
            <div class="metric-change {change_class}">{pnl_arrow}{daily_return:.2f}% today</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card {'green' if daily_pnl >= 0 else 'red'}">
            <div class="metric-label">Daily P&L</div>
            <div class="metric-value {pnl_class}">{pnl_arrow}EUR {daily_pnl:.2f}</div>
            <div class="metric-change {change_class}">{pnl_arrow}{daily_return:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">{win_rate:.1f}%</div>
            <div class="metric-change">All time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card blue">
            <div class="metric-label">Open Positions</div>
            <div class="metric-value">{positions}</div>
            <div class="metric-change">/ {TradingConfig.MAX_CONCURRENT_POSITIONS} max</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card blue">
            <div class="metric-label">Trades Today</div>
            <div class="metric-value">{trades}</div>
            <div class="metric-change">/ {TradingConfig.MAX_TRADES_PER_DAY} max</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        session_colors = {'asian': '#06b6d4', 'london': '#3b82f6', 'newyork': '#f59e0b', 'overlap': '#10b981', 'off_hours': '#64748b'}
        s_color = session_colors.get(session, '#64748b')
        st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-label">Session</div>
            <div class="metric-value" style="font-size: 20px; color: {s_color};">{session.upper()}</div>
            <div class="metric-change">x{session_mult:.1f} confidence</div>
        </div>
        """, unsafe_allow_html=True)


def render_analysis_panel(analysis: dict):
    """Render full technical analysis panel with 10-point scoring"""
    if not analysis:
        return
    
    overall = analysis['overall']
    overall_color = '#10b981' if 'BUY' in overall else '#ef4444' if 'SELL' in overall else '#f59e0b'
    bull = analysis.get('bullish_score', 0)
    bear = analysis.get('bearish_score', 0)
    total = analysis.get('total_score', 0)
    
    # Score gauge bar
    gauge_pct = max(0, min(100, (total + 10) * 5))  # -10 to +10 -> 0% to 100%
    gauge_color = '#10b981' if total >= 3 else '#ef4444' if total <= -3 else '#f59e0b'
    
    st.markdown(f"""
    <div class="analysis-box">
        <div class="analysis-title">Technical Analysis - {analysis['symbol']}</div>
        <div style="text-align: center; margin: 15px 0;">
            <div style="font-size: 32px; font-weight: 800; color: {overall_color}; 
                        font-family: 'JetBrains Mono', monospace;">{overall}</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">
                10-Point Composite Score: <span style="color: {gauge_color}; font-weight: 700;">{total:+d}</span> 
                &nbsp;|&nbsp; Bullish: {bull} &nbsp;|&nbsp; Bearish: {bear}
            </div>
            <div style="margin: 12px auto; width: 80%; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                <div style="width: {gauge_pct}%; height: 100%; background: linear-gradient(90deg, #ef4444, #f59e0b 40%, #10b981 70%); 
                            border-radius: 4px; transition: width 0.3s;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; width: 80%; margin: 0 auto; font-size: 10px; color: var(--text-muted);">
                <span>STRONG SELL</span><span>SELL</span><span>NEUTRAL</span><span>BUY</span><span>STRONG BUY</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Row 1: Trend, RSI, MACD
    col1, col2, col3 = st.columns(3)
    
    with col1:
        trend_color = '#10b981' if analysis['trend'] == 'BULLISH' else '#ef4444'
        adx_val = analysis.get('adx', 0)
        adx_status = analysis.get('adx_status', 'N/A')
        adx_color = '#10b981' if adx_val > 25 else '#f59e0b'
        st.markdown(f"""
        <div class="analysis-box">
            <div class="analysis-title">Trend & Strength</div>
            <div style="color: {trend_color}; font-weight: 700; font-size: 16px;">{analysis['trend']}</div>
            <div style="color: var(--text-secondary); font-size: 12px; margin-top: 4px;">
                EMA Divergence: {analysis['trend_strength']:.3f}%
            </div>
            <div style="color: {adx_color}; font-size: 13px; font-weight: 600; margin-top: 6px;">
                ADX: {adx_val:.1f} ({adx_status})
            </div>
            <div style="color: var(--text-muted); font-size: 11px; margin-top: 6px;">
                EMA 20: {analysis['ema_20']:.5f}<br>
                EMA 50: {analysis['ema_50']:.5f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        rsi_color = '#10b981' if analysis['rsi_status'] == 'OVERSOLD' else '#ef4444' if analysis['rsi_status'] == 'OVERBOUGHT' else '#f59e0b'
        st.markdown(f"""
        <div class="analysis-box">
            <div class="analysis-title">RSI ({analysis['rsi']:.1f})</div>
            <div style="color: {rsi_color}; font-weight: 700; font-size: 16px;">{analysis['rsi_status']}</div>
            <div style="margin: 6px 0; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden;">
                <div style="width: {min(100, analysis['rsi'])}%; height: 100%; 
                            background: {'#ef4444' if analysis['rsi'] > 70 else '#10b981' if analysis['rsi'] < 30 else '#f59e0b'};
                            border-radius: 3px;"></div>
            </div>
            <div style="color: var(--text-muted); font-size: 11px; margin-top: 6px;">
                Stochastic K: {analysis['stoch_k']:.1f} | D: {analysis['stoch_d']:.1f}<br>
                Stoch: {analysis['stoch_status']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        macd_color = '#10b981' if analysis['macd_trend'] == 'BULLISH' else '#ef4444'
        cross_text = "CROSSOVER!" if analysis['macd_crossover'] else "No crossover"
        cross_icon = "⚡" if analysis['macd_crossover'] else ""
        st.markdown(f"""
        <div class="analysis-box">
            <div class="analysis-title">MACD</div>
            <div style="color: {macd_color}; font-weight: 700; font-size: 16px;">{analysis['macd_trend']}</div>
            <div style="color: {'#f59e0b' if analysis['macd_crossover'] else 'var(--text-muted)'}; 
                        font-size: 12px; margin-top: 4px; font-weight: {'700' if analysis['macd_crossover'] else '400'};">
                {cross_icon} {cross_text}
            </div>
            <div style="color: var(--text-muted); font-size: 11px; margin-top: 6px;">
                Volatility: {analysis['vol_status']} ({analysis['volatility']:.3f}%)<br>
                ATR: {analysis['atr']:.5f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Row 2: Momentum, VWAP, Fibonacci
    col4, col5, col6 = st.columns(3)
    
    with col4:
        mom = analysis.get('momentum', 0)
        mom_status = analysis.get('mom_status', 'N/A')
        mom_color = '#10b981' if mom > 0 else '#ef4444' if mom < 0 else '#f59e0b'
        st.markdown(f"""
        <div class="analysis-box">
            <div class="analysis-title">Momentum</div>
            <div style="color: {mom_color}; font-weight: 700; font-size: 18px; font-family: 'JetBrains Mono';">
                {'+'if mom>=0 else ''}{mom:.2f}%
            </div>
            <div style="color: {mom_color}; font-size: 12px; margin-top: 4px;">{mom_status}</div>
            <div style="color: var(--text-muted); font-size: 11px; margin-top: 6px;">
                10-period rate of change
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        vwap = analysis.get('vwap', 0)
        vwap_status = analysis.get('vwap_status', 'N/A')
        vwap_color = '#10b981' if 'ABOVE' in vwap_status else '#ef4444'
        st.markdown(f"""
        <div class="analysis-box">
            <div class="analysis-title">VWAP</div>
            <div style="color: {vwap_color}; font-weight: 700; font-size: 16px;">{vwap_status}</div>
            <div style="color: var(--text-muted); font-size: 13px; font-family: 'JetBrains Mono'; margin-top: 6px;">
                {vwap:.5f}
            </div>
            <div style="color: var(--text-muted); font-size: 11px; margin-top: 4px;">
                Volume-weighted avg price
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        nearest_fib = analysis.get('nearest_fib', 'N/A')
        st.markdown(f"""
        <div class="analysis-box">
            <div class="analysis-title">Fibonacci</div>
            <div style="color: #8b5cf6; font-weight: 700; font-size: 16px;">Near {nearest_fib}% Level</div>
            <div style="color: var(--text-muted); font-size: 11px; margin-top: 6px;">
                Bollinger: {analysis['bb_status']}<br>
                BB Position: {analysis['bb_position']:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Key Levels
    st.markdown(f"""
    <div class="analysis-box">
        <div class="analysis-title">Key Price Levels</div>
        <div style="display: flex; justify-content: space-around; padding: 10px 0; flex-wrap: wrap;">
            <div style="text-align: center; min-width: 100px;">
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">Support</div>
                <div style="font-size: 16px; font-weight: 700; color: #06b6d4; font-family: 'JetBrains Mono';">{analysis['support']:.5f}</div>
            </div>
            <div style="text-align: center; min-width: 100px;">
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">Current</div>
                <div style="font-size: 16px; font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono';">{analysis['price']:.5f}</div>
            </div>
            <div style="text-align: center; min-width: 100px;">
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">Resistance</div>
                <div style="font-size: 16px; font-weight: 700; color: #f59e0b; font-family: 'JetBrains Mono';">{analysis['resistance']:.5f}</div>
            </div>
            <div style="text-align: center; min-width: 100px;">
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">VWAP</div>
                <div style="font-size: 16px; font-weight: 700; color: #8b5cf6; font-family: 'JetBrains Mono';">{vwap:.5f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main dashboard entry point"""
    
    # ==================== AUTHENTICATION ====================
    db = get_database()
    user = check_auth()  # Shows login page if not authenticated
    
    render_header()
    
    # ==================== LOAD USER DATA FROM DB ====================
    if 'engine' not in st.session_state:
        st.session_state.engine = TradingDataEngine()
    if 'signals' not in st.session_state:
        st.session_state.signals = []
    if 'market_data' not in st.session_state:
        st.session_state.market_data = {}
    if 'active_positions' not in st.session_state:
        st.session_state.active_positions = []
    if 'trade_log' not in st.session_state:
        st.session_state.trade_log = []
    if 'selected_symbol' not in st.session_state:
        st.session_state.selected_symbol = TradingConfig.INSTRUMENTS[0]
    if 'alert_history' not in st.session_state:
        st.session_state.alert_history = []
    if 'alerted_signals' not in st.session_state:
        st.session_state.alerted_signals = set()
    
    # Load user settings from DB on first run
    if 'db_loaded' not in st.session_state:
        user_settings = db.get_settings(user['user_id'])
        if user_settings:
            st.session_state.initial_capital = float(user_settings.get('initial_capital', TradingConfig.INITIAL_CAPITAL))
            saved_symbols = user_settings.get('selected_symbols')
            if saved_symbols:
                st.session_state.selected_symbols = saved_symbols
            st.session_state.alert_threshold_saved = user_settings.get('alert_threshold', 70)
            st.session_state.alerts_enabled_saved = user_settings.get('alerts_enabled', True)
        
        # Load open positions from DB
        db_positions = db.get_open_positions(user['user_id'])
        if db_positions:
            st.session_state.active_positions = db_positions
        
        # Load trade history from DB
        db_trades = db.get_trade_history(user['user_id'], limit=50)
        if db_trades:
            st.session_state.trade_log = [
                {
                    'time': t.get('timestamp', datetime.now()).strftime('%H:%M:%S') if isinstance(t.get('timestamp'), datetime) else str(t.get('timestamp', '')),
                    'action': t['action'],
                    'symbol': t['symbol'],
                    'price': t['price'],
                    'pnl': t.get('pnl', 0),
                }
                for t in db_trades
            ]
        
        # Load alerts from DB
        db_alerts = db.get_alerts(user['user_id'], limit=20)
        if db_alerts:
            st.session_state.alert_history = [
                {
                    'time': a.get('timestamp', datetime.now()).strftime('%H:%M:%S') if isinstance(a.get('timestamp'), datetime) else str(a.get('timestamp', '')),
                    'symbol': a['symbol'],
                    'action': a['action'],
                    'confidence': a['confidence'],
                    'price': a.get('price', ''),
                    'strategy': a.get('strategy', ''),
                    'name': TradingConfig.SYMBOL_UNIVERSE.get(a['symbol'], a['symbol']),
                    'rr_ratio': a.get('rr_ratio', 0),
                    'tp': a.get('tp'),
                    'sl': a.get('sl'),
                }
                for a in db_alerts
            ]
        
        st.session_state.db_loaded = True
    
    engine = st.session_state.engine
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0 10px 0;">
            <div style="font-size: 20px; font-weight: 800; 
                        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                QUANTUMTRADE
            </div>
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 2px;">
                Engine
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # User info + logout
        render_user_sidebar(user)
        
        st.markdown("---")
        
        # Symbol selector (uses dynamically selected symbols)
        active_symbols = st.session_state.get('selected_symbols', TradingConfig.INSTRUMENTS)
        if st.session_state.selected_symbol not in active_symbols:
            st.session_state.selected_symbol = active_symbols[0] if active_symbols else TradingConfig.INSTRUMENTS[0]
        selected = st.selectbox(
            "Select Instrument",
            active_symbols,
            index=active_symbols.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in active_symbols else 0,
            format_func=lambda x: f"{x} - {TradingConfig.SYMBOL_UNIVERSE.get(x, x)}"
        )
        st.session_state.selected_symbol = selected
        
        # Portfolio capital setting
        st.markdown("---")
        st.markdown("**💰 Portfolio Settings**")
        capital_val = float(st.session_state.get('initial_capital', TradingConfig.INITIAL_CAPITAL))
        new_capital = st.number_input(
            "Starting Capital (EUR)",
            min_value=10.0,
            max_value=10000000.0,
            value=capital_val,
            step=100.0,
            format="%.2f"
        )
        if new_capital != st.session_state.get('initial_capital', 0):
            st.session_state.initial_capital = new_capital
            TradingConfig.INITIAL_CAPITAL = new_capital
            engine.execution_manager.broker.balance = new_capital
            engine.execution_manager.broker.equity = new_capital
            engine.api_client.paper_balance = new_capital
            # Save to DB
            db.save_settings(user['user_id'], {'initial_capital': new_capital})
        st.session_state.initial_capital = new_capital
        st.markdown(f'<div style="font-size:12px; color:#10b981; font-weight:600;">💰 Balance: €{new_capital:,.2f}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Scan button
        if st.button("SCAN MARKETS", type="primary"):
            with st.spinner("Analyzing all markets..."):
                # Load data for all selected symbols
                active_symbols = st.session_state.get('selected_symbols', TradingConfig.INSTRUMENTS)
                for sym in active_symbols:
                    if sym not in st.session_state.market_data:
                        try:
                            df = engine.get_market_data(sym)
                            if not df.empty:
                                st.session_state.market_data[sym] = df
                        except Exception:
                            pass
                signals, market_data = engine.get_signals()
                st.session_state.signals = signals
                st.session_state.market_data.update(market_data)
                st.rerun()
        
        # Chart options
        st.markdown("---")
        st.markdown("**Chart Indicators**")
        show_bb = st.checkbox("Bollinger Bands", value=True)
        show_ema = st.checkbox("Moving Averages", value=True)
        show_volume = st.checkbox("Volume", value=True)
        show_rsi = st.checkbox("RSI", value=True)
        show_macd = st.checkbox("MACD", value=True)
        
        st.markdown("---")
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-Refresh (Live Prices)", value=False)
        if auto_refresh:
            refresh_sec = st.slider("Interval (sec)", 10, 120, 30)
            st.markdown(f'<div style="color:#10b981; font-size:11px;">Live refresh every {refresh_sec}s</div>', unsafe_allow_html=True)
        
        # Alert settings
        st.markdown("---")
        st.markdown("**🔔 Signal Alerts**")
        alerts_enabled = st.checkbox("Enable Alerts", value=True)
        if alerts_enabled:
            alert_threshold = st.slider("Min Confidence %", 50, 95, 70, step=5)
            alert_sound = st.checkbox("Sound Alert", value=True)
            st.markdown(f'<div style="font-size:11px; color:#f59e0b;">Alerts for signals ≥ {alert_threshold}%</div>', unsafe_allow_html=True)
        else:
            alert_threshold = 100
            alert_sound = False
        
        # Show alert count
        alert_count = len(st.session_state.alert_history)
        if alert_count > 0:
            st.markdown(f'<div style="font-size:11px; color:#10b981; font-weight:600;">📬 {alert_count} alerts this session</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; padding: 10px 0;">
            <div style="font-size: 10px; color: #64748b;">
                Powered by QuantumTrade Engine<br>
                {datetime.now().strftime('%H:%M:%S')} UTC+2
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Metrics row
    render_metrics(engine)
    st.markdown('<div class="pro-separator"></div>', unsafe_allow_html=True)
    
    # Auto-scan on first load
    if not st.session_state.market_data:
        with st.spinner("Loading all market data..."):
            signals, market_data = engine.get_signals()
            st.session_state.signals = signals
            st.session_state.market_data = market_data
    
    # Auto-refresh timer (reloads all data periodically)
    if auto_refresh:
        import time as _time
        _refresh_placeholder = st.empty()
        _time.sleep(refresh_sec)
        # Reload all data + rescan signals
        active_syms = st.session_state.get('selected_symbols', TradingConfig.INSTRUMENTS)
        for sym in active_syms:
            try:
                df = engine.get_market_data(sym)
                if not df.empty:
                    st.session_state.market_data[sym] = df
            except Exception:
                pass
        # Rescan signals on auto-refresh
        try:
            signals, market_data = engine.get_signals()
            st.session_state.signals = signals
            st.session_state.market_data.update(market_data)
        except Exception:
            pass
        st.rerun()
    
    # ==================== SIGNAL ALERT SYSTEM ====================
    if alerts_enabled and st.session_state.signals:
        new_alerts = []
        for sig_data in st.session_state.signals:
            sig = sig_data['signal']
            confidence = sig.confidence * 100
            sig_id = f"{sig.symbol}_{sig.signal_type.value}_{sig.entry_price:.4f}"
            
            if confidence >= alert_threshold and sig_id not in st.session_state.alerted_signals:
                # New high-confidence signal!
                st.session_state.alerted_signals.add(sig_id)
                
                action = "BUY" if sig.signal_type == SignalType.BUY else "SELL"
                price_str = f"{sig.entry_price:.2f}" if sig.entry_price > 10 else f"{sig.entry_price:.5f}"
                sym_name = TradingConfig.SYMBOL_UNIVERSE.get(sig.symbol, sig.symbol)
                
                alert_info = {
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'symbol': sig.symbol,
                    'name': sym_name,
                    'action': action,
                    'confidence': confidence,
                    'price': price_str,
                    'tp': sig.take_profit,
                    'sl': sig.stop_loss,
                    'strategy': sig.strategy,
                    'rr_ratio': sig_data.get('rr_ratio', 0),
                }
                new_alerts.append(alert_info)
                st.session_state.alert_history.insert(0, alert_info)
                # Save alert to DB
                db.save_alert(user['user_id'], alert_info)
        
        # Show alert banners for new signals
        if new_alerts:
            for alert in new_alerts:
                a_color = '#10b981' if alert['action'] == 'BUY' else '#ef4444'
                a_icon = '🟢' if alert['action'] == 'BUY' else '🔴'
                rr = alert.get('rr_ratio', 0)
                tp_str = f"{alert['tp']:.2f}" if alert['tp'] and alert['tp'] > 10 else f"{alert['tp']:.5f}" if alert['tp'] else "N/A"
                sl_str = f"{alert['sl']:.2f}" if alert['sl'] and alert['sl'] > 10 else f"{alert['sl']:.5f}" if alert['sl'] else "N/A"
                
                st.markdown(f"""
                <div style="background: {a_color}15; border: 2px solid {a_color}; border-radius: 12px; 
                            padding: 16px 24px; margin-bottom: 12px; animation: pulse 2s infinite;">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="font-size: 22px; font-weight: 900; color: {a_color};">
                                {a_icon} ALERT: {alert['action']} {alert['symbol']}
                            </div>
                            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">
                                {alert['name']} — {alert['strategy']} — {alert['time']}
                            </div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 11px; color: var(--text-muted);">CONFIDENCE</div>
                            <div style="font-size: 24px; font-weight: 900; color: {a_color};">{alert['confidence']:.0f}%</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 11px; color: var(--text-muted);">PRICE</div>
                            <div style="font-size: 18px; font-weight: 700; font-family: 'JetBrains Mono'; color: var(--text-primary);">{alert['price']}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 11px; color: var(--text-muted);">TP / SL</div>
                            <div style="font-size: 13px; font-family: 'JetBrains Mono';">
                                <span style="color: #10b981;">{tp_str}</span> / <span style="color: #ef4444;">{sl_str}</span>
                            </div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 11px; color: var(--text-muted);">R:R</div>
                            <div style="font-size: 16px; font-weight: 700; color: #8b5cf6;">{rr:.1f}x</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Browser sound alert using JavaScript
            if alert_sound:
                st.markdown("""
                <script>
                    // Play alert sound
                    (function() {
                        try {
                            var ctx = new (window.AudioContext || window.webkitAudioContext)();
                            // Alert beep sequence
                            function beep(freq, start, duration) {
                                var osc = ctx.createOscillator();
                                var gain = ctx.createGain();
                                osc.connect(gain);
                                gain.connect(ctx.destination);
                                osc.frequency.value = freq;
                                osc.type = 'sine';
                                gain.gain.value = 0.3;
                                osc.start(ctx.currentTime + start);
                                osc.stop(ctx.currentTime + start + duration);
                            }
                            beep(880, 0, 0.15);
                            beep(1100, 0.2, 0.15);
                            beep(880, 0.4, 0.15);
                            beep(1320, 0.6, 0.3);
                        } catch(e) {}
                    })();
                </script>
                """, unsafe_allow_html=True)
            
            # Also show toast notification
            for alert in new_alerts:
                st.toast(f"🔔 {alert['action']} {alert['symbol']} @ {alert['price']} — Confidence: {alert['confidence']:.0f}%", icon="🚨")
    
    # Show recent alert history (collapsed)
    if st.session_state.alert_history:
        with st.expander(f"📬 Alert History ({len(st.session_state.alert_history)} alerts)", expanded=False):
            for i, alert in enumerate(st.session_state.alert_history[:20]):
                a_color = '#10b981' if alert['action'] == 'BUY' else '#ef4444'
                st.markdown(f"""
                <div style="border-left: 3px solid {a_color}; padding: 4px 12px; margin-bottom: 6px;">
                    <span style="font-size: 12px; font-weight: 700; color: {a_color};">{alert['action']} {alert['symbol']}</span>
                    <span style="font-size: 11px; color: var(--text-secondary);"> @ {alert['price']} — {alert['confidence']:.0f}% — {alert['time']}</span>
                    <span style="font-size: 10px; color: var(--text-muted);"> ({alert['strategy']})</span>
                </div>
                """, unsafe_allow_html=True)
    
    # Main tabs — admin gets extra tab
    if user.get('role') == 'admin':
        tab_overview, tab_chart, tab_signals, tab_positions, tab_analysis, tab_quantum, tab_performance, tab_social, tab_admin = st.tabs([
            "MARKET OVERVIEW", "CHART", "SIGNALS & TRADE", "POSITIONS", "ANALYSIS", "QUANTUM AI", "PERFORMANCE", "GLOBAL SOCIAL SIGNALS", "ADMIN"
        ])
    else:
        tab_overview, tab_chart, tab_signals, tab_positions, tab_analysis, tab_quantum, tab_performance, tab_social = st.tabs([
            "MARKET OVERVIEW", "CHART", "SIGNALS & TRADE", "POSITIONS", "ANALYSIS", "QUANTUM AI", "PERFORMANCE", "GLOBAL SOCIAL SIGNALS"
        ])
        tab_admin = None
    
    # ==================== TAB: MARKET OVERVIEW ====================
    with tab_overview:
        # Symbol selector with search
        st.markdown("""
        <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; 
                    letter-spacing: 2px; margin-bottom: 8px; font-weight: 600;">
            Market Scanner - Select Instruments
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize selected symbols in session state
        if 'selected_symbols' not in st.session_state:
            st.session_state.selected_symbols = TradingConfig.INSTRUMENTS.copy()
        
        # Symbol selector UI
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Get all available symbols
            all_symbols = list(TradingConfig.SYMBOL_UNIVERSE.keys())
            
            # Multi-select with search
            selected = st.multiselect(
                "Select up to 10 instruments to monitor:",
                options=all_symbols,
                default=st.session_state.selected_symbols[:10],
                format_func=lambda x: f"{x} - {TradingConfig.SYMBOL_UNIVERSE.get(x, x)}",
                max_selections=10,
                key="symbol_selector"
            )
            
            if selected:
                st.session_state.selected_symbols = selected
        
        with col2:
            # Quick presets
            preset = st.selectbox(
                "Quick Preset:",
                ["Custom", "Forex Majors", "Tech Stocks", "Crypto", "Indices", "Commodities"],
                key="preset_selector"
            )
            
            if preset != "Custom":
                if preset == "Forex Majors":
                    st.session_state.selected_symbols = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF', 'NZD/USD', 'USD/CAD']
                elif preset == "Tech Stocks":
                    st.session_state.selected_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD']
                elif preset == "Crypto":
                    st.session_state.selected_symbols = ['BTC/USD', 'ETH/USD', 'BNB/USD', 'XRP/USD', 'ADA/USD', 'SOL/USD']
                elif preset == "Indices":
                    st.session_state.selected_symbols = ['SPX500', 'US30', 'NAS100', 'UK100', 'GER40', 'JPN225']
                elif preset == "Commodities":
                    st.session_state.selected_symbols = ['XAU/USD', 'XAG/USD', 'OIL/USD', 'BRENT/USD', 'GAS/USD']
                st.rerun()
        
        with col3:
            if st.button("🔄 Refresh All"):
                # Clear cached data for selected symbols and reload
                for sym in st.session_state.selected_symbols:
                    if sym in st.session_state.market_data:
                        del st.session_state.market_data[sym]
                st.rerun()
        
        st.markdown("---")
        
        # Auto-load data for any selected symbols that don't have data yet
        missing_symbols = [sym for sym in st.session_state.selected_symbols 
                          if sym not in st.session_state.market_data]
        
        if missing_symbols:
            with st.spinner(f"Loading data for {', '.join(missing_symbols)}..."):
                for sym in missing_symbols:
                    try:
                        df = engine.get_market_data(sym)
                        if not df.empty:
                            st.session_state.market_data[sym] = df
                    except Exception as e:
                        st.warning(f"Could not load {sym}: {e}")
            if any(sym in st.session_state.market_data for sym in missing_symbols):
                st.rerun()
        
        # Display selected instruments
        for sym in st.session_state.selected_symbols:
            if sym in st.session_state.market_data:
                sym_df = st.session_state.market_data[sym]
                sym_analysis = engine.get_full_analysis(sym_df, sym)
                
                if sym_analysis:
                    ov = sym_analysis['overall']
                    ov_color = '#10b981' if 'BUY' in ov else '#ef4444' if 'SELL' in ov else '#f59e0b'
                    t_score = sym_analysis.get('total_score', 0)
                    price = sym_analysis['price']
                    price_str = f"{price:.2f}" if price > 10 else f"{price:.5f}"
                    rsi_val = sym_analysis['rsi']
                    rsi_col = '#10b981' if rsi_val < 30 else '#ef4444' if rsi_val > 70 else '#f59e0b'
                    trend = sym_analysis['trend']
                    trend_col = '#10b981' if trend == 'BULLISH' else '#ef4444'
                    adx_val = sym_analysis.get('adx', 0)
                    mom_val = sym_analysis.get('momentum', 0)
                    mom_col = '#10b981' if mom_val > 0 else '#ef4444'
                    
                    # Quantum fields
                    q_prob = sym_analysis.get('quantum_prob', 0.5)
                    q_pct = int(q_prob * 100)
                    q_col = '#10b981' if q_prob > 0.6 else '#f59e0b' if q_prob > 0.45 else '#ef4444'
                    regime = sym_analysis.get('regime', 'normal')
                    s_trend = sym_analysis.get('struct_trend', 'N/A')
                    s_trend_col = '#10b981' if s_trend == 'bullish' else '#ef4444' if s_trend == 'bearish' else '#f59e0b'
                    s_break = sym_analysis.get('struct_break', False)
                    s_break_type = sym_analysis.get('struct_break_type', '')
                    s_break_dir = sym_analysis.get('struct_break_dir', '')
                    
                    # Check if there's an active signal for this symbol
                    sym_sigs = [s for s in st.session_state.signals if s['signal'].symbol == sym]
                    sig_badge = ""
                    if sym_sigs:
                        best = sym_sigs[0]['signal']
                        sig_action = "BUY" if best.signal_type == SignalType.BUY else "SELL"
                        sig_col = '#10b981' if sig_action == 'BUY' else '#ef4444'
                        sig_conf = best.confidence * 100
                        sig_badge = f'<span style="background: {sig_col}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-left: 8px;">{sig_action} {sig_conf:.0f}%</span>'
                    
                    # Structure break badge
                    break_badge = ""
                    if s_break:
                        b_col = '#10b981' if s_break_dir == 'bullish' else '#ef4444'
                        break_badge = f'<span style="background: {b_col}30; color: {b_col}; padding: 1px 6px; border-radius: 3px; font-size: 9px; font-weight: 700; margin-left: 6px;">{s_break_type}</span>'
                    
                    # Symbol name for display
                    sym_name = TradingConfig.SYMBOL_UNIVERSE.get(sym, sym)
                    
                    # Expandable row: click to see chart + TA
                    with st.expander(f"**{sym}** — {sym_name}  |  {price_str}  |  {ov} (Score {t_score:+d})  |  RSI {rsi_val:.1f}  |  Quantum {q_pct}%", expanded=False):
                        
                        # ---- Summary bar ----
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; justify-content: space-around; flex-wrap: wrap; gap: 8px;
                                    background: rgba(15,23,42,0.6); border: 1px solid rgba(59,130,246,0.15); border-radius: 8px;
                                    padding: 10px 14px; margin-bottom: 12px;">
                            <div style="text-align:center;">
                                <div style="font-size:10px; color:var(--text-muted);">PRICE</div>
                                <div style="font-size:18px; font-weight:800; color:var(--text-primary); font-family:'JetBrains Mono';">{price_str}</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-size:10px; color:var(--text-muted);">SIGNAL</div>
                                <div style="font-size:15px; font-weight:800; color:{ov_color};">{ov} {sig_badge}</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-size:10px; color:var(--text-muted);">QUANTUM</div>
                                <div style="font-size:15px; font-weight:800; color:{q_col};">{q_pct}% {break_badge}</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-size:10px; color:var(--text-muted);">STRUCTURE</div>
                                <div style="font-size:13px; font-weight:700; color:{s_trend_col};">{s_trend.upper()} | ADX:{adx_val:.0f}</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-size:10px; color:var(--text-muted);">RSI</div>
                                <div style="font-size:13px; font-weight:700; color:{rsi_col};">{rsi_val:.1f}</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-size:10px; color:var(--text-muted);">MOMENTUM</div>
                                <div style="font-size:13px; font-weight:700; color:{mom_col};">{'+'if mom_val>=0 else ''}{mom_val:.2f}%</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # ---- Live Chart ----
                        chart_col, ta_col = st.columns([3, 2])
                        
                        with chart_col:
                            fig = go.Figure()
                            fig.add_trace(go.Candlestick(
                                x=sym_df.index,
                                open=sym_df['open'],
                                high=sym_df['high'],
                                low=sym_df['low'],
                                close=sym_df['close'],
                                name='Price',
                                increasing_line_color='#10b981',
                                decreasing_line_color='#ef4444'
                            ))
                            # Add EMAs
                            if 'ema_20' in sym_df.columns:
                                fig.add_trace(go.Scatter(
                                    x=sym_df.index, y=sym_df['ema_20'],
                                    name='EMA 20', line=dict(color='#3b82f6', width=1)
                                ))
                            if 'ema_50' in sym_df.columns:
                                fig.add_trace(go.Scatter(
                                    x=sym_df.index, y=sym_df['ema_50'],
                                    name='EMA 50', line=dict(color='#f59e0b', width=1)
                                ))
                            # Add Bollinger Bands
                            if 'bb_upper' in sym_df.columns:
                                fig.add_trace(go.Scatter(
                                    x=sym_df.index, y=sym_df['bb_upper'],
                                    name='BB Upper', line=dict(color='#6366f1', width=0.5, dash='dot'),
                                    opacity=0.4
                                ))
                                fig.add_trace(go.Scatter(
                                    x=sym_df.index, y=sym_df['bb_lower'],
                                    name='BB Lower', line=dict(color='#6366f1', width=0.5, dash='dot'),
                                    fill='tonexty', fillcolor='rgba(99,102,241,0.05)',
                                    opacity=0.4
                                ))
                            fig.update_layout(
                                template='plotly_dark',
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(10,14,23,0.8)',
                                height=350,
                                margin=dict(l=0, r=0, t=30, b=0),
                                title=dict(text=f"{sym} — {sym_name}", font=dict(size=13)),
                                xaxis_rangeslider_visible=False,
                                showlegend=False,
                                yaxis=dict(gridcolor='rgba(42,48,66,0.4)'),
                                xaxis=dict(gridcolor='rgba(42,48,66,0.4)')
                            )
                            st.plotly_chart(fig, key=f"chart_{sym}")
                        
                        # ---- Technical Analysis Suggestions ----
                        with ta_col:
                            st.markdown("##### Technical Analysis")
                            
                            # Build TA suggestions
                            suggestions = []
                            
                            # RSI
                            if rsi_val < 30:
                                suggestions.append(("OVERSOLD", f"RSI at {rsi_val:.1f} — strong buy zone. Price may bounce up.", "#10b981"))
                            elif rsi_val < 40:
                                suggestions.append(("RSI LOW", f"RSI at {rsi_val:.1f} — approaching oversold. Watch for reversal.", "#f59e0b"))
                            elif rsi_val > 70:
                                suggestions.append(("OVERBOUGHT", f"RSI at {rsi_val:.1f} — strong sell zone. Price may pull back.", "#ef4444"))
                            elif rsi_val > 60:
                                suggestions.append(("RSI HIGH", f"RSI at {rsi_val:.1f} — approaching overbought. Be cautious.", "#f59e0b"))
                            else:
                                suggestions.append(("RSI NEUTRAL", f"RSI at {rsi_val:.1f} — no extreme. Wait for direction.", "#94a3b8"))
                            
                            # Trend
                            ema20 = sym_df['ema_20'].iloc[-1] if 'ema_20' in sym_df.columns else 0
                            ema50 = sym_df['ema_50'].iloc[-1] if 'ema_50' in sym_df.columns else 0
                            if ema20 > ema50:
                                suggestions.append(("UPTREND", f"EMA 20 ({ema20:.2f}) above EMA 50 ({ema50:.2f}). Bullish momentum.", "#10b981"))
                            elif ema20 < ema50:
                                suggestions.append(("DOWNTREND", f"EMA 20 ({ema20:.2f}) below EMA 50 ({ema50:.2f}). Bearish pressure.", "#ef4444"))
                            else:
                                suggestions.append(("FLAT", "EMAs converging. Breakout may be coming.", "#f59e0b"))
                            
                            # MACD
                            macd_val = sym_df['macd'].iloc[-1] if 'macd' in sym_df.columns else 0
                            macd_sig = sym_df['macd_signal'].iloc[-1] if 'macd_signal' in sym_df.columns else 0
                            macd_hist = sym_df['macd_hist'].iloc[-1] if 'macd_hist' in sym_df.columns else 0
                            if macd_val > macd_sig and macd_hist > 0:
                                suggestions.append(("MACD BULLISH", f"MACD above signal. Histogram positive ({macd_hist:.4f}). Buy pressure.", "#10b981"))
                            elif macd_val < macd_sig and macd_hist < 0:
                                suggestions.append(("MACD BEARISH", f"MACD below signal. Histogram negative ({macd_hist:.4f}). Sell pressure.", "#ef4444"))
                            else:
                                suggestions.append(("MACD CROSSING", "MACD near signal line. Potential crossover.", "#f59e0b"))
                            
                            # ADX trend strength
                            if adx_val > 40:
                                suggestions.append(("STRONG TREND", f"ADX at {adx_val:.0f} — very strong trend. Follow it.", "#8b5cf6"))
                            elif adx_val > 25:
                                suggestions.append(("TRENDING", f"ADX at {adx_val:.0f} — moderate trend developing.", "#3b82f6"))
                            else:
                                suggestions.append(("RANGING", f"ADX at {adx_val:.0f} — no clear trend. Range trading.", "#94a3b8"))
                            
                            # Bollinger Band position
                            if 'bb_upper' in sym_df.columns:
                                bb_upper = sym_df['bb_upper'].iloc[-1]
                                bb_lower = sym_df['bb_lower'].iloc[-1]
                                bb_mid = sym_df['bb_middle'].iloc[-1]
                                if price > bb_upper:
                                    suggestions.append(("ABOVE BB", f"Price above upper Bollinger Band. Overbought / breakout.", "#ef4444"))
                                elif price < bb_lower:
                                    suggestions.append(("BELOW BB", f"Price below lower Bollinger Band. Oversold / breakdown.", "#10b981"))
                                elif price > bb_mid:
                                    suggestions.append(("UPPER BB", f"Price in upper half of Bollinger Bands. Bullish bias.", "#3b82f6"))
                                else:
                                    suggestions.append(("LOWER BB", f"Price in lower half of Bollinger Bands. Bearish bias.", "#f59e0b"))
                            
                            # Overall recommendation
                            buy_signals = sum(1 for s in suggestions if s[2] == '#10b981')
                            sell_signals = sum(1 for s in suggestions if s[2] == '#ef4444')
                            
                            if buy_signals >= 3:
                                rec = ("BUY", "#10b981", "Multiple bullish indicators align. Consider long position.")
                            elif sell_signals >= 3:
                                rec = ("SELL", "#ef4444", "Multiple bearish indicators align. Consider short position.")
                            elif buy_signals > sell_signals:
                                rec = ("LEAN BUY", "#10b981", "Slight bullish bias. Wait for confirmation.")
                            elif sell_signals > buy_signals:
                                rec = ("LEAN SELL", "#ef4444", "Slight bearish bias. Wait for confirmation.")
                            else:
                                rec = ("HOLD", "#f59e0b", "Mixed signals. Stay flat or wait for clearer setup.")
                            
                            # Render overall recommendation
                            st.markdown(f"""
                            <div style="background: {rec[1]}20; border: 1px solid {rec[1]}40; border-radius: 8px; 
                                        padding: 10px; margin-bottom: 10px; text-align: center;">
                                <div style="font-size: 18px; font-weight: 800; color: {rec[1]};">{rec[0]}</div>
                                <div style="font-size: 11px; color: var(--text-secondary);">{rec[2]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Render individual suggestions
                            for label, desc, color in suggestions:
                                st.markdown(f"""
                                <div style="border-left: 3px solid {color}; padding: 4px 10px; margin-bottom: 6px;">
                                    <div style="font-size: 11px; font-weight: 700; color: {color};">{label}</div>
                                    <div style="font-size: 10px; color: var(--text-secondary);">{desc}</div>
                                </div>
                                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: rgba(15,23,42,0.4); border: 1px solid rgba(100,116,139,0.2); border-radius: 10px; 
                            padding: 16px 20px; margin-bottom: 10px;">
                    <div style="font-size: 16px; font-weight: 700; color: var(--text-muted);">{sym} - {TradingConfig.SYMBOL_UNIVERSE.get(sym, sym)}</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Loading data...</div>
                </div>
                """, unsafe_allow_html=True)
    
    # ==================== TAB: CHART ====================
    with tab_chart:
        chart_mode = st.radio("View", ["ALL INSTRUMENTS", "SINGLE DETAILED"], horizontal=True, label_visibility="collapsed")
        
        if chart_mode == "ALL INSTRUMENTS":
            # Load all instruments
            for sym in TradingConfig.INSTRUMENTS:
                if sym not in st.session_state.market_data:
                    with st.spinner(f"Loading {sym}..."):
                        df_tmp = engine.get_market_data(sym)
                        if not df_tmp.empty:
                            st.session_state.market_data[sym] = df_tmp
            
            # Dynamic grid: 2 columns, as many rows as needed
            instruments = TradingConfig.INSTRUMENTS
            for row_start in range(0, len(instruments), 2):
                row_syms = instruments[row_start:row_start + 2]
                cols = st.columns(2)
                
                for col_idx, sym in enumerate(row_syms):
                    with cols[col_idx]:
                        if sym in st.session_state.market_data:
                            sym_df = st.session_state.market_data[sym]
                            sym_signals = [s for s in st.session_state.signals if s['signal'].symbol == sym]
                            sym_positions = [p for p in engine.risk_manager.open_positions.values() if p.symbol == sym]
                            
                            fig = ProChartBuilder.create_main_chart(
                                sym_df, sym,
                                signals=sym_signals,
                                positions=sym_positions,
                                show_bb=show_bb,
                                show_ema=show_ema,
                                show_volume=False,
                                show_rsi=False,
                                show_macd=False
                            )
                            fig.update_layout(height=320)
                            
                            st.plotly_chart(fig, width='stretch', config={
                                'displayModeBar': False,
                                'scrollZoom': True
                            })
                            
                            # Mini analysis bar
                            a = engine.get_full_analysis(sym_df, sym)
                            if a:
                                ov = a['overall']
                                ov_c = '#10b981' if 'BUY' in ov else '#ef4444' if 'SELL' in ov else '#f59e0b'
                                ts = a.get('total_score', 0)
                                price_str = f"{a['price']:.2f}" if a['price'] > 10 else f"{a['price']:.5f}"
                                st.markdown(f"""
                                <div style="background: rgba(15,23,42,0.5); border: 1px solid rgba(59,130,246,0.1); border-radius: 6px; padding: 8px 12px; margin-top: -10px; margin-bottom: 12px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span style="font-weight: 800; color: {ov_c};">{ov} ({ts:+d})</span>
                                        <span style="font-size: 12px; font-family: 'JetBrains Mono'; color: var(--text-primary);">{price_str}</span>
                                        <span style="font-size: 11px; color: var(--text-muted);">RSI:{a['rsi']:.0f} ADX:{a.get('adx',0):.0f}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info(f"No data for {sym}")
        
        else:
            # Single detailed chart
            symbol = st.session_state.selected_symbol
            
            if symbol not in st.session_state.market_data:
                with st.spinner(f"Loading {symbol} data..."):
                    df = engine.get_market_data(symbol)
                    if not df.empty:
                        st.session_state.market_data[symbol] = df
            
            if symbol in st.session_state.market_data:
                df = st.session_state.market_data[symbol]
                symbol_signals = [s for s in st.session_state.signals if s['signal'].symbol == symbol]
                positions = list(engine.risk_manager.open_positions.values())
                
                fig = ProChartBuilder.create_main_chart(
                    df, symbol,
                    signals=symbol_signals,
                    positions=positions,
                    show_bb=show_bb,
                    show_ema=show_ema,
                    show_volume=show_volume,
                    show_rsi=show_rsi,
                    show_macd=show_macd
                )
                
                st.plotly_chart(fig, width='stretch', config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
                    'scrollZoom': True
                })
                
                # Quick analysis below chart
                analysis = engine.get_full_analysis(df, symbol)
                if analysis:
                    overall = analysis['overall']
                    overall_color = '#10b981' if 'BUY' in overall else '#ef4444' if 'SELL' in overall else '#f59e0b'
                    t_score = analysis.get('total_score', 0)
                    gauge_pct = max(0, min(100, (t_score + 10) * 5))
                    adx_v = analysis.get('adx', 0)
                    mom_v = analysis.get('momentum', 0)
                    mom_c = '#10b981' if mom_v > 0 else '#ef4444'
                    
                    st.markdown(f"""
                    <div style="background: rgba(15,23,42,0.5); border: 1px solid rgba(59,130,246,0.12); border-radius: 8px; 
                                padding: 12px 16px; margin-top: 8px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
                            <div>
                                <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Signal</span><br>
                                <span style="font-size: 18px; font-weight: 800; color: {overall_color};">{overall}</span>
                                <span style="font-size: 12px; color: var(--text-muted); margin-left: 6px;">({t_score:+d})</span>
                            </div>
                            <div>
                                <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Price</span><br>
                                <span style="font-size: 16px; font-weight: 700; font-family: 'JetBrains Mono'; color: var(--text-primary);">{analysis['price']:.5f}</span>
                            </div>
                            <div>
                                <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Trend</span><br>
                                <span style="color: {('#10b981' if analysis['trend']=='BULLISH' else '#ef4444')}; font-weight: 700;">{analysis['trend']}</span>
                                <span style="font-size: 11px; color: var(--text-muted);"> ADX:{adx_v:.0f}</span>
                            </div>
                            <div>
                                <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">RSI</span><br>
                                <span style="font-weight: 700; color: {'#10b981' if analysis['rsi']<30 else '#ef4444' if analysis['rsi']>70 else '#f59e0b'};">{analysis['rsi']:.1f}</span>
                            </div>
                            <div>
                                <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Momentum</span><br>
                                <span style="color: {mom_c}; font-weight: 700;">{'+'if mom_v>=0 else ''}{mom_v:.2f}%</span>
                            </div>
                            <div style="min-width: 120px;">
                                <div style="height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {gauge_pct}%; height: 100%; background: linear-gradient(90deg, #ef4444, #f59e0b 40%, #10b981 70%); border-radius: 3px;"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Click **SCAN MARKETS** in the sidebar to load market data.")
    
    # ==================== TAB: SIGNALS & TRADE ====================
    with tab_signals:
        st.markdown("""
        <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; 
                    letter-spacing: 2px; margin-bottom: 16px; font-weight: 600;">
            Active Trading Signals
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("REFRESH SIGNALS", type="primary", width='stretch'):
            with st.spinner("Scanning markets..."):
                signals, market_data = engine.get_signals()
                st.session_state.signals = signals
                st.session_state.market_data = market_data
                st.rerun()
        
        if st.session_state.signals:
            for idx, sig_data in enumerate(st.session_state.signals):
                sig = sig_data['signal']
                val = sig_data['validation']
                is_val = sig_data.get('is_validated', True)
                
                action = "BUY" if sig.signal_type == SignalType.BUY else "SELL"
                card_class = "buy" if sig.signal_type == SignalType.BUY else "sell"
                badge_class = "buy" if sig.signal_type == SignalType.BUY else "sell"
                
                quality = "high" if sig.confidence >= 0.4 else "medium" if sig.confidence >= 0.25 else "low"
                quality_text = "HIGH QUALITY" if quality == "high" else "MEDIUM" if quality == "medium" else "LOW"
                
                st.markdown(f'<div class="signal-card-pro {card_class}">', unsafe_allow_html=True)
                
                col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1.5, 1])
                
                with col1:
                    st.markdown(f"""
                    <span class="signal-badge {badge_class}">{action}</span>
                    <span class="signal-badge {quality}">{quality_text}</span>
                    <div style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin-top: 8px;
                                font-family: 'JetBrains Mono';">{sig.symbol}</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
                        {sig.strategy.replace('_', ' ').title()} | {sig.confidence*100:.1f}% confidence
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">Entry Price</div>
                    <div style="font-size: 18px; font-weight: 700; color: var(--text-primary);
                                font-family: 'JetBrains Mono';">{sig.entry_price:.5f}</div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    tp_pct = ((sig.take_profit / sig.entry_price - 1) * 100)
                    st.markdown(f"""
                    <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">Take Profit</div>
                    <div style="font-size: 18px; font-weight: 700; color: #10b981;
                                font-family: 'JetBrains Mono';">{sig.take_profit:.5f}</div>
                    <div style="font-size: 11px; color: #10b981;">+{abs(tp_pct):.2f}%</div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    sl_pct = ((sig.stop_loss / sig.entry_price - 1) * 100)
                    st.markdown(f"""
                    <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">Stop Loss</div>
                    <div style="font-size: 18px; font-weight: 700; color: #ef4444;
                                font-family: 'JetBrains Mono';">{sig.stop_loss:.5f}</div>
                    <div style="font-size: 11px; color: #ef4444;">{sl_pct:.2f}%</div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    btn_disabled = sig.confidence < 0.10
                    if sig.signal_type == SignalType.BUY:
                        if st.button(f"BUY", key=f"exec_buy_{idx}", type="primary", 
                                    width='stretch', disabled=btn_disabled):
                            success, result = engine.execute_trade(sig_data)
                            if success:
                                trade_entry = {
                                    'time': datetime.now().strftime('%H:%M:%S'),
                                    'action': 'BUY',
                                    'symbol': sig.symbol,
                                    'price': sig.entry_price,
                                    'order_id': result
                                }
                                st.session_state.trade_log.append(trade_entry)
                                # Save to DB
                                db.save_position(user['user_id'], {
                                    'order_id': result, 'symbol': sig.symbol, 'side': 'buy',
                                    'entry_price': sig.entry_price, 'quantity': sig_data.get('quantity', 0),
                                    'stop_loss': sig.stop_loss, 'take_profit': sig.take_profit,
                                    'strategy': sig.strategy, 'confidence': sig.confidence
                                })
                                db.save_trade(user['user_id'], {
                                    'symbol': sig.symbol, 'action': 'BUY',
                                    'price': sig.entry_price, 'strategy': sig.strategy,
                                    'confidence': sig.confidence
                                })
                                db.log_event('TRADE_EXECUTED', user_id=user['user_id'],
                                    username=user['username'], success=True,
                                    details={'action': 'BUY', 'symbol': sig.symbol,
                                             'price': sig.entry_price, 'strategy': sig.strategy,
                                             'confidence': round(sig.confidence, 2)})
                                st.success(f"BUY executed: {sig.symbol}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Failed: {result}")
                    else:
                        if st.button(f"SELL", key=f"exec_sell_{idx}", type="primary",
                                    width='stretch', disabled=btn_disabled):
                            success, result = engine.execute_trade(sig_data)
                            if success:
                                trade_entry = {
                                    'time': datetime.now().strftime('%H:%M:%S'),
                                    'action': 'SELL',
                                    'symbol': sig.symbol,
                                    'price': sig.entry_price,
                                    'order_id': result
                                }
                                st.session_state.trade_log.append(trade_entry)
                                # Save to DB
                                db.save_position(user['user_id'], {
                                    'order_id': result, 'symbol': sig.symbol, 'side': 'sell',
                                    'entry_price': sig.entry_price, 'quantity': sig_data.get('quantity', 0),
                                    'stop_loss': sig.stop_loss, 'take_profit': sig.take_profit,
                                    'strategy': sig.strategy, 'confidence': sig.confidence
                                })
                                db.save_trade(user['user_id'], {
                                    'symbol': sig.symbol, 'action': 'SELL',
                                    'price': sig.entry_price, 'strategy': sig.strategy,
                                    'confidence': sig.confidence
                                })
                                db.log_event('TRADE_EXECUTED', user_id=user['user_id'],
                                    username=user['username'], success=True,
                                    details={'action': 'SELL', 'symbol': sig.symbol,
                                             'price': sig.entry_price, 'strategy': sig.strategy,
                                             'confidence': round(sig.confidence, 2)})
                                st.success(f"SELL executed: {sig.symbol}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Failed: {result}")
                
                with st.expander("Signal Details & Analysis"):
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        st.markdown(f"**Reason:** {sig.reason}")
                        if val.reasons:
                            st.markdown(f"**Strengths:** {', '.join(val.reasons)}")
                    with dc2:
                        if val.warnings:
                            st.warning(f"**Warnings:** {', '.join(val.warnings)}")
                        if not is_val:
                            st.error("Did not pass full validation - higher risk trade")
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 60px; color: var(--text-muted);">
                <div style="font-size: 40px; margin-bottom: 12px;">📡</div>
                <div style="font-size: 16px; font-weight: 600;">No Active Signals</div>
                <div style="font-size: 13px; margin-top: 4px;">Click SCAN MARKETS to analyze all instruments</div>
            </div>
            """, unsafe_allow_html=True)
    
    # ==================== TAB: POSITIONS ====================
    with tab_positions:
        st.markdown("""
        <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; 
                    letter-spacing: 2px; margin-bottom: 16px; font-weight: 600;">
            Active Positions & Trade Log
        </div>
        """, unsafe_allow_html=True)
        
        # Open positions
        positions = engine.risk_manager.open_positions
        
        if positions:
            for order_id, pos in positions.items():
                try:
                    market = engine.api_client.get_market_data(pos.symbol)
                    current_price = market.get('bid', pos.entry_price)
                except:
                    current_price = pos.entry_price
                
                if pos.side == 'buy':
                    pnl = (current_price - pos.entry_price) * pos.quantity
                else:
                    pnl = (pos.entry_price - current_price) * pos.quantity
                
                pnl_pct = (pnl / (pos.entry_price * pos.quantity)) * 100 if pos.entry_price * pos.quantity > 0 else 0
                card_class = "profit" if pnl >= 0 else "loss"
                pnl_color = "#10b981" if pnl >= 0 else "#ef4444"
                side_color = "#10b981" if pos.side == 'buy' else "#ef4444"
                
                st.markdown(f'<div class="position-card {card_class}">', unsafe_allow_html=True)
                
                pc1, pc2, pc3, pc4, pc5 = st.columns([1.5, 1.5, 1.5, 1.5, 1])
                
                with pc1:
                    st.markdown(f"""
                    <div style="font-size: 18px; font-weight: 800; color: var(--text-primary);
                                font-family: 'JetBrains Mono';">{pos.symbol}</div>
                    <div style="font-size: 12px; color: {side_color}; font-weight: 700; text-transform: uppercase;">
                        {pos.side} | {pos.strategy.replace('_',' ').title()}
                    </div>
                    """, unsafe_allow_html=True)
                
                with pc2:
                    st.markdown(f"""
                    <div style="font-size: 11px; color: var(--text-muted);">Entry</div>
                    <div style="font-size: 16px; font-weight: 600; font-family: 'JetBrains Mono'; color: var(--text-primary);">
                        {pos.entry_price:.5f}
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);">Qty: {pos.quantity:.4f}</div>
                    """, unsafe_allow_html=True)
                
                with pc3:
                    # Show trailing stop / break-even status
                    trail_badge = ""
                    if getattr(pos, 'trailing_stop_active', False):
                        trail_badge = '<span style="background: #8b5cf6; color: white; padding: 1px 6px; border-radius: 3px; font-size: 9px; font-weight: 700;">TRAILING</span>'
                    elif getattr(pos, 'break_even_applied', False):
                        trail_badge = '<span style="background: #06b6d4; color: white; padding: 1px 6px; border-radius: 3px; font-size: 9px; font-weight: 700;">BREAK-EVEN</span>'
                    
                    sl_color = '#8b5cf6' if getattr(pos, 'trailing_stop_active', False) else '#ef4444'
                    st.markdown(f"""
                    <div style="font-size: 11px; color: var(--text-muted);">Current Price</div>
                    <div style="font-size: 16px; font-weight: 600; font-family: 'JetBrains Mono'; color: var(--text-primary);">
                        {current_price:.5f}
                    </div>
                    <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
                        SL: <span style="color: {sl_color};">{pos.stop_loss:.5f}</span> {trail_badge}
                    </div>
                    """, unsafe_allow_html=True)
                
                with pc4:
                    st.markdown(f"""
                    <div style="font-size: 11px; color: var(--text-muted);">Unrealized P&L</div>
                    <div style="font-size: 18px; font-weight: 800; font-family: 'JetBrains Mono'; color: {pnl_color};">
                        {'+'if pnl>=0 else ''}EUR {pnl:.2f}
                    </div>
                    <div style="font-size: 12px; color: {pnl_color};">{'+'if pnl_pct>=0 else ''}{pnl_pct:.2f}%</div>
                    """, unsafe_allow_html=True)
                
                with pc5:
                    if st.button("CLOSE", key=f"close_{order_id}", width='stretch'):
                        success = engine.close_position(order_id)
                        if success:
                            st.session_state.trade_log.append({
                                'time': datetime.now().strftime('%H:%M:%S'),
                                'action': 'CLOSE',
                                'symbol': pos.symbol,
                                'price': current_price,
                                'pnl': pnl
                            })
                            st.success(f"Position closed: {pos.symbol}")
                            time.sleep(1)
                            st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                <div style="font-size: 40px; margin-bottom: 12px;">📭</div>
                <div style="font-size: 16px; font-weight: 600;">No Open Positions</div>
                <div style="font-size: 13px; margin-top: 4px;">Execute a trade from the Signals tab</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Trade log
        st.markdown('<div class="pro-separator"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; 
                    letter-spacing: 2px; margin-bottom: 12px; font-weight: 600;">
            Trade Log
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.trade_log:
            for trade in reversed(st.session_state.trade_log[-20:]):
                action_color = "#10b981" if trade['action'] == 'BUY' else "#ef4444" if trade['action'] == 'SELL' else "#f59e0b"
                pnl_text = f" | P&L: EUR {trade.get('pnl', 0):.2f}" if 'pnl' in trade else ""
                st.markdown(f"""
                <div style="padding: 8px 12px; border-left: 3px solid {action_color}; margin: 4px 0;
                            background: rgba(26,31,46,0.5); border-radius: 0 6px 6px 0; font-size: 13px;">
                    <span style="color: var(--text-muted); font-family: 'JetBrains Mono'; font-size: 11px;">{trade['time']}</span>
                    <span style="color: {action_color}; font-weight: 700; margin: 0 8px;">{trade['action']}</span>
                    <span style="color: var(--text-primary); font-weight: 600;">{trade['symbol']}</span>
                    <span style="color: var(--text-secondary); font-family: 'JetBrains Mono';"> @ {trade['price']:.5f}</span>
                    <span style="color: var(--text-muted);">{pnl_text}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No trades executed yet this session")
    
    # ==================== TAB: ANALYSIS ====================
    with tab_analysis:
        # Full universe search — any symbol
        all_symbols = list(TradingConfig.SYMBOL_UNIVERSE.keys())
        
        analysis_symbol = st.selectbox(
            "🔍 Search any instrument for Technical Analysis:",
            all_symbols,
            index=all_symbols.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in all_symbols else 0,
            format_func=lambda x: f"{x} - {TradingConfig.SYMBOL_UNIVERSE.get(x, x)}",
            key="analysis_symbol_selector"
        )
        
        # Auto-load data if not already loaded
        if analysis_symbol not in st.session_state.market_data:
            with st.spinner(f"Loading {analysis_symbol} data..."):
                df = engine.get_market_data(analysis_symbol)
                if not df.empty:
                    st.session_state.market_data[analysis_symbol] = df
        
        if analysis_symbol in st.session_state.market_data:
            df = st.session_state.market_data[analysis_symbol]
            analysis = engine.get_full_analysis(df, analysis_symbol)
            
            if analysis:
                render_analysis_panel(analysis)
            else:
                st.info("Not enough data for analysis.")
        else:
            st.warning(f"Could not load data for {analysis_symbol}. Try another symbol.")
    
    # ==================== TAB: QUANTUM AI ====================
    with tab_quantum:
        st.markdown('<div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:2px;margin-bottom:16px;font-weight:600;">Quantum AI Systems Dashboard</div>', unsafe_allow_html=True)
        
        # System status cards
        q1, q2, q3, q4 = st.columns(4)
        
        learn_status = engine.adaptive_learner.get_learning_status()
        exec_stats = engine.execution_manager.get_execution_stats()
        
        with q1:
            ml_color = '#10b981' if learn_status['ml_active'] else '#f59e0b'
            ml_label = 'ACTIVE' if learn_status['ml_active'] else f"{learn_status['trades_until_ml']} trades to ML"
            st.markdown(f'<div style="background:rgba(15,23,42,0.6);border:1px solid {ml_color}40;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;">AI Learning</div><div style="font-size:20px;font-weight:800;color:{ml_color};">{ml_label}</div><div style="font-size:11px;color:var(--text-muted);">{learn_status["completed_trades"]} trades learned</div></div>', unsafe_allow_html=True)
        
        with q2:
            wr = learn_status['overall_win_rate']
            wr_color = '#10b981' if wr > 0.55 else '#ef4444' if wr < 0.45 else '#f59e0b'
            st.markdown(f'<div style="background:rgba(15,23,42,0.6);border:1px solid {wr_color}40;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;">Win Rate</div><div style="font-size:20px;font-weight:800;color:{wr_color};">{wr*100:.1f}%</div><div style="font-size:11px;color:var(--text-muted);">{learn_status["wins"]}W / {learn_status["losses"]}L</div></div>', unsafe_allow_html=True)
        
        with q3:
            acc = learn_status['ml_accuracy']
            acc_color = '#10b981' if acc > 0.6 else '#f59e0b' if acc > 0 else '#64748b'
            ml_type = 'sklearn' if learn_status['has_sklearn'] else 'simple'
            st.markdown(f'<div style="background:rgba(15,23,42,0.6);border:1px solid {acc_color}40;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;">ML Accuracy</div><div style="font-size:20px;font-weight:800;color:{acc_color};">{acc*100:.1f}%</div><div style="font-size:11px;color:var(--text-muted);">{ml_type} model</div></div>', unsafe_allow_html=True)
        
        with q4:
            ks_color = '#ef4444' if exec_stats['kill_switch_active'] else '#10b981'
            ks_label = 'ACTIVE' if exec_stats['kill_switch_active'] else 'SAFE'
            st.markdown(f'<div style="background:rgba(15,23,42,0.6);border:1px solid {ks_color}40;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;">Kill Switch</div><div style="font-size:20px;font-weight:800;color:{ks_color};">{ks_label}</div><div style="font-size:11px;color:var(--text-muted);">{exec_stats["broker_type"]}</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Signal scoring details for current signals
        st.markdown("### Signal Scoring Breakdown")
        
        if st.session_state.signals:
            for sig_data in st.session_state.signals[:5]:
                sig = sig_data['signal']
                q_score = sig_data.get('quantum_score', 0.5)
                adj_score = sig_data.get('adjusted_score', q_score)
                scoring = sig_data.get('scoring', None)
                structure = sig_data.get('structure', None)
                ai_det = sig_data.get('ai_details', {})
                rec = sig_data.get('recommendation', 'N/A')
                rec_det = sig_data.get('rec_detail', '')
                regime = sig_data.get('regime', 'normal')
                rr = sig_data.get('rr_ratio', 0)
                
                action = "BUY" if sig.signal_type == SignalType.BUY else "SELL"
                act_col = '#10b981' if action == 'BUY' else '#ef4444'
                rec_col = '#10b981' if 'ENTRY' in rec else '#f59e0b' if 'CAUTION' in rec or 'WEAK' in rec else '#ef4444'
                
                # Score gauge
                gauge_pct = int(adj_score * 100)
                
                q_score_col = '#10b981' if q_score > 0.6 else '#f59e0b' if q_score > 0.45 else '#ef4444'
                adj_score_col = '#10b981' if adj_score > 0.6 else '#f59e0b' if adj_score > 0.45 else '#ef4444'
                rr_col = '#10b981' if rr >= 2 else '#f59e0b' if rr >= 1 else '#ef4444'
                blend_mode = ai_det.get('blend_mode', 'N/A').upper()
                
                card_html = f'<div style="background:rgba(15,23,42,0.6);border:1px solid rgba(59,130,246,0.15);border-radius:10px;padding:16px 20px;margin-bottom:12px;">'
                card_html += f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
                card_html += f'<div><span style="font-size:18px;font-weight:800;color:var(--text-primary);font-family:JetBrains Mono,monospace;">{sig.symbol}</span>'
                card_html += f' <span style="background:{act_col};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{action}</span>'
                card_html += f' <span style="font-size:12px;color:var(--text-muted);">{sig.strategy.replace("_"," ").title()}</span></div>'
                card_html += f'<div style="text-align:right;"><div style="font-size:14px;font-weight:800;color:{rec_col};">{rec}</div>'
                card_html += f'<div style="font-size:10px;color:var(--text-muted);">{rec_det}</div></div></div>'
                
                card_html += f'<div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:10px;">'
                card_html += f'<div><span style="font-size:10px;color:var(--text-muted);">QUANTUM SCORE</span><br><span style="font-size:22px;font-weight:800;color:{q_score_col};">{q_score:.1%}</span></div>'
                card_html += f'<div><span style="font-size:10px;color:var(--text-muted);">AI ADJUSTED</span><br><span style="font-size:22px;font-weight:800;color:{adj_score_col};">{adj_score:.1%}</span></div>'
                card_html += f'<div><span style="font-size:10px;color:var(--text-muted);">R:R RATIO</span><br><span style="font-size:22px;font-weight:800;color:{rr_col};">{rr:.1f}:1</span></div>'
                card_html += f'<div><span style="font-size:10px;color:var(--text-muted);">REGIME</span><br><span style="font-size:14px;font-weight:700;color:var(--text-secondary);">{regime.upper()}</span></div>'
                card_html += f'<div><span style="font-size:10px;color:var(--text-muted);">AI MODE</span><br><span style="font-size:14px;font-weight:700;color:var(--text-secondary);">{blend_mode}</span></div>'
                card_html += f'</div>'
                
                card_html += f'<div style="height:8px;background:#1e293b;border-radius:4px;overflow:hidden;margin-bottom:6px;">'
                card_html += f'<div style="width:{gauge_pct}%;height:100%;background:linear-gradient(90deg,#ef4444,#f59e0b 35%,#10b981 65%);border-radius:4px;"></div></div>'
                card_html += f'<div style="display:flex;justify-content:space-between;font-size:9px;color:var(--text-muted);">'
                card_html += f'<span>NO TRADE</span><span>WEAK</span><span>MODERATE</span><span>GOOD</span><span>STRONG</span></div>'
                card_html += f'</div>'
                
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Expandable details
                with st.expander(f"Details: {sig.symbol} {action}"):
                    dc1, dc2 = st.columns(2)
                    
                    with dc1:
                        st.markdown("**Scoring Factors:**")
                        if scoring and scoring.raw_scores:
                            for factor, raw in sorted(scoring.raw_scores.items(), key=lambda x: abs(x[1]), reverse=True):
                                bar_w = int(abs(raw) * 100)
                                bar_col = '#10b981' if raw > 0 else '#ef4444'
                                fname = factor.replace('_',' ').title()
                                bar_html = f'<div style="display:flex;align-items:center;gap:8px;margin:2px 0;"><span style="font-size:11px;width:140px;color:var(--text-muted);">{fname}</span><div style="flex:1;height:4px;background:#1e293b;border-radius:2px;"><div style="width:{bar_w}%;height:100%;background:{bar_col};border-radius:2px;"></div></div><span style="font-size:11px;color:{bar_col};width:40px;text-align:right;">{raw:+.2f}</span></div>'
                                st.markdown(bar_html, unsafe_allow_html=True)
                        
                        if scoring:
                            st.markdown(f"**Edge:** {scoring.edge_description}")
                    
                    with dc2:
                        st.markdown("**Market Structure:**")
                        if structure:
                            s_trend_col = '#10b981' if structure.trend == 'bullish' else '#ef4444' if structure.trend == 'bearish' else '#f59e0b'
                            st.markdown(f"- Structure Trend: <span style='color:{s_trend_col};font-weight:700'>{structure.trend.upper()}</span>", unsafe_allow_html=True)
                            if structure.structure_break:
                                sb_col = '#10b981' if structure.break_direction == 'bullish' else '#ef4444'
                                st.markdown(f"- Break: <span style='color:{sb_col};font-weight:700'>{structure.break_type} {structure.break_direction}</span>", unsafe_allow_html=True)
                            st.markdown(f"- Order Blocks: {len(structure.order_blocks)}")
                            st.markdown(f"- Liquidity Zones: {len(structure.liquidity_zones)}")
                            st.markdown(f"- S/D Zones: {len(structure.supply_demand_zones)}")
                            align_col = '#10b981' if structure.alignment_score > 0.1 else '#ef4444' if structure.alignment_score < -0.1 else '#f59e0b'
                            st.markdown(f"- Alignment: <span style='color:{align_col};font-weight:700'>{structure.alignment_score:+.2f}</span>", unsafe_allow_html=True)
                            st.markdown(f"- {structure.narrative}")
                        
                        st.markdown("**AI Details:**")
                        st.markdown(f"- ML Probability: {ai_det.get('ml_probability', 'N/A')}")
                        st.markdown(f"- Performance Adj: {ai_det.get('performance_adj', 'N/A')}")
                        st.markdown(f"- Blend Mode: {ai_det.get('blend_mode', 'N/A')}")
        else:
            st.info("Click **SCAN MARKETS** to generate signals with quantum scoring.")
        
        st.markdown("---")
        
        # Execution Engine stats
        st.markdown("### Execution Engine")
        e1, e2, e3, e4 = st.columns(4)
        with e1:
            st.metric("Orders Executed", exec_stats['total_orders'])
        with e2:
            st.metric("Success Rate", f"{exec_stats['success_rate']*100:.1f}%")
        with e3:
            st.metric("Avg Slippage", f"{exec_stats['avg_slippage']:.5f}")
        with e4:
            st.metric("Avg Exec Time", f"{exec_stats['avg_exec_time_ms']:.0f}ms")
        
        # Kill switch controls
        st.markdown("---")
        ks1, ks2 = st.columns(2)
        with ks1:
            if st.button("ACTIVATE KILL SWITCH", type="primary"):
                engine.execution_manager.activate_kill_switch("Manual from dashboard")
                st.error("KILL SWITCH ACTIVATED - All trading stopped")
                st.rerun()
        with ks2:
            if st.button("DEACTIVATE KILL SWITCH"):
                engine.execution_manager.deactivate_kill_switch()
                st.success("Kill switch deactivated")
                st.rerun()
    
    # ==================== TAB: PERFORMANCE ====================
    with tab_performance:
        st.markdown("""
        <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; 
                    letter-spacing: 2px; margin-bottom: 16px; font-weight: 600;">
            Performance Analytics
        </div>
        """, unsafe_allow_html=True)
        
        try:
            with open('daily_stats.json', 'r') as f:
                daily_stats = json.load(f)
            
            if daily_stats:
                dates = list(sorted(daily_stats.keys()))
                balances = [daily_stats[d]['ending_balance'] for d in dates]
                pnls = [daily_stats[d]['total_pnl'] for d in dates]
                
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(
                    x=dates, y=balances,
                    mode='lines+markers',
                    fill='tozeroy',
                    line=dict(color='#3b82f6', width=2),
                    fillcolor='rgba(59,130,246,0.1)',
                    marker=dict(size=6),
                    name='Equity'
                ))
                fig_eq.update_layout(
                    title="Equity Curve",
                    height=350,
                    template='plotly_dark',
                    paper_bgcolor='#0a0e17',
                    plot_bgcolor='#0a0e17',
                    font=dict(family='Inter', color='#94a3b8'),
                    margin=dict(l=40, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_eq, width='stretch')
                
                colors = ['#10b981' if p >= 0 else '#ef4444' for p in pnls]
                fig_pnl = go.Figure()
                fig_pnl.add_trace(go.Bar(
                    x=dates, y=pnls,
                    marker_color=colors,
                    name='Daily P&L'
                ))
                fig_pnl.update_layout(
                    title="Daily P&L",
                    height=250,
                    template='plotly_dark',
                    paper_bgcolor='#0a0e17',
                    plot_bgcolor='#0a0e17',
                    font=dict(family='Inter', color='#94a3b8'),
                    margin=dict(l=40, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_pnl, width='stretch')
            else:
                st.info("No performance data yet.")
        except FileNotFoundError:
            st.markdown("""
            <div style="text-align: center; padding: 60px; color: var(--text-muted);">
                <div style="font-size: 40px; margin-bottom: 12px;">📊</div>
                <div style="font-size: 16px; font-weight: 600;">No Performance Data Yet</div>
                <div style="font-size: 13px; margin-top: 4px;">Start trading to see analytics here</div>
            </div>
            """, unsafe_allow_html=True)
    
    # ==================== TAB: GLOBAL SOCIAL SIGNALS ====================
    with tab_social:
        st.markdown("""
        <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; 
                    letter-spacing: 2px; margin-bottom: 8px; font-weight: 600;">
            Global Social & Market Signals
        </div>
        """, unsafe_allow_html=True)
        
        # Try to import and use free social signals
        try:
            from social.free_signals_provider import FreeSocialSignalsProvider
            
            # Initialize free signals provider
            if 'free_signals_provider' not in st.session_state:
                st.session_state.free_signals_provider = FreeSocialSignalsProvider()
            
            # Get signals provider
            signals_provider = st.session_state.free_signals_provider
            
            # Create sub-tabs for social signals
            social_tab1, social_tab2, social_tab3 = st.tabs(["LIVE SIGNALS", "TRENDING TOPICS", "ANALYTICS"])
            
            with social_tab1:
                st.subheader("Live Social Signals")
                st.info("Real-time social media trading signals from Twitter, Reddit, and news sources")
                
                # Get signals from free provider
                try:
                    # Try to get real RSS signals
                    signals = signals_provider.get_free_signals(limit=10)
                    
                    # If no RSS signals available, use mock signals
                    if not signals:
                        signals = signals_provider.get_mock_signals()
                    
                    if signals:
                        for signal in signals:
                            symbol = signal.get('asset', 'UNKNOWN')
                            sentiment = "Bullish" if signal.get('sentiment', 0) > 0 else "Bearish"
                            confidence = signal.get('confidence', 0) * 100
                            source = signal.get('source', 'Unknown')
                            
                            # Format time
                            signal_time = signal.get('timestamp', '')
                            if signal_time:
                                try:
                                    dt = datetime.fromisoformat(signal_time.replace('Z', '+00:00'))
                                    time_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 60
                                    time_str = f"{int(time_ago)} min ago" if time_ago < 60 else f"{int(time_ago/60)}h ago"
                                except:
                                    time_str = "Unknown"
                            else:
                                time_str = "Unknown"
                            
                            color = "#10b981" if sentiment == "Bullish" else "#ef4444"
                            st.markdown(f"""
                            <div style="border-left: 3px solid {color}; padding: 12px; margin-bottom: 8px; background: rgba(255,255,255,0.02);">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <span style="font-size: 14px; font-weight: 700; color: white;">{symbol}</span>
                                        <span style="font-size: 12px; color: {color}; margin-left: 8px;">{sentiment}</span>
                                    </div>
                                    <div style="text-align: right;">
                                        <div style="font-size: 11px; color: #94a3b8;">{source}</div>
                                        <div style="font-size: 10px; color: #64748b;">{time_str}</div>
                                    </div>
                                </div>
                                <div style="margin-top: 4px;">
                                    <span style="font-size: 12px; color: #94a3b8;">Confidence: {confidence:.0f}%</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No social signals available. This is normal when first starting - signals will appear as social media data is collected.")
                        
                except Exception as e:
                    st.error(f"Error loading social signals: {e}")
                    st.info("Social signals temporarily unavailable. Using fallback display.")
                    
                    # Fallback mock data
                    mock_signals = [
                        {"symbol": "AAPL", "sentiment": "Bullish", "confidence": 85, "source": "Twitter", "time": "2 min ago"},
                        {"symbol": "NVDA", "sentiment": "Bullish", "confidence": 92, "source": "Reddit", "time": "5 min ago"},
                        {"symbol": "TSLA", "sentiment": "Bearish", "confidence": 78, "source": "News", "time": "8 min ago"},
                    ]
                    
                    for signal in mock_signals:
                        color = "#10b981" if signal["sentiment"] == "Bullish" else "#ef4444"
                        st.markdown(f"""
                        <div style="border-left: 3px solid {color}; padding: 12px; margin-bottom: 8px; background: rgba(255,255,255,0.02);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 14px; font-weight: 700; color: white;">{signal['symbol']}</span>
                                    <span style="font-size: 12px; color: {color}; margin-left: 8px;">{signal['sentiment']}</span>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 11px; color: #94a3b8;">{signal['source']}</div>
                                    <div style="font-size: 10px; color: #64748b;">{signal['time']}</div>
                                </div>
                            </div>
                            <div style="margin-top: 4px;">
                                <span style="font-size: 12px; color: #94a3b8;">Confidence: {signal['confidence']}%</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            
            with social_tab2:
                st.subheader("Trending Topics")
                st.info("Most discussed trading topics and assets across social platforms")
                
                mock_trends = [
                    {"topic": "AI Stocks Rally", "mentions": 1250, "sentiment": "Positive", "assets": ["NVDA", "AMD", "SMCI"]},
                    {"topic": "Fed Rate Decision", "mentions": 890, "sentiment": "Neutral", "assets": ["SPY", "QQQ", "DIA"]},
                    {"topic": "Oil Price Drop", "mentions": 567, "sentiment": "Negative", "assets": ["XLE", "CVX", "XOM"]},
                ]
                
                for trend in mock_trends:
                    st.markdown(f"""
                    <div style="padding: 12px; margin-bottom: 8px; background: rgba(255,255,255,0.02); border-radius: 8px;">
                        <div style="font-size: 14px; font-weight: 700; color: white; margin-bottom: 4px;">{trend['topic']}</div>
                        <div style="display: flex; gap: 16px; font-size: 12px; color: #94a3b8;">
                            <span>_mentions: {trend['mentions']}</span>
                            <span style="color: {'#10b981' if trend['sentiment'] == 'Positive' else '#ef4444' if trend['sentiment'] == 'Negative' else '#64748b'};">{trend['sentiment']}</span>
                        </div>
                        <div style="margin-top: 6px;">
                            <span style="font-size: 11px; color: #64748b;">Assets: {', '.join(trend['assets'])}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with social_tab3:
                st.subheader("Social Analytics")
                st.info("Aggregate sentiment analysis and signal performance metrics")
                
                # Mock analytics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Signals", "1,247", "+12%")
                with col2:
                    st.metric("Avg Confidence", "82%", "+3%")
                with col3:
                    st.metric("Success Rate", "76%", "+5%")
                with col4:
                    st.metric("Active Sources", "8", "+2")
                
                st.markdown("---")
                
                # Simple chart
                import plotly.express as px
                df = pd.DataFrame({
                    'hour': ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                    'signals': [45, 62, 89, 156, 134, 78],
                    'sentiment': [0.3, 0.45, 0.67, 0.82, 0.71, 0.58]
                })
                
                fig = px.line(df, x='hour', y='signals', title='Signal Volume by Hour', 
                            template='plotly_dark', color_discrete_sequence=['#3b82f6'])
                fig.update_layout(height=300, paper_bgcolor='#0a0e17', plot_bgcolor='#0a0e17')
                st.plotly_chart(fig, width='stretch')
                
        except ImportError as e:
            st.error(f"Social signals module not available: {e}")
            st.info("Install social signals dependencies: pip install -r requirements_social_signals.txt")
        except Exception as e:
            st.error(f"Error loading social signals: {e}")
            st.info("Social signals temporarily unavailable")
    
    # ==================== TAB: ADMIN (admin only) ====================
    if tab_admin is not None:
        with tab_admin:
            render_admin_panel(db)
    
    # Save selected symbols to DB when they change
    current_symbols = st.session_state.get('selected_symbols', TradingConfig.INSTRUMENTS)
    db.save_settings(user['user_id'], {'selected_symbols': current_symbols})
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_sec)
        signals, market_data = engine.get_signals()
        st.session_state.signals = signals
        st.session_state.market_data = market_data
        st.rerun()


if __name__ == "__main__":
    main()
