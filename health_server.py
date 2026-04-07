"""
FastAPI Health Endpoint for Vercel Keep-Alive
Lightweight endpoint to prevent Vercel free tier from sleeping
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import asyncio
import threading
import time

app = FastAPI(title="QuantumTrade Health API")

# Global keep-alive state
last_ping = datetime.now()
ping_count = 0

@app.get("/health")
async def health_check():
    """Health check endpoint for keep-alive pings"""
    global last_ping, ping_count
    last_ping = datetime.now()
    ping_count += 1
    
    return JSONResponse({
        "status": "healthy",
        "timestamp": last_ping.isoformat(),
        "service": "QuantumTrade Engine v3.1",
        "ping_count": ping_count,
        "uptime": "active"
    })

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "QuantumTrade Engine v3.1 Health API",
        "health": "/health",
        "status": "running"
    }

def start_health_server():
    """Start health server in background thread"""
    def run_server():
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    print("Starting QuantumTrade Health API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
