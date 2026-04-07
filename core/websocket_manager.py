"""
WebSocket Data Streaming Manager
Real-time market data and social signals streaming
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
import aiohttp
import threading
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time data streaming"""
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.data_queue = Queue()
        self.running = False
        self._server = None
        
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start WebSocket server"""
        self.running = True
        
        self._server = await websockets.serve(
            self.handle_client,
            host,
            port,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info(f"WebSocket server started on {host}:{port}")
        
        # Start data processing thread
        threading.Thread(target=self._process_data_queue, daemon=True).start()
        
    async def handle_client(self, websocket, path):
        """Handle new WebSocket client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}_{datetime.now().timestamp()}"
        self.connections[client_id] = websocket
        
        try:
            logger.info(f"Client connected: {client_id}")
            
            # Send initial connection message
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            }))
            
            # Handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(client_id, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            if client_id in self.connections:
                del self.connections[client_id]
    
    async def handle_client_message(self, client_id: str, message: Dict):
        """Handle messages from clients"""
        msg_type = message.get("type")
        
        if msg_type == "subscribe":
            # Subscribe to data streams
            streams = message.get("streams", [])
            for stream in streams:
                if stream not in self.subscribers:
                    self.subscribers[stream] = []
                self.subscribers[stream].append(client_id)
            
            await self.connections[client_id].send(json.dumps({
                "type": "subscription_ack",
                "streams": streams
            }))
            
        elif msg_type == "unsubscribe":
            # Unsubscribe from data streams
            streams = message.get("streams", [])
            for stream in streams:
                if stream in self.subscribers:
                    self.subscribers[stream] = [c for c in self.subscribers[stream] if c != client_id]
    
    def broadcast_data(self, stream: str, data: Dict):
        """Broadcast data to all subscribers of a stream"""
        self.data_queue.put({
            "stream": stream,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    
    def _process_data_queue(self):
        """Process data queue and broadcast to subscribers"""
        while self.running:
            try:
                item = self.data_queue.get(timeout=1)
                
                if item["stream"] in self.subscribers:
                    message = json.dumps({
                        "type": "data",
                        "stream": item["stream"],
                        "data": item["data"],
                        "timestamp": item["timestamp"]
                    })
                    
                    # Send to all subscribers
                    disconnected_clients = []
                    for client_id in self.subscribers[item["stream"]]:
                        if client_id in self.connections:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    self.connections[client_id].send(message),
                                    self._server.loop
                                )
                            except Exception as e:
                                logger.error(f"Error sending to client {client_id}: {e}")
                                disconnected_clients.append(client_id)
                    
                    # Remove disconnected clients
                    for client_id in disconnected_clients:
                        if client_id in self.connections:
                            del self.connections[client_id]
                        if client_id in self.subscribers[item["stream"]]:
                            self.subscribers[item["stream"]].remove(client_id)
                            
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing data queue: {e}")
    
    async def stop_server(self):
        """Stop WebSocket server"""
        self.running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("WebSocket server stopped")


class MarketDataStream:
    """Real-time market data streaming from various sources"""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.running = False
        self.data_sources = {}
        
    async def start_streaming(self):
        """Start streaming market data from all sources"""
        self.running = True
        
        # Start streaming tasks for different data sources
        tasks = [
            asyncio.create_task(self._stream_forex_data()),
            asyncio.create_task(self._stream_crypto_data()),
            asyncio.create_task(self._stream_stock_data()),
            asyncio.create_task(self._stream_social_signals())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _stream_forex_data(self):
        """Stream real-time forex data"""
        while self.running:
            try:
                # Simulate real-time forex data (replace with actual API)
                forex_data = {
                    "EUR/USD": {"bid": 1.1577, "ask": 1.1579, "change": 0.0012},
                    "GBP/USD": {"bid": 1.3256, "ask": 1.3258, "change": -0.0008},
                    "USD/JPY": {"bid": 159.85, "ask": 159.87, "change": 0.15}
                }
                
                self.ws_manager.broadcast_data("forex", {
                    "type": "price_update",
                    "data": forex_data
                })
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error streaming forex data: {e}")
                await asyncio.sleep(5)
    
    async def _stream_crypto_data(self):
        """Stream real-time cryptocurrency data"""
        while self.running:
            try:
                # Simulate real-time crypto data (replace with Binance WebSocket)
                crypto_data = {
                    "BTC/USD": {"price": 68212, "change": 1.2, "volume": 1234567},
                    "ETH/USD": {"price": 3456, "change": -0.8, "volume": 987654}
                }
                
                self.ws_manager.broadcast_data("crypto", {
                    "type": "price_update",
                    "data": crypto_data
                })
                
                await asyncio.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logger.error(f"Error streaming crypto data: {e}")
                await asyncio.sleep(5)
    
    async def _stream_stock_data(self):
        """Stream real-time stock data"""
        while self.running:
            try:
                # Simulate real-time stock data (replace with actual API)
                stock_data = {
                    "AAPL": {"price": 252.09, "change": 0.5, "volume": 4567890},
                    "SPX500": {"price": 6590.5, "change": 0.3, "volume": 1234567}
                }
                
                self.ws_manager.broadcast_data("stocks", {
                    "type": "price_update",
                    "data": stock_data
                })
                
                await asyncio.sleep(3)  # Update every 3 seconds
                
            except Exception as e:
                logger.error(f"Error streaming stock data: {e}")
                await asyncio.sleep(5)
    
    async def _stream_social_signals(self):
        """Stream real-time social signals"""
        while self.running:
            try:
                # Simulate social signals (replace with actual social media monitoring)
                social_signals = {
                    "sentiment": {"positive": 0.65, "negative": 0.15, "neutral": 0.20},
                    "trending_topics": ["AI", "Fed", "Earnings", "Oil"],
                    "high_impact_events": [
                        {"source": "Twitter", "content": "Fed announces rate decision", "impact": "high"},
                        {"source": "Reddit", "content": "Tech earnings beat expectations", "impact": "medium"}
                    ]
                }
                
                self.ws_manager.broadcast_data("social_signals", {
                    "type": "signal_update",
                    "data": social_signals
                })
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error streaming social signals: {e}")
                await asyncio.sleep(10)
    
    def stop_streaming(self):
        """Stop market data streaming"""
        self.running = False


class WebSocketClient:
    """WebSocket client for connecting to streaming data"""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.websocket = None
        self.callbacks = {}
        
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"Connected to WebSocket server: {self.uri}")
            
            # Start listening for messages
            asyncio.create_task(self._listen())
            
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {e}")
    
    async def _listen(self):
        """Listen for messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening to WebSocket: {e}")
    
    async def _handle_message(self, message: Dict):
        """Handle incoming messages"""
        msg_type = message.get("type")
        stream = message.get("stream")
        
        if msg_type == "data" and stream in self.callbacks:
            for callback in self.callbacks[stream]:
                await callback(message["data"])
    
    def subscribe(self, stream: str, callback: Callable):
        """Subscribe to a data stream"""
        if stream not in self.callbacks:
            self.callbacks[stream] = []
        self.callbacks[stream].append(callback)
        
        # Send subscription message
        if self.websocket:
            asyncio.create_task(self.websocket.send(json.dumps({
                "type": "subscribe",
                "streams": [stream]
            })))
    
    async def unsubscribe(self, stream: str):
        """Unsubscribe from a data stream"""
        if stream in self.callbacks:
            del self.callbacks[stream]
        
        # Send unsubscription message
        if self.websocket:
            asyncio.create_task(self.websocket.send(json.dumps({
                "type": "unsubscribe",
                "streams": [stream]
            })))
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
