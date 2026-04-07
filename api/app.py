"""
Vercel-compatible QuantumTrade Engine
Uses FastAPI instead of Streamlit for Vercel deployment
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
from datetime import datetime
import uvicorn

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

@app.get("/api/features")
async def features():
    """API features endpoint"""
    return JSONResponse({
        "features": {
            "ai_trading": "12 advanced AI modules",
            "real_time_data": "Sub-second market updates",
            "social_signals": "Twitter & RSS integration",
            "portfolio_analytics": "Comprehensive performance metrics",
            "risk_management": "Advanced position sizing",
            "mobile_responsive": "PWA support",
            "websocket_streaming": "Real-time data streaming"
        },
        "deployment": {
            "vercel": "Marketing site & API",
            "local": "Full trading dashboard",
            "docker": "Production deployment"
        }
    })

# Handle all other routes
@app.get("/{path:path}")
async def catch_all(path: str):
    """Catch all other routes"""
    if path.endswith('.html') or path.endswith('.css') or path.endswith('.js'):
        # Try to serve static files
        try:
            with open(f"web/{path}", "r") as f:
                return HTMLResponse(content=f.read())
        except:
            pass
    
    # Return to home page
    return await home()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
