"""
QuantumTrade Engine - Modular Broker API Client
================================================
Provides a uniform DataProvider interface backed by either:
  - OANDA v20 REST + Streaming API  (forex, indices, commodities)
  - Binance Spot/Futures REST + WebSocket  (crypto)
  - YFinance fallback  (all symbols, no credentials required)

Drop-in replacement for the yfinance calls inside fortrade_api_client.py.
All providers expose the same three methods:
    get_price(symbol)               -> {'bid', 'ask', 'mid', 'timestamp'}
    get_ohlcv(symbol, tf, limit)    -> List[{'timestamp','open','high','low','close','volume'}]
    get_order_book(symbol, depth)   -> {'bids': [...], 'asks': [...]}

WebSocket streaming is opt-in via start_stream() / stop_stream().
"""

from __future__ import annotations
import os, time, hmac, hashlib, logging, threading, json
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
from utils.data_cache import DataCache

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# SYMBOL MAPS
# ──────────────────────────────────────────────────────────────

OANDA_SYMBOL_MAP: Dict[str, str] = {
    'EUR/USD': 'EUR_USD', 'GBP/USD': 'GBP_USD', 'USD/JPY': 'USD_JPY',
    'USD/CHF': 'USD_CHF', 'AUD/USD': 'AUD_USD', 'NZD/USD': 'NZD_USD',
    'USD/CAD': 'USD_CAD', 'EUR/GBP': 'EUR_GBP', 'EUR/JPY': 'EUR_JPY',
    'GBP/JPY': 'GBP_JPY', 'AUD/JPY': 'AUD_JPY',
    'XAU/USD': 'XAU_USD', 'XAG/USD': 'XAG_USD',
    'SPX500': 'SPX500_USD', 'US30': 'US30_USD',
    'NAS100': 'NAS100_USD', 'UK100': 'UK100_GBP',
    'GER40': 'DE40_EUR', 'JPN225': 'JP225_USD',
    'OIL/USD': 'WTICO_USD', 'BRENT/USD': 'BCO_USD', 'GAS/USD': 'NATGAS_USD',
    'BTC/USD': 'BTC_USD', 'ETH/USD': 'ETH_USD',
}

BINANCE_SYMBOL_MAP: Dict[str, str] = {
    'BTC/USD': 'BTCUSDT', 'ETH/USD': 'ETHUSDT', 'BNB/USD': 'BNBUSDT',
    'XRP/USD': 'XRPUSDT', 'ADA/USD': 'ADAUSDT', 'SOL/USD': 'SOLUSDT',
    'DOGE/USD': 'DOGEUSDT', 'MATIC/USD': 'MATICUSDT',
}

YFINANCE_SYMBOL_MAP: Dict[str, str] = {
    'EUR/USD': 'EURUSD=X', 'GBP/USD': 'GBPUSD=X', 'USD/JPY': 'USDJPY=X',
    'USD/CHF': 'USDCHF=X', 'AUD/USD': 'AUDUSD=X', 'NZD/USD': 'NZDUSD=X',
    'USD/CAD': 'USDCAD=X', 'EUR/GBP': 'EURGBP=X', 'EUR/JPY': 'EURJPY=X',
    'GBP/JPY': 'GBPJPY=X', 'AUD/JPY': 'AUDJPY=X',
    'XAU/USD': 'GC=F', 'XAG/USD': 'SI=F', 'OIL/USD': 'CL=F',
    'BRENT/USD': 'BZ=F', 'GAS/USD': 'NG=F',
    'SPX500': '^GSPC', 'US30': '^DJI', 'NAS100': '^NDX',
    'UK100': '^FTSE', 'GER40': '^GDAXI', 'JPN225': '^N225',
    'BTC/USD': 'BTC-USD', 'ETH/USD': 'ETH-USD', 'BNB/USD': 'BNB-USD',
    'XRP/USD': 'XRP-USD', 'ADA/USD': 'ADA-USD', 'SOL/USD': 'SOL-USD',
    'DOGE/USD': 'DOGE-USD', 'MATIC/USD': 'MATIC-USD',
}

OANDA_TF_MAP = {
    '1m': 'M1', '5m': 'M5', '15m': 'M15', '30m': 'M30',
    '1h': 'H1', '4h': 'H4', '1d': 'D',
}

BINANCE_TF_MAP = {
    '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
    '1h': '1h', '4h': '4h', '1d': '1d',
}

YFINANCE_TF_MAP = {
    '1m': ('1m', '7d'), '5m': ('5m', '60d'), '15m': ('15m', '60d'),
    '30m': ('30m', '60d'), '1h': ('1h', '730d'), '4h': ('1h', '730d'),
    '1d': ('1d', '2y'),
}


# ──────────────────────────────────────────────────────────────
# RATE LIMITER (token bucket)
# ──────────────────────────────────────────────────────────────

class RateLimiter:
    """Thread-safe token-bucket rate limiter."""
    def __init__(self, calls_per_second: float = 2.0):
        self._rate = calls_per_second
        self._tokens = calls_per_second
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            self._tokens = min(self._rate, self._tokens + (now - self._last) * self._rate)
            self._last = now
            if self._tokens < 1:
                sleep_for = (1 - self._tokens) / self._rate
                time.sleep(sleep_for)
                self._tokens = 0
            else:
                self._tokens -= 1


# ──────────────────────────────────────────────────────────────
# ABSTRACT BASE
# ──────────────────────────────────────────────────────────────

class DataProvider(ABC):
    """Abstract interface all broker providers must implement."""

    def __init__(self):
        self._cache = DataCache(disk_dir='.cache')
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_active = False
        self._tick_callbacks: List[Callable] = []

    # ── Required ────────────────────────────────────────────

    @abstractmethod
    def get_price(self, symbol: str) -> Dict:
        """Return current bid/ask/mid."""

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        """Return list of OHLCV dicts, newest last."""

    @abstractmethod
    def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        """Return {'bids': [[price, size], ...], 'asks': [...]}."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if credentials are present and API is reachable."""

    # ── Optional streaming ──────────────────────────────────

    def start_stream(self, symbols: List[str], callback: Callable):
        """Subscribe to real-time tick stream. Override in subclasses."""
        self._tick_callbacks.append(callback)
        logger.warning(f"[{self.__class__.__name__}] Streaming not implemented")

    def stop_stream(self):
        self._stream_active = False
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=5)

    # ── Cache helpers ───────────────────────────────────────

    def _cache_get(self, symbol, tf): return self._cache.get(symbol, tf)
    def _cache_set(self, symbol, tf, data): self._cache.set(symbol, tf, data)


# ──────────────────────────────────────────────────────────────
# OANDA PROVIDER
# ──────────────────────────────────────────────────────────────

class OANDAProvider(DataProvider):
    """
    OANDA v20 REST + Streaming.
    Env vars: OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT (practice|live)
    """
    PRACTICE_URL = 'https://api-fxpractice.oanda.com/v3'
    LIVE_URL = 'https://api-fxtrade.oanda.com/v3'
    PRACTICE_STREAM = 'https://stream-fxpractice.oanda.com/v3'
    LIVE_STREAM = 'https://stream-fxtrade.oanda.com/v3'

    def __init__(self,
                 api_key: Optional[str] = None,
                 account_id: Optional[str] = None,
                 environment: str = 'practice'):
        super().__init__()
        self.api_key = api_key or os.getenv('OANDA_API_KEY', '')
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID', '')
        self.environment = environment or os.getenv('OANDA_ENVIRONMENT', 'practice')
        self.base_url = self.LIVE_URL if self.environment == 'live' else self.PRACTICE_URL
        self.stream_url = self.LIVE_STREAM if self.environment == 'live' else self.PRACTICE_STREAM
        self._rl = RateLimiter(calls_per_second=1.5)
        self._session = requests.Session()
        if self.api_key:
            self._session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept-Datetime-Format': 'UNIX',
            })

    def is_available(self) -> bool:
        if not self.api_key or not self.account_id:
            return False
        try:
            r = self._get(f'/accounts/{self.account_id}/summary')
            return 'account' in r
        except Exception:
            return False

    def _get(self, endpoint: str, params: Optional[Dict] = None, retries: int = 3) -> Dict:
        url = self.base_url + endpoint
        for attempt in range(retries):
            self._rl.acquire()
            try:
                r = self._session.get(url, params=params, timeout=10)
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 5))
                    logger.warning(f"[OANDA] Rate limited, sleeping {retry_after}s")
                    time.sleep(retry_after)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.Timeout:
                logger.warning(f"[OANDA] Timeout on attempt {attempt+1}")
                time.sleep(2 ** attempt)
            except requests.HTTPError as e:
                logger.error(f"[OANDA] HTTP {r.status_code}: {r.text[:200]}")
                raise
            except requests.RequestException as e:
                logger.warning(f"[OANDA] Request error attempt {attempt+1}: {e}")
                time.sleep(2 ** attempt)
        raise RuntimeError(f"[OANDA] {endpoint} failed after {retries} retries")

    @staticmethod
    def _to_oanda(symbol: str) -> str:
        return OANDA_SYMBOL_MAP.get(symbol, symbol.replace('/', '_'))

    def get_price(self, symbol: str) -> Dict:
        instr = self._to_oanda(symbol)
        try:
            data = self._get(f'/accounts/{self.account_id}/pricing',
                             params={'instruments': instr})
            p = data['prices'][0]
            bid = float(p['bids'][0]['price'])
            ask = float(p['asks'][0]['price'])
            return {'symbol': symbol, 'bid': bid, 'ask': ask,
                    'mid': (bid + ask) / 2,
                    'timestamp': datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            logger.error(f"[OANDA] get_price({symbol}): {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        cached = self._cache_get(symbol, timeframe)
        if cached is not None:
            return cached

        instr = self._to_oanda(symbol)
        gran = OANDA_TF_MAP.get(timeframe, 'M15')
        try:
            data = self._get(f'/instruments/{instr}/candles',
                             params={'count': limit, 'granularity': gran, 'price': 'M'})
            candles = []
            for c in data.get('candles', []):
                if not c.get('complete', True):
                    continue
                m = c['mid']
                candles.append({
                    'timestamp': int(float(c['time']) * 1000),
                    'open': float(m['o']),
                    'high': float(m['h']),
                    'low': float(m['l']),
                    'close': float(m['c']),
                    'volume': float(c.get('volume', 0)),
                })
            self._cache_set(symbol, timeframe, candles)
            logger.info(f"[OANDA] {symbol} {timeframe}: {len(candles)} candles")
            return candles
        except Exception as e:
            logger.error(f"[OANDA] get_ohlcv({symbol},{timeframe}): {e}")
            raise

    def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        instr = self._to_oanda(symbol)
        try:
            data = self._get(f'/instruments/{instr}/orderBook')
            book = data.get('orderBook', {})
            buckets = book.get('buckets', [])
            bids, asks = [], []
            for b in buckets[:depth * 2]:
                price = float(b['price'])
                long_pct = float(b.get('longCountPercent', 0))
                short_pct = float(b.get('shortCountPercent', 0))
                if long_pct > 0:
                    bids.append([price, long_pct])
                if short_pct > 0:
                    asks.append([price, short_pct])
            return {'symbol': symbol, 'bids': bids[:depth], 'asks': asks[:depth],
                    'timestamp': datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            logger.warning(f"[OANDA] order book unavailable for {symbol}: {e}")
            return {'symbol': symbol, 'bids': [], 'asks': []}

    def start_stream(self, symbols: List[str], callback: Callable):
        """
        Open OANDA pricing stream for real-time ticks.
        Runs in background thread with auto-reconnect.
        """
        self._tick_callbacks.append(callback)
        if self._stream_active:
            return
        self._stream_active = True
        instruments = ','.join(self._to_oanda(s) for s in symbols)

        def _run():
            backoff = 1
            while self._stream_active:
                try:
                    url = f"{self.stream_url}/accounts/{self.account_id}/pricing/stream"
                    with self._session.get(url, params={'instruments': instruments},
                                           stream=True, timeout=30) as resp:
                        resp.raise_for_status()
                        backoff = 1
                        for line in resp.iter_lines():
                            if not self._stream_active:
                                break
                            if not line:
                                continue
                            try:
                                msg = json.loads(line)
                                if msg.get('type') == 'PRICE':
                                    tick = {
                                        'symbol': msg['instrument'].replace('_', '/'),
                                        'bid': float(msg['bids'][0]['price']),
                                        'ask': float(msg['asks'][0]['price']),
                                        'timestamp': msg.get('time', ''),
                                    }
                                    for cb in self._tick_callbacks:
                                        cb(tick)
                            except (json.JSONDecodeError, KeyError):
                                pass
                except Exception as e:
                    if self._stream_active:
                        logger.warning(f"[OANDA] Stream error, reconnecting in {backoff}s: {e}")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 60)

        self._stream_thread = threading.Thread(target=_run, daemon=True, name='oanda-stream')
        self._stream_thread.start()
        logger.info(f"[OANDA] Stream started for: {symbols}")


# ──────────────────────────────────────────────────────────────
# BINANCE PROVIDER
# ──────────────────────────────────────────────────────────────

class BinanceProvider(DataProvider):
    """
    Binance Spot REST + WebSocket streams.
    Env vars: BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET (true|false)
    Supports spot market data + futures OHLCV via separate base URLs.
    """
    SPOT_URL = 'https://api.binance.com'
    FUTURES_URL = 'https://fapi.binance.com'
    TESTNET_URL = 'https://testnet.binance.vision'
    WS_BASE = 'wss://stream.binance.com:9443/ws'

    def __init__(self,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 testnet: bool = False,
                 use_futures: bool = False):
        super().__init__()
        self.api_key = api_key or os.getenv('BINANCE_API_KEY', '')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET', '')
        self.testnet = testnet or os.getenv('BINANCE_TESTNET', '').lower() == 'true'
        self.use_futures = use_futures
        if self.testnet:
            self.base_url = self.TESTNET_URL
        elif use_futures:
            self.base_url = self.FUTURES_URL
        else:
            self.base_url = self.SPOT_URL
        # Binance allows 1200 req/min weight = ~20/s, stay conservative
        self._rl = RateLimiter(calls_per_second=5.0)
        self._session = requests.Session()
        self._session.headers.update({'X-MBX-APIKEY': self.api_key})

    def is_available(self) -> bool:
        try:
            r = self._public_get('/api/v3/ping')
            return r == {}
        except Exception:
            return False

    def _public_get(self, endpoint: str, params: Optional[Dict] = None,
                    retries: int = 3) -> Dict:
        url = self.base_url + endpoint
        for attempt in range(retries):
            self._rl.acquire()
            try:
                r = self._session.get(url, params=params, timeout=10)
                if r.status_code == 429 or r.status_code == 418:
                    retry_after = int(r.headers.get('Retry-After', 10))
                    logger.warning(f"[BINANCE] Rate limited ({r.status_code}), sleeping {retry_after}s")
                    time.sleep(retry_after)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.Timeout:
                logger.warning(f"[BINANCE] Timeout attempt {attempt+1}")
                time.sleep(2 ** attempt)
            except requests.HTTPError as e:
                logger.error(f"[BINANCE] HTTP {r.status_code}: {r.text[:200]}")
                raise
            except requests.RequestException as e:
                logger.warning(f"[BINANCE] Request error attempt {attempt+1}: {e}")
                time.sleep(2 ** attempt)
        raise RuntimeError(f"[BINANCE] {endpoint} failed after {retries} retries")

    def _signed_get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        params = params or {}
        params['timestamp'] = int(time.time() * 1000)
        query = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
        sig = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        params['signature'] = sig
        return self._public_get(endpoint, params)

    @staticmethod
    def _to_binance(symbol: str) -> str:
        return BINANCE_SYMBOL_MAP.get(symbol, symbol.replace('/', '').upper())

    def get_price(self, symbol: str) -> Dict:
        bsym = self._to_binance(symbol)
        try:
            data = self._public_get('/api/v3/ticker/bookTicker', {'symbol': bsym})
            bid = float(data['bidPrice'])
            ask = float(data['askPrice'])
            return {'symbol': symbol, 'bid': bid, 'ask': ask,
                    'mid': (bid + ask) / 2,
                    'timestamp': datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            logger.error(f"[BINANCE] get_price({symbol}): {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        cached = self._cache_get(symbol, timeframe)
        if cached is not None:
            return cached

        bsym = self._to_binance(symbol)
        interval = BINANCE_TF_MAP.get(timeframe, '15m')
        try:
            raw = self._public_get('/api/v3/klines',
                                   {'symbol': bsym, 'interval': interval, 'limit': limit})
            candles = [{
                'timestamp': int(c[0]),
                'open': float(c[1]),
                'high': float(c[2]),
                'low': float(c[3]),
                'close': float(c[4]),
                'volume': float(c[5]),
            } for c in raw]
            self._cache_set(symbol, timeframe, candles)
            logger.info(f"[BINANCE] {symbol} {timeframe}: {len(candles)} candles")
            return candles
        except Exception as e:
            logger.error(f"[BINANCE] get_ohlcv({symbol},{timeframe}): {e}")
            raise

    def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        bsym = self._to_binance(symbol)
        limit = min(depth, 100)
        try:
            data = self._public_get('/api/v3/depth', {'symbol': bsym, 'limit': limit})
            bids = [[float(p), float(q)] for p, q in data.get('bids', [])]
            asks = [[float(p), float(q)] for p, q in data.get('asks', [])]
            return {'symbol': symbol, 'bids': bids, 'asks': asks,
                    'timestamp': datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            logger.warning(f"[BINANCE] order book error {symbol}: {e}")
            return {'symbol': symbol, 'bids': [], 'asks': []}

    def start_stream(self, symbols: List[str], callback: Callable):
        """
        Binance combined stream: <symbol>@bookTicker for real-time best bid/ask.
        Auto-reconnects with exponential backoff.
        """
        self._tick_callbacks.append(callback)
        if self._stream_active:
            return
        self._stream_active = True

        streams = '/'.join(f"{self._to_binance(s).lower()}@bookTicker" for s in symbols)
        ws_url = f"wss://stream.binance.com:9443/stream?streams={streams}"

        def _run():
            try:
                import websocket as ws_lib
            except ImportError:
                logger.error("[BINANCE] websocket-client not installed: pip install websocket-client")
                return

            backoff = 1
            while self._stream_active:
                try:
                    def on_message(ws, msg):
                        try:
                            data = json.loads(msg).get('data', {})
                            if 'b' in data and 'a' in data:
                                sym_raw = data.get('s', '')
                                # reverse map BTCUSDT -> BTC/USD
                                sym = next((k for k, v in BINANCE_SYMBOL_MAP.items()
                                            if v == sym_raw), sym_raw)
                                tick = {'symbol': sym,
                                        'bid': float(data['b']),
                                        'ask': float(data['a']),
                                        'timestamp': datetime.now(timezone.utc).isoformat()}
                                for cb in self._tick_callbacks:
                                    cb(tick)
                        except Exception:
                            pass

                    def on_error(ws, err):
                        logger.warning(f"[BINANCE] WS error: {err}")

                    def on_close(ws, *args):
                        logger.info("[BINANCE] WS closed")

                    wsa = ws_lib.WebSocketApp(ws_url, on_message=on_message,
                                              on_error=on_error, on_close=on_close)
                    wsa.run_forever(ping_interval=20, ping_timeout=10)
                    backoff = 1
                except Exception as e:
                    if self._stream_active:
                        logger.warning(f"[BINANCE] WS reconnect in {backoff}s: {e}")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 60)

        self._stream_thread = threading.Thread(target=_run, daemon=True, name='binance-ws')
        self._stream_thread.start()
        logger.info(f"[BINANCE] WebSocket stream started for: {symbols}")


# ──────────────────────────────────────────────────────────────
# YFINANCE FALLBACK PROVIDER
# ──────────────────────────────────────────────────────────────

class YFinanceProvider(DataProvider):
    """
    yfinance fallback — no credentials needed.
    Used when neither OANDA nor Binance keys are configured,
    or for non-crypto symbols not covered by Binance.
    """
    def __init__(self):
        super().__init__()
        self._rl = RateLimiter(calls_per_second=1.0)

    def is_available(self) -> bool:
        try:
            import yfinance  # noqa
            return True
        except ImportError:
            return False

    @staticmethod
    def _to_yf(symbol: str) -> str:
        return YFINANCE_SYMBOL_MAP.get(symbol, symbol)

    def get_price(self, symbol: str) -> Dict:
        import yfinance as yf
        self._rl.acquire()
        try:
            t = yf.Ticker(self._to_yf(symbol))
            hist = t.history(period='1d', interval='1m')
            if hist.empty:
                raise ValueError(f"No data for {symbol}")
            price = float(hist['Close'].iloc[-1])
            spread = price * 0.0005
            return {'symbol': symbol, 'bid': price, 'ask': price + spread,
                    'mid': price + spread / 2,
                    'timestamp': datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            logger.error(f"[YF] get_price({symbol}): {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        import yfinance as yf
        import pandas as pd

        cached = self._cache_get(symbol, timeframe)
        if cached is not None:
            return cached

        self._rl.acquire()
        interval, period = YFINANCE_TF_MAP.get(timeframe, ('15m', '60d'))
        try:
            t = yf.Ticker(self._to_yf(symbol))
            df = t.history(period=period, interval=interval)
            if df.empty:
                df = t.history(period='3mo', interval='1d')
            if df.empty:
                raise ValueError(f"Empty data for {symbol}")
            df = df.tail(limit)
            candles = []
            for idx, row in df.iterrows():
                ts_ms = int(idx.timestamp() * 1000) if hasattr(idx, 'timestamp') \
                    else int(pd.Timestamp(idx).timestamp() * 1000)
                candles.append({
                    'timestamp': ts_ms,
                    'open': float(row['Open']), 'high': float(row['High']),
                    'low': float(row['Low']), 'close': float(row['Close']),
                    'volume': float(row.get('Volume', 0)),
                })
            self._cache_set(symbol, timeframe, candles)
            logger.info(f"[YF] {symbol} {timeframe}: {len(candles)} candles")
            return candles
        except Exception as e:
            logger.error(f"[YF] get_ohlcv({symbol},{timeframe}): {e}")
            raise

    def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        return {'symbol': symbol, 'bids': [], 'asks': [],
                'note': 'yfinance does not provide order book data'}

    def start_stream(self, symbols: List[str], callback: Callable):
        logger.warning("[YF] Real-time streaming not supported. Use polling.")


# ──────────────────────────────────────────────────────────────
# PROVIDER FACTORY — auto-selects best available provider
# ──────────────────────────────────────────────────────────────

def _is_crypto(symbol: str) -> bool:
    return symbol in BINANCE_SYMBOL_MAP

def create_provider(symbol: str = '',
                    force: Optional[str] = None) -> DataProvider:
    """
    Auto-select the best provider for a given symbol.
    Override with force='oanda'|'binance'|'yfinance'.

    Priority:
      - Crypto symbols   → Binance (if key set) else YFinance
      - Forex/indices    → OANDA (if key set) else YFinance
      - force kwarg overrides everything
    """
    oanda_key = bool(os.getenv('OANDA_API_KEY'))
    binance_key = bool(os.getenv('BINANCE_API_KEY'))

    if force == 'oanda':
        return OANDAProvider()
    if force == 'binance':
        return BinanceProvider()
    if force == 'yfinance':
        return YFinanceProvider()

    if _is_crypto(symbol):
        if binance_key:
            return BinanceProvider()
        return YFinanceProvider()
    else:
        if oanda_key:
            return OANDAProvider()
        return YFinanceProvider()


class MultiProvider(DataProvider):
    """
    Umbrella provider: routes each symbol to the right sub-provider,
    with automatic fallback to YFinance on any error.

    This is the recommended class to use from fortrade_api_client.py.
    """
    def __init__(self):
        super().__init__()
        self._oanda: Optional[OANDAProvider] = None
        self._binance: Optional[BinanceProvider] = None
        self._yfinance = YFinanceProvider()
        self._lock = threading.Lock()

        if os.getenv('OANDA_API_KEY'):
            self._oanda = OANDAProvider()
            logger.info("[MultiProvider] OANDA provider loaded")
        if os.getenv('BINANCE_API_KEY'):
            self._binance = BinanceProvider()
            logger.info("[MultiProvider] Binance provider loaded")
        if not self._oanda and not self._binance:
            logger.info("[MultiProvider] No broker keys — using yfinance fallback")

    def _pick(self, symbol: str) -> DataProvider:
        if _is_crypto(symbol) and self._binance:
            return self._binance
        if not _is_crypto(symbol) and self._oanda:
            return self._oanda
        return self._yfinance

    def is_available(self) -> bool:
        return self._yfinance.is_available()

    def get_price(self, symbol: str) -> Dict:
        provider = self._pick(symbol)
        try:
            return provider.get_price(symbol)
        except Exception as e:
            logger.warning(f"[MultiProvider] {type(provider).__name__} failed for {symbol}, falling back: {e}")
            return self._yfinance.get_price(symbol)

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        provider = self._pick(symbol)
        try:
            return provider.get_ohlcv(symbol, timeframe, limit)
        except Exception as e:
            logger.warning(f"[MultiProvider] {type(provider).__name__} failed for {symbol}, falling back: {e}")
            return self._yfinance.get_ohlcv(symbol, timeframe, limit)

    def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        provider = self._pick(symbol)
        try:
            return provider.get_order_book(symbol, depth)
        except Exception as e:
            logger.warning(f"[MultiProvider] order book error {symbol}: {e}")
            return {'symbol': symbol, 'bids': [], 'asks': []}

    def start_stream(self, symbols: List[str], callback: Callable):
        """Start streams on all available providers for their respective symbol sets."""
        crypto_syms = [s for s in symbols if _is_crypto(s)]
        other_syms = [s for s in symbols if not _is_crypto(s)]
        if self._binance and crypto_syms:
            self._binance.start_stream(crypto_syms, callback)
        if self._oanda and other_syms:
            self._oanda.start_stream(other_syms, callback)

    def stop_stream(self):
        if self._binance:
            self._binance.stop_stream()
        if self._oanda:
            self._oanda.stop_stream()


# ──────────────────────────────────────────────────────────────
# MODULE-LEVEL SINGLETON
# ──────────────────────────────────────────────────────────────
_provider_instance: Optional[MultiProvider] = None
_provider_lock = threading.Lock()

def get_provider() -> MultiProvider:
    """Return (or create) the global MultiProvider singleton."""
    global _provider_instance
    with _provider_lock:
        if _provider_instance is None:
            _provider_instance = MultiProvider()
    return _provider_instance


# ──────────────────────────────────────────────────────────────
# EXAMPLE USAGE
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    p = get_provider()

    # Historical OHLCV
    candles = p.get_ohlcv('EUR/USD', '15m', limit=5)
    print("EUR/USD last 5 candles:")
    for c in candles:
        ts = datetime.fromtimestamp(c['timestamp'] / 1000)
        print(f"  {ts}  O={c['open']:.5f}  H={c['high']:.5f}  L={c['low']:.5f}  C={c['close']:.5f}")

    # Live price
    try:
        price = p.get_price('BTC/USD')
        print(f"\nBTC/USD  bid={price['bid']:.2f}  ask={price['ask']:.2f}")
    except Exception as e:
        print(f"Price fetch error: {e}")

    # Order book (Binance only, graceful on others)
    book = p.get_order_book('BTC/USD', depth=5)
    print(f"\nOrder book top bids: {book['bids'][:3]}")
    print(f"Order book top asks: {book['asks'][:3]}")

    # WebSocket stream (runs until Ctrl+C)
    def on_tick(tick):
        print(f"TICK  {tick['symbol']}  bid={tick['bid']}  ask={tick['ask']}")

    p.start_stream(['BTC/USD', 'EUR/USD'], on_tick)
    print("\nStreaming ticks (Ctrl+C to stop)...")
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        p.stop_stream()
        print("Stream stopped.")
