"""
Vercel entry point - QuantumTrade Engine
This file should be in the root for Vercel to find it
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
from datetime import datetime

app = FastAPI(title="QuantumTrade Engine v3.1")

# Load the marketing HTML
def load_marketing_page():
    try:
        with open("web/quantumtrade_marketing.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return """
        <html>
        <head><title>QuantumTrade Engine v3.1</title></head>
        <body>
        <h1>QuantumTrade Engine v3.1</h1>
        <p>Enterprise AI Trading Platform</p>
        <p>For full trading dashboard, run locally with: run.bat</p>
        </body>
        </html>
        """

@app.get("/")
async def home():
    """Main page - marketing site"""
    html_content = load_marketing_page()
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "QuantumTrade Engine v3.1",
        "version": "3.1.0",
        "environment": "vercel"
    })

@app.get("/api/dashboard")
async def dashboard_info():
    """Dashboard information"""
    return JSONResponse({
        "message": "QuantumTrade Engine Dashboard",
        "features": [
            "Real-time market data",
            "AI-powered signals",
            "Portfolio analytics",
            "Risk management",
            "Mobile responsive"
        ],
        "local_deployment": "Run 'run.bat' for full dashboard",
        "version": "3.1.0"
    })

# Vercel handler
def handler(request):
    """Vercel serverless function handler"""
    return app(request.scope, request.receive, request.send)
