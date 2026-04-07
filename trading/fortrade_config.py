"""
Fortrade Automated Trading System - Configuration
CRITICAL: This system prioritizes CAPITAL PRESERVATION over profits
"""

import os
from typing import Dict, Any

class TradingConfig:
    """Central configuration for the trading system"""
    
    # ==================== API CREDENTIALS ====================
    FORTRADE_API_KEY = os.getenv('FORTRADE_API_KEY', '')
    FORTRADE_API_SECRET = os.getenv('FORTRADE_API_SECRET', '')
    FORTRADE_ACCOUNT_ID = os.getenv('FORTRADE_ACCOUNT_ID', '')

    # ==================== OANDA CREDENTIALS ====================
    # Sign up at https://www.oanda.com/register/ (practice account is free)
    # Env: OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT=practice|live
    OANDA_API_KEY = os.getenv('OANDA_API_KEY', '')
    OANDA_ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID', '')
    OANDA_ENVIRONMENT = os.getenv('OANDA_ENVIRONMENT', 'practice')

    # ==================== BINANCE CREDENTIALS ====================
    # Sign up at https://www.binance.com/en/register
    # Env: BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET=true|false
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'

    # ==================== DATA PROVIDER ====================
    # 'auto'     — OANDA for forex/indices, Binance for crypto, yfinance fallback
    # 'oanda'    — force OANDA for everything
    # 'binance'  — force Binance for everything
    # 'yfinance' — force yfinance fallback (no credentials needed)
    DATA_PROVIDER = os.getenv('DATA_PROVIDER', 'auto')

    # Historical data disk cache directory (set '' to disable disk cache)
    CACHE_DIR = os.getenv('CACHE_DIR', '.cache')

    # API Endpoints (update based on Fortrade documentation)
    API_BASE_URL = "https://api.fortrade.com/v1"
    WS_URL = "wss://stream.fortrade.com/v1"
    
    # ==================== TRADING MODE ====================
    TRADING_MODE = "PAPER"  # Options: "PAPER", "LIVE"
    
    # ==================== ACCOUNT SETTINGS ====================
    INITIAL_CAPITAL = 100.0  # EUR
    
    # ==================== RISK MANAGEMENT (CRITICAL) ====================
    # Maximum risk per trade (1-2% is conservative)
    RISK_PER_TRADE_PERCENT = 1.0  # 1% of account per trade
    
    # Maximum daily loss before stopping all trading
    MAX_DAILY_LOSS_PERCENT = 5.0  # Stop if down 5% in a day
    
    # Maximum total drawdown before system shutdown
    MAX_TOTAL_DRAWDOWN_PERCENT = 15.0  # Emergency stop at 15% total loss
    
    # Position sizing
    MAX_POSITION_SIZE_PERCENT = 10.0  # Never use more than 10% of capital per position
    
    # Maximum open positions at once
    MAX_CONCURRENT_POSITIONS = 4
    
    # Maximum trades per day (prevent overtrading)
    MAX_TRADES_PER_DAY = 10
    
    # Minimum time between trades (seconds) - prevent rapid fire
    MIN_TIME_BETWEEN_TRADES = 300  # 5 minutes
    
    # ==================== STRATEGY SETTINGS ====================
    STRATEGIES_ENABLED = {
        'trend_following': True,
        'rsi_mean_reversion': True,
        'macd_momentum': True
    }
    
    # Strategy-specific limits
    STRATEGY_MAX_TRADES = {
        'trend_following': 2,
        'rsi_mean_reversion': 3,
        'macd_momentum': 2
    }
    
    # ==================== INDICATOR PARAMETERS ====================
    # Moving Averages
    MA_FAST = 20
    MA_MEDIUM = 50
    MA_SLOW = 200
    
    # RSI
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_NEUTRAL = 50
    
    # MACD
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # ==================== TIMEFRAMES ====================
    TIMEFRAMES = {
        'trend_following': '15m',
        'rsi_mean_reversion': '5m',
        'macd_momentum': '30m'
    }
    
    # ==================== TAKE PROFIT / STOP LOSS ====================
    # Strategy-specific TP/SL (percentage)
    STRATEGY_TP_SL = {
        'trend_following': {'tp': 1.5, 'sl': 0.75},
        'rsi_mean_reversion': {'tp': 1.0, 'sl': 0.5},
        'macd_momentum': {'tp': 1.2, 'sl': 0.6}
    }
    
    # ==================== TRADING INSTRUMENTS ====================
    # Default instruments shown in dashboard
    INSTRUMENTS = [
        'EUR/USD',
        'GBP/USD',
        'USD/JPY',
        'AUD/USD',
        'XAU/USD',    # Gold
        'XAG/USD',    # Silver
        'OIL/USD',    # Crude Oil (WTI)
        'AAPL',       # Apple Inc.
        'SPX500',     # S&P 500 Index
        'BTC/USD',    # Bitcoin
    ]
    
    # Complete symbol universe for search/selection
    SYMBOL_UNIVERSE = {
        # FOREX MAJORS
        'EUR/USD': 'Euro / US Dollar',
        'GBP/USD': 'British Pound / US Dollar',
        'USD/JPY': 'US Dollar / Japanese Yen',
        'USD/CHF': 'US Dollar / Swiss Franc',
        'AUD/USD': 'Australian Dollar / US Dollar',
        'NZD/USD': 'New Zealand Dollar / US Dollar',
        'USD/CAD': 'US Dollar / Canadian Dollar',
        
        # FOREX CROSSES
        'EUR/GBP': 'Euro / British Pound',
        'EUR/JPY': 'Euro / Japanese Yen',
        'GBP/JPY': 'British Pound / Japanese Yen',
        'AUD/JPY': 'Australian Dollar / Japanese Yen',
        
        # COMMODITIES
        'XAU/USD': 'Gold',
        'XAG/USD': 'Silver',
        'OIL/USD': 'Crude Oil WTI',
        'CL': 'Crude Oil WTI (CL Futures)',
        'BRENT/USD': 'Brent Crude Oil',
        'GAS/USD': 'Natural Gas',
        
        # INDICES
        'SPX500': 'S&P 500',
        'US30': 'Dow Jones',
        'NAS100': 'NASDAQ 100',
        'UK100': 'FTSE 100',
        'GER40': 'DAX 40',
        'JPN225': 'Nikkei 225',
        
        # US TECH STOCKS
        'AAPL': 'Apple Inc.',
        'MSFT': 'Microsoft Corporation',
        'GOOGL': 'Alphabet Inc. (Google)',
        'AMZN': 'Amazon.com Inc.',
        'META': 'Meta Platforms (Facebook)',
        'TSLA': 'Tesla Inc.',
        'NVDA': 'NVIDIA Corporation',
        'AMD': 'Advanced Micro Devices',
        'NFLX': 'Netflix Inc.',
        'INTC': 'Intel Corporation',
        'ORCL': 'Oracle Corporation',
        'CSCO': 'Cisco Systems',
        'ADBE': 'Adobe Inc.',
        'CRM': 'Salesforce Inc.',
        'PYPL': 'PayPal Holdings',
        'SQ': 'Block Inc. (Square)',
        'SHOP': 'Shopify Inc.',
        'UBER': 'Uber Technologies',
        'LYFT': 'Lyft Inc.',
        'SNAP': 'Snap Inc.',
        
        # US FINANCE
        'JPM': 'JPMorgan Chase',
        'BAC': 'Bank of America',
        'WFC': 'Wells Fargo',
        'GS': 'Goldman Sachs',
        'MS': 'Morgan Stanley',
        'V': 'Visa Inc.',
        'MA': 'Mastercard Inc.',
        'AXP': 'American Express',
        
        # US CONSUMER
        'WMT': 'Walmart Inc.',
        'HD': 'Home Depot',
        'NKE': 'Nike Inc.',
        'MCD': 'McDonald\'s Corporation',
        'SBUX': 'Starbucks Corporation',
        'DIS': 'Walt Disney Company',
        'COST': 'Costco Wholesale',
        'TGT': 'Target Corporation',
        
        # US HEALTHCARE
        'JNJ': 'Johnson & Johnson',
        'UNH': 'UnitedHealth Group',
        'PFE': 'Pfizer Inc.',
        'ABBV': 'AbbVie Inc.',
        'TMO': 'Thermo Fisher Scientific',
        'ABT': 'Abbott Laboratories',
        'CVS': 'CVS Health',
        
        # US ENERGY
        'XOM': 'Exxon Mobil',
        'CVX': 'Chevron Corporation',
        'COP': 'ConocoPhillips',
        'SLB': 'Schlumberger',
        
        # US INDUSTRIAL
        'BA': 'Boeing Company',
        'CAT': 'Caterpillar Inc.',
        'GE': 'General Electric',
        'LMT': 'Lockheed Martin',
        'MMM': '3M Company',
        
        # CRYPTOCURRENCY
        'BTC/USD': 'Bitcoin',
        'ETH/USD': 'Ethereum',
        'BNB/USD': 'Binance Coin',
        'XRP/USD': 'Ripple',
        'ADA/USD': 'Cardano',
        'SOL/USD': 'Solana',
        'DOGE/USD': 'Dogecoin',
        'MATIC/USD': 'Polygon',
    }
    
    # ==================== SAFETY FEATURES ====================
    # Kill switch - stops all trading immediately
    KILL_SWITCH_ACTIVE = False
    
    # Trading hours (UTC) - avoid low liquidity periods
    TRADING_HOURS_START = 0  # 0 AM UTC (24h for paper mode)
    TRADING_HOURS_END = 24   # 24 = trade all day
    ENFORCE_TRADING_HOURS = False  # Set True for live trading
    
    # Avoid trading during major news events
    AVOID_NEWS_TRADING = True
    
    # ==================== TRAILING STOP ====================
    ENABLE_TRAILING_STOP = True
    TRAILING_STOP_ACTIVATION_PERCENT = 0.5  # Activate after 0.5% profit
    TRAILING_STOP_DISTANCE_PERCENT = 0.3    # Trail 0.3% behind price
    
    # ==================== BREAK-EVEN STOP ====================
    ENABLE_BREAK_EVEN_STOP = True
    BREAK_EVEN_ACTIVATION_PERCENT = 0.4  # Move SL to entry after 0.4% profit
    BREAK_EVEN_OFFSET_PIPS = 2  # Small profit buffer above entry
    
    # ==================== SPREAD & COMMISSION ====================
    ESTIMATED_SPREAD_PIPS = {
        'EUR/USD': 1.2,
        'GBP/USD': 1.5,
        'USD/JPY': 1.3,
        'AUD/USD': 1.4,
        'XAU/USD': 3.5,    # Gold - wider spread
        'XAG/USD': 3.0,    # Silver
        'OIL/USD': 4.0,    # Crude Oil
        'AAPL': 0.5,       # Apple - tight spread
        'SPX500': 0.8,     # S&P 500
        'BTC/USD': 15.0,   # Bitcoin - wide spread
    }
    COMMISSION_PER_TRADE = 0.0  # EUR per trade
    
    # ==================== CORRELATION FILTER ====================
    ENABLE_CORRELATION_FILTER = True
    CORRELATED_PAIRS = {
        'EUR/USD': ['GBP/USD'],
        'GBP/USD': ['EUR/USD'],
        'AUD/USD': ['EUR/USD'],
        'XAU/USD': ['XAG/USD'],   # Gold & Silver move together
        'XAG/USD': ['XAU/USD'],
    }
    MAX_CORRELATED_SAME_DIRECTION = 1  # Max same-direction trades on correlated pairs
    
    # ==================== SESSION SETTINGS ====================
    # Adjust aggressiveness by session (multiplier on confidence)
    SESSION_MULTIPLIERS = {
        'asian':   0.8,   # Less aggressive (lower liquidity)
        'london':  1.2,   # Most aggressive (highest liquidity)
        'newyork': 1.1,   # Aggressive
        'overlap': 1.3,   # London/NY overlap = best time
        'off_hours': 0.6  # Late night = very conservative
    }
    
    # ==================== ADAPTIVE PARAMETERS ====================
    ENABLE_ADAPTIVE_PARAMS = True
    # In high volatility: widen SL/TP, reduce position size
    HIGH_VOLATILITY_SL_MULTIPLIER = 1.5
    HIGH_VOLATILITY_SIZE_MULTIPLIER = 0.7
    # In low volatility: tighten SL/TP, increase position size slightly
    LOW_VOLATILITY_SL_MULTIPLIER = 0.8
    LOW_VOLATILITY_SIZE_MULTIPLIER = 1.2
    
    # ==================== LOGGING & MONITORING ====================
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
    LOG_FILE = "trading_system.log"
    TRADE_HISTORY_DB = "trade_history.db"
    
    # Performance tracking
    TRACK_METRICS = True
    METRICS_UPDATE_INTERVAL = 60  # seconds
    
    # ==================== BACKTESTING ====================
    BACKTEST_START_DATE = "2024-01-01"
    BACKTEST_END_DATE = "2024-12-31"
    BACKTEST_INITIAL_CAPITAL = 100.0
    
    # ==================== NOTIFICATIONS ====================
    ENABLE_NOTIFICATIONS = True
    NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL', '')
    
    # Notify on these events
    NOTIFY_ON_TRADE = True
    NOTIFY_ON_DAILY_LOSS_LIMIT = True
    NOTIFY_ON_ERROR = True
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        issues = []
        
        if cls.TRADING_MODE == "LIVE":
            if not cls.FORTRADE_API_KEY:
                issues.append("FORTRADE_API_KEY not set")
            if not cls.FORTRADE_API_SECRET:
                issues.append("FORTRADE_API_SECRET not set")
            if not cls.FORTRADE_ACCOUNT_ID:
                issues.append("FORTRADE_ACCOUNT_ID not set")
        
        if cls.RISK_PER_TRADE_PERCENT > 2.0:
            issues.append("RISK_PER_TRADE_PERCENT too high (>2%)")
        
        if cls.MAX_POSITION_SIZE_PERCENT > 20.0:
            issues.append("MAX_POSITION_SIZE_PERCENT too high (>20%)")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    @classmethod
    def get_summary(cls) -> str:
        """Get configuration summary"""
        return f"""
╔══════════════════════════════════════════════════════════╗
║        FORTRADE AUTOMATED TRADING SYSTEM CONFIG          ║
╚══════════════════════════════════════════════════════════╝

Mode: {cls.TRADING_MODE}
Initial Capital: €{cls.INITIAL_CAPITAL}

RISK MANAGEMENT:
├─ Risk per trade: {cls.RISK_PER_TRADE_PERCENT}%
├─ Max daily loss: {cls.MAX_DAILY_LOSS_PERCENT}%
├─ Max drawdown: {cls.MAX_TOTAL_DRAWDOWN_PERCENT}%
├─ Max position size: {cls.MAX_POSITION_SIZE_PERCENT}%
├─ Max concurrent positions: {cls.MAX_CONCURRENT_POSITIONS}
└─ Max trades/day: {cls.MAX_TRADES_PER_DAY}

STRATEGIES ENABLED:
├─ Trend Following: {cls.STRATEGIES_ENABLED['trend_following']}
├─ RSI Mean Reversion: {cls.STRATEGIES_ENABLED['rsi_mean_reversion']}
└─ MACD Momentum: {cls.STRATEGIES_ENABLED['macd_momentum']}

INSTRUMENTS: {', '.join(cls.INSTRUMENTS)}

⚠️  IMPORTANT: This system prioritizes capital preservation.
    Realistic expectation: €3-€7/day in good conditions.
    Some days will have losses. This is normal.
"""
