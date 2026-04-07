# QuantumTrade Engine v3.0

## Enterprise-Grade AI Trading Dashboard

QuantumTrade Engine v3.0 is a sophisticated, enterprise-grade trading platform that combines advanced AI analytics, real-time market data, and global social signals to deliver hedge-fund grade trading intelligence.

---

## Quick Start

### One-Click Launch
```bash
# Windows
run.bat

# Linux/Mac
./run.sh

# Or manually
python -m streamlit run dashboards/pro_trading_dashboard.py
```

### Access
- **URL**: http://localhost:8501
- **Default Admin**: Create your own admin account with `python scripts/create_admin.py`

---

## Project Structure

```
S-P 500/
|
|--- config/          # Single .env file + requirements
|--- dashboards/      # pro_trading_dashboard.py (main UI)
|--- core/           # Quantum AI modules (12 total)
|--- intelligence/   # Advanced ML & backtesting
|--- social/         # Global social signals system
|--- trading/        # Execution & risk management
|--- auth/           # Security & database
|--- utils/          # Helper utilities
|--- data/           # JSON storage & reports
|--- logs/           # System logs
|--- web/            # Marketing page
|--- docs/           # Single documentation file (this)
|--- scripts/        # Setup utilities
|
|--- run.bat         # One-click launcher (Windows)
|--- run.sh          # One-click launcher (Linux/Mac)
```

---

## Core Features

### AI-Powered Trading Intelligence
- **12 Advanced AI Modules**: Quantum scoring, market structure analysis, regime detection, portfolio optimization
- **Real-time Signal Generation**: Technical analysis combined with AI predictions
- **Risk Management**: Advanced position sizing and portfolio risk controls
- **Backtesting Engine**: Historical strategy validation with performance analytics

### Global Social Signals
- **Real-time Social Media Monitoring**: Twitter/X, Reddit, news feeds
- **NLP-Powered Sentiment Analysis**: Advanced text processing for market sentiment
- **Topic Clustering**: Identifies trending market topics and themes
- **Social Signal Integration**: Converts social sentiment into actionable trading signals

### Professional Dashboard
- **Multi-Timeframe Analysis**: 15m, 1h, 4h, daily charts
- **Real-time Market Data**: Forex, stocks, commodities, cryptocurrencies
- **Advanced Charting**: Interactive charts with technical indicators
- **Portfolio Management**: Track positions, P&L, and performance metrics

### Advanced Features (NEW)
- **Real-time WebSocket Streaming**: Live market data and social signals via WebSocket connections
- **Comprehensive Error Handling**: Advanced logging, circuit breakers, and retry mechanisms
- **Portfolio Performance Analytics**: Risk metrics, attribution analysis, and performance reporting
- **Automated Strategy Backtesting**: Parameter optimization, walk-forward analysis, and Monte Carlo simulations
- **Mobile-Responsive Design**: Touch-optimized interface with PWA support
- **Enterprise Security**: Zero hardcoded secrets, comprehensive audit logging

---

## New Features v3.1

### Real-time WebSocket Streaming
- **WebSocket Manager**: High-performance WebSocket server for real-time data streaming
- **Market Data Streams**: Live forex, crypto, and stock price updates
- **Social Signal Streams**: Real-time social media sentiment and trending topics
- **Client Connection Management**: Automatic reconnection and subscription management
- **Low Latency**: Sub-second data updates with efficient message routing

**Usage:**
```python
from core.websocket_manager import WebSocketManager, MarketDataStream

# Start WebSocket server
ws_manager = WebSocketManager()
await ws_manager.start_server()

# Start market data streaming
market_stream = MarketDataStream(ws_manager)
await market_stream.start_streaming()
```

### Comprehensive Error Handling & Logging
- **Structured Logging**: Advanced logging with JSON output and rotation
- **Error Tracking**: Comprehensive error reporting with context and stack traces
- **Circuit Breaker Pattern**: Automatic failure detection and recovery
- **Retry Mechanisms**: Exponential backoff with configurable parameters
- **Performance Monitoring**: Real-time error metrics and system health

**Usage:**
```python
from utils.error_handler import handle_errors, circuit_breaker, retry_handler

@handle_errors(severity="error")
@circuit_breaker(failure_threshold=5)
@retry_handler(max_attempts=3)
def risky_operation():
    # Your code here
    pass
```

### Portfolio Performance Analytics
- **Risk Metrics**: VaR, CVaR, beta, alpha, Sharpe ratio, Sortino ratio
- **Performance Attribution**: Asset allocation, security selection, and timing effects
- **Drawdown Analysis**: Maximum drawdown, duration, and recovery analysis
- **Trade Analytics**: Win rate, profit factor, average win/loss ratios
- **Benchmark Comparison**: Alpha, beta, and information ratio calculations

**Usage:**
```python
from intelligence.portfolio_analytics import PortfolioAnalyzer

analyzer = PortfolioAnalyzer(benchmark_returns)
metrics = analyzer.calculate_performance_metrics(returns, trades)
risk_metrics = analyzer.calculate_risk_metrics(returns)
```

### Automated Strategy Backtesting
- **Strategy Classes**: Base strategy framework with MA crossover and RSI strategies
- **Parameter Optimization**: Grid search and random search optimization
- **Walk-Forward Analysis**: Rolling window out-of-sample testing
- **Monte Carlo Simulation**: Statistical validation with bootstrap sampling
- **Performance Metrics**: Comprehensive backtest reporting with risk-adjusted returns

**Usage:**
```python
from intelligence.backtesting_engine import BacktestEngine, MovingAverageStrategy

engine = BacktestEngine(initial_capital=100000)
strategy = MovingAverageStrategy("MA_Cross", {"short_window": 10, "long_window": 30})
result = engine.run_backtest(strategy, data)

# Parameter optimization
param_grid = {"short_window": [5, 10, 15], "long_window": [20, 30, 40]}
optimization = engine.optimize_parameters(MovingAverageStrategy, param_grid, data)
```

### Mobile-Responsive Design
- **Responsive Components**: Adaptive UI for mobile, tablet, and desktop
- **Touch Optimization**: Large touch targets and swipe gestures
- **PWA Support**: Progressive Web App features with offline capability
- **Performance Optimization**: Lazy loading and efficient rendering
- **Breakpoint Detection**: Automatic layout adaptation based on screen size

**Usage:**
```python
from utils.mobile_responsive import ResponsiveDesign, MobileComponents

# Responsive columns
cols = ResponsiveDesign.responsive_columns(3, 2, 1)

# Mobile-optimized cards
MobileComponents.mobile_card("Title", "Content", icon="chart")

# Touch-friendly buttons
MobileComponents.large_button("Trade Now", icon="buy")
```

### Enhanced Security
- **Zero Hardcoded Secrets**: All credentials loaded from environment variables
- **Comprehensive Audit Logging**: Complete system activity tracking
- **Input Validation**: Sanitization and validation of all user inputs
- **Session Management**: Secure JWT tokens with proper expiration
- **Rate Limiting**: Brute force protection and API throttling

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- MongoDB Atlas account (free tier works)
- Git

### Setup Process

1. **Clone/Download the Project**
   ```bash
   # If using git
   git clone <repository-url>
   cd S-P-500
   ```

2. **Configure Environment**
   - Edit `config/.env` with your MongoDB Atlas connection string
   - MongoDB URI format: `mongodb+srv://user:pass@cluster.mongodb.net/dbname`

3. **Run the Application**
   ```bash
   # Windows
   run.bat
   
   # Linux/Mac
   ./run.sh
   ```

4. **Create Admin Account**
   ```bash
   python scripts/create_admin.py
   ```

---

## System Architecture

### Database Layer
- **MongoDB Atlas**: Cloud-based NoSQL database
- **Collections**: users, positions, trades, signals, events, sessions
- **Real-time Sync**: Instant data updates across all components

### AI/ML Layer
- **Quantum Scorer**: Advanced signal confidence scoring
- **Market Structure Analyzer**: Identifies key market levels and patterns
- **Regime Detection**: Detects market conditions (trending, ranging, volatile)
- **Portfolio Optimizer**: Modern portfolio theory implementation
- **Adaptive Learner**: Machine learning for strategy improvement

### Social Signals Layer
- **Data Collection**: Multi-source social media monitoring
- **NLP Processing**: Sentiment analysis and entity extraction
- **Signal Generation**: Converts social data into trading signals
- **Trend Detection**: Identifies emerging market trends

---

## Configuration

### Environment Variables (.env)
```ini
# MongoDB Atlas (required)
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname

# Social Signals Database
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/social_db
MONGODB_DATABASE_NAME=quantumtrade_social

# Optional: Trading APIs
# OANDA_API_KEY=your_api_key
# BINANCE_API_KEY=your_api_key
# TWITTER_BEARER_TOKEN=your_twitter_token
```

### Dependencies
All dependencies are included in `config/requirements.txt`:
- Streamlit (dashboard framework)
- Plotly (interactive charts)
- Pandas/NumPy (data analysis)
- MongoDB (database)
- Transformers (AI/ML)
- Social media APIs

---

## User Management

### Admin Features
- **User Creation**: Add new users with role-based permissions
- **User Deletion**: Remove users with audit logging
- **Role Management**: admin, trader, viewer, user roles
- **Audit Logs**: Complete system activity tracking

### Security
- **JWT Authentication**: Secure session management
- **Password Hashing**: bcrypt encryption
- **Rate Limiting**: Brute force protection
- **Session Persistence**: "Remember me" functionality

---

## Trading Features

### Supported Assets
- **Forex**: EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF, NZD/USD
- **Commodities**: Gold (XAU/USD), Silver (XAG/USD), Oil (OIL/USD)
- **Stocks**: AAPL, SPX500, and major indices
- **Cryptocurrencies**: BTC/USD, ETH/USD, and major pairs

### Technical Indicators
- Moving Averages (SMA, EMA)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Volume Analysis
- Support/Resistance Levels

### Risk Management
- **Position Sizing**: Based on account balance and risk tolerance
- **Stop Loss**: Automatic loss protection
- **Take Profit**: Profit target automation
- **Portfolio Diversification**: Asset allocation optimization

---

## Social Signals Integration

### Data Sources
- **Twitter/X**: Real-time tweets and sentiment
- **Reddit**: Community discussions and analysis
- **News Feeds**: Financial news and announcements
- **RSS Feeds**: Market updates and analysis

### Signal Processing
- **Sentiment Analysis**: Positive/negative/neutral classification
- **Entity Recognition**: Company and ticker identification
- **Impact Scoring**: Signal relevance and confidence
- **Trend Detection**: Emerging market themes

### Integration
- **Real-time Updates**: Live social signal processing
- **Dashboard Integration**: Social signals alongside technical analysis
- **Alert System**: Notifications for high-impact social events
- **Historical Analysis**: Social signal performance tracking

---

## Performance & Analytics

### Real-time Metrics
- **Portfolio Value**: Current account balance
- **P&L Tracking**: Real-time profit/loss calculation
- **Win Rate**: Success rate of trading signals
- **Risk Metrics**: VaR, maximum drawdown, Sharpe ratio

### Historical Analysis
- **Trade History**: Complete record of all trades
- **Performance Reports**: Monthly/quarterly analytics
- **Strategy Backtesting**: Historical strategy validation
- **Risk Analytics**: Portfolio risk assessment

---

## Troubleshooting

### Common Issues

**MongoDB Connection Error**
- Verify MongoDB Atlas connection string in `.env`
- Check network access (IP whitelist)
- Ensure username/password are correct

**Import Errors**
- Run `run.bat` to automatically install dependencies
- Check Python version (3.8+ required)
- Verify virtual environment activation

**Social Signals Not Working**
- Configure API keys in `.env` file
- Check internet connection
- Verify API rate limits

### Support Tools
- `check_users.py` - Verify database users
- `reset_password.py` - Reset user passwords
- `debug_login.py` - Diagnose authentication issues

---

## Development & Customization

### Adding New Features
1. Create new modules in appropriate folders (`core/`, `intelligence/`, `trading/`)
2. Update imports in `dashboards/pro_trading_dashboard.py`
3. Add database schema changes if needed
4. Update documentation

### API Integration
- Add new data providers in `trading/` folder
- Update `config/requirements.txt` with new dependencies
- Configure API keys in `.env` file
- Add UI components in dashboard

### Custom Indicators
- Create indicator functions in `trading/trading_strategies.py`
- Add to dashboard chart options
- Update signal generation logic
- Test with historical data

---

## Security Best Practices

### Database Security
- Use strong passwords for MongoDB
- Enable IP whitelisting
- Regular backup of database
- Monitor access logs

### API Security
- Store API keys in environment variables
- Use HTTPS for all API calls
- Implement rate limiting
- Monitor API usage

### Application Security
- Keep dependencies updated
- Use secure password policies
- Enable 2FA for admin accounts
- Regular security audits

---

## Deployment

### Production Deployment
1. **Database**: Use MongoDB Atlas production tier
2. **Environment**: Configure production `.env` file
3. **Security**: Enable HTTPS and security headers
4. **Monitoring**: Set up logging and alerts
5. **Backup**: Regular database and file backups

### Cloud Deployment Options
- **Streamlit Cloud**: Easiest deployment option
- **Heroku**: Full-featured PaaS deployment
- **AWS/Azure**: Enterprise cloud deployment
- **Docker**: Containerized deployment

---

## License & Support

### License
This project is for educational and research purposes. Use at your own risk.

### Disclaimer
Trading involves substantial risk of loss. This software is for informational purposes only. Past performance does not guarantee future results.

### Support
- Documentation: This README file
- Issues: Check troubleshooting section
- Community: GitHub discussions (if applicable)

---

## Version History

### v3.0 (Current)
- Complete folder reorganization
- Unified configuration system
- Enhanced social signals integration
- Advanced AI modules
- Professional admin panel
- One-click deployment

### v2.0
- Social signals integration
- Enhanced AI capabilities
- Improved dashboard UI

### v1.0
- Basic trading dashboard
- MongoDB integration
- User authentication

---

**QuantumTrade Engine v3.0 - Professional Trading Intelligence Platform**

*Built with cutting-edge AI, real-time data, and comprehensive market analysis.*
