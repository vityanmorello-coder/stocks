"""
TREND ENGINE
Detects trending topics, clusters related events, and flags spikes.
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, field

from social.social_signals_engine import ProcessedEvent

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TOPIC CLUSTER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TopicCluster:
    """A group of related events talking about the same topic."""
    cluster_id: str
    label: str                        # human-readable label, e.g. "NVIDIA Earnings"
    topic: str                        # canonical topic (AI, crypto, oil…)
    events: List[ProcessedEvent] = field(default_factory=list)
    mention_count: int = 0
    total_engagement: int = 0
    dominant_sentiment: str = 'neutral'
    sentiment_score: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    is_trending: bool = False
    trend_score: float = 0.0          # 0-100

    @property
    def sources(self) -> List[str]:
        return list({e.source for e in self.events})

    @property
    def top_entities(self) -> List[str]:
        counts = Counter(ent for e in self.events for ent in e.entities)
        return [e for e, _ in counts.most_common(5)]

    @property
    def age_minutes(self) -> float:
        if not self.first_seen:
            return 0
        delta = datetime.now(timezone.utc) - self.first_seen
        return delta.total_seconds() / 60


# ─────────────────────────────────────────────────────────────────────────────
# TREND ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class TrendEngine:
    """
    Maintains a sliding time-window of events and computes:
    1. Topic clusters — groups similar events together
    2. Trending topics — detects unusual mention frequency spikes
    3. Trend scores — ranks clusters by recency + volume + engagement
    """

    def __init__(self,
                 window_minutes: int = 60,
                 trending_threshold: int = 3,
                 spike_multiplier: float = 2.0):
        """
        window_minutes    : Only keep events within this window
        trending_threshold: Min events in a cluster to be 'trending'
        spike_multiplier  : A topic is spiking if recent rate > N×baseline rate
        """
        self.window_minutes = window_minutes
        self.trending_threshold = trending_threshold
        self.spike_multiplier = spike_multiplier

        self._clusters: Dict[str, TopicCluster] = {}
        self._baseline: Dict[str, float] = defaultdict(float)   # topic -> hourly rate
        self._history: List[ProcessedEvent] = []                # all events in window

    # ── Public API ───────────────────────────────────────────

    def ingest(self, events: List[ProcessedEvent]):
        """Add new events to the engine. Call this after processing raw events."""
        for evt in events:
            self._history.append(evt)
            self._assign_to_cluster(evt)
        self._prune_window()
        self._recalculate_trends()

    def get_trending_clusters(self, top_n: int = 10) -> List[TopicCluster]:
        """Return top N trending clusters sorted by trend_score."""
        clusters = [c for c in self._clusters.values() if c.is_trending]
        return sorted(clusters, key=lambda c: c.trend_score, reverse=True)[:top_n]

    def get_all_clusters(self, top_n: int = 20) -> List[TopicCluster]:
        clusters = sorted(
            self._clusters.values(),
            key=lambda c: c.trend_score,
            reverse=True
        )
        return clusters[:top_n]

    def get_recent_events(self, minutes: int = 30,
                          topic_filter: Optional[str] = None) -> List[ProcessedEvent]:
        """Return events from the last N minutes, optionally filtered by topic."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = [
            e for e in self._history
            if e.timestamp >= cutoff
            and (topic_filter is None or e.topic == topic_filter)
        ]
        return sorted(result, key=lambda e: e.timestamp, reverse=True)

    def mark_event_clusters(self, events: List[ProcessedEvent]) -> List[ProcessedEvent]:
        """Annotate events with cluster_id and is_trending fields."""
        for evt in events:
            for cid, cluster in self._clusters.items():
                if evt in cluster.events:
                    evt.cluster_id = cid
                    evt.is_trending = cluster.is_trending
                    break
        return events

    # ── Internal ─────────────────────────────────────────────

    def _cluster_key(self, evt: ProcessedEvent) -> str:
        """
        Determine which cluster an event belongs to.
        Uses topic + primary entity (or topic alone) as key.
        """
        primary_entity = evt.entities[0] if evt.entities else ''
        # Strip ticker suffix for cleaner key
        entity_clean = primary_entity.split('(')[0].strip().lower().replace(' ', '_')
        if entity_clean:
            return f"{evt.topic}__{entity_clean}"
        return f"{evt.topic}__general"

    def _cluster_label(self, topic: str, entity: str) -> str:
        """Human-readable cluster label."""
        if entity and entity != 'general':
            return f"{entity.replace('_', ' ').title()} — {topic.upper()}"
        return topic.upper()

    def _assign_to_cluster(self, evt: ProcessedEvent):
        key = self._cluster_key(evt)
        if key not in self._clusters:
            entity_part = key.split('__')[1] if '__' in key else ''
            self._clusters[key] = TopicCluster(
                cluster_id=key,
                label=self._cluster_label(evt.topic, entity_part),
                topic=evt.topic,
                first_seen=evt.timestamp,
            )

        cluster = self._clusters[key]
        if evt not in cluster.events:
            cluster.events.append(evt)
        cluster.mention_count = len(cluster.events)
        cluster.total_engagement += evt.engagement
        cluster.last_seen = evt.timestamp
        if not cluster.first_seen or evt.timestamp < cluster.first_seen:
            cluster.first_seen = evt.timestamp

        # Recalculate dominant sentiment
        scores = [e.sentiment_score for e in cluster.events]
        avg = sum(scores) / len(scores) if scores else 0.0
        cluster.sentiment_score = avg
        cluster.dominant_sentiment = (
            'positive' if avg > 0.05 else
            'negative' if avg < -0.05 else
            'neutral'
        )

    def _prune_window(self):
        """Remove events outside the sliding window."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.window_minutes)

        self._history = [e for e in self._history if e.timestamp >= cutoff]

        # Prune clusters
        for key in list(self._clusters.keys()):
            cluster = self._clusters[key]
            cluster.events = [e for e in cluster.events if e.timestamp >= cutoff]
            cluster.mention_count = len(cluster.events)
            if cluster.mention_count == 0:
                del self._clusters[key]

    def _recalculate_trends(self):
        """Compute trend_score and is_trending for all clusters."""
        now = datetime.now(timezone.utc)

        for cluster in self._clusters.values():
            if not cluster.events:
                cluster.is_trending = False
                cluster.trend_score = 0.0
                continue

            # Velocity: events per 10 minutes in the last 30 min
            recent_window = now - timedelta(minutes=30)
            recent_count = sum(
                1 for e in cluster.events if e.timestamp >= recent_window
            )
            velocity = recent_count / 3.0  # per 10 min

            # Engagement boost (log scale)
            eng = max(1, cluster.total_engagement)
            engagement_boost = math.log10(eng) * 5

            # Source diversity boost (multiple sources = more credible)
            source_boost = min(20, len(cluster.sources) * 6)

            # Breaking / urgency boost
            urgency_boost = sum(
                15 if e.urgency == 'breaking' else
                7 if e.urgency == 'trending' else 0
                for e in cluster.events
            )

            # Recency decay: full score if last event <5 min ago
            age_min = (now - cluster.last_seen).total_seconds() / 60 if cluster.last_seen else 60
            recency_factor = max(0.2, 1.0 - age_min / self.window_minutes)

            trend_score = (
                velocity * 15 +
                engagement_boost +
                source_boost +
                min(20, urgency_boost)
            ) * recency_factor

            cluster.trend_score = min(100.0, trend_score)
            cluster.is_trending = (
                cluster.mention_count >= self.trending_threshold or
                cluster.trend_score >= 25.0
            )
