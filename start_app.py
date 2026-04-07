#!/usr/bin/env python3
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

# Install dependencies
print("Installing dependencies...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

# Start health server for keep-alive
def start_health_server():
    """Start FastAPI health server in background"""
    try:
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        
        app = FastAPI(title="QuantumTrade Health API")
        
        @app.get("/health")
        async def health_check():
            return JSONResponse({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "QuantumTrade Engine v3.1",
                "uptime": "active"
            })
        
        def run_health_server():
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
        
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        print("Health server started on port 8000")
        return health_thread
    except Exception as e:
        print(f"Health server failed: {e}")
        return None

# Start keep-alive thread
def start_keep_alive():
    """Keep app alive with internal pings"""
    def keep_alive_loop():
        while True:
            try:
                import requests
                # Ping our own health endpoint
                requests.get("http://localhost:8000/health", timeout=2)
                time.sleep(25)  # Ping every 25 seconds
            except:
                time.sleep(5)  # Quick retry on error
    
    keep_alive_thread = threading.Thread(target=keep_alive_loop, daemon=True)
    keep_alive_thread.start()
    print("Keep-alive system started")

# Start background services
start_health_server()
time.sleep(2)  # Let health server start
start_keep_alive()

# Start Streamlit app
print("Starting QuantumTrade Engine...")
port = os.environ.get('PORT', 8501)
os.system(f"streamlit run dashboards/pro_trading_dashboard.py --server.port={port} --server.address=0.0.0.0")
