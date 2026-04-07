"""
SIGNAL ENGINE
Converts processed social/news events into actionable trading signals.
Rule-based engine with confidence weighting.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from social.social_signals_engine import (
    ProcessedEvent, TradingSignal,
    COMPANY_TICKERS, ASSET_KEYWORDS, HIGH_IMPACT_PEOPLE,
)
from social.trend_engine import TopicCluster

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL RULES
# Each rule is (condition_fn, signal_factory_fn)
# condition_fn(evt) -> bool
# signal_factory_fn(evt) -> TradingSignal
# ─────────────────────────────────────────────────────────────────────────────

def _has_keyword(evt: ProcessedEvent, *words) -> bool:
    t = evt.text.lower()
    return any(w in t for w in words)

def _has_entity(evt: ProcessedEvent, *names) -> bool:
    lower_ents = [e.lower() for e in evt.entities]
    return any(n in e for n in names for e in lower_ents)

def _positive(evt: ProcessedEvent) -> bool:
    return evt.sentiment == 'positive'

def _negative(evt: ProcessedEvent) -> bool:
    return evt.sentiment == 'negative'

def _neutral_or_pos(evt: ProcessedEvent) -> bool:
    return evt.sentiment in ('positive', 'neutral')


SIGNAL_RULES: List[Tuple] = [

    # ── AI boom → NVDA up ────────────────────────────────────────────────────
    (
        lambda e: e.topic == 'AI' and _positive(e) and _has_entity(e, 'nvidia', 'nvda'),
        lambda e: TradingSignal(
            asset='NVDA', direction='up', impact_type='stock_up',
            confidence=_conf(e, 0.75),
            reason=f"AI positive + NVDA entity | {e.headline[:80]}"
        )
    ),

    # ── AI boom general → NAS100 up ──────────────────────────────────────────
    (
        lambda e: e.topic == 'AI' and _positive(e),
        lambda e: TradingSignal(
            asset='NAS100', direction='up', impact_type='stock_up',
            confidence=_conf(e, 0.55),
            reason=f"AI sector positive sentiment | {e.headline[:80]}"
        )
    ),

    # ── AI negative → NAS100 down ────────────────────────────────────────────
    (
        lambda e: e.topic == 'AI' and _negative(e),
        lambda e: TradingSignal(
            asset='NAS100', direction='down', impact_type='stock_down',
            confidence=_conf(e, 0.50),
            reason=f"AI sector negative | {e.headline[:80]}"
        )
    ),

    # ── Elon Musk + crypto positive → BTC up ─────────────────────────────────
    (
        lambda e: _has_entity(e, 'elon musk', 'musk') and
                  e.topic == 'crypto' and _positive(e),
        lambda e: TradingSignal(
            asset='BTC/USD', direction='up', impact_type='crypto_up',
            confidence=_conf(e, 0.80),
            reason=f"Elon Musk crypto bullish | {e.headline[:80]}"
        )
    ),

    # ── Musk + Tesla positive → TSLA up ──────────────────────────────────────
    (
        lambda e: _has_entity(e, 'elon musk', 'musk', 'tesla', 'tsla') and
                  _positive(e) and e.topic in ('tech', 'AI', 'earnings'),
        lambda e: TradingSignal(
            asset='TSLA', direction='up', impact_type='stock_up',
            confidence=_conf(e, 0.70),
            reason=f"Tesla/Musk positive news | {e.headline[:80]}"
        )
    ),

    # ── War / geopolitical tension → oil up + risk off ───────────────────────
    (
        lambda e: e.topic == 'war',
        lambda e: TradingSignal(
            asset='OIL/USD', direction='up', impact_type='oil_up',
            confidence=_conf(e, 0.70),
            reason=f"Geopolitical tension → oil premium | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'war',
        lambda e: TradingSignal(
            asset='XAU/USD', direction='up', impact_type='risk_off',
            confidence=_conf(e, 0.65),
            reason=f"Safe haven demand | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'war',
        lambda e: TradingSignal(
            asset='SPX500', direction='down', impact_type='risk_off',
            confidence=_conf(e, 0.60),
            reason=f"Risk-off on conflict | {e.headline[:80]}"
        )
    ),

    # ── Oil-specific news positive → oil up ──────────────────────────────────
    (
        lambda e: e.topic == 'oil' and _positive(e),
        lambda e: TradingSignal(
            asset='OIL/USD', direction='up', impact_type='oil_up',
            confidence=_conf(e, 0.65),
            reason=f"Oil positive news | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'oil' and _negative(e),
        lambda e: TradingSignal(
            asset='OIL/USD', direction='down', impact_type='stock_down',
            confidence=_conf(e, 0.60),
            reason=f"Oil negative news | {e.headline[:80]}"
        )
    ),

    # ── Crypto positive → BTC up ─────────────────────────────────────────────
    (
        lambda e: e.topic == 'crypto' and _positive(e),
        lambda e: TradingSignal(
            asset='BTC/USD', direction='up', impact_type='crypto_up',
            confidence=_conf(e, 0.60),
            reason=f"Crypto bullish sentiment | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'crypto' and _negative(e),
        lambda e: TradingSignal(
            asset='BTC/USD', direction='down', impact_type='stock_down',
            confidence=_conf(e, 0.60),
            reason=f"Crypto bearish sentiment | {e.headline[:80]}"
        )
    ),

    # ── Fed / economy positive → USD up ──────────────────────────────────────
    (
        lambda e: e.topic == 'economy' and
                  _has_keyword(e, 'rate hike', 'hawkish', 'inflation surge') and
                  _neutral_or_pos(e),
        lambda e: TradingSignal(
            asset='USD', direction='up', impact_type='risk_on',
            confidence=_conf(e, 0.60),
            reason=f"Hawkish Fed signal → USD strength | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'economy' and
                  _has_keyword(e, 'rate cut', 'dovish', 'recession', 'soft landing'),
        lambda e: TradingSignal(
            asset='XAU/USD', direction='up', impact_type='risk_off',
            confidence=_conf(e, 0.55),
            reason=f"Dovish/recession signal → gold | {e.headline[:80]}"
        )
    ),

    # ── Trump policy → tariff / dollar risk ──────────────────────────────────
    (
        lambda e: _has_entity(e, 'donald trump', 'trump') and
                  _has_keyword(e, 'tariff', 'trade war', 'sanction', 'china'),
        lambda e: TradingSignal(
            asset='SPX500', direction='down', impact_type='risk_off',
            confidence=_conf(e, 0.65),
            reason=f"Trump trade-war risk | {e.headline[:80]}"
        )
    ),

    # ── Earnings beat for specific companies ─────────────────────────────────
    (
        lambda e: e.topic == 'earnings' and _positive(e) and
                  _has_entity(e, 'nvidia', 'nvda'),
        lambda e: TradingSignal(
            asset='NVDA', direction='up', impact_type='stock_up',
            confidence=_conf(e, 0.82),
            reason=f"NVDA earnings beat | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'earnings' and _positive(e) and
                  _has_entity(e, 'apple', 'aapl'),
        lambda e: TradingSignal(
            asset='AAPL', direction='up', impact_type='stock_up',
            confidence=_conf(e, 0.75),
            reason=f"AAPL earnings beat | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'earnings' and _positive(e) and
                  _has_entity(e, 'microsoft', 'msft'),
        lambda e: TradingSignal(
            asset='MSFT', direction='up', impact_type='stock_up',
            confidence=_conf(e, 0.75),
            reason=f"MSFT earnings beat | {e.headline[:80]}"
        )
    ),
    (
        lambda e: e.topic == 'earnings' and _negative(e),
        lambda e: TradingSignal(
            asset=_primary_stock(e) or 'SPX500',
            direction='down', impact_type='stock_down',
            confidence=_conf(e, 0.60),
            reason=f"Earnings miss | {e.headline[:80]}"
        )
    ),

    # ── Tech regulation negative → NAS100 down ───────────────────────────────
    (
        lambda e: e.topic == 'tech' and _negative(e) and
                  _has_keyword(e, 'ban', 'regulation', 'antitrust', 'fine', 'probe'),
        lambda e: TradingSignal(
            asset='NAS100', direction='down', impact_type='stock_down',
            confidence=_conf(e, 0.55),
            reason=f"Tech regulatory headwind | {e.headline[:80]}"
        )
    ),

    # ── Gold / safe haven keywords ────────────────────────────────────────────
    (
        lambda e: _has_keyword(e, 'gold hits', 'gold surges', 'gold record',
                               'buy gold', 'gold rally'),
        lambda e: TradingSignal(
            asset='XAU/USD', direction='up', impact_type='risk_off',
            confidence=_conf(e, 0.60),
            reason=f"Gold bullish mention | {e.headline[:80]}"
        )
    ),
]


def _conf(evt: ProcessedEvent, base: float) -> float:
    """Adjust base confidence by author weight, sentiment strength, and urgency."""
    c = base
    c += (evt.author_weight - 1.0) * 0.08    # high-impact person boost
    c += abs(evt.sentiment_score) * 0.10      # stronger sentiment = higher conf
    if evt.urgency == 'breaking':
        c += 0.08
    elif evt.urgency == 'trending':
        c += 0.04
    if evt.is_trending:
        c += 0.05
    return round(min(0.97, max(0.10, c)), 3)


def _primary_stock(evt: ProcessedEvent) -> Optional[str]:
    """Extract the most-mentioned stock ticker from entities."""
    for ent in evt.entities:
        lower = ent.lower()
        for company, ticker in COMPANY_TICKERS.items():
            if company in lower:
                return ticker
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL ENGINE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class SignalEngine:
    """
    Evaluates every processed event against the rule set and attaches
    TradingSignal objects to the event.  Also generates cluster-level
    aggregated signals for trending topics.
    """

    def generate_for_event(self, evt: ProcessedEvent) -> ProcessedEvent:
        """Apply all rules to one event; mutates evt.signals in place."""
        evt.signals = []
        for condition, factory in SIGNAL_RULES:
            try:
                if condition(evt):
                    sig = factory(evt)
                    evt.signals.append(sig)
            except Exception as e:
                logger.debug(f"Rule error: {e}")
        return evt

    def generate_for_events(self, events: List[ProcessedEvent]) -> List[ProcessedEvent]:
        return [self.generate_for_event(e) for e in events]

    def generate_cluster_signal(self, cluster: TopicCluster) -> Optional[TradingSignal]:
        """
        Aggregate signals across a cluster to produce one consensus signal.
        Only returns a signal if cluster confidence is high enough.
        """
        if not cluster.events:
            return None

        all_signals: List[TradingSignal] = [
            s for e in cluster.events for s in e.signals
        ]
        if not all_signals:
            return None

        # Count by (asset, direction)
        from collections import Counter
        combo_counts: Dict[Tuple[str, str], float] = {}
        for s in all_signals:
            key = (s.asset, s.direction)
            combo_counts[key] = combo_counts.get(key, 0) + s.confidence

        best_key = max(combo_counts, key=combo_counts.get)
        best_conf = combo_counts[best_key] / len(cluster.events)  # average

        # Scale by cluster trending score
        best_conf = min(0.97, best_conf * (1 + cluster.trend_score / 200))

        if best_conf < 0.30:
            return None

        asset, direction = best_key
        impact_map = {
            ('BTC/USD', 'up'): 'crypto_up',
            ('OIL/USD', 'up'): 'oil_up',
            ('XAU/USD', 'up'): 'risk_off',
            ('SPX500', 'down'): 'risk_off',
        }
        impact = impact_map.get((asset, direction),
                                'stock_up' if direction == 'up' else 'stock_down')

        return TradingSignal(
            asset=asset,
            direction=direction,
            impact_type=impact,
            confidence=round(best_conf, 3),
            reason=f"Cluster consensus: {cluster.label} ({cluster.mention_count} events)",
        )

    def get_top_signals(self, events: List[ProcessedEvent],
                        min_confidence: float = 0.40,
                        top_n: int = 15) -> List[Dict]:
        """
        Return a flat sorted list of the most confident signals from all events.
        """
        results = []
        for evt in events:
            for sig in evt.signals:
                if sig.confidence >= min_confidence:
                    results.append({
                        'signal': sig,
                        'event': evt,
                        'composite_score': sig.confidence * evt.author_weight,
                    })

        results.sort(key=lambda x: x['composite_score'], reverse=True)
        return results[:top_n]
