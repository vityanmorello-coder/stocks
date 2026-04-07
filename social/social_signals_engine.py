"""
SOCIAL SIGNALS ENGINE
Core NLP, entity detection, sentiment analysis, and data structures.
All modules import from here.
"""

import re
import math
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RawEvent:
    """A single raw post / headline before processing."""
    source: str              # 'reddit', 'rss', 'twitter_sim'
    author: str
    text: str
    url: str
    timestamp: datetime
    engagement: int = 0      # upvotes / likes / shares
    raw_id: str = ''         # dedupe key


@dataclass
class TradingSignal:
    """A signal derived from a social/news event."""
    asset: str               # 'NVDA', 'BTC/USD', 'OIL/USD', 'SPX500'
    direction: str           # 'up' | 'down' | 'risk_off' | 'risk_on'
    confidence: float        # 0.0 – 1.0
    impact_type: str         # 'stock_up','stock_down','oil_up','crypto_up','risk_off'
    reason: str              # human-readable explanation


@dataclass
class ProcessedEvent:
    """A fully enriched event ready for the UI and signal engine."""
    event_id: str
    source: str
    author: str
    author_weight: float       # 1.0 = normal, 3.0 = high-impact person
    text: str
    headline: str              # cleaned, truncated headline
    url: str
    timestamp: datetime
    engagement: int

    # NLP results
    sentiment: str             # 'positive' | 'neutral' | 'negative'
    sentiment_score: float     # -1.0 to +1.0
    topic: str                 # 'AI', 'crypto', 'war', 'oil', 'economy', 'tech', 'earnings'
    urgency: str               # 'breaking' | 'trending' | 'normal'
    entities: List[str]        # detected names / companies / assets
    keywords: List[str]

    # Generated signals
    signals: List[TradingSignal] = field(default_factory=list)

    # Cluster membership (set by TrendEngine)
    cluster_id: Optional[str] = None
    is_trending: bool = False

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['signals'] = [asdict(s) for s in self.signals]
        return d


# ─────────────────────────────────────────────────────────────────────────────
# ENTITY CATALOGUE
# ─────────────────────────────────────────────────────────────────────────────

# People with HIGH market impact — weight > 1
HIGH_IMPACT_PEOPLE: Dict[str, float] = {
    'elon musk': 3.0, 'musk': 2.5,
    'donald trump': 3.0, 'trump': 3.0,
    'jerome powell': 2.5, 'powell': 2.5,
    'janet yellen': 2.0, 'yellen': 2.0,
    'sam altman': 2.0, 'altman': 2.0,
    'satoshi': 1.5,
    'michael saylor': 2.0, 'saylor': 1.8,
    'warren buffett': 2.0, 'buffett': 2.0,
    'xi jinping': 2.5, 'xi': 2.0,
    'joe biden': 2.0, 'biden': 2.0,
    'gary gensler': 2.0, 'gensler': 2.0,
    'cathie wood': 1.5,
    'mark zuckerberg': 1.5, 'zuckerberg': 1.5,
    'jeff bezos': 1.5, 'bezos': 1.5,
    'tim cook': 1.5,
    'jensen huang': 2.0, 'huang': 1.8,
    'larry ellison': 1.5,
}

# Companies mapped to their ticker symbols
COMPANY_TICKERS: Dict[str, str] = {
    'nvidia': 'NVDA', 'nvda': 'NVDA',
    'apple': 'AAPL', 'aapl': 'AAPL',
    'microsoft': 'MSFT', 'msft': 'MSFT',
    'google': 'GOOGL', 'alphabet': 'GOOGL', 'googl': 'GOOGL',
    'amazon': 'AMZN', 'amzn': 'AMZN',
    'meta': 'META', 'facebook': 'META',
    'tesla': 'TSLA', 'tsla': 'TSLA',
    'amd': 'AMD',
    'intel': 'INTC', 'intc': 'INTC',
    'openai': 'MSFT',       # OpenAI impact flows to Microsoft
    'anthropic': 'GOOGL',   # Anthropic backed by Google
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

# Asset keywords mapped to trading symbols
ASSET_KEYWORDS: Dict[str, str] = {
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

# Topic keyword sets
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    'AI': ['artificial intelligence', 'ai ', ' ai', 'chatgpt', 'llm', 'machine learning',
           'deep learning', 'openai', 'anthropic', 'gemini', 'gpt', 'neural', 'agi',
           'nvidia chips', 'gpu', 'data center', 'inference', 'training'],
    'crypto': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain', 'defi',
               'nft', 'solana', 'coinbase', 'sec crypto', 'binance', 'stablecoin',
               'halving', 'altcoin', 'web3', 'microstrategy'],
    'war': ['war', 'attack', 'missile', 'invasion', 'conflict', 'military', 'troops',
            'bombing', 'nato', 'sanctions', 'ukraine', 'russia', 'israel', 'hamas',
            'iran', 'taiwan', 'escalation', 'ceasefire', 'airstrike'],
    'oil': ['oil', 'crude', 'opec', 'petroleum', 'energy', 'natural gas', 'refinery',
            'pipeline', 'barrel', 'wti', 'brent', 'saudi', 'aramco'],
    'economy': ['inflation', 'interest rate', 'fed', 'federal reserve', 'gdp', 'recession',
                'unemployment', 'cpi', 'ppi', 'jobs report', 'rate cut', 'rate hike',
                'powell', 'yellen', 'treasury', 'bond yield', 'debt ceiling'],
    'tech': ['earnings', 'revenue', 'profit', 'guidance', 'product launch', 'acquisition',
             'merger', 'ipo', 'layoffs', 'hiring', 'semiconductor', 'chips', 'cloud',
             'regulation', 'antitrust', 'fine'],
    'earnings': ['earnings', 'quarterly', 'eps', 'revenue beat', 'revenue miss',
                 'guidance', 'forecast', 'outlook', 'q1', 'q2', 'q3', 'q4'],
}

# Urgency markers
BREAKING_MARKERS = [
    'breaking', 'just in', 'urgent', 'flash', 'alert', 'developing',
    'confirms', 'announced', 'emergency', 'exclusive',
]
TRENDING_MARKERS = [
    'trending', 'viral', 'surge', 'spike', 'soar', 'crash', 'plunge',
    'massive', 'record', 'historic', 'unprecedented',
]

# Sentiment word lists (lightweight, no external deps required)
POSITIVE_WORDS = [
    'surge', 'soar', 'rally', 'bull', 'bullish', 'gain', 'profit', 'beat',
    'exceed', 'record', 'strong', 'boom', 'rise', 'up', 'positive', 'good',
    'great', 'growth', 'buy', 'long', 'confidence', 'optimistic', 'approve',
    'launch', 'partnership', 'deal', 'win', 'success', 'breakthrough',
    'expand', 'upgrade', 'innovation', 'revenue beat', 'eps beat',
]
NEGATIVE_WORDS = [
    'crash', 'plunge', 'drop', 'fall', 'bear', 'bearish', 'loss', 'miss',
    'fail', 'decline', 'weak', 'bust', 'down', 'negative', 'bad', 'worse',
    'worry', 'concern', 'fear', 'sell', 'short', 'collapse', 'halt',
    'ban', 'sanction', 'fine', 'lawsuit', 'investigation', 'layoff',
    'cut', 'downgrade', 'recession', 'inflation', 'attack', 'war',
    'crisis', 'default', 'bankrupt',
]

INTENSIFIERS = ['very', 'extremely', 'massively', 'hugely', 'significantly',
                'sharply', 'dramatically', 'unexpectedly']


# ─────────────────────────────────────────────────────────────────────────────
# NLP PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

class NLPProcessor:
    """
    Lightweight NLP engine — no external ML deps required.
    Falls back gracefully if transformers/textblob not installed.
    """

    def __init__(self):
        self._transformer_pipeline = None
        self._try_load_transformer()

    def _try_load_transformer(self):
        """Optionally load HuggingFace sentiment pipeline for higher accuracy."""
        try:
            from transformers import pipeline
            self._transformer_pipeline = pipeline(
                'sentiment-analysis',
                model='ProsusAI/finbert',
                max_length=512,
                truncation=True,
            )
        except Exception:
            pass  # Use rule-based fallback

    def clean_text(self, text: str) -> str:
        """Remove URLs, HTML, excessive whitespace."""
        text = re.sub(r'http\S+|www\.\S+', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'[^\w\s.,!?\'"-]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def get_sentiment(self, text: str) -> Tuple[str, float]:
        """
        Returns (label, score) where label in ['positive','neutral','negative']
        and score in [-1.0, 1.0].
        Uses FinBERT if available, otherwise rule-based.
        """
        if self._transformer_pipeline:
            try:
                result = self._transformer_pipeline(text[:512])[0]
                label = result['label'].lower()
                score = result['score']
                if label == 'positive':
                    return 'positive', score
                elif label == 'negative':
                    return 'negative', -score
                else:
                    return 'neutral', 0.0
            except Exception:
                pass

        return self._rule_based_sentiment(text)

    def _rule_based_sentiment(self, text: str) -> Tuple[str, float]:
        lower = text.lower()
        pos = sum(1 for w in POSITIVE_WORDS if w in lower)
        neg = sum(1 for w in NEGATIVE_WORDS if w in lower)
        intensifier = sum(1 for w in INTENSIFIERS if w in lower)

        # Apply intensifier boost
        multiplier = 1 + intensifier * 0.3

        score = (pos - neg) * 0.15 * multiplier
        score = max(-1.0, min(1.0, score))

        if score > 0.05:
            return 'positive', score
        elif score < -0.05:
            return 'negative', score
        return 'neutral', score

    def detect_topic(self, text: str) -> str:
        """Return the dominant topic for the text."""
        lower = text.lower()
        scores: Dict[str, int] = {}
        for topic, keywords in TOPIC_KEYWORDS.items():
            scores[topic] = sum(1 for kw in keywords if kw in lower)
        if not scores or max(scores.values()) == 0:
            return 'general'
        return max(scores, key=scores.get)

    def detect_urgency(self, text: str) -> str:
        lower = text.lower()
        if any(m in lower for m in BREAKING_MARKERS):
            return 'breaking'
        if any(m in lower for m in TRENDING_MARKERS):
            return 'trending'
        return 'normal'

    def detect_entities(self, text: str) -> Tuple[List[str], float]:
        """
        Returns (entity_list, author_weight).
        entity_list: list of recognised entity names.
        author_weight: max impact weight found.
        """
        lower = text.lower()
        found_entities: List[str] = []
        max_weight = 1.0

        # People
        for name, weight in HIGH_IMPACT_PEOPLE.items():
            if name in lower:
                found_entities.append(name.title())
                if weight > max_weight:
                    max_weight = weight

        # Companies
        for company, ticker in COMPANY_TICKERS.items():
            if company in lower:
                label = f"{company.title()} ({ticker})"
                if label not in found_entities:
                    found_entities.append(label)

        # Assets
        for keyword, symbol in ASSET_KEYWORDS.items():
            if keyword in lower:
                if symbol not in found_entities:
                    found_entities.append(symbol)

        return found_entities[:8], max_weight  # cap at 8

    def extract_keywords(self, text: str) -> List[str]:
        """Return significant keywords found in text."""
        lower = text.lower()
        all_kw = (
            POSITIVE_WORDS + NEGATIVE_WORDS +
            BREAKING_MARKERS + TRENDING_MARKERS +
            [kw for kws in TOPIC_KEYWORDS.values() for kw in kws]
        )
        found = list({kw for kw in all_kw if kw in lower and len(kw) > 3})
        return sorted(found)[:12]

    def make_headline(self, text: str, max_len: int = 140) -> str:
        """Return a cleaned, truncated headline."""
        clean = self.clean_text(text)
        if len(clean) <= max_len:
            return clean
        # Try to cut at last space before max_len
        cut = clean[:max_len].rsplit(' ', 1)[0]
        return cut + '…'


# ─────────────────────────────────────────────────────────────────────────────
# EVENT PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

class EventProcessor:
    """
    Turns a RawEvent into a fully enriched ProcessedEvent.
    Thread-safe; stateless.
    """

    def __init__(self):
        self.nlp = NLPProcessor()

    def process(self, raw: RawEvent) -> ProcessedEvent:
        clean = self.nlp.clean_text(raw.text)
        headline = self.nlp.make_headline(clean)
        sentiment_label, sentiment_score = self.nlp.get_sentiment(clean)
        topic = self.nlp.detect_topic(clean)
        urgency = self.nlp.detect_urgency(clean)
        entities, author_weight = self.nlp.detect_entities(
            f"{raw.author} {clean}"
        )
        keywords = self.nlp.extract_keywords(clean)

        # Author weight from known high-impact people
        for name, weight in HIGH_IMPACT_PEOPLE.items():
            if name in raw.author.lower():
                author_weight = max(author_weight, weight)

        event_id = hashlib.md5(
            f"{raw.source}{raw.raw_id or raw.text[:60]}".encode()
        ).hexdigest()[:12]

        return ProcessedEvent(
            event_id=event_id,
            source=raw.source,
            author=raw.author,
            author_weight=author_weight,
            text=clean[:1000],
            headline=headline,
            url=raw.url,
            timestamp=raw.timestamp,
            engagement=raw.engagement,
            sentiment=sentiment_label,
            sentiment_score=sentiment_score,
            topic=topic,
            urgency=urgency,
            entities=entities,
            keywords=keywords,
        )

    def event_importance(self, evt: ProcessedEvent) -> float:
        """
        Composite importance score 0–100 used for sorting and highlighting.
        """
        score = 50.0

        # Urgency boost
        if evt.urgency == 'breaking':
            score += 25
        elif evt.urgency == 'trending':
            score += 12

        # Sentiment extremity
        score += abs(evt.sentiment_score) * 15

        # Author weight
        score += (evt.author_weight - 1.0) * 10

        # Engagement (log scale)
        if evt.engagement > 0:
            score += min(15, math.log10(evt.engagement + 1) * 5)

        # Entity richness
        score += min(10, len(evt.entities) * 2)

        return min(100.0, score)
