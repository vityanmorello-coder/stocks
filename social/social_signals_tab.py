"""
SOCIAL + MARKET SIGNALS TAB
Streamlit UI component — import and call render_social_signals_tab() from
the main dashboard.

Architecture:
  ListenerManager  →  EventProcessor  →  TrendEngine  →  SignalEngine
                    (raw events)       (NLP/entities)  (clustering)   (signals)

All state is stored in st.session_state under the 'social_*' namespace.
"""

import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

import streamlit as st

from social.social_signals_engine import ProcessedEvent, RawEvent, EventProcessor
from social.social_listener import ListenerManager
from social.trend_engine import TrendEngine
from intelligence.signal_engine import SignalEngine

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE INITIALISATION (singleton per Streamlit session)
# ─────────────────────────────────────────────────────────────────────────────

def _init_pipeline():
    """Create and start the listener pipeline once per session."""
    if 'social_pipeline_started' not in st.session_state:
        import os
        st.session_state.social_listener = ListenerManager(
            reddit_client_id=os.environ.get('REDDIT_CLIENT_ID', ''),
            reddit_secret=os.environ.get('REDDIT_CLIENT_SECRET', ''),
            use_simulated=True,
            use_rss=True,
            use_reddit=True,
        )
        st.session_state.social_listener.start()

        st.session_state.social_processor = EventProcessor()
        st.session_state.social_trend_engine = TrendEngine(
            window_minutes=90,
            trending_threshold=3,
        )
        st.session_state.social_signal_engine = SignalEngine()

        st.session_state.social_events: List[ProcessedEvent] = []
        st.session_state.social_last_refresh = datetime.now(timezone.utc)
        st.session_state.social_pipeline_started = True


def _poll_pipeline(max_new: int = 60):
    """
    Drain the listener queue, process events through NLP + signal engine,
    ingest into TrendEngine.  Caps the stored event list at 300.
    """
    listener: ListenerManager = st.session_state.social_listener
    processor: EventProcessor = st.session_state.social_processor
    trend_eng: TrendEngine = st.session_state.social_trend_engine
    sig_eng: SignalEngine = st.session_state.social_signal_engine

    raw_events: List[RawEvent] = listener.get_events(max_new)
    if not raw_events:
        return

    new_processed: List[ProcessedEvent] = []
    for raw in raw_events:
        try:
            evt = processor.process(raw)
            evt = sig_eng.generate_for_event(evt)
            new_processed.append(evt)
        except Exception as e:
            logger.debug(f"Process error: {e}")

    if new_processed:
        trend_eng.ingest(new_processed)
        trend_eng.mark_event_clusters(new_processed)
        # Prepend newest first
        st.session_state.social_events = (
            new_processed + st.session_state.social_events
        )[:300]

    st.session_state.social_last_refresh = datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# COLOUR HELPERS
# ─────────────────────────────────────────────────────────────────────────────

SENTIMENT_COLORS = {
    'positive': '#10b981',
    'neutral':  '#f59e0b',
    'negative': '#ef4444',
}
URGENCY_COLORS = {
    'breaking':  '#ef4444',
    'trending':  '#f59e0b',
    'normal':    '#64748b',
}
IMPACT_COLORS = {
    'stock_up':   '#10b981',
    'crypto_up':  '#8b5cf6',
    'oil_up':     '#f59e0b',
    'risk_off':   '#ef4444',
    'stock_down': '#ef4444',
    'risk_on':    '#3b82f6',
}
SOURCE_ICONS = {
    'reddit':   '👽',
    'rss':      '📰',
    'twitter_sim': '🐦',
    'x / twitter': '🐦',
}
TOPIC_ICONS = {
    'AI':       '🤖',
    'crypto':   '₿',
    'war':      '⚔️',
    'oil':      '🛢️',
    'economy':  '🏦',
    'tech':     '💻',
    'earnings': '📊',
    'general':  '🌐',
}


def _src_icon(source: str) -> str:
    lower = source.lower()
    for k, v in SOURCE_ICONS.items():
        if k in lower:
            return v
    return '📡'


def _confidence_bar(conf: float) -> str:
    pct = int(conf * 100)
    color = '#10b981' if pct >= 70 else '#f59e0b' if pct >= 45 else '#ef4444'
    filled = int(pct / 5)
    bar = '█' * filled + '░' * (20 - filled)
    return f'<span style="font-family:monospace;color:{color};">{bar}</span> <b style="color:{color};">{pct}%</b>'


# ─────────────────────────────────────────────────────────────────────────────
# EVENT CARD RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def _render_event_card(evt: ProcessedEvent, processor: EventProcessor,
                       show_signals: bool = True):
    """Render one enriched event as an HTML card."""
    importance = processor.event_importance(evt)
    is_high_impact = importance >= 70 or evt.author_weight >= 2.5

    sent_color = SENTIMENT_COLORS.get(evt.sentiment, '#64748b')
    urg_color = URGENCY_COLORS.get(evt.urgency, '#64748b')
    topic_icon = TOPIC_ICONS.get(evt.topic, '🌐')
    src_icon = _src_icon(evt.source)
    border_color = '#ef4444' if is_high_impact else '#1e293b'
    glow = f'box-shadow: 0 0 12px {border_color}40;' if is_high_impact else ''

    # Urgency badge
    urg_badge = (
        f'<span style="background:{urg_color};color:white;padding:1px 7px;'
        f'border-radius:4px;font-size:10px;font-weight:700;margin-left:6px;">'
        f'{evt.urgency.upper()}</span>'
    )

    # High-impact badge
    hi_badge = ''
    if is_high_impact:
        hi_badge = (
            '<span style="background:#ef4444;color:white;padding:1px 7px;'
            'border-radius:4px;font-size:10px;font-weight:800;margin-left:6px;">'
            '⚡ HIGH IMPACT</span>'
        )

    # Trending badge
    trend_badge = ''
    if evt.is_trending:
        trend_badge = (
            '<span style="background:#8b5cf6;color:white;padding:1px 7px;'
            'border-radius:4px;font-size:10px;font-weight:700;margin-left:6px;">'
            '🔥 TRENDING</span>'
        )

    # Entities
    entities_html = ''
    if evt.entities:
        tags = ''.join(
            f'<span style="background:rgba(59,130,246,0.15);color:#93c5fd;'
            f'padding:1px 6px;border-radius:3px;font-size:10px;margin-right:4px;">'
            f'{e}</span>'
            for e in evt.entities[:5]
        )
        entities_html = f'<div style="margin-top:5px;">{tags}</div>'

    # Time display
    age = datetime.now(timezone.utc) - evt.timestamp
    if age.total_seconds() < 60:
        time_str = 'just now'
    elif age.total_seconds() < 3600:
        time_str = f'{int(age.total_seconds() / 60)}m ago'
    else:
        time_str = evt.timestamp.strftime('%H:%M')

    card_html = f"""
    <div style="background:rgba(15,23,42,0.75);border:1px solid {border_color};
                border-radius:10px;padding:14px 16px;margin-bottom:10px;{glow}">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
            <span style="font-size:13px;">{src_icon}</span>
            <span style="font-size:11px;color:#64748b;font-weight:600;">{evt.source}</span>
            <span style="font-size:11px;color:#3b82f6;font-weight:700;">@{evt.author}</span>
            {urg_badge}{hi_badge}{trend_badge}
            <span style="font-size:10px;color:#475569;margin-left:auto;">{time_str}</span>
          </div>
          <div style="font-size:14px;color:#f1f5f9;font-weight:600;line-height:1.4;margin-bottom:6px;">
            {topic_icon} {evt.headline}
          </div>
          {entities_html}
          <div style="display:flex;gap:12px;margin-top:6px;flex-wrap:wrap;">
            <span style="font-size:11px;color:{sent_color};font-weight:700;">
              {'▲' if evt.sentiment=='positive' else '▼' if evt.sentiment=='negative' else '►'}
              {evt.sentiment.upper()} ({evt.sentiment_score:+.2f})
            </span>
            <span style="font-size:11px;color:#94a3b8;">Topic: <b style="color:#e2e8f0;">{evt.topic.upper()}</b></span>
            <span style="font-size:11px;color:#94a3b8;">Importance: <b style="color:#e2e8f0;">{importance:.0f}/100</b></span>
            {'<span style="font-size:11px;color:#f59e0b;">👤 High-impact author</span>' if evt.author_weight >= 2.0 else ''}
          </div>
        </div>
      </div>
    </div>"""

    st.markdown(card_html, unsafe_allow_html=True)

    # Trading signals below the card
    if show_signals and evt.signals:
        for sig in evt.signals[:3]:
            imp_color = IMPACT_COLORS.get(sig.impact_type, '#64748b')
            direction_arrow = '↑' if sig.direction in ('up', 'risk_on') else '↓'
            conf_bar = _confidence_bar(sig.confidence)
            sig_html = f"""
            <div style="background:rgba(15,23,42,0.5);border-left:3px solid {imp_color};
                        border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:6px;
                        margin-left:16px;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="color:{imp_color};font-weight:800;font-size:13px;">
                  {direction_arrow} {sig.asset}
                </span>
                <span style="font-size:10px;background:{imp_color}20;color:{imp_color};
                             padding:1px 6px;border-radius:3px;font-weight:700;">
                  {sig.impact_type.replace('_',' ').upper()}
                </span>
                <span style="font-size:11px;">{conf_bar}</span>
              </div>
              <div style="font-size:11px;color:#64748b;margin-top:3px;">{sig.reason[:120]}</div>
            </div>"""
            st.markdown(sig_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TAB RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_social_signals_tab(db=None, user: Dict = None):
    """
    Call this inside  `with tab_social:`  in the main dashboard.
    """
    _init_pipeline()
    _poll_pipeline()

    processor: EventProcessor = st.session_state.social_processor
    trend_eng: TrendEngine = st.session_state.social_trend_engine
    sig_eng: SignalEngine = st.session_state.social_signal_engine
    all_events: List[ProcessedEvent] = st.session_state.social_events

    # ── Header ────────────────────────────────────────────────────────────────
    last_ref = st.session_state.social_last_refresh
    age_s = int((datetime.now(timezone.utc) - last_ref).total_seconds())
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                margin-bottom:16px;flex-wrap:wrap;gap:8px;">
      <div>
        <span style="font-size:11px;color:#64748b;text-transform:uppercase;
                     letter-spacing:2px;font-weight:600;">
          🌍 GLOBAL SOCIAL + MARKET SIGNALS
        </span>
      </div>
      <div style="font-size:11px;color:#475569;">
        {len(all_events)} events · last refresh {age_s}s ago · queue: {st.session_state.social_listener.qsize()}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Controls row ──────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1, 1, 1, 1])
    with ctrl1:
        topic_filter = st.selectbox(
            "Topic Filter",
            ['All', 'AI', 'crypto', 'war', 'oil', 'economy', 'tech', 'earnings'],
            key='social_topic_filter',
        )
    with ctrl2:
        urgency_filter = st.selectbox(
            "Urgency",
            ['All', 'breaking', 'trending', 'normal'],
            key='social_urgency_filter',
        )
    with ctrl3:
        sentiment_filter = st.selectbox(
            "Sentiment",
            ['All', 'positive', 'neutral', 'negative'],
            key='social_sentiment_filter',
        )
    with ctrl4:
        min_conf = st.slider(
            "Min Signal Confidence %",
            0, 90, 40, step=5,
            key='social_min_conf',
        )

    refresh_col, _ = st.columns([1, 3])
    with refresh_col:
        if st.button("🔄 Refresh Feed", type="primary", key='social_refresh_btn'):
            _poll_pipeline(max_new=100)
            st.rerun()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = all_events
    if topic_filter != 'All':
        filtered = [e for e in filtered if e.topic == topic_filter]
    if urgency_filter != 'All':
        filtered = [e for e in filtered if e.urgency == urgency_filter]
    if sentiment_filter != 'All':
        filtered = [e for e in filtered if e.sentiment == sentiment_filter]

    # ── Metric summary row ────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    breaking = sum(1 for e in all_events if e.urgency == 'breaking')
    trending_evts = sum(1 for e in all_events if e.is_trending)
    hi_impact = sum(1 for e in all_events if e.author_weight >= 2.0)
    total_sigs = sum(len(e.signals) for e in all_events)
    pos_sigs = sum(1 for e in all_events for s in e.signals if s.direction == 'up')

    def _metric(col, label, value, color='#3b82f6'):
        col.markdown(f"""
        <div style="background:rgba(15,23,42,0.6);border:1px solid {color}30;
                    border-radius:8px;padding:10px 14px;text-align:center;">
          <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;">{label}</div>
          <div style="font-size:22px;font-weight:800;color:{color};">{value}</div>
        </div>""", unsafe_allow_html=True)

    _metric(m1, "Total Events", len(all_events), '#3b82f6')
    _metric(m2, "Breaking", breaking, '#ef4444')
    _metric(m3, "Trending", trending_evts, '#8b5cf6')
    _metric(m4, "High-Impact Authors", hi_impact, '#f59e0b')
    _metric(m5, "Trading Signals", total_sigs, '#10b981')

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ── MAIN LAYOUT: left feed + right sidebar ────────────────────────────────
    feed_col, side_col = st.columns([3, 2])

    # ── LEFT: Event Feed ──────────────────────────────────────────────────────
    with feed_col:
        st.markdown("""
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin-bottom:10px;">
          📡 Live Event Feed
        </div>""", unsafe_allow_html=True)

        display_events = sorted(
            filtered,
            key=lambda e: (
                e.urgency == 'breaking',
                e.is_trending,
                e.author_weight,
                e.timestamp,
            ),
            reverse=True
        )[:40]

        if not display_events:
            st.markdown("""
            <div style="text-align:center;padding:60px;color:#475569;">
              <div style="font-size:32px;">📡</div>
              <div style="font-size:14px;margin-top:8px;">Waiting for events…</div>
              <div style="font-size:11px;color:#334155;margin-top:4px;">
                Click "Refresh Feed" or wait for auto-poll
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            for evt in display_events:
                _render_event_card(evt, processor, show_signals=True)

    # ── RIGHT: Trending + Signals sidebar ─────────────────────────────────────
    with side_col:
        # ── Trending Topics ───────────────────────────────────────────────────
        st.markdown("""
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin-bottom:10px;">
          🔥 Trending Topics
        </div>""", unsafe_allow_html=True)

        trending_clusters = trend_eng.get_trending_clusters(top_n=8)
        if trending_clusters:
            for cluster in trending_clusters:
                sent_color = SENTIMENT_COLORS.get(cluster.dominant_sentiment, '#64748b')
                topic_icon = TOPIC_ICONS.get(cluster.topic, '🌐')
                bar_w = int(min(100, cluster.trend_score))
                cluster_sig = sig_eng.generate_cluster_signal(cluster)

                sig_html = ''
                if cluster_sig:
                    imp_color = IMPACT_COLORS.get(cluster_sig.impact_type, '#64748b')
                    arrow = '↑' if cluster_sig.direction in ('up', 'risk_on') else '↓'
                    sig_html = (
                        f'<div style="font-size:11px;color:{imp_color};font-weight:700;margin-top:4px;">'
                        f'{arrow} {cluster_sig.asset} — {int(cluster_sig.confidence*100)}% confidence</div>'
                    )

                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.6);border:1px solid #1e293b;
                            border-radius:8px;padding:10px 12px;margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:13px;font-weight:700;color:#f1f5f9;">
                      {topic_icon} {cluster.label}
                    </span>
                    <span style="font-size:10px;color:#475569;">{cluster.mention_count} mentions</span>
                  </div>
                  <div style="height:4px;background:#1e293b;border-radius:2px;margin:6px 0;">
                    <div style="width:{bar_w}%;height:100%;
                                background:linear-gradient(90deg,#3b82f6,#8b5cf6);
                                border-radius:2px;"></div>
                  </div>
                  <div style="display:flex;gap:8px;font-size:10px;color:#64748b;flex-wrap:wrap;">
                    <span style="color:{sent_color};">● {cluster.dominant_sentiment}</span>
                    <span>Sources: {', '.join(cluster.sources[:2])}</span>
                    <span>Score: {cluster.trend_score:.0f}</span>
                  </div>
                  {sig_html}
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#475569;font-size:13px;padding:20px 0;">No trending topics yet.</div>',
                        unsafe_allow_html=True)

        # ── Top Trading Signals ───────────────────────────────────────────────
        st.markdown("""
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;
                    letter-spacing:1px;font-weight:600;margin:16px 0 10px;">
          ⚡ Top Trading Signals
        </div>""", unsafe_allow_html=True)

        top_signals = sig_eng.get_top_signals(
            all_events, min_confidence=min_conf / 100, top_n=12
        )

        if top_signals:
            for item in top_signals:
                sig = item['signal']
                evt = item['event']
                imp_color = IMPACT_COLORS.get(sig.impact_type, '#64748b')
                arrow = '↑' if sig.direction in ('up', 'risk_on') else '↓'
                conf_pct = int(sig.confidence * 100)
                conf_color = '#10b981' if conf_pct >= 70 else '#f59e0b' if conf_pct >= 45 else '#ef4444'

                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.7);border:1px solid {imp_color}40;
                            border-left:3px solid {imp_color};border-radius:6px;
                            padding:10px 12px;margin-bottom:8px;">
                  <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div>
                      <span style="font-size:16px;font-weight:800;color:{imp_color};">
                        {arrow} {sig.asset}
                      </span>
                      <span style="font-size:10px;background:{imp_color}20;color:{imp_color};
                                   padding:1px 5px;border-radius:3px;margin-left:6px;font-weight:700;">
                        {sig.impact_type.replace('_',' ').upper()}
                      </span>
                    </div>
                    <div style="font-size:18px;font-weight:900;color:{conf_color};">
                      {conf_pct}%
                    </div>
                  </div>
                  <div style="font-size:10px;color:#64748b;margin-top:4px;">
                    {sig.reason[:100]}
                  </div>
                  <div style="font-size:10px;color:#334155;margin-top:2px;">
                    via {evt.source} · @{evt.author}
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="color:#475569;font-size:13px;">No signals above {min_conf}% confidence.</div>',
                        unsafe_allow_html=True)

    # ── Persist to MongoDB ────────────────────────────────────────────────────
    if db is not None and all_events:
        _persist_to_db(db, all_events[:20])


def _persist_to_db(db, events: List[ProcessedEvent]):
    """Save top events to MongoDB global_signals collection."""
    try:
        if not hasattr(db, 'db') or not hasattr(db, '_connected'):
            return
        col = db.db['global_signals']
        for evt in events:
            doc = evt.to_dict()
            col.update_one(
                {'event_id': evt.event_id},
                {'$set': doc},
                upsert=True,
            )
    except Exception as e:
        logger.debug(f"[MongoDB] global_signals save: {e}")
