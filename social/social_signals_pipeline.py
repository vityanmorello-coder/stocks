"""
Real-time Social Signals Pipeline v1.0
Orchestrates the complete flow from data collection to signal generation and execution.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import threading

from social.social_listener import SocialListener
from social.social_signals_engine import RawEvent, ProcessedEvent, EventProcessor
from social.trend_engine import TrendEngine
from intelligence.signal_engine import SignalEngine
from social.social_signals_database import db_manager
from trading.execution_engine import ExecutionManager, OrderRequest, OrderType

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the social signals pipeline"""
    # Data collection settings
    collection_interval_seconds: int = 60
    max_events_per_batch: int = 100
    
    # Processing settings
    enable_trend_detection: bool = True
    enable_signal_generation: bool = True
    enable_auto_execution: bool = False  # Disabled by default for safety
    
    # Filtering settings
    min_confidence_threshold: float = 0.4
    max_signals_per_minute: int = 5
    
    # Risk settings
    max_position_size_percent: float = 2.0
    stop_loss_percent: float = 1.0
    take_profit_percent: float = 2.0


class SocialSignalsPipeline:
    """
    Main pipeline that orchestrates:
    1. Social media data collection
    2. NLP processing and entity detection
    3. Trend detection and clustering
    4. Signal generation
    5. Optional automatic execution
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.running = False
        self.paused = False
        
        # Initialize components
        self.social_listener = SocialListener()
        self.event_processor = EventProcessor()
        self.trend_engine = TrendEngine()
        self.signal_engine = SignalEngine()
        self.execution_manager = None  # Will be initialized if needed
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'signals_generated': 0,
            'trades_executed': 0,
            'last_update': None,
            'errors': 0,
            'start_time': None
        }
        
        # Callbacks for external monitoring
        self.event_callbacks: List[Callable] = []
        self.signal_callbacks: List[Callable] = []
        
        # Rate limiting
        self.last_execution_time = 0
        self.signals_this_minute = 0
        self.minute_reset_time = time.time()
    
    def add_event_callback(self, callback: Callable):
        """Add callback for new events"""
        self.event_callbacks.append(callback)
    
    def add_signal_callback(self, callback: Callable):
        """Add callback for new trading signals"""
        self.signal_callbacks.append(callback)
    
    async def initialize(self, execution_manager: ExecutionManager = None):
        """Initialize all pipeline components"""
        try:
            # Initialize database
            await db_manager.initialize()
            
            # Initialize execution manager if provided
            if execution_manager and self.config.enable_auto_execution:
                self.execution_manager = execution_manager
                logger.info("Auto-execution enabled")
            
            # Set up social listener callbacks
            self.social_listener.add_callback(self._on_raw_events)
            
            logger.info("Social signals pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            return False
    
    async def start(self):
        """Start the real-time pipeline"""
        if self.running:
            logger.warning("Pipeline is already running")
            return
        
        self.running = True
        self.paused = False
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        logger.info("Starting social signals pipeline...")
        
        # Start social media listener in background
        listener_task = asyncio.create_task(
            self.social_listener.start_listening(self.config.collection_interval_seconds)
        )
        
        # Start main processing loop
        processor_task = asyncio.create_task(self._processing_loop())
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        try:
            await asyncio.gather(listener_task, processor_task, cleanup_task)
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.running = False
    
    async def stop(self):
        """Stop the pipeline"""
        self.running = False
        self.social_listener.stop_listening()
        logger.info("Social signals pipeline stopped")
    
    async def pause(self):
        """Pause the pipeline"""
        self.paused = True
        logger.info("Pipeline paused")
    
    async def resume(self):
        """Resume the pipeline"""
        self.paused = False
        logger.info("Pipeline resumed")
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                if not self.paused:
                    await self._process_latest_events()
                    await self._generate_cluster_signals()
                    await self._update_stats()
                
                await asyncio.sleep(10)  # Process every 10 seconds
                
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _cleanup_loop(self):
        """Periodic cleanup and maintenance"""
        while self.running:
            try:
                # Clean old data (keep 7 days)
                await db_manager.db.cleanup_old_data(days_to_keep=7)
                
                # Reset rate limiting counters
                current_time = time.time()
                if current_time - self.minute_reset_time > 60:
                    self.signals_this_minute = 0
                    self.minute_reset_time = current_time
                
                # Sleep for 1 hour between cleanups
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _on_raw_events(self, raw_events: List[RawEvent]):
        """Handle new raw events from social listener"""
        try:
            # Store raw events
            for event in raw_events:
                await db_manager.db.store_raw_event(event)
            
            # Process events
            processed_events = []
            for raw_event in raw_events:
                processed = self.event_processor.process(raw_event)
                processed_events.append(processed)
            
            # Update trend engine
            self.trend_engine.ingest(processed_events)
            
            # Mark trending events
            processed_events = self.trend_engine.mark_event_clusters(processed_events)
            
            # Generate signals
            if self.config.enable_signal_generation:
                processed_events = self.signal_engine.generate_for_events(processed_events)
            
            # Store processed events
            for event in processed_events:
                await db_manager.db.store_processed_event(event)
                
                # Notify callbacks
                for callback in self.event_callbacks:
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Event callback error: {e}")
                
                # Handle signals
                for signal in event.signals:
                    await self._handle_trading_signal(signal, event)
            
            self.stats['events_processed'] += len(raw_events)
            
        except Exception as e:
            logger.error(f"Error processing raw events: {e}")
            self.stats['errors'] += 1
    
    async def _process_latest_events(self):
        """Process any unprocessed events from database"""
        try:
            # Get recent unprocessed events (simplified approach)
            # In a real implementation, you'd track processing status
            pass
        except Exception as e:
            logger.error(f"Error processing latest events: {e}")
    
    async def _generate_cluster_signals(self):
        """Generate signals from trending clusters"""
        try:
            if not self.config.enable_signal_generation:
                return
            
            # Get trending clusters
            clusters = self.trend_engine.get_trending_clusters(top_n=10)
            
            for cluster in clusters:
                # Generate cluster-level signal
                cluster_signal = self.signal_engine.generate_cluster_signal(cluster)
                
                if cluster_signal:
                    # Store cluster signal
                    await db_manager.db.store_signal(cluster_signal)
                    
                    # Store cluster
                    await db_manager.db.store_cluster(cluster)
                    
                    # Handle signal
                    await self._handle_trading_signal(cluster_signal, None)
                    
                    self.stats['signals_generated'] += 1
            
        except Exception as e:
            logger.error(f"Error generating cluster signals: {e}")
    
    async def _handle_trading_signal(self, signal, event: Optional[ProcessedEvent] = None):
        """Handle a trading signal - notify callbacks and optionally execute"""
        try:
            # Notify signal callbacks
            for callback in self.signal_callbacks:
                try:
                    await callback(signal, event)
                except Exception as e:
                    logger.error(f"Signal callback error: {e}")
            
            # Auto-execution if enabled and signal meets criteria
            if (self.config.enable_auto_execution and 
                self.execution_manager and 
                signal.confidence >= self.config.min_confidence_threshold):
                
                # Check rate limiting
                current_time = time.time()
                if current_time - self.minute_reset_time > 60:
                    self.signals_this_minute = 0
                    self.minute_reset_time = current_time
                
                if self.signals_this_minute < self.config.max_signals_per_minute:
                    await self._execute_signal(signal, event)
                else:
                    logger.warning(f"Rate limit exceeded for signal execution")
            
        except Exception as e:
            logger.error(f"Error handling trading signal: {e}")
    
    async def _execute_signal(self, signal, event: Optional[ProcessedEvent] = None):
        """Execute a trading signal"""
        try:
            if not self.execution_manager:
                return
            
            # Create order request
            order_request = OrderRequest(
                symbol=signal.asset,
                side='buy' if signal.direction == 'up' else 'sell',
                quantity=0.01,  # Default small size
                confidence=signal.confidence,
                strategy='social_signals',
                comment=f"Social signal: {signal.reason}"
            )
            
            # Execute order
            result = self.execution_manager.execute_signal(order_request)
            
            if result.success:
                self.stats['trades_executed'] += 1
                logger.info(f"Executed trade: {signal.asset} {signal.direction} @ {result.fill_price}")
            else:
                logger.warning(f"Trade execution failed: {result.error_message}")
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def _update_stats(self):
        """Update pipeline statistics"""
        self.stats['last_update'] = datetime.now(timezone.utc).isoformat()
    
    def get_stats(self) -> Dict:
        """Get current pipeline statistics"""
        stats = self.stats.copy()
        
        # Add uptime
        if stats['start_time']:
            uptime = datetime.now(timezone.utc) - stats['start_time']
            stats['uptime_seconds'] = uptime.total_seconds()
            stats['uptime_formatted'] = str(uptime).split('.')[0]
        
        # Add trending clusters count
        try:
            stats['trending_clusters'] = len(self.trend_engine.get_trending_clusters())
        except:
            stats['trending_clusters'] = 0
        
        return stats
    
    def get_recent_signals(self, limit: int = 20, min_confidence: float = 0.3) -> List[Dict]:
        """Get recent trading signals"""
        try:
            # This would typically query the database
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []
    
    def get_trending_topics(self, limit: int = 10) -> List[Dict]:
        """Get current trending topics"""
        try:
            clusters = self.trend_engine.get_trending_clusters(top_n=limit)
            
            return [{
                'topic': cluster.topic,
                'label': cluster.label,
                'trend_score': cluster.trend_score,
                'mention_count': cluster.mention_count,
                'dominant_sentiment': cluster.dominant_sentiment,
                'sources': cluster.sources,
                'top_entities': cluster.top_entities
            } for cluster in clusters]
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []


# Global pipeline instance
pipeline = SocialSignalsPipeline()


async def start_social_signals_pipeline(execution_manager: ExecutionManager = None):
    """Start the global social signals pipeline"""
    await pipeline.initialize(execution_manager)
    
    # Run in background thread
    def run_pipeline():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(pipeline.start())
    
    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()
    
    return pipeline


def get_pipeline_stats() -> Dict:
    """Get global pipeline statistics"""
    return pipeline.get_stats()


def get_recent_signals(limit: int = 20) -> List[Dict]:
    """Get recent signals from global pipeline"""
    return pipeline.get_recent_signals(limit)


def get_trending_topics(limit: int = 10) -> List[Dict]:
    """Get trending topics from global pipeline"""
    return pipeline.get_trending_topics(limit)
