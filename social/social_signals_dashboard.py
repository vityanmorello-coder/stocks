"""
Social Signals Dashboard v1.0 - Streamlit Integration
Real-time social media and market signals visualization for QuantumTrade.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional
import re

# Import social signals components
from social.social_signals_engine import ProcessedEvent, TradingSignal
from social.social_signals_database import db_manager
from social.trend_engine import TopicCluster
from social.social_listener import SocialListener
from intelligence.signal_engine import SignalEngine
from social.social_signals_engine import EventProcessor


class SocialSignalsDashboard:
    """Main dashboard class for social signals visualization"""
    
    def __init__(self):
        self.signal_engine = SignalEngine()
        self.event_processor = EventProcessor()
        self.social_listener = None
        self._db_connected = False
        
    async def initialize(self):
        """Initialize dashboard components"""
        try:
            # Connect to database
            self._db_connected = await db_manager.initialize()
            
            # Initialize social listener (optional, for real-time updates)
            if st.session_state.get('enable_real_time', False):
                self.social_listener = SocialListener()
                
            return True
        except Exception as e:
            st.error(f"Failed to initialize social signals: {e}")
            return False
    
    def render_social_signals_tab(self):
        """Render the main Social + Market Signals tab"""
        st.markdown("""
        <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; 
                    letter-spacing: 2px; margin-bottom: 16px; font-weight: 600;">
            Social + Market Signals
        </div>
        """, unsafe_allow_html=True)
        
        # Configuration controls
        self._render_controls()
        
        # Main metrics row
        self._render_metrics()
        
        # Main content columns
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Events feed
            self._render_events_feed()
            
        with col2:
            # Trending clusters
            self._render_trending_clusters()
        
        # Trading signals section
        st.markdown("---")
        self._render_trading_signals()
        
        # Analytics section
        st.markdown("---")
        self._render_analytics()
    
    def _render_controls(self):
        """Render dashboard controls and filters"""
        with st.container():
            ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
            
            with ctrl1:
                # Topic filter
                topics = ['All', 'AI', 'crypto', 'war', 'oil', 'economy', 'tech', 'earnings', 'general']
                selected_topic = st.selectbox("Filter by Topic", topics, key='social_topic_filter')
                st.session_state['social_topic_filter'] = selected_topic if selected_topic != 'All' else None
            
            with ctrl2:
                # Source filter
                sources = ['All', 'reddit', 'rss', 'twitter_sim']
                selected_source = st.selectbox("Filter by Source", sources, key='social_source_filter')
                st.session_state['social_source_filter'] = selected_source if selected_source != 'All' else None
            
            with ctrl3:
                # Time range
                time_ranges = ['Last Hour', 'Last 6 Hours', 'Last 24 Hours', 'Last 3 Days']
                time_range = st.selectbox("Time Range", time_ranges, key='social_time_range')
                hours_map = {'Last Hour': 1, 'Last 6 Hours': 6, 'Last 24 Hours': 24, 'Last 3 Days': 72}
                st.session_state['social_hours'] = hours_map[time_range]
            
            with ctrl4:
                # Real-time toggle
                enable_real_time = st.checkbox("Real-time Updates", key='enable_real_time')
                if enable_real_time and not self.social_listener:
                    st.info("Real-time mode requires API credentials")
    
    def _render_metrics(self):
        """Render key metrics cards"""
        try:
            # Get analytics data
            analytics = asyncio.run(db_manager.db.get_analytics()) if self._db_connected else {}
            
            m1, m2, m3, m4 = st.columns(4)
            
            with m1:
                st.markdown("""
                <div class="metric-card blue">
                    <div class="metric-label">EVENTS PROCESSED</div>
                    <div class="metric-value">{}</div>
                </div>
                """.format(analytics.get('events_count', 0)), unsafe_allow_html=True)
            
            with m2:
                st.markdown("""
                <div class="metric-card green">
                    <div class="metric-label">SIGNALS GENERATED</div>
                    <div class="metric-value">{}</div>
                </div>
                """.format(analytics.get('signals_count', 0)), unsafe_allow_html=True)
            
            with m3:
                st.markdown("""
                <div class="metric-card purple">
                    <div class="metric-label">TRENDING TOPICS</div>
                    <div class="metric-value">{}</div>
                </div>
                """.format(analytics.get('trending_clusters', 0)), unsafe_allow_html=True)
            
            with m4:
                # Calculate high-impact events
                high_impact = asyncio.run(self._get_high_impact_count()) if self._db_connected else 0
                st.markdown("""
                <div class="metric-card red">
                    <div class="metric-label">HIGH IMPACT</div>
                    <div class="metric-value">{}</div>
                </div>
                """.format(high_impact), unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error loading metrics: {e}")
    
    async def _get_high_impact_count(self) -> int:
        """Get count of high-impact events"""
        try:
            events = await db_manager.db.get_recent_events(limit=1000, hours=24)
            high_impact = sum(1 for e in events if e.get('author_weight', 1.0) > 1.5 or e.get('urgency') == 'breaking')
            return high_impact
        except:
            return 0
    
    def _render_events_feed(self):
        """Render the real-time events feed"""
        st.markdown("### Real-time Events Feed")
        
        try:
            # Get events with filters
            topic_filter = st.session_state.get('social_topic_filter')
            source_filter = st.session_state.get('social_source_filter')
            hours = st.session_state.get('social_hours', 24)
            
            events = asyncio.run(db_manager.db.get_recent_events(
                limit=50, 
                hours=hours,
                topic_filter=topic_filter,
                source_filter=source_filter
            )) if self._db_connected else self._get_demo_events()
            
            if not events:
                st.info("No events found. Configure social media APIs to see real data.")
                return
            
            # Sort by importance score
            events.sort(key=lambda x: self._calculate_importance(x), reverse=True)
            
            # Render event cards
            for i, event in enumerate(events[:20]):  # Show top 20
                self._render_event_card(event, i)
                
        except Exception as e:
            st.error(f"Error loading events: {e}")
    
    def _render_event_card(self, event: Dict, index: int):
        """Render a single event card"""
        try:
            # Extract event data
            source = event.get('source', 'unknown')
            author = event.get('author', 'unknown')
            headline = event.get('headline', event.get('text', ''))[:140]
            timestamp = event.get('timestamp', '')
            sentiment = event.get('sentiment', 'neutral')
            topic = event.get('topic', 'general')
            urgency = event.get('urgency', 'normal')
            engagement = event.get('engagement', 0)
            author_weight = event.get('author_weight', 1.0)
            entities = event.get('entities', [])
            signals = event.get('signals', [])
            
            # Determine colors based on sentiment and urgency
            sentiment_colors = {
                'positive': '#10b981',
                'negative': '#ef4444', 
                'neutral': '#f59e0b'
            }
            sentiment_color = sentiment_colors.get(sentiment, '#f59e0b')
            
            urgency_badges = {
                'breaking': 'BREAKING',
                'trending': 'TRENDING',
                'normal': ''
            }
            urgency_badge = urgency_badges.get(urgency, '')
            
            # Calculate importance score
            importance = self._calculate_importance(event)
            
            # Card HTML
            card_html = f'''
            <div class="signal-card-pro" style="border-left: 4px solid {sentiment_color};">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <span style="font-size: 11px; color: #64748b; text-transform: uppercase;">{source.upper()}</span>
                        {f'<span style="margin-left: 8px; padding: 2px 8px; background: rgba(239, 68, 68, 0.2); color: #ef4444; border-radius: 4px; font-size: 10px; font-weight: 600;">{urgency_badge}</span>' if urgency_badge else ''}
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 10px; color: #64748b;">{self._format_timestamp(timestamp)}</div>
                        <div style="font-size: 11px; color: {sentiment_color}; font-weight: 600;">{sentiment.upper()}</div>
                    </div>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <div style="font-weight: 600; color: #f1f5f9; margin-bottom: 4px;">{headline}</div>
                    <div style="font-size: 12px; color: #94a3b8;">by {author}</div>
                </div>
                
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
                    <span style="padding: 2px 6px; background: rgba(59, 130, 246, 0.2); color: #3b82f6; border-radius: 4px; font-size: 10px;">{topic.upper()}</span>
                    <span style="font-size: 10px; color: #64748b;">Engagement: {engagement}</span>
                    <span style="font-size: 10px; color: #64748b;">Impact: {author_weight:.1f}x</span>
                    <span style="font-size: 10px; color: #64748b;">Score: {importance:.0f}</span>
                </div>
            '''
            
            # Add entities if any
            if entities:
                entity_tags = ', '.join(entities[:3])  # Show top 3
                card_html += f'''
                <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">
                    <strong>Entities:</strong> {entity_tags}
                </div>
                '''
            
            # Add trading signals if any
            if signals:
                signal_count = len(signals)
                card_html += f'''
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                '''
                for signal in signals[:2]:  # Show top 2 signals
                    asset = signal.get('asset', '')
                    direction = signal.get('direction', '')
                    confidence = signal.get('confidence', 0)
                    direction_color = '#10b981' if direction == 'up' else '#ef4444'
                    
                    card_html += f'''
                    <span style="padding: 4px 8px; background: rgba(16, 185, 129, 0.1); border: 1px solid {direction_color}; color: {direction_color}; border-radius: 6px; font-size: 10px; font-weight: 600;">
                        {asset} {direction.upper()} {confidence:.0%}
                    </span>
                    '''
                
                if signal_count > 2:
                    card_html += f'<span style="font-size: 10px; color: #64748b;">+{signal_count - 2} more</span>'
                
                card_html += '</div>'
            
            card_html += '</div>'
            
            st.markdown(card_html, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error rendering event card: {e}")
    
    def _render_trending_clusters(self):
        """Render trending topics section"""
        st.markdown("### Trending Topics")
        
        try:
            clusters = asyncio.run(db_manager.db.get_trending_clusters(limit=10)) if self._db_connected else self._get_demo_clusters()
            
            if not clusters:
                st.info("No trending topics detected.")
                return
            
            for cluster in clusters:
                self._render_cluster_card(cluster)
                
        except Exception as e:
            st.error(f"Error loading trending clusters: {e}")
    
    def _render_cluster_card(self, cluster: Dict):
        """Render a single trending cluster card"""
        try:
            label = cluster.get('label', 'Unknown Topic')
            topic = cluster.get('topic', 'general')
            mention_count = cluster.get('mention_count', 0)
            trend_score = cluster.get('trend_score', 0)
            dominant_sentiment = cluster.get('dominant_sentiment', 'neutral')
            sources = cluster.get('sources', [])
            top_entities = cluster.get('top_entities', [])
            
            # Color based on sentiment
            sentiment_colors = {
                'positive': '#10b981',
                'negative': '#ef4444',
                'neutral': '#f59e0b'
            }
            sentiment_color = sentiment_colors.get(dominant_sentiment, '#f59e0b')
            
            # Trend score color
            trend_color = '#10b981' if trend_score > 50 else '#f59e0b' if trend_score > 25 else '#ef4444'
            
            cluster_html = f'''
            <div class="analysis-box" style="border-left: 4px solid {trend_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #f1f5f9; font-size: 14px;">{label}</div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span style="padding: 2px 6px; background: rgba(59, 130, 246, 0.2); color: #3b82f6; border-radius: 4px; font-size: 10px;">{topic.upper()}</span>
                        <span style="font-size: 12px; color: {trend_color}; font-weight: 600;">Score: {trend_score:.0f}</span>
                    </div>
                </div>
                
                <div style="display: flex; gap: 16px; margin-bottom: 8px;">
                    <div>
                        <span style="font-size: 10px; color: #64748b;">MENTIONS</span><br>
                        <span style="font-size: 16px; font-weight: 700; color: #f1f5f9;">{mention_count}</span>
                    </div>
                    <div>
                        <span style="font-size: 10px; color: #64748b;">SENTIMENT</span><br>
                        <span style="font-size: 14px; font-weight: 600; color: {sentiment_color};">{dominant_sentiment.upper()}</span>
                    </div>
                    <div>
                        <span style="font-size: 10px; color: #64748b;">SOURCES</span><br>
                        <span style="font-size: 12px; color: #94a3b8;">{', '.join(sources)}</span>
                    </div>
                </div>
            '''
            
            if top_entities:
                cluster_html += f'''
                <div style="font-size: 11px; color: #64748b;">
                    <strong>Key Entities:</strong> {', '.join(top_entities[:3])}
                </div>
                '''
            
            cluster_html += '</div>'
            
            st.markdown(cluster_html, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error rendering cluster card: {e}")
    
    def _render_trading_signals(self):
        """Render trading signals section"""
        st.markdown("### Trading Signals")
        
        try:
            # Get top signals
            signals = asyncio.run(db_manager.db.get_top_signals(limit=20, min_confidence=0.3)) if self._db_connected else self._get_demo_signals()
            
            if not signals:
                st.info("No trading signals generated yet.")
                return
            
            # Signal statistics
            sig1, sig2, sig3, sig4 = st.columns(4)
            
            with sig1:
                bullish_signals = sum(1 for s in signals if s.get('direction') == 'up')
                st.metric("Bullish Signals", bullish_signals)
            
            with sig2:
                bearish_signals = sum(1 for s in signals if s.get('direction') == 'down')
                st.metric("Bearish Signals", bearish_signals)
            
            with sig3:
                avg_confidence = sum(s.get('confidence', 0) for s in signals) / len(signals) if signals else 0
                st.metric("Avg Confidence", f"{avg_confidence:.1%}")
            
            with sig4:
                high_confidence = sum(1 for s in signals if s.get('confidence', 0) > 0.7)
                st.metric("High Confidence", high_confidence)
            
            # Signals table
            signals_df = []
            for signal in signals[:15]:
                signals_df.append({
                    'Asset': signal.get('asset', ''),
                    'Direction': signal.get('direction', '').upper(),
                    'Confidence': f"{signal.get('confidence', 0):.1%}",
                    'Impact': signal.get('impact_type', ''),
                    'Reason': signal.get('reason', '')[:50] + '...' if len(signal.get('reason', '')) > 50 else signal.get('reason', ''),
                    'Time': self._format_timestamp(signal.get('timestamp', ''))
                })
            
            if signals_df:
                df = pd.DataFrame(signals_df)
                
                # Color code the direction column
                def color_direction(val):
                    color = 'background-color: rgba(16, 185, 129, 0.2)' if val == 'UP' else 'background-color: rgba(239, 68, 68, 0.2)'
                    return color
                
                styled_df = df.style.applymap(color_direction, subset=['Direction'])
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Error loading trading signals: {e}")
    
    def _render_analytics(self):
        """Render analytics section"""
        st.markdown("### Analytics")
        
        try:
            analytics = asyncio.run(db_manager.db.get_analytics()) if self._db_connected else {}
            
            if not analytics:
                st.info("No analytics data available.")
                return
            
            # Topic distribution chart
            topic_dist = analytics.get('topic_distribution', [])
            if topic_dist:
                topics = [item['_id'] for item in topic_dist]
                counts = [item['count'] for item in topic_dist]
                
                fig_topic = go.Figure(data=[
                    go.Bar(x=topics, y=counts, marker_color='#3b82f6')
                ])
                fig_topic.update_layout(
                    title="Topic Distribution",
                    xaxis_title="Topic",
                    yaxis_title="Count",
                    height=300,
                    template='plotly_dark',
                    paper_bgcolor='#0a0e17',
                    plot_bgcolor='#0a0e17',
                    font=dict(color='#94a3b8')
                )
                st.plotly_chart(fig_topic, use_container_width=True)
            
            # Asset distribution chart
            asset_dist = analytics.get('asset_distribution', [])
            if asset_dist:
                assets = [item['_id'] for item in asset_dist]
                counts = [item['count'] for item in asset_dist]
                
                fig_asset = go.Figure(data=[
                    go.Pie(labels=assets, values=counts, hole=0.3)
                ])
                fig_asset.update_layout(
                    title="Signal Distribution by Asset",
                    height=300,
                    template='plotly_dark',
                    paper_bgcolor='#0a0e17',
                    font=dict(color='#94a3b8')
                )
                st.plotly_chart(fig_asset, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error loading analytics: {e}")
    
    def _calculate_importance(self, event: Dict) -> float:
        """Calculate importance score for an event"""
        try:
            score = 50.0
            
            # Urgency boost
            urgency = event.get('urgency', 'normal')
            if urgency == 'breaking':
                score += 25
            elif urgency == 'trending':
                score += 12
            
            # Sentiment extremity
            sentiment_score = event.get('sentiment_score', 0)
            score += abs(sentiment_score) * 15
            
            # Author weight
            author_weight = event.get('author_weight', 1.0)
            score += (author_weight - 1.0) * 10
            
            # Engagement (log scale)
            engagement = event.get('engagement', 0)
            if engagement > 0:
                score += min(15, (engagement ** 0.5) * 0.5)
            
            # Entity richness
            entities = event.get('entities', [])
            score += min(10, len(entities) * 2)
            
            return min(100.0, score)
            
        except:
            return 50.0
    
    def _format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display"""
        try:
            if not timestamp:
                return ''
            
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo)
            diff = now - dt
            
            if diff.total_seconds() < 3600:  # Less than 1 hour
                minutes = int(diff.total_seconds() / 60)
                return f"{minutes}m ago" if minutes > 0 else "Just now"
            elif diff.total_seconds() < 86400:  # Less than 1 day
                hours = int(diff.total_seconds() / 3600)
                return f"{hours}h ago"
            else:
                days = int(diff.total_seconds() / 86400)
                return f"{days}d ago"
                
        except:
            return timestamp[:19] if timestamp else ''
    
    def _get_demo_events(self) -> List[Dict]:
        """Get demo events for when database is not available"""
        return [
            {
                'source': 'reddit',
                'author': 'elonmusk',
                'headline': 'Tesla AI breakthrough announced - Full Self-Driving beta expanded',
                'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat(),
                'sentiment': 'positive',
                'topic': 'AI',
                'urgency': 'breaking',
                'engagement': 1500,
                'author_weight': 3.0,
                'entities': ['Tesla (TSLA)', 'NVIDIA (NVDA)'],
                'signals': [
                    {'asset': 'TSLA', 'direction': 'up', 'confidence': 0.85, 'impact_type': 'stock_up'},
                    {'asset': 'NVDA', 'direction': 'up', 'confidence': 0.70, 'impact_type': 'stock_up'}
                ]
            },
            {
                'source': 'rss',
                'author': 'Reuters',
                'headline': 'Fed signals potential rate pause amid economic uncertainty',
                'timestamp': (datetime.now() - timedelta(minutes=45)).isoformat(),
                'sentiment': 'neutral',
                'topic': 'economy',
                'urgency': 'trending',
                'engagement': 800,
                'author_weight': 2.0,
                'entities': ['Federal Reserve', 'USD'],
                'signals': [
                    {'asset': 'XAU/USD', 'direction': 'up', 'confidence': 0.65, 'impact_type': 'risk_off'}
                ]
            }
        ]
    
    def _get_demo_clusters(self) -> List[Dict]:
        """Get demo clusters for when database is not available"""
        return [
            {
                'label': 'NVIDIA Earnings Surge',
                'topic': 'AI',
                'mention_count': 25,
                'trend_score': 78,
                'dominant_sentiment': 'positive',
                'sources': ['reddit', 'rss'],
                'top_entities': ['NVIDIA (NVDA)', 'AI', 'Chips']
            },
            {
                'label': 'Fed Policy Discussion',
                'topic': 'economy',
                'mention_count': 18,
                'trend_score': 62,
                'dominant_sentiment': 'neutral',
                'sources': ['rss', 'reddit'],
                'top_entities': ['Federal Reserve', 'USD', 'Inflation']
            }
        ]
    
    def _get_demo_signals(self) -> List[Dict]:
        """Get demo signals for when database is not available"""
        return [
            {
                'asset': 'NVDA',
                'direction': 'up',
                'confidence': 0.85,
                'impact_type': 'stock_up',
                'reason': 'AI positive + NVDA entity | Tesla AI breakthrough',
                'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat()
            },
            {
                'asset': 'TSLA',
                'direction': 'up',
                'confidence': 0.80,
                'impact_type': 'stock_up',
                'reason': 'Tesla/Musk positive news | FSD beta expansion',
                'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat()
            },
            {
                'asset': 'XAU/USD',
                'direction': 'up',
                'confidence': 0.65,
                'impact_type': 'risk_off',
                'reason': 'Dovish/recession signal -> gold',
                'timestamp': (datetime.now() - timedelta(minutes=45)).isoformat()
            }
        ]


# Global dashboard instance
social_dashboard = SocialSignalsDashboard()


def render_social_signals_tab():
    """Main entry point for rendering the social signals tab"""
    try:
        # Initialize dashboard
        if not hasattr(st.session_state, 'social_dashboard_initialized'):
            asyncio.run(social_dashboard.initialize())
            st.session_state['social_dashboard_initialized'] = True
        
        # Render the tab
        social_dashboard.render_social_signals_tab()
        
    except Exception as e:
        st.error(f"Error loading social signals dashboard: {e}")
        st.info("Please check your configuration and try again.")
