"""
QUANTUMTRADE MOBILE APP
Mobile-optimized trading dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(__file__))

from trading.fortrade_config import TradingConfig
from trading.fortrade_api_client import FortradeAPIClient
from trading.trading_strategies import StrategyManager, TradingSignal, SignalType, TechnicalIndicators
from trading.risk_manager import RiskManager
from intelligence.advanced_signal_validator import AdvancedSignalValidator
from core.quantum_scorer import QuantumScorer, ScoringBreakdown
from core.market_structure import MarketStructureAnalyzer, StructureAnalysis
from core.adaptive_learner import AdaptiveLearner
from trading.execution_engine import ExecutionManager, PaperBroker, OrderRequest, OrderType

# ============================================================
# MOBILE PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="QuantumTrade Mobile",
    page_icon="https://img.icons8.com/fluency/48/combo-chart.png",
    layout="centered",  # Changed to centered for mobile
    initial_sidebar_state="collapsed"  # Collapsed for mobile
)

# ============================================================
# MOBILE CSS STYLING
# ============================================================
MOBILE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

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

/* Mobile-first design */
.stApp {
    background: var(--bg-primary) !important;
    font-family: 'Inter', sans-serif !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden !important;}

/* Mobile sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    width: 100% !important;
    max-width: 300px !important;
}

/* Mobile metric cards */
.mobile-metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    text-align: center;
    transition: all 0.3s ease;
}

.mobile-metric-card:hover {
    border-color: var(--accent-blue);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.1);
}

.mobile-metric-label {
    font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin-bottom: 4px;
}

.mobile-metric-value {
    font-size: 20px;
    font-weight: 800;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -1px;
}

.mobile-metric-value.positive { color: var(--accent-green); }
.mobile-metric-value.negative { color: var(--accent-red); }

/* Mobile signal cards */
.mobile-signal-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    margin: 12px 0;
    transition: all 0.3s ease;
    position: relative;
}

.mobile-signal-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.mobile-signal-card.buy {
    border-left: 4px solid var(--accent-green);
}

.mobile-signal-card.sell {
    border-left: 4px solid var(--accent-red);
}

.mobile-signal-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.mobile-signal-badge.buy { background: rgba(16,185,129,0.15); color: var(--accent-green); }
.mobile-signal-badge.sell { background: rgba(239,68,68,0.15); color: var(--accent-red); }

/* Mobile charts */
.mobile-chart-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 12px;
    margin: 8px 0;
    height: 300px !important;
}

/* Mobile navigation */
.mobile-nav {
    display: flex;
    justify-content: space-around;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 8px;
    margin: 16px 0;
    position: sticky;
    top: 0;
    z-index: 100;
}

.mobile-nav-item {
    flex: 1;
    text-align: center;
    padding: 8px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
}

.mobile-nav-item:hover {
    background: var(--bg-card);
    color: var(--text-primary);
}

.mobile-nav-item.active {
    background: var(--accent-blue);
    color: white;
}

/* Mobile buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 12px 20px !important;
    transition: all 0.2s ease !important;
    border: none !important;
    width: 100% !important;
}

.stButton > button[kind="primary"] {
    background: var(--gradient-blue) !important;
    color: white !important;
}

/* Mobile tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 4px;
    border: 1px solid var(--border-color);
    overflow-x: auto !important;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.3px;
    padding: 8px 12px;
    color: var(--text-secondary) !important;
    white-space: nowrap !important;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-blue) !important;
    color: white !important;
}

/* Mobile responsive */
@media (max-width: 768px) {
    .mobile-metric-card {
        padding: 12px;
        margin: 4px 0;
    }
    
    .mobile-metric-value {
        font-size: 18px;
    }
    
    .mobile-chart-container {
        height: 250px !important;
    }
}

@media (max-width: 480px) {
    .mobile-metric-value {
        font-size: 16px;
    }
    
    .mobile-chart-container {
        height: 200px !important;
    }
}
</style>
"""

# ============================================================
# MOBILE DATA ENGINE (Same as desktop)
# ============================================================
class MobileTradingDataEngine:
    """Mobile-optimized trading data engine"""
    
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
    
    def get_market_data(self, symbol: str, periods: int = 100) -> pd.DataFrame:
        """Fetch market data with mobile optimization"""
        candles = self.api_client.get_historical_data(
            symbol=symbol, timeframe='15m', limit=periods
        )
        
        if not candles:
            return pd.DataFrame()
        
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df.sort_index()
        
        # Calculate indicators (simplified for mobile)
        df = self._add_mobile_indicators(df)
        
        return df
    
    def _add_mobile_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add essential indicators for mobile"""
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Moving Averages
        df['ema_20'] = close.ewm(span=20).mean()
        df['ema_50'] = close.ewm(span=50).mean()
        
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
        
        # Bollinger Bands
        df['bb_middle'] = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        return df
    
    def get_signals(self):
        """Get signals with mobile optimization"""
        market_data = {}
        strategy_data = {}
        
        # Limit symbols for mobile performance
        mobile_symbols = TradingConfig.INSTRUMENTS[:4]  # First 4 symbols
        
        for symbol in mobile_symbols:
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
            sig_type = signal.signal_type.value
            
            # Simplified validation for mobile
            validation = self.signal_validator.validate_signal(signal, df)
            
            # Quick quantum scoring
            try:
                scoring = self.quantum_scorer.score_signal(
                    df=df,
                    signal_type=sig_type,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    symbol=signal.symbol,
                    strategy=signal.strategy
                )
            except Exception:
                scoring = ScoringBreakdown(final_score=0.5)
            
            signal.confidence = scoring.final_score
            
            result.append({
                'signal': signal,
                'validation': validation,
                'is_validated': validation.is_valid,
                'session': session,
                'quantum_score': scoring.final_score,
                'scoring': scoring,
                'recommendation': 'BUY' if scoring.final_score > 0.6 else 'SELL' if scoring.final_score < 0.4 else 'HOLD',
            })
        
        result.sort(key=lambda x: x['quantum_score'], reverse=True)
        return result, market_data

# ============================================================
# MOBILE CHART BUILDER
# ============================================================
class MobileChartBuilder:
    """Mobile-optimized chart builder"""
    
    @staticmethod
    def create_mobile_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
        """Create mobile-friendly chart"""
        if df.empty:
            return go.Figure()
        
        # Create figure with mobile dimensions
        fig = go.Figure()
        
        # Add candlestick chart
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol,
            increasing_line_color='#10b981',
            decreasing_line_color='#ef4444'
        ))
        
        # Add EMAs
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['ema_20'],
            line=dict(color='#3b82f6', width=1),
            name='EMA 20'
        ))
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['ema_50'],
            line=dict(color='#f59e0b', width=1),
            name='EMA 50'
        ))
        
        # Mobile layout
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0a0e17',
            plot_bgcolor='#0a0e17',
            height=300,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(
                showgrid=False,
                showticklabels=True,
                tickfont=dict(size=8)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#1a1f2e',
                showticklabels=True,
                tickfont=dict(size=8)
            ),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=8)
            )
        )
        
        return fig

# ============================================================
# MOBILE UI COMPONENTS
# ============================================================
def render_mobile_header():
    """Render mobile header"""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 24px; font-weight: 800; margin: 0; color: #3b82f6;">
            QUANTUMTRADE
        </h1>
        <p style="font-size: 12px; color: #94a3b8; margin: 4px 0;">
            Mobile Trading Terminal
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_mobile_metrics(engine):
    """Render mobile metrics"""
    broker = engine.execution_manager.broker
    balance = broker.get_balance()
    positions = broker.get_open_positions()
    
    # Calculate metrics
    daily_pnl = sum(pos.get('pnl', 0) for pos in positions.values())
    win_rate = 85.0  # Placeholder
    trades_today = len(positions)
    session = engine.risk_manager.get_current_session()
    
    # Mobile metric cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="mobile-metric-card">
            <div class="mobile-metric-label">Portfolio</div>
            <div class="mobile-metric-value">EUR {balance:.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        pnl_class = 'positive' if daily_pnl >= 0 else 'negative'
        pnl_arrow = '+' if daily_pnl >= 0 else ''
        st.markdown(f"""
        <div class="mobile-metric-card">
            <div class="mobile-metric-label">Daily P&L</div>
            <div class="mobile-metric-value {pnl_class}">{pnl_arrow}EUR {daily_pnl:.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown(f"""
        <div class="mobile-metric-card">
            <div class="mobile-metric-label">Win Rate</div>
            <div class="mobile-metric-value">{win_rate:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="mobile-metric-card">
            <div class="mobile-metric-label">Positions</div>
            <div class="mobile-metric-value">{trades_today}</div>
        </div>
        """, unsafe_allow_html=True)

def render_mobile_signals(signals):
    """Render mobile signals"""
    if not signals:
        st.info("No signals available")
        return
    
    st.markdown("### Active Signals")
    
    for signal_data in signals[:3]:  # Show top 3 signals
        signal = signal_data['signal']
        score = signal_data['quantum_score']
        recommendation = signal_data['recommendation']
        
        signal_type = 'buy' if signal.signal_type.value == 'buy' else 'sell'
        
        st.markdown(f"""
        <div class="mobile-signal-card {signal_type}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 700; font-size: 14px;">{signal.symbol}</span>
                <span class="mobile-signal-badge {signal_type}">{signal.signal_type.value.upper()}</span>
            </div>
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px;">
                Entry: {signal.entry_price:.5f} | Stop: {signal.stop_loss:.5f}
            </div>
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">
                Target: {signal.take_profit:.5f}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 11px; color: #64748b;">Score: {score:.1%}</span>
                <span style="font-size: 11px; font-weight: 600; color: #10b981;">{recommendation}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_mobile_chart(df, symbol):
    """Render mobile chart"""
    if df.empty:
        st.warning("No chart data available")
        return
    
    fig = MobileChartBuilder.create_mobile_chart(df, symbol)
    st.plotly_chart(fig, use_container_width=True, height=300)

# ============================================================
# MAIN MOBILE APP
# ============================================================
def main():
    """Main mobile application"""
    render_mobile_header()
    
    # Initialize data engine
    if 'mobile_engine' not in st.session_state:
        st.session_state.mobile_engine = MobileTradingDataEngine()
    
    engine = st.session_state.mobile_engine
    
    # Mobile navigation
    page = st.selectbox(
        "Navigate",
        ["Dashboard", "Signals", "Charts", "Positions"],
        index=0,
        key="mobile_nav"
    )
    
    # Render based on page
    if page == "Dashboard":
        st.markdown("### Dashboard")
        render_mobile_metrics(engine)
        
        # Quick signals preview
        signals, market_data = engine.get_signals()
        if signals:
            st.markdown("### Top Signals")
            render_mobile_signals(signals)
    
    elif page == "Signals":
        st.markdown("### Trading Signals")
        signals, market_data = engine.get_signals()
        render_mobile_signals(signals)
    
    elif page == "Charts":
        st.markdown("### Charts")
        
        # Symbol selector
        symbols = TradingConfig.INSTRUMENTS[:4]  # Mobile limit
        symbol = st.selectbox("Select Symbol", symbols)
        
        # Get data and render chart
        df = engine.get_market_data(symbol)
        render_mobile_chart(df, symbol)
        
        # Quick analysis
        if not df.empty and len(df) >= 20:
            last = df.iloc[-1]
            rsi = last['rsi']
            trend = "BULLISH" if last['ema_20'] > last['ema_50'] else "BEARISH"
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("RSI", f"{rsi:.1f}")
            with col2:
                st.metric("Trend", trend)
    
    elif page == "Positions":
        st.markdown("### Open Positions")
        positions = engine.execution_manager.broker.get_open_positions()
        
        if not positions:
            st.info("No open positions")
        else:
            for pos_id, pos in positions.items():
                pnl = pos.get('pnl', 0)
                pnl_class = 'positive' if pnl >= 0 else 'negative'
                
                st.markdown(f"""
                <div class="mobile-signal-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700;">{pos['symbol']}</span>
                        <span style="font-weight: 600;" class="{pnl_class}">EUR {pnl:.2f}</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                        {pos['side']} @ {pos['entry_price']:.5f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
