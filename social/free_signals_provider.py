"""
Free Social Signals Provider
Uses RSS feeds and Twitter API to generate trading signals
"""

import feedparser
import requests
import re
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import json
import time

logger = logging.getLogger(__name__)


class FreeSocialSignalsProvider:
    """Generate social signals from free RSS feeds and public APIs"""
    
    def __init__(self):
        self.rss_feeds = [
            # Financial News RSS Feeds (No API Key Required)
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "https://www.marketwatch.com/rss/topstories",
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://seekingalpha.com/feed/stock-market-news",
            "https://feeds.reuters.com/news/wealth",
            
            # Crypto News RSS Feeds
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://decrypt.co/feed",
            
            # Stock Specific RSS Feeds
            "https://seekingalpha.com/symbol/tsla/feed",
            "https://seekingalpha.com/symbol/aapl/feed",
            "https://seekingalpha.com/symbol/btc/feed"
        ]
        
        # Initialize Twitter collector if Bearer Token is available
        self.twitter_collector = None
        bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        if bearer_token:
            try:
                from social.twitter_collector import TwitterDataCollector
                self.twitter_collector = TwitterDataCollector(bearer_token)
                logger.info("Twitter collector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Twitter collector: {e}")
        else:
            logger.info("No TWITTER_BEARER_TOKEN found - using RSS only")
        
        self.asset_keywords = {
            'BTC/USD': ['bitcoin', 'btc', 'cryptocurrency', 'crypto'],
            'ETH/USD': ['ethereum', 'eth', 'ether'],
            'EUR/USD': ['euro', 'eur/usd', 'forex'],
            'GBP/USD': ['pound', 'gbp', 'sterling'],
            'AAPL': ['apple', 'aapl', 'iphone'],
            'TSLA': ['tesla', 'tsla', 'elon musk'],
            'OIL/USD': ['oil', 'crude', 'petroleum', 'wti'],
            'GOLD': ['gold', 'xau', 'precious metal'],
            'SPX500': ['s&p', 'sp500', 'stock market']
        }
    
    def fetch_rss_feeds(self) -> List[Dict[str, Any]]:
        """Fetch news from RSS feeds"""
        articles = []
        
        for feed_url in self.rss_feeds:
            try:
                logger.info(f"Fetching RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # Get 5 most recent articles
                    article = {
                        'title': entry.title,
                        'summary': getattr(entry, 'summary', ''),
                        'published': getattr(entry, 'published', ''),
                        'source': feed.feed.get('title', 'Unknown'),
                        'link': getattr(entry, 'link', '')
                    }
                    articles.append(article)
                    
                time.sleep(1)  # Be respectful to RSS servers
                
            except Exception as e:
                logger.warning(f"Failed to fetch RSS feed {feed_url}: {e}")
                continue
        
        return articles
    
    def analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis without external dependencies"""
        # Positive and negative word lists
        positive_words = ['bullish', 'up', 'rise', 'gain', 'profit', 'strong', 'growth', 'high', 'buy', 'rally', 'surge', 'jump']
        negative_words = ['bearish', 'down', 'fall', 'loss', 'weak', 'decline', 'low', 'sell', 'drop', 'crash', 'plunge', 'slump']
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = pos_count + neg_count
        if total_words == 0:
            return 0.0
        
        # Return sentiment between -1 and 1
        return (pos_count - neg_count) / total_words
    
    def extract_asset_from_text(self, text: str) -> str:
        """Extract which asset the text is talking about"""
        text_lower = text.lower()
        
        for asset, keywords in self.asset_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return asset
        
        return None
    
    def generate_signals_from_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate trading signals from news articles"""
        signals = []
        
        for article in articles:
            # Combine title and summary for analysis
            text_to_analyze = f"{article['title']} {article['summary']}"
            
            # Extract asset
            asset = self.extract_asset_from_text(text_to_analyze)
            if not asset:
                continue
            
            # Analyze sentiment
            sentiment = self.analyze_sentiment(text_to_analyze)
            
            # Calculate confidence based on sentiment strength
            confidence = abs(sentiment)
            
            # Only include signals with reasonable confidence
            if confidence > 0.2:
                signal = {
                    'asset': asset,
                    'sentiment': sentiment,
                    'confidence': min(confidence, 0.95),  # Cap at 95%
                    'source': article['source'],
                    'timestamp': datetime.now().isoformat(),
                    'signal_type': 'bullish' if sentiment > 0 else 'bearish',
                    'title': article['title'],
                    'summary': article['summary'][:200] + '...' if len(article['summary']) > 200 else article['summary']
                }
                signals.append(signal)
        
        return signals
    
    def get_free_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trading signals from free sources"""
        all_signals = []
        
        # 1. Get RSS signals
        logger.info("Generating signals from free RSS feeds...")
        try:
            articles = self.fetch_rss_feeds()
            rss_signals = self.generate_signals_from_articles(articles)
            all_signals.extend(rss_signals)
        except Exception as e:
            logger.warning(f"RSS signals failed: {e}")
        
        # 2. Get Twitter signals if available
        if self.twitter_collector:
            logger.info("Generating signals from Twitter...")
            try:
                twitter_signals = self.twitter_collector.get_twitter_signals()
                all_signals.extend(twitter_signals)
            except Exception as e:
                logger.warning(f"Twitter signals failed: {e}")
        
        # Sort by confidence and limit results
        all_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return all_signals[:limit]
    
    def get_mock_signals(self) -> List[Dict[str, Any]]:
        """Get mock signals for testing (enhanced version)"""
        return [
            {
                'asset': 'BTC/USD',
                'sentiment': 0.8,
                'confidence': 0.85,
                'source': 'CoinDesk RSS Feed',
                'timestamp': datetime.now().isoformat(),
                'signal_type': 'bullish',
                'title': 'Bitcoin Surges Past $68,000 as Institutional Interest Grows',
                'summary': 'Major financial institutions announce increased Bitcoin allocation strategies...'
            },
            {
                'asset': 'EUR/USD',
                'sentiment': -0.6,
                'confidence': 0.72,
                'source': 'Reuters Market News',
                'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat(),
                'signal_type': 'bearish',
                'title': 'ECB Signals Potential Rate Cut Amid Economic Concerns',
                'summary': 'European Central Bank officials hint at monetary policy easing...'
            },
            {
                'asset': 'AAPL',
                'sentiment': 0.9,
                'confidence': 0.91,
                'source': 'Seeking Alpha',
                'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat(),
                'signal_type': 'bullish',
                'title': 'Apple Stock Rises on Strong iPhone 15 Sales Numbers',
                'summary': 'Latest quarterly report shows better-than-expected iPhone sales growth...'
            },
            {
                'asset': 'OIL/USD',
                'sentiment': -0.4,
                'confidence': 0.68,
                'source': 'Bloomberg Markets',
                'timestamp': (datetime.now() - timedelta(minutes=45)).isoformat(),
                'signal_type': 'bearish',
                'title': 'Oil Prices Decline on Increased OPEC Production',
                'summary': 'OPEC announces production increase to meet global demand...'
            },
            {
                'asset': 'TSLA',
                'sentiment': 0.7,
                'confidence': 0.78,
                'source': 'MarketWatch',
                'timestamp': (datetime.now() - timedelta(minutes=60)).isoformat(),
                'signal_type': 'bullish',
                'title': 'Tesla Announces Record Deliveries in Q4',
                'summary': 'Electric vehicle maker reports highest quarterly deliveries ever...'
            }
        ]


def install_textblob():
    """Install required dependencies"""
    import subprocess
    import sys
    
    try:
        import textblob
        logger.info("TextBlob already installed")
    except ImportError:
        logger.info("Installing TextBlob...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "textblob"])
        
        # Download required TextBlob data
        try:
            from textblob.download_corpora import download_all
            download_all()
            logger.info("TextBlob data downloaded")
        except:
            logger.warning("Could not download TextBlob data - using fallback sentiment analysis")


if __name__ == "__main__":
    # Test the free signals provider
    install_textblob()
    
    provider = FreeSocialSignalsProvider()
    
    # Get mock signals
    mock_signals = provider.get_mock_signals()
    print("=== Mock Signals ===")
    for signal in mock_signals:
        print(f"{signal['asset']}: {signal['signal_type']} ({signal['confidence']:.0%}) - {signal['source']}")
    
    # Try to get real RSS signals
    try:
        real_signals = provider.get_free_signals(limit=5)
        print("\n=== Real RSS Signals ===")
        for signal in real_signals:
            print(f"{signal['asset']}: {signal['signal_type']} ({signal['confidence']:.0%}) - {signal['source']}")
    except Exception as e:
        print(f"RSS signals not available: {e}")
        print("This is normal if TextBlob is not fully installed")
