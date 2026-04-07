# Social Signals Configuration
# Configuration file for the Global Social + Market Signals system

import os
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class SocialSignalsConfig:
    """Configuration for social signals system"""
    
    # Database Configuration (REQUIRED - no defaults for security)
    mongodb_connection_string: str = os.getenv('MONGODB_CONNECTION_STRING', '')
    mongodb_database_name: str = os.getenv('MONGODB_DATABASE_NAME', 'quantumtrade_social')
    
    # Social Media API Credentials
    # Twitter/X API
    twitter_api_key: Optional[str] = os.getenv('TWITTER_API_KEY')
    twitter_api_secret: Optional[str] = os.getenv('TWITTER_API_SECRET')
    twitter_bearer_token: Optional[str] = os.getenv('TWITTER_BEARER_TOKEN')
    
    # Reddit API
    reddit_client_id: Optional[str] = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret: Optional[str] = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_user_agent: str = os.getenv('REDDIT_USER_AGENT', 'QuantumTrade/1.0')
    
    # Data Collection Settings
    collection_interval_seconds: int = 60
    max_events_per_batch: int = 100
    enable_twitter_collection: bool = False  # Disabled - credits depleted
    enable_reddit_collection: bool = False  # Disabled until API keys configured
    enable_rss_collection: bool = True
    enable_simulated_data: bool = True  # Enable simulated data for immediate testing
    
    # Processing Settings
    enable_trend_detection: bool = True
    enable_signal_generation: bool = True
    enable_auto_execution: bool = False  # SAFETY: Disabled by default
    
    # Signal Filtering
    min_confidence_threshold: float = 0.4
    max_signals_per_minute: int = 5
    max_signals_per_day: int = 50
    
    # Risk Management
    max_position_size_percent: float = 2.0
    stop_loss_percent: float = 1.0
    take_profit_percent: float = 2.0
    cooldown_minutes: int = 30
    
    # Important People and Entities (weights for impact scoring)
    high_impact_people: Dict[str, float] = None
    company_tickers: Dict[str, str] = None
    asset_keywords: Dict[str, str] = None
    
    # RSS Feeds to Monitor
    rss_feeds: List[tuple] = None
    
    # Logging
    log_level: str = os.getenv('SOCIAL_SIGNALS_LOG_LEVEL', 'INFO')
    enable_structured_logging: bool = True
    
    def __post_init__(self):
        """Initialize default values for complex fields"""
        if self.high_impact_people is None:
            self.high_impact_people = {
                'elon musk': 3.0, 'musk': 2.5,
                'donald trump': 3.0, 'trump': 3.0,
                'jerome powell': 2.5, 'powell': 2.5,
                'sam altman': 2.0, 'altman': 2.0,
                'jensen huang': 2.0, 'huang': 1.8,
                'michael saylor': 2.0, 'saylor': 1.8,
                'vitalik buterin': 2.0,
                'brian armstrong': 1.5,
                'cathie wood': 1.5,
                'mark zuckerberg': 1.5,
                'jeff bezos': 1.5,
                'tim cook': 1.5,
                'larry ellison': 1.5,
            }
        
        if self.company_tickers is None:
            self.company_tickers = {
                'nvidia': 'NVDA', 'nvda': 'NVDA',
                'apple': 'AAPL', 'aapl': 'AAPL',
                'microsoft': 'MSFT', 'msft': 'MSFT',
                'google': 'GOOGL', 'alphabet': 'GOOGL', 'googl': 'GOOGL',
                'amazon': 'AMZN', 'amzn': 'AMZN',
                'meta': 'META', 'facebook': 'META',
                'tesla': 'TSLA', 'tsla': 'TSLA',
                'amd': 'AMD',
                'intel': 'INTC', 'intc': 'INTC',
                'openai': 'MSFT',
                'anthropic': 'GOOGL',
                'oracle': 'ORCL', 'orcl': 'ORCL',
                'salesforce': 'CRM',
                'netflix': 'NFLX', 'nflx': 'NFLX',
                'jpmorgan': 'JPM', 'jp morgan': 'JPM', 'jpm': 'JPM',
                'goldman sachs': 'GS', 'goldman': 'GS',
                'blackrock': 'BLK',
                'coinbase': 'COIN',
                'microstrategy': 'MSTR',
                'palantir': 'PLTR',
                'arm holdings': 'ARM', 'arm': 'ARM',
            }
        
        if self.asset_keywords is None:
            self.asset_keywords = {
                'bitcoin': 'BTC/USD', 'btc': 'BTC/USD', 'crypto': 'BTC/USD',
                'ethereum': 'ETH/USD', 'eth': 'ETH/USD',
                'solana': 'SOL/USD', 'sol': 'SOL/USD',
                'oil': 'OIL/USD', 'crude': 'OIL/USD', 'wti': 'OIL/USD', 'opec': 'OIL/USD',
                'gold': 'XAU/USD', 'xau': 'XAU/USD',
                'silver': 'XAG/USD',
                's&p': 'SPX500', 's&p 500': 'SPX500', 'spx': 'SPX500', 's&p500': 'SPX500',
                'nasdaq': 'NAS100', 'nasdaq 100': 'NAS100',
                'dow': 'US30', 'dow jones': 'US30',
                'euro': 'EUR/USD', 'eur': 'EUR/USD', 'eurusd': 'EUR/USD',
                'dollar': 'USD', 'fed': 'USD',
                'yen': 'USD/JPY', 'jpy': 'USD/JPY',
                'natural gas': 'GAS/USD',
            }
        
        if self.rss_feeds is None:
            self.rss_feeds = [
                # Financial News
                ('Reuters Business', 'https://feeds.reuters.com/reuters/businessNews'),
                ('Reuters Top News', 'https://feeds.reuters.com/reuters/topNews'),
                ('Bloomberg Markets', 'https://feeds.bloomberg.com/markets/news.rss'),
                ('CNBC Latest', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
                ('MarketWatch', 'https://www.marketwatch.com/rss/topstories'),
                
                # Tech News
                ('TechCrunch', 'https://techcrunch.com/feed/'),
                ('The Verge', 'https://www.theverge.com/rss/index.xml'),
                ('Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index'),
                
                # Crypto News
                ('CoinDesk', 'https://www.coindesk.com/arc/outboundfeeds/rss/'),
                ('Cointelegraph', 'https://cointelegraph.com/rss'),
                
                # General News
                ('BBC News', 'http://feeds.bbci.co.uk/news/rss.xml'),
                ('CNN Top Stories', 'http://rss.cnn.com/rss/edition.rss'),
            ]
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings"""
        warnings = []
        
        # Check database connection
        if not self.mongodb_connection_string:
            warnings.append("No MongoDB connection string configured - using file storage fallback")
        
        # Check API credentials
        if self.enable_twitter_collection and not self.twitter_bearer_token:
            warnings.append("Twitter API credentials not configured - Twitter collection disabled")
            self.enable_twitter_collection = False
        
        if self.enable_reddit_collection and not (self.reddit_client_id and self.reddit_client_secret):
            warnings.append("Reddit API credentials not configured - Reddit collection disabled")
            self.enable_reddit_collection = False
        
        # Safety checks
        if self.enable_auto_execution:
            warnings.append("AUTO-EXECUTION IS ENABLED - This will automatically place trades!")
        
        if self.max_position_size_percent > 5.0:
            warnings.append("Maximum position size is very high - consider reducing risk")
        
        if self.min_confidence_threshold < 0.3:
            warnings.append("Minimum confidence threshold is very low - may generate poor quality signals")
        
        return warnings
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return {
            'database': {
                'connection_string': self.mongodb_connection_string,
                'database_name': self.mongodb_database_name,
            },
            'apis': {
                'twitter_enabled': self.enable_twitter_collection,
                'reddit_enabled': self.enable_reddit_collection,
                'rss_enabled': self.enable_rss_collection,
            },
            'collection': {
                'interval_seconds': self.collection_interval_seconds,
                'max_events_per_batch': self.max_events_per_batch,
            },
            'processing': {
                'trend_detection': self.enable_trend_detection,
                'signal_generation': self.enable_signal_generation,
                'auto_execution': self.enable_auto_execution,
            },
            'filtering': {
                'min_confidence': self.min_confidence_threshold,
                'max_signals_per_minute': self.max_signals_per_minute,
                'max_signals_per_day': self.max_signals_per_day,
            },
            'risk': {
                'max_position_size_percent': self.max_position_size_percent,
                'stop_loss_percent': self.stop_loss_percent,
                'take_profit_percent': self.take_profit_percent,
                'cooldown_minutes': self.cooldown_minutes,
            }
        }


# Global configuration instance
config = SocialSignalsConfig()


def get_config() -> SocialSignalsConfig:
    """Get global configuration instance"""
    return config


def load_config_from_file(config_file: str = 'social_signals_config.json'):
    """Load configuration from JSON file"""
    import json
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update global config with loaded values
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            print(f"Configuration loaded from {config_file}")
        else:
            print(f"Configuration file {config_file} not found, using defaults")
            
    except Exception as e:
        print(f"Error loading configuration: {e}")


def save_config_to_file(config_file: str = 'social_signals_config.json'):
    """Save current configuration to JSON file"""
    import json
    
    try:
        config_data = config.to_dict()
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"Configuration saved to {config_file}")
        
    except Exception as e:
        print(f"Error saving configuration: {e}")


def print_config_summary():
    """Print a summary of current configuration"""
    print("=" * 60)
    print("SOCIAL SIGNALS CONFIGURATION SUMMARY")
    print("=" * 60)
    
    warnings = config.validate()
    
    print(f"Database: {config.mongodb_database_name}")
    print(f"Twitter Collection: {'ENABLED' if config.enable_twitter_collection else 'DISABLED'}")
    print(f"Reddit Collection: {'ENABLED' if config.enable_reddit_collection else 'DISABLED'}")
    print(f"RSS Collection: {'ENABLED' if config.enable_rss_collection else 'DISABLED'}")
    print(f"Auto-Execution: {'ENABLED' if config.enable_auto_execution else 'DISABLED'}")
    print(f"Min Confidence: {config.min_confidence_threshold:.1%}")
    print(f"Max Position Size: {config.max_position_size_percent}%")
    print(f"Collection Interval: {config.collection_interval_seconds}s")
    
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("=" * 60)


if __name__ == "__main__":
    # Test configuration
    print_config_summary()
