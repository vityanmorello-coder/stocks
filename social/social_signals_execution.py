"""
Social Signals Execution Integration v1.0
Integrates social signals with the existing execution engine for automated trading.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from trading.execution_engine import ExecutionManager, OrderRequest, OrderType, OrderResult
from social.social_signals_engine import TradingSignal, ProcessedEvent
from social.social_signals_pipeline import SocialSignalsPipeline
from trading.risk_manager import RiskManager
from trading.fortrade_config import TradingConfig

logger = logging.getLogger(__name__)


@dataclass
class SocialSignalOrder:
    """Enhanced order request for social signal execution"""
    signal: TradingSignal
    event: Optional[ProcessedEvent]
    confidence_multiplier: float = 1.0
    max_risk_percent: float = 1.0
    reason: str = ""


class SocialSignalsExecutor:
    """
    Handles execution of social signals with enhanced risk management
    and position sizing based on signal confidence and source credibility.
    """
    
    def __init__(self, execution_manager: ExecutionManager, risk_manager: RiskManager):
        self.execution_manager = execution_manager
        self.risk_manager = risk_manager
        
        # Execution settings
        self.min_confidence_threshold = 0.5  # Higher threshold for social signals
        self.max_daily_signals = 10
        self.max_position_size_percent = 2.0  # Conservative sizing for social signals
        self.cooldown_minutes = 30  # Wait between same asset signals
        
        # Tracking
        self.signals_today = 0
        self.last_signals: Dict[str, datetime] = {}  # asset -> last signal time
        self.executed_orders: List[Dict] = []
        
        # Asset-specific settings
        self.asset_settings = {
            'BTC/USD': {'max_risk': 1.5, 'min_confidence': 0.6},
            'ETH/USD': {'max_risk': 1.2, 'min_confidence': 0.6},
            'NVDA': {'max_risk': 2.0, 'min_confidence': 0.55},
            'TSLA': {'max_risk': 1.8, 'min_confidence': 0.55},
            'OIL/USD': {'max_risk': 1.5, 'min_confidence': 0.5},
            'XAU/USD': {'max_risk': 1.0, 'min_confidence': 0.5},
            'SPX500': {'max_risk': 1.5, 'min_confidence': 0.6},
            'NAS100': {'max_risk': 1.8, 'min_confidence': 0.55},
        }
    
    async def execute_signal(self, signal: TradingSignal, event: Optional[ProcessedEvent] = None) -> OrderResult:
        """
        Execute a social signal with enhanced validation and risk management.
        """
        try:
            # Validate signal
            if not self._validate_signal(signal, event):
                return OrderResult(success=False, error_message="Signal validation failed")
            
            # Check cooldown
            if not self._check_cooldown(signal.asset):
                return OrderResult(success=False, error_message=f"Asset {signal.asset} in cooldown period")
            
            # Check daily limits
            if not self._check_daily_limits():
                return OrderResult(success=False, error_message="Daily signal limit reached")
            
            # Calculate position size
            position_size = self._calculate_position_size(signal, event)
            if position_size <= 0:
                return OrderResult(success=False, error_message="Position size too small")
            
            # Create order request
            order_request = self._create_order_request(signal, event, position_size)
            
            # Execute order
            result = self.execution_manager.execute_signal(order_request)
            
            # Record execution
            if result.success:
                self._record_execution(signal, event, result)
                logger.info(f"Social signal executed: {signal.asset} {signal.direction} @ {result.fill_price}")
            else:
                logger.warning(f"Social signal execution failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing social signal: {e}")
            return OrderResult(success=False, error_message=str(e))
    
    def _validate_signal(self, signal: TradingSignal, event: Optional[ProcessedEvent] = None) -> bool:
        """Validate signal meets execution criteria"""
        # Check minimum confidence
        asset_config = self.asset_settings.get(signal.asset, {'min_confidence': self.min_confidence_threshold})
        if signal.confidence < asset_config['min_confidence']:
            return False
        
        # Check if signal is too old (more than 1 hour)
        if event and (datetime.now(timezone.utc) - event.timestamp).total_seconds() > 3600:
            return False
        
        # Check for conflicting signals in same asset
        if event and event.signals:
            conflicting_signals = [s for s in event.signals if s.asset == signal.asset and s.direction != signal.direction]
            if conflicting_signals:
                return False
        
        # Check market hours (simplified)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:  # Avoid late night trading
            return False
        
        return True
    
    def _check_cooldown(self, asset: str) -> bool:
        """Check if asset is in cooldown period"""
        last_signal_time = self.last_signals.get(asset)
        if last_signal_time:
            cooldown_period = timedelta(minutes=self.cooldown_minutes)
            if datetime.now(timezone.utc) - last_signal_time < cooldown_period:
                return False
        
        return True
    
    def _check_daily_limits(self) -> bool:
        """Check daily signal limits"""
        # Reset counter at midnight
        now = datetime.now()
        if now.hour == 0 and now.minute < 5:
            self.signals_today = 0
        
        return self.signals_today < self.max_daily_signals
    
    def _calculate_position_size(self, signal: TradingSignal, event: Optional[ProcessedEvent] = None) -> float:
        """Calculate position size based on signal confidence and risk"""
        try:
            # Base position size (very conservative for social signals)
            base_size = 0.01  # 0.01 lots minimum
            
            # Confidence multiplier
            confidence_multiplier = signal.confidence * 2.0  # Scale confidence
            
            # Author/event credibility multiplier
            credibility_multiplier = 1.0
            if event:
                credibility_multiplier = min(2.0, event.author_weight)
            
            # Asset-specific risk multiplier
            asset_config = self.asset_settings.get(signal.asset, {'max_risk': 1.0})
            risk_multiplier = asset_config['max_risk'] / 100.0
            
            # Calculate final size
            position_size = base_size * confidence_multiplier * credibility_multiplier * risk_multiplier
            
            # Apply maximum limit
            max_size = self.max_position_size_percent / 100.0
            position_size = min(position_size, max_size)
            
            # Ensure minimum size
            position_size = max(position_size, 0.01)
            
            return round(position_size, 2)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def _create_order_request(self, signal: TradingSignal, event: Optional[ProcessedEvent], position_size: float) -> OrderRequest:
        """Create order request from social signal"""
        # Determine order type based on urgency and confidence
        order_type = OrderType.MARKET
        if signal.confidence > 0.8 and event and event.urgency == 'breaking':
            order_type = OrderType.MARKET  # Execute immediately for breaking news
        elif signal.confidence < 0.6:
            order_type = OrderType.LIMIT  # Use limit orders for lower confidence
        
        # Build comment
        comment_parts = [f"Social signal: {signal.reason[:50]}"]
        if event:
            comment_parts.append(f"Source: {event.source}")
            comment_parts.append(f"Author: {event.author}")
        comment = " | ".join(comment_parts)
        
        return OrderRequest(
            symbol=signal.asset,
            side='buy' if signal.direction == 'up' else 'sell',
            quantity=position_size,
            order_type=order_type,
            confidence=signal.confidence,
            strategy='social_signals',
            comment=comment
        )
    
    def _record_execution(self, signal: TradingSignal, event: Optional[ProcessedEvent], result: OrderResult):
        """Record successful execution"""
        self.signals_today += 1
        self.last_signals[signal.asset] = datetime.now(timezone.utc)
        
        execution_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'signal': signal.__dict__,
            'event': event.__dict__ if event else None,
            'result': result.__dict__,
            'position_size': result.fill_quantity
        }
        
        self.executed_orders.append(execution_record)
        
        # Keep only last 100 executions
        if len(self.executed_orders) > 100:
            self.executed_orders = self.executed_orders[-100:]
    
    def get_execution_stats(self) -> Dict:
        """Get execution statistics"""
        if not self.executed_orders:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_confidence': 0.0,
                'signals_today': self.signals_today,
                'assets_traded': []
            }
        
        successful_executions = [e for e in self.executed_orders if e['result']['success']]
        success_rate = len(successful_executions) / len(self.executed_orders)
        
        avg_confidence = sum(e['signal']['confidence'] for e in self.executed_orders) / len(self.executed_orders)
        
        assets_traded = list(set(e['signal']['asset'] for e in self.executed_orders))
        
        return {
            'total_executions': len(self.executed_orders),
            'success_rate': success_rate,
            'avg_confidence': avg_confidence,
            'signals_today': self.signals_today,
            'assets_traded': assets_traded,
            'last_execution': self.executed_orders[-1]['timestamp'] if self.executed_orders else None
        }
    
    def get_recent_executions(self, limit: int = 20) -> List[Dict]:
        """Get recent execution records"""
        return self.executed_orders[-limit:]


class SocialSignalsIntegration:
    """
    Main integration class that connects social signals pipeline with execution engine.
    """
    
    def __init__(self, execution_manager: ExecutionManager, risk_manager: RiskManager):
        self.executor = SocialSignalsExecutor(execution_manager, risk_manager)
        self.pipeline = None
    
    async def initialize(self, pipeline: SocialSignalsPipeline):
        """Initialize integration with social signals pipeline"""
        self.pipeline = pipeline
        
        # Add signal callback
        self.pipeline.add_signal_callback(self._on_signal)
        
        logger.info("Social signals integration initialized")
    
    async def _on_signal(self, signal: TradingSignal, event: Optional[ProcessedEvent] = None):
        """Handle new trading signal from pipeline"""
        try:
            # Execute signal if it meets criteria
            result = await self.executor.execute_signal(signal, event)
            
            if result.success:
                logger.info(f"Auto-executed social signal: {signal.asset} {signal.direction}")
            else:
                logger.debug(f"Social signal not executed: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Error handling social signal: {e}")
    
    def get_integration_stats(self) -> Dict:
        """Get integration statistics"""
        stats = self.executor.get_execution_stats()
        
        if self.pipeline:
            pipeline_stats = self.pipeline.get_stats()
            stats.update({
                'pipeline_events_processed': pipeline_stats.get('events_processed', 0),
                'pipeline_signals_generated': pipeline_stats.get('signals_generated', 0),
                'pipeline_trending_clusters': pipeline_stats.get('trending_clusters', 0),
                'pipeline_uptime': pipeline_stats.get('uptime_formatted', 'N/A')
            })
        
        return stats


# Global integration instance
_integration: Optional[SocialSignalsIntegration] = None


async def initialize_social_signals_integration(execution_manager: ExecutionManager, risk_manager: RiskManager, pipeline: SocialSignalsPipeline) -> SocialSignalsIntegration:
    """Initialize global social signals integration"""
    global _integration
    _integration = SocialSignalsIntegration(execution_manager, risk_manager)
    await _integration.initialize(pipeline)
    return _integration


def get_integration_stats() -> Dict:
    """Get global integration statistics"""
    if _integration:
        return _integration.get_integration_stats()
    return {}
