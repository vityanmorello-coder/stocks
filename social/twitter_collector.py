"""
Twitter Data Collector using Bearer Token
Real-time Twitter/X data collection for social signals
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import re

logger = logging.getLogger(__name__)


class TwitterDataCollector:
    """Collect Twitter data using Bearer Token authentication"""
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        # Trading-related keywords to monitor
        self.trading_keywords = [
            "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
            "forex", "eur/usd", "gbp/usd", "stocks", "trading", "market",
            "bullish", "bearish", "buy", "sell", "rally", "crash",
            "tesla", "tsla", "apple", "aapl", "sp500", "nasdaq"
        ]
        
        # Financial accounts to monitor
        self.financial_accounts = [
            "elonmusk", "cz_binance", "saylor", "michael_saylor", 
            "VitalikButerin", "brian_armstrong", "santamental",
            "cryptomanran", "woonomic", "crypto_birb", "TheCryptoDog"
        ]
    
    def search_tweets(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for tweets with specific query"""
        try:
            # Build search query
            search_query = f"{query} -is:retweet lang:en"
            
            params = {
                "query": search_query,
                "max_results": min(max_results, 100),  # Twitter API limit
                "tweet.fields": "created_at,public_metrics,lang,author_id",
                "expansions": "author_id",
                "user.fields": "username,name"
            }
            
            response = requests.get(
                f"{self.base_url}/tweets/search/recent",
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._process_tweet_data(data)
            else:
                logger.warning(f"Twitter API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return []
    
    def _process_tweet_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process Twitter API response into usable format"""
        tweets = []
        
        try:
            if "data" not in data:
                return tweets
            
            # Create user lookup
            users = {}
            if "includes" in data and "users" in data["includes"]:
                for user in data["includes"]["users"]:
                    users[user["id"]] = user
            
            for tweet in data["data"]:
                # Get user info
                author_id = tweet.get("author_id", "")
                user = users.get(author_id, {"username": "unknown", "name": "Unknown"})
                
                tweet_data = {
                    "id": tweet.get("id", ""),
                    "text": tweet.get("text", ""),
                    "created_at": tweet.get("created_at", ""),
                    "author": {
                        "id": author_id,
                        "username": user.get("username", "unknown"),
                        "name": user.get("name", "Unknown")
                    },
                    "public_metrics": tweet.get("public_metrics", {}),
                    "lang": tweet.get("lang", "en")
                }
                
                tweets.append(tweet_data)
                
        except Exception as e:
            logger.error(f"Error processing tweet data: {e}")
        
        return tweets
    
    def get_trading_tweets(self) -> List[Dict[str, Any]]:
        """Get recent tweets about trading and finance"""
        all_tweets = []
        
        # Search for different trading topics
        trading_queries = [
            "bitcoin OR btc OR cryptocurrency",
            "forex OR trading OR market",
            "tesla OR tsla OR apple OR aapl",
            "bullish OR bearish OR buy OR sell"
        ]
        
        for query in trading_queries:
            try:
                tweets = self.search_tweets(query, max_results=5)
                all_tweets.extend(tweets)
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error searching for '{query}': {e}")
                continue
        
        return all_tweets
    
    def get_tweets_from_accounts(self) -> List[Dict[str, Any]]:
        """Get recent tweets from financial accounts"""
        all_tweets = []
        
        # Get tweets from specific accounts (up to 2 tweets per account)
        for username in self.financial_accounts[:5]:  # Limit to avoid rate limits
            try:
                query = f"from:{username}"
                tweets = self.search_tweets(query, max_results=2)
                all_tweets.extend(tweets)
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error getting tweets from @{username}: {e}")
                continue
        
        return all_tweets
    
    def analyze_tweet_sentiment(self, tweet_text: str) -> float:
        """Simple sentiment analysis for tweets"""
        positive_words = [
            'bullish', 'up', 'rise', 'gain', 'profit', 'strong', 'growth', 
            'high', 'buy', 'rally', 'surge', 'jump', 'moon', 'pump', 
            'good', 'great', 'excellent', 'amazing', 'breakout'
        ]
        
        negative_words = [
            'bearish', 'down', 'fall', 'loss', 'weak', 'decline', 'low', 
            'sell', 'drop', 'crash', 'plunge', 'slump', 'dump', 'bad',
            'terrible', 'awful', 'horrible', 'collapse'
        ]
        
        text_lower = tweet_text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = pos_count + neg_count
        if total_words == 0:
            return 0.0
        
        return (pos_count - neg_count) / total_words
    
    def extract_asset_from_tweet(self, tweet_text: str) -> Optional[str]:
        """Extract trading asset from tweet text"""
        asset_keywords = {
            'BTC/USD': ['bitcoin', 'btc', '#btc', '#bitcoin'],
            'ETH/USD': ['ethereum', 'eth', '#eth', '#ethereum'],
            'EUR/USD': ['eur/usd', 'euro', '#eur', '#forex'],
            'GBP/USD': ['gbp/usd', 'pound', '#gbp'],
            'AAPL': ['apple', 'aapl', '#aapl', '$aapl'],
            'TSLA': ['tesla', 'tsla', '#tsla', '$tsla'],
            'SPX500': ['sp500', 's&p', '#sp500'],
            'OIL/USD': ['oil', 'crude', '#oil', 'wti']
        }
        
        text_lower = tweet_text.lower()
        
        for asset, keywords in asset_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return asset
        
        return None
    
    def generate_signals_from_tweets(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate trading signals from tweets"""
        signals = []
        
        for tweet in tweets:
            text = tweet.get("text", "")
            if not text:
                continue
            
            # Extract asset
            asset = self.extract_asset_from_tweet(text)
            if not asset:
                continue
            
            # Analyze sentiment
            sentiment = self.analyze_tweet_sentiment(text)
            
            # Calculate confidence based on engagement
            metrics = tweet.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)
            replies = metrics.get("reply_count", 0)
            
            # Higher engagement = higher confidence
            engagement_score = likes + (retweets * 2) + (replies * 1.5)
            confidence = min(0.95, 0.3 + (engagement_score / 100))  # Base 30% + engagement
            
            # Only include signals with reasonable sentiment and confidence
            if abs(sentiment) > 0.1 and confidence > 0.4:
                signal = {
                    'asset': asset,
                    'sentiment': sentiment,
                    'confidence': confidence,
                    'source': f"Twitter @{tweet['author']['username']}",
                    'timestamp': tweet.get("created_at", datetime.now().isoformat()),
                    'signal_type': 'bullish' if sentiment > 0 else 'bearish',
                    'title': f"Tweet from @{tweet['author']['username']}",
                    'summary': text[:200] + '...' if len(text) > 200 else text,
                    'engagement': {
                        'likes': likes,
                        'retweets': retweets,
                        'replies': replies
                    }
                }
                signals.append(signal)
        
        # Sort by confidence
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        return signals[:10]  # Return top 10 signals
    
    def get_twitter_signals(self) -> List[Dict[str, Any]]:
        """Main method to get trading signals from Twitter"""
        logger.info("Collecting Twitter data for trading signals...")
        
        try:
            # Get tweets from trading searches
            trading_tweets = self.get_trading_tweets()
            
            # Get tweets from financial accounts
            account_tweets = self.get_tweets_from_accounts()
            
            # Combine all tweets
            all_tweets = trading_tweets + account_tweets
            
            # Generate signals
            signals = self.generate_signals_from_tweets(all_tweets)
            
            logger.info(f"Generated {len(signals)} signals from {len(all_tweets)} tweets")
            return signals
            
        except Exception as e:
            logger.error(f"Error getting Twitter signals: {e}")
            return []


if __name__ == "__main__":
    # Test the Twitter collector
    import os
    
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
    if bearer_token:
        collector = TwitterDataCollector(bearer_token)
        signals = collector.get_twitter_signals()
        
        print("=== Twitter Trading Signals ===")
        for signal in signals:
            print(f"{signal['asset']}: {signal['signal_type']} ({signal['confidence']:.0%}) - {signal['source']}")
            print(f"  {signal['summary'][:100]}...")
            print()
    else:
        print("No TWITTER_BEARER_TOKEN found in environment variables")
