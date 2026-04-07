"""
Fortrade API Client
Handles all communication with Fortrade API
"""

import requests
import hmac
import hashlib
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import pandas as pd
from trading.broker_api_client import get_provider

logger = logging.getLogger(__name__)


class FortradeAPIClient:
    """
    Client for Fortrade API integration
    
    NOTE: This is a template implementation. You'll need to adjust
    based on actual Fortrade API documentation.
    """
    
    def __init__(self, api_key: str, api_secret: str, account_id: str, 
                 base_url: str, paper_trading: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_id = account_id
        self.base_url = base_url
        self.paper_trading = paper_trading
        self.session = requests.Session()
        
        # Paper trading simulation
        self.paper_balance = 100.0
        self.paper_positions = {}
        self.paper_trades = []
        
        logger.info(f"Fortrade API Client initialized (Paper Trading: {paper_trading})")
    
    def _generate_signature(self, endpoint: str, params: Dict) -> str:
        """Generate HMAC signature for API request"""
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{endpoint}{json.dumps(params, sort_keys=True)}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature, timestamp
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make authenticated API request"""
        if self.paper_trading:
            return self._simulate_request(method, endpoint, params)
        
        params = params or {}
        signature, timestamp = self._generate_signature(endpoint, params)
        
        headers = {
            'X-API-KEY': self.api_key,
            'X-SIGNATURE': signature,
            'X-TIMESTAMP': timestamp,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, json=params)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def _simulate_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Simulate API requests for paper trading"""
        params = params or {}
        
        if 'account' in endpoint and method == 'GET':
            return {
                'account_id': self.account_id,
                'balance': self.paper_balance,
                'currency': 'EUR',
                'equity': self.paper_balance,
                'margin_available': self.paper_balance * 0.9
            }
        
        elif 'positions' in endpoint and method == 'GET':
            return {'positions': list(self.paper_positions.values())}
        
        elif 'orders' in endpoint and method == 'POST':
            return self._simulate_order(params)
        
        elif 'orders' in endpoint and method == 'DELETE':
            order_id = params.get('order_id')
            if order_id in self.paper_positions:
                del self.paper_positions[order_id]
            return {'status': 'closed', 'order_id': order_id}
        
        elif 'market-data' in endpoint:
            return self._simulate_market_data(params)
        
        return {'status': 'success'}
    
    def _simulate_order(self, params: Dict) -> Dict:
        """Simulate order execution for paper trading"""
        order_id = f"PAPER_{int(time.time() * 1000)}"
        
        order = {
            'order_id': order_id,
            'symbol': params.get('symbol'),
            'side': params.get('side'),
            'quantity': params.get('quantity'),
            'entry_price': params.get('price', 1.0),
            'stop_loss': params.get('stop_loss'),
            'take_profit': params.get('take_profit'),
            'timestamp': datetime.now().isoformat(),
            'status': 'open'
        }
        
        self.paper_positions[order_id] = order
        self.paper_trades.append(order)
        
        logger.info(f"Paper trade executed: {order}")
        return order
    
    # Realistic base prices for all instrument types
    INSTRUMENT_PRICES = {
        'EUR/USD': {'price': 1.0850, 'volatility': 0.001, 'pip': 0.0001},
        'GBP/USD': {'price': 1.2650, 'volatility': 0.0012, 'pip': 0.0001},
        'USD/JPY': {'price': 149.50, 'volatility': 0.15, 'pip': 0.01},
        'AUD/USD': {'price': 0.6520, 'volatility': 0.0008, 'pip': 0.0001},
        'XAU/USD': {'price': 2340.00, 'volatility': 5.0, 'pip': 0.01},
        'XAG/USD': {'price': 29.50, 'volatility': 0.15, 'pip': 0.001},
        'OIL/USD': {'price': 78.50, 'volatility': 0.5, 'pip': 0.01},
        'AAPL':    {'price': 195.00, 'volatility': 1.5, 'pip': 0.01},
        'SPX500':  {'price': 5450.00, 'volatility': 15.0, 'pip': 0.01},
        'BTC/USD': {'price': 68500.00, 'volatility': 300.0, 'pip': 0.01},
    }
    
    def _get_instrument_info(self, symbol: str) -> dict:
        """Get price info for any instrument"""
        return self.INSTRUMENT_PRICES.get(symbol, {'price': 1.0, 'volatility': 0.001, 'pip': 0.0001})
    
    def _simulate_market_data(self, params: Dict) -> Dict:
        """Get current market data via broker_api_client (OANDA/Binance/yfinance)"""
        import random
        symbol = params.get('symbol', 'EUR/USD')

        try:
            result = get_provider().get_price(symbol)
            return {
                'symbol': symbol,
                'bid': result['bid'],
                'ask': result['ask'],
                'timestamp': result.get('timestamp', datetime.now().isoformat())
            }
        except Exception:
            pass

        # Fallback to simulated prices
        info = self._get_instrument_info(symbol)
        base = info['price']
        vol = info['volatility']
        spread = vol * 0.1
        bid = base + random.uniform(-vol, vol)
        ask = bid + spread
        return {'symbol': symbol, 'bid': bid, 'ask': ask,
                'timestamp': datetime.now().isoformat()}
    
    # ==================== PUBLIC API METHODS ====================
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        return self._make_request('GET', '/account')
    
    def get_balance(self) -> float:
        """Get current account balance"""
        account = self.get_account_info()
        return account.get('balance', 0.0)
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        response = self._make_request('GET', '/positions')
        return response.get('positions', [])
    
    def get_market_data(self, symbol: str) -> Dict:
        """Get current market data for symbol"""
        return self._make_request('GET', '/market-data', {'symbol': symbol})
    
    def get_historical_data(self, symbol: str, timeframe: str,
                           limit: int = 100) -> List[Dict]:
        """
        Get real historical OHLCV data via broker_api_client.
        Routes to OANDA (forex/indices), Binance (crypto), or yfinance (fallback).
        Results are cached per timeframe TTL.

        Args:
            symbol: Internal symbol ('EUR/USD', 'BTC/USD', 'AAPL', etc.)
            timeframe: '1m', '5m', '15m', '30m', '1h', '4h', '1d'
            limit: Number of candles to return
        """
        try:
            candles = get_provider().get_ohlcv(symbol, timeframe, limit)
            if candles:
                print(f"[REAL DATA] {symbol} {timeframe}: {len(candles)} candles, "
                      f"last={candles[-1]['close']:.5g}")
                return candles
        except Exception as e:
            logger.error(f"broker_api_client failed for {symbol}: {e}")

        return self._fallback_simulated_data(symbol, limit)
    
    def _fallback_simulated_data(self, symbol: str, limit: int) -> List[Dict]:
        """Fallback to simulated data if yfinance fails"""
        import random
        import math
        candles = []
        
        info = self._get_instrument_info(symbol)
        base_price = info['price']
        vol = info['volatility']
        trend = random.uniform(-0.3, 0.3)
        
        for i in range(limit):
            cycle = math.sin(i / 20.0) * vol * 0.5
            noise = random.gauss(0, vol)
            change = noise + cycle * 0.05 + trend * vol * 0.01
            open_price = base_price
            close_price = base_price + change
            high_price = max(open_price, close_price) + random.uniform(0, vol * 0.5)
            low_price = min(open_price, close_price) - random.uniform(0, vol * 0.5)
            base_vol = 5000 if '/' in symbol else 50000
            volume = random.uniform(base_vol * 0.5, base_vol * 1.5)
            
            candles.append({
                'timestamp': int(time.time() - (limit - i) * 300) * 1000,
                'open': round(open_price, 5 if vol < 1 else 2),
                'high': round(high_price, 5 if vol < 1 else 2),
                'low': round(low_price, 5 if vol < 1 else 2),
                'close': round(close_price, 5 if vol < 1 else 2),
                'volume': round(volume, 2)
            })
            base_price = close_price
        
        return candles
    
    def place_order(self, symbol: str, side: str, quantity: float,
                   stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None,
                   order_type: str = 'market') -> Dict:
        """
        Place a trading order
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            quantity: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
            order_type: 'market' or 'limit'
        """
        order_params = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'type': order_type,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        
        logger.info(f"Placing order: {order_params}")
        return self._make_request('POST', '/orders', order_params)
    
    def close_position(self, order_id: str) -> Dict:
        """Close an open position"""
        logger.info(f"Closing position: {order_id}")
        return self._make_request('DELETE', f'/orders', {'order_id': order_id})
    
    def modify_position(self, order_id: str, stop_loss: Optional[float] = None,
                       take_profit: Optional[float] = None) -> Dict:
        """Modify stop loss or take profit on existing position"""
        params = {'order_id': order_id}
        if stop_loss:
            params['stop_loss'] = stop_loss
        if take_profit:
            params['take_profit'] = take_profit
        
        return self._make_request('POST', '/orders/modify', params)
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get recent trade history"""
        if self.paper_trading:
            return self.paper_trades[-limit:]
        
        return self._make_request('GET', '/trades', {'limit': limit})
    
    def health_check(self) -> bool:
        """Check if API connection is healthy"""
        try:
            self.get_account_info()
            return True
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False
