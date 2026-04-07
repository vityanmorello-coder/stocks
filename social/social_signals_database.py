"""
Social Signals Database v1.0 - MongoDB Integration
Stores and retrieves social signals, events, and clusters with indexing.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import asdict
import json

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logging.warning("MongoDB libraries not installed. Using file-based fallback.")

from social.social_signals_engine import ProcessedEvent, TradingSignal, RawEvent
from social.trend_engine import TopicCluster

logger = logging.getLogger(__name__)


class SocialSignalsDB:
    """
    Async MongoDB client for social signals with fallback to JSON files.
    Handles events, signals, clusters, and analytics.
    """
    
    def __init__(self, connection_string: str = None, database_name: str = "quantumtrade_social"):
        # Load from .env file if exists (look in config folder)
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()
        
        self.connection_string = connection_string or os.getenv('MONGODB_CONNECTION_STRING', '')
        self.database_name = database_name or os.getenv('MONGODB_DATABASE_NAME', 'quantumtrade_social')
        
        # Collections
        self.events_collection = "global_signals"
        self.raw_events_collection = "raw_events"
        self.clusters_collection = "trending_clusters"
        self.signals_collection = "trading_signals"
        self.analytics_collection = "analytics"
        
        # Fallback storage
        self._fallback_data = {
            'events': [],
            'raw_events': [],
            'clusters': [],
            'signals': [],
            'analytics': {}
        }
        
        self._connected = False
        self._client = None
        self._db = None
        
    async def connect(self) -> bool:
        """Connect to MongoDB or initialize fallback storage"""
        if not MONGODB_AVAILABLE:
            logger.warning("Using file-based fallback storage")
            self._load_fallback_data()
            self._connected = True
            return True
            
        try:
            self._client = AsyncIOMotorClient(self.connection_string, serverSelectionTimeoutMS=5000)
            await self._client.admin.command('ping')
            self._db = self._client[self.database_name]
            
            # Create indexes for performance
            await self._create_indexes()
            
            self._connected = True
            logger.info(f"Connected to MongoDB: {self.database_name}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            logger.warning("Using file-based fallback storage")
            self._load_fallback_data()
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False
    
    async def disconnect(self):
        """Close database connection"""
        if self._client:
            self._client.close()
        self._save_fallback_data()
    
    async def _create_indexes(self):
        """Create MongoDB indexes for optimal query performance"""
        if self._db is None:
            return
            
        try:
            # Events collection indexes
            await self._db[self.events_collection].create_index("timestamp")
            await self._db[self.events_collection].create_index("topic")
            await self._db[self.events_collection].create_index("source")
            await self._db[self.events_collection].create_index("urgency")
            await self._db[self.events_collection].create_index([("timestamp", -1)])
            await self._db[self.events_collection].create_index([("topic", 1), ("timestamp", -1)])
            
            # Raw events deduplication index
            await self._db[self.raw_events_collection].create_index("raw_id", unique=True)
            await self._db[self.raw_events_collection].create_index("timestamp")
            
            # Clusters collection indexes
            await self._db[self.clusters_collection].create_index("cluster_id", unique=True)
            await self._db[self.clusters_collection].create_index("is_trending")
            await self._db[self.clusters_collection].create_index([("trend_score", -1)])
            await self._db[self.clusters_collection].create_index("last_seen")
            
            # Signals collection indexes
            await self._db[self.signals_collection].create_index("timestamp")
            await self._db[self.signals_collection].create_index("asset")
            await self._db[self.signals_collection].create_index("direction")
            await self._db[self.signals_collection].create_index("confidence")
            await self._db[self.signals_collection].create_index([("confidence", -1)])
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    # ========================================================================
    # EVENT STORAGE
    # ========================================================================
    
    async def store_raw_event(self, event: RawEvent) -> bool:
        """Store a raw event with deduplication"""
        if not self._connected:
            return False
            
        try:
            event_dict = asdict(event)
            event_dict['timestamp'] = event.timestamp.isoformat()
            
            if MONGODB_AVAILABLE and self._db is not None:
                try:
                    await self._db[self.raw_events_collection].insert_one(event_dict)
                    return True
                except DuplicateKeyError:
                    return True  # Already exists
            else:
                # Fallback storage
                self._fallback_data['raw_events'].append(event_dict)
                return True
                
        except Exception as e:
            logger.error(f"Error storing raw event: {e}")
            return False
    
    async def store_processed_event(self, event: ProcessedEvent) -> bool:
        """Store a processed event with signals"""
        if not self._connected:
            return False
            
        try:
            event_dict = event.to_dict()
            
            if MONGODB_AVAILABLE and self._db is not None:
                await self._db[self.events_collection].insert_one(event_dict)
            else:
                # Fallback storage
                self._fallback_data['events'].append(event_dict)
            
            # Store individual signals
            for signal in event.signals:
                await self.store_signal(signal, event.event_id)
                
            return True
            
        except Exception as e:
            logger.error(f"Error storing processed event: {e}")
            return False
    
    async def store_signal(self, signal: TradingSignal, event_id: str = None) -> bool:
        """Store a trading signal"""
        if not self._connected:
            return False
            
        try:
            signal_dict = asdict(signal)
            signal_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
            signal_dict['event_id'] = event_id
            
            if MONGODB_AVAILABLE and self._db is not None:
                await self._db[self.signals_collection].insert_one(signal_dict)
            else:
                # Fallback storage
                self._fallback_data['signals'].append(signal_dict)
                
            return True
            
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
            return False
    
    async def store_cluster(self, cluster: TopicCluster) -> bool:
        """Store a trending cluster"""
        if not self._connected:
            return False
            
        try:
            cluster_dict = asdict(cluster)
            
            # Convert datetime fields
            if cluster.first_seen:
                cluster_dict['first_seen'] = cluster.first_seen.isoformat()
            if cluster.last_seen:
                cluster_dict['last_seen'] = cluster.last_seen.isoformat()
            
            # Convert events to IDs only to save space
            cluster_dict['event_ids'] = [e.event_id for e in cluster.events]
            cluster_dict['events'] = []  # Don't store full events in cluster
            
            if MONGODB_AVAILABLE and self._db is not None:
                await self._db[self.clusters_collection].update_one(
                    {"cluster_id": cluster.cluster_id},
                    {"$set": cluster_dict},
                    upsert=True
                )
            else:
                # Fallback storage
                self._fallback_data['clusters'].append(cluster_dict)
                
            return True
            
        except Exception as e:
            logger.error(f"Error storing cluster: {e}")
            return False
    
    # ========================================================================
    # DATA RETRIEVAL
    # ========================================================================
    
    async def get_recent_events(self, limit: int = 100, hours: int = 24,
                               topic_filter: str = None,
                               source_filter: str = None) -> List[Dict]:
        """Get recent events with optional filters"""
        if not self._connected:
            return []
            
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Build query
            query = {"timestamp": {"$gte": cutoff.isoformat()}}
            if topic_filter:
                query["topic"] = topic_filter
            if source_filter:
                query["source"] = source_filter
            
            if MONGODB_AVAILABLE and self._db is not None:
                cursor = self._db[self.events_collection].find(query).sort("timestamp", -1).limit(limit)
                events = await cursor.to_list(length=limit)
                return events
            else:
                # Fallback retrieval
                events = self._fallback_data['events']
                events = [e for e in events if datetime.fromisoformat(e['timestamp']) >= cutoff]
                if topic_filter:
                    events = [e for e in events if e['topic'] == topic_filter]
                if source_filter:
                    events = [e for e in events if e['source'] == source_filter]
                events.sort(key=lambda x: x['timestamp'], reverse=True)
                return events[:limit]
                
        except Exception as e:
            logger.error(f"Error retrieving events: {e}")
            return []
    
    async def get_trending_clusters(self, limit: int = 20, min_score: float = 25.0) -> List[Dict]:
        """Get trending clusters sorted by trend score"""
        if not self._connected:
            return []
            
        try:
            query = {"is_trending": True, "trend_score": {"$gte": min_score}}
            
            if MONGODB_AVAILABLE and self._db is not None:
                cursor = self._db[self.clusters_collection].find(query).sort("trend_score", -1).limit(limit)
                clusters = await cursor.to_list(length=limit)
                return clusters
            else:
                # Fallback retrieval
                clusters = self._fallback_data['clusters']
                clusters = [c for c in clusters if c.get('is_trending', False) and c.get('trend_score', 0) >= min_score]
                clusters.sort(key=lambda x: x.get('trend_score', 0), reverse=True)
                return clusters[:limit]
                
        except Exception as e:
            logger.error(f"Error retrieving clusters: {e}")
            return []
    
    async def get_top_signals(self, limit: int = 50, min_confidence: float = 0.4,
                            asset_filter: str = None) -> List[Dict]:
        """Get top trading signals by confidence"""
        if not self._connected:
            return []
            
        try:
            query = {"confidence": {"$gte": min_confidence}}
            if asset_filter:
                query["asset"] = asset_filter
            
            if MONGODB_AVAILABLE and self._db is not None:
                cursor = self._db[self.signals_collection].find(query).sort("confidence", -1).sort("timestamp", -1).limit(limit)
                signals = await cursor.to_list(length=limit)
                return signals
            else:
                # Fallback retrieval
                signals = self._fallback_data['signals']
                signals = [s for s in signals if s.get('confidence', 0) >= min_confidence]
                if asset_filter:
                    signals = [s for s in signals if s.get('asset') == asset_filter]
                signals.sort(key=lambda x: (x.get('confidence', 0), x.get('timestamp')), reverse=True)
                return signals[:limit]
                
        except Exception as e:
            logger.error(f"Error retrieving signals: {e}")
            return []
    
    async def get_analytics(self) -> Dict:
        """Get analytics summary"""
        if not self._connected:
            return {}
            
        try:
            if MONGODB_AVAILABLE and self._db is not None:
                # Get counts from MongoDB
                events_count = await self._db[self.events_collection].count_documents({})
                signals_count = await self._db[self.signals_collection].count_documents({})
                clusters_count = await self._db[self.clusters_collection].count_documents({"is_trending": True})
                
                # Get topic distribution
                topic_pipeline = [
                    {"$group": {"_id": "$topic", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
                topic_dist = await self._db[self.events_collection].aggregate(topic_pipeline).to_list(None)
                
                # Get asset distribution
                asset_pipeline = [
                    {"$group": {"_id": "$asset", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
                asset_dist = await self._db[self.signals_collection].aggregate(asset_pipeline).to_list(None)
                
            else:
                # Fallback analytics
                events_count = len(self._fallback_data['events'])
                signals_count = len(self._fallback_data['signals'])
                clusters_count = len([c for c in self._fallback_data['clusters'] if c.get('is_trending', False)])
                
                # Simple topic distribution
                topics = {}
                for event in self._fallback_data['events']:
                    topic = event.get('topic', 'unknown')
                    topics[topic] = topics.get(topic, 0) + 1
                topic_dist = [{"_id": k, "count": v} for k, v in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]]
                
                # Simple asset distribution
                assets = {}
                for signal in self._fallback_data['signals']:
                    asset = signal.get('asset', 'unknown')
                    assets[asset] = assets.get(asset, 0) + 1
                asset_dist = [{"_id": k, "count": v} for k, v in sorted(assets.items(), key=lambda x: x[1], reverse=True)[:10]]
            
            return {
                "events_count": events_count,
                "signals_count": signals_count,
                "trending_clusters": clusters_count,
                "topic_distribution": topic_dist,
                "asset_distribution": asset_dist,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {}
    
    # ========================================================================
    # CLEANUP AND MAINTENANCE
    # ========================================================================
    
    async def cleanup_old_data(self, days_to_keep: int = 7):
        """Remove old data to save space"""
        if not self._connected:
            return
            
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            cutoff_str = cutoff.isoformat()
            
            if MONGODB_AVAILABLE and self._db is not None:
                # Clean old events
                events_result = await self._db[self.events_collection].delete_many(
                    {"timestamp": {"$lt": cutoff_str}}
                )
                
                # Clean old raw events
                raw_result = await self._db[self.raw_events_collection].delete_many(
                    {"timestamp": {"$lt": cutoff_str}}
                )
                
                # Clean old signals
                signals_result = await self._db[self.signals_collection].delete_many(
                    {"timestamp": {"$lt": cutoff_str}}
                )
                
                # Clean old clusters
                clusters_result = await self._db[self.clusters_collection].delete_many(
                    {"last_seen": {"$lt": cutoff_str}}
                )
                
                logger.info(f"Cleanup completed: events={events_result.deleted_count}, "
                          f"raw={raw_result.deleted_count}, signals={signals_result.deleted_count}, "
                          f"clusters={clusters_result.deleted_count}")
            else:
                # Fallback cleanup
                cutoff_dt = cutoff
                self._fallback_data['events'] = [
                    e for e in self._fallback_data['events'] 
                    if datetime.fromisoformat(e['timestamp']) >= cutoff_dt
                ]
                self._fallback_data['raw_events'] = [
                    e for e in self._fallback_data['raw_events'] 
                    if datetime.fromisoformat(e['timestamp']) >= cutoff_dt
                ]
                self._fallback_data['signals'] = [
                    s for s in self._fallback_data['signals'] 
                    if datetime.fromisoformat(s['timestamp']) >= cutoff_dt
                ]
                self._fallback_data['clusters'] = [
                    c for c in self._fallback_data['clusters']
                    if not c.get('last_seen') or datetime.fromisoformat(c['last_seen']) >= cutoff_dt
                ]
                
                logger.info("Fallback cleanup completed")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # ========================================================================
    # FALLBACK STORAGE METHODS
    # ========================================================================
    
    def _load_fallback_data(self):
        """Load fallback data from JSON files"""
        try:
            import os
            
            if os.path.exists('social_signals_fallback.json'):
                with open('social_signals_fallback.json', 'r') as f:
                    self._fallback_data = json.load(f)
                logger.info("Loaded fallback data from file")
        except Exception as e:
            logger.warning(f"Could not load fallback data: {e}")
    
    def _save_fallback_data(self):
        """Save fallback data to JSON file"""
        try:
            import os
            
            with open('social_signals_fallback.json', 'w') as f:
                json.dump(self._fallback_data, f, indent=2)
            logger.info("Saved fallback data to file")
        except Exception as e:
            logger.error(f"Could not save fallback data: {e}")


# ========================================================================
# DATABASE MANAGER (SINGLETON)
# ========================================================================

class DatabaseManager:
    """Singleton database manager for social signals"""
    
    _instance = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._db is None:
            self._db = SocialSignalsDB()
    
    async def initialize(self, connection_string: str = None) -> bool:
        """Initialize database connection"""
        return await self._db.connect()
    
    async def close(self):
        """Close database connection"""
        await self._db.disconnect()
    
    @property
    def db(self) -> SocialSignalsDB:
        """Get database instance"""
        return self._db


# Global database manager instance
db_manager = DatabaseManager()
