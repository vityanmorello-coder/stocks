"""
SOCIAL LISTENER
Multi-source ingestion: Reddit (PRAW), RSS/Atom news feeds, simulated feed.
Runs async; stores RawEvent objects in a shared thread-safe queue.
"""

import asyncio
import threading
import time
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from queue import Queue, Empty

from social.social_signals_engine import RawEvent

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# DEDUPLICATION CACHE
# ─────────────────────────────────────────────────────────────────────────────

class DedupeCache:
    """LRU-style seen-set limited to N entries."""

    def __init__(self, maxsize: int = 5000):
        self._seen = {}
        self._maxsize = maxsize

    def is_duplicate(self, key: str) -> bool:
        return key in self._seen

    def add(self, key: str):
        if len(self._seen) >= self._maxsize:
            # Remove oldest 20 %
            remove = list(self._seen.keys())[:self._maxsize // 5]
            for k in remove:
                self._seen.pop(k, None)
        self._seen[key] = True


# ─────────────────────────────────────────────────────────────────────────────
# RSS / NEWS LISTENER
# ─────────────────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    # Financial / general news
    ('Reuters Business',    'https://feeds.reuters.com/reuters/businessNews'),
    ('Reuters Top',         'https://feeds.reuters.com/reuters/topNews'),
    ('CNBC Markets',        'https://www.cnbc.com/id/20910258/device/rss/rss.html'),
    ('CNBC Finance',        'https://www.cnbc.com/id/10000664/device/rss/rss.html'),
    ('MarketWatch',         'https://feeds.marketwatch.com/marketwatch/topstories/'),
    ('Investing.com',       'https://www.investing.com/rss/news.rss'),
    ('CoinDesk',            'https://www.coindesk.com/arc/outboundfeeds/rss/'),
    ('CoinTelegraph',       'https://cointelegraph.com/rss'),
    ('Yahoo Finance',       'https://finance.yahoo.com/news/rssindex'),
    ('BBC Business',        'https://feeds.bbci.co.uk/news/business/rss.xml'),
    ('FT Markets',          'https://www.ft.com/markets?format=rss'),
    ('Bloomberg Markets',   'https://feeds.bloomberg.com/markets/news.rss'),
]


class RSSListener:
    """Polls RSS feeds and emits RawEvents."""

    def __init__(self, queue: Queue, dedupe: DedupeCache,
                 poll_interval: int = 120):
        self.queue = queue
        self.dedupe = dedupe
        self.poll_interval = poll_interval
        self._stop = threading.Event()

    def _fetch_feed(self, name: str, url: str) -> List[RawEvent]:
        events = []
        try:
            import feedparser
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title = getattr(entry, 'title', '')
                summary = getattr(entry, 'summary', '')
                link = getattr(entry, 'link', url)
                text = f"{title}. {summary}"

                # Timestamp
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    import calendar
                    ts = datetime.fromtimestamp(
                        calendar.timegm(entry.published_parsed), tz=timezone.utc
                    )
                else:
                    ts = datetime.now(timezone.utc)

                raw_id = hashlib.md5(link.encode()).hexdigest()[:10]
                if self.dedupe.is_duplicate(raw_id):
                    continue
                self.dedupe.add(raw_id)

                events.append(RawEvent(
                    source='rss',
                    author=name,
                    text=text.strip(),
                    url=link,
                    timestamp=ts,
                    engagement=0,
                    raw_id=raw_id,
                ))
        except Exception as e:
            logger.debug(f"[RSS] {name} fetch failed: {e}")
        return events

    def run(self):
        """Blocking loop — call in a daemon thread."""
        while not self._stop.is_set():
            for name, url in RSS_FEEDS:
                if self._stop.is_set():
                    break
                for evt in self._fetch_feed(name, url):
                    self.queue.put(evt)
                time.sleep(0.5)   # gentle pacing between feeds
            self._stop.wait(self.poll_interval)

    def stop(self):
        self._stop.set()


# ─────────────────────────────────────────────────────────────────────────────
# REDDIT LISTENER
# ─────────────────────────────────────────────────────────────────────────────

SUBREDDITS = [
    'wallstreetbets', 'stocks', 'investing', 'StockMarket',
    'CryptoCurrency', 'Bitcoin', 'ethfinance',
    'economics', 'worldnews', 'technology',
    'MachineLearning', 'artificial',
]


class RedditListener:
    """
    Polls Reddit via PRAW (needs REDDIT_CLIENT_ID / SECRET env vars).
    Falls back to RSS-based Reddit if PRAW is unavailable.
    """

    def __init__(self, queue: Queue, dedupe: DedupeCache,
                 poll_interval: int = 90,
                 client_id: str = '',
                 client_secret: str = '',
                 user_agent: str = 'QuantumTrade/1.0'):
        self.queue = queue
        self.dedupe = dedupe
        self.poll_interval = poll_interval
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._stop = threading.Event()
        self._reddit = None
        self._use_rss = False
        self._init_client()

    def _init_client(self):
        if not self.client_id:
            logger.info("[Reddit] No API creds — using RSS fallback")
            self._use_rss = True
            return
        try:
            import praw
            self._reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                read_only=True,
            )
        except Exception as e:
            logger.warning(f"[Reddit] PRAW init failed: {e} — using RSS")
            self._use_rss = True

    def _fetch_praw(self, subreddit_name: str) -> List[RawEvent]:
        events = []
        try:
            sub = self._reddit.subreddit(subreddit_name)
            for post in sub.hot(limit=20):
                raw_id = post.id
                if self.dedupe.is_duplicate(raw_id):
                    continue
                self.dedupe.add(raw_id)
                text = f"{post.title}. {post.selftext[:400]}"
                ts = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                events.append(RawEvent(
                    source='reddit',
                    author=f"r/{subreddit_name}",
                    text=text,
                    url=f"https://reddit.com{post.permalink}",
                    timestamp=ts,
                    engagement=post.score,
                    raw_id=raw_id,
                ))
        except Exception as e:
            logger.debug(f"[Reddit-PRAW] r/{subreddit_name}: {e}")
        return events

    def _fetch_rss(self, subreddit_name: str) -> List[RawEvent]:
        """Reddit exposes public RSS — no auth needed."""
        events = []
        try:
            import feedparser
            url = f"https://www.reddit.com/r/{subreddit_name}/hot.rss?limit=15"
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                raw_id = hashlib.md5(
                    getattr(entry, 'id', entry.title).encode()
                ).hexdigest()[:10]
                if self.dedupe.is_duplicate(raw_id):
                    continue
                self.dedupe.add(raw_id)
                title = getattr(entry, 'title', '')
                summary = getattr(entry, 'summary', '')[:400]
                text = f"{title}. {summary}"
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    import calendar
                    ts = datetime.fromtimestamp(
                        calendar.timegm(entry.published_parsed), tz=timezone.utc
                    )
                else:
                    ts = datetime.now(timezone.utc)
                events.append(RawEvent(
                    source='reddit',
                    author=f"r/{subreddit_name}",
                    text=text,
                    url=getattr(entry, 'link', ''),
                    timestamp=ts,
                    engagement=0,
                    raw_id=raw_id,
                ))
        except Exception as e:
            logger.debug(f"[Reddit-RSS] r/{subreddit_name}: {e}")
        return events

    def run(self):
        while not self._stop.is_set():
            for sub in SUBREDDITS:
                if self._stop.is_set():
                    break
                if self._use_rss:
                    evts = self._fetch_rss(sub)
                else:
                    evts = self._fetch_praw(sub)
                for evt in evts:
                    self.queue.put(evt)
                time.sleep(1)
            self._stop.wait(self.poll_interval)

    def stop(self):
        self._stop.set()


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATED FEED (for demo / development without API keys)
# ─────────────────────────────────────────────────────────────────────────────

SIMULATED_EVENTS = [
    ('X / Twitter', 'Elon Musk', "Just bought more Bitcoin. To the moon! 🚀 #BTC", 45000),
    ('X / Twitter', 'Elon Musk', "Tesla AI day announcement next week. Revolutionary robotics.", 38000),
    ('Reddit r/wallstreetbets', 'DegenTrader99', "NVDA earnings crushed it. AI demand unstoppable. Calls printing.", 12000),
    ('Reuters', 'Reuters Business', "BREAKING: Federal Reserve signals rate cut pause amid sticky inflation data.", 0),
    ('Reuters', 'Reuters Business', "NVIDIA reports record quarterly revenue, beats estimates by 25%", 0),
    ('CNBC', 'CNBC Markets', "Oil prices surge 4% after OPEC+ announces unexpected production cut", 0),
    ('Reddit r/CryptoCurrency', 'CryptoWhale', "Bitcoin ETF inflows hit record $800M in single day. Institutional FOMO real.", 8500),
    ('Bloomberg', 'Bloomberg Markets', "Trump proposes 50% tariff on Chinese semiconductors in new executive order", 0),
    ('X / Twitter', 'Sam Altman', "OpenAI GPT-5 will change everything. Deployment this quarter.", 29000),
    ('Reuters', 'Reuters Business', "Breaking: Russia-Ukraine ceasefire talks collapse. Oil jumps 3%.", 0),
    ('CNBC', 'CNBC Finance', "Amazon acquires AI startup for $4 billion, expanding cloud intelligence.", 0),
    ('Reddit r/stocks', 'ValueInvestor', "TSLA deliveries missed badly. Bad sign for Q4 guidance.", 6700),
    ('X / Twitter', 'Michael Saylor', "MicroStrategy adds 5,000 BTC to treasury. Total now 174,530 BTC.", 18000),
    ('MarketWatch', 'MarketWatch', "US CPI comes in hotter than expected at 3.4%. Dollar surges.", 0),
    ('CoinDesk', 'CoinDesk', "SEC approves first Ethereum spot ETF applications from BlackRock and Fidelity.", 0),
    ('X / Twitter', 'Donald Trump', "We will impose 100% tariffs on any country that moves away from the dollar!", 55000),
    ('Reuters', 'Reuters Business', "China threatens military action over Taiwan semiconductor dispute escalation.", 0),
    ('Reddit r/investing', 'QuietAnalyst', "Microsoft Azure revenue +35% YoY. OpenAI partnership clearly paying off.", 4200),
    ('CNBC', 'CNBC Markets', "Gold hits all-time high at $2,400 as investors flee to safety amid uncertainty.", 0),
    ('Bloomberg', 'Bloomberg Markets', "Oracle wins $8B US military AI cloud contract, stock up 12% premarket.", 0),
]


class SimulatedListener:
    """
    Emits synthetic events from the SIMULATED_EVENTS list.
    Cycles through them with a configurable delay — useful for demos.
    """

    def __init__(self, queue: Queue, dedupe: DedupeCache,
                 interval: float = 8.0, loop: bool = True):
        self.queue = queue
        self.dedupe = dedupe
        self.interval = interval
        self.loop = loop
        self._stop = threading.Event()

    def run(self):
        idx = 0
        while not self._stop.is_set():
            source, author, text, engagement = SIMULATED_EVENTS[idx % len(SIMULATED_EVENTS)]
            raw_id = hashlib.md5(f"sim_{idx}".encode()).hexdigest()[:10]
            if not self.dedupe.is_duplicate(raw_id):
                self.dedupe.add(raw_id)
                self.queue.put(RawEvent(
                    source=source,
                    author=author,
                    text=text,
                    url='',
                    timestamp=datetime.now(timezone.utc),
                    engagement=engagement,
                    raw_id=raw_id,
                ))
            idx += 1
            if not self.loop and idx >= len(SIMULATED_EVENTS):
                break
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()


# ─────────────────────────────────────────────────────────────────────────────
# LISTENER MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class ListenerManager:
    """
    Orchestrates all listeners and exposes a single shared queue.
    Call start() once; drain the queue at any time with get_events().
    """

    def __init__(self,
                 reddit_client_id: str = '',
                 reddit_secret: str = '',
                 use_simulated: bool = True,
                 use_rss: bool = True,
                 use_reddit: bool = True):
        self.queue: Queue = Queue(maxsize=2000)
        self.dedupe = DedupeCache()
        self._threads: List[threading.Thread] = []
        self._listeners = []

        if use_simulated:
            self._listeners.append(SimulatedListener(self.queue, self.dedupe))

        if use_rss:
            self._listeners.append(RSSListener(self.queue, self.dedupe))

        if use_reddit:
            self._listeners.append(
                RedditListener(self.queue, self.dedupe,
                               client_id=reddit_client_id,
                               client_secret=reddit_secret)
            )

    def start(self):
        for listener in self._listeners:
            t = threading.Thread(target=listener.run, daemon=True)
            t.start()
            self._threads.append(t)
        logger.info(f"[Listeners] Started {len(self._listeners)} listeners")

    def stop(self):
        for listener in self._listeners:
            listener.stop()

    def get_events(self, max_items: int = 50) -> List[RawEvent]:
        """Drain up to max_items from the queue (non-blocking)."""
        events = []
        for _ in range(max_items):
            try:
                events.append(self.queue.get_nowait())
            except Empty:
                break
        return events

    def qsize(self) -> int:
        return self.queue.qsize()
