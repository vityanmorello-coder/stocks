"""
Vercel Serverless Function for QuantumTrade Engine
Main entry point for Vercel deployment
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

def handler(request):
    """Main handler for Vercel serverless function"""
    
    # Handle health check
    if request.method == 'GET' and request.url.endswith('/health'):
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'service': 'QuantumTrade Engine v3.1',
                'uptime': 'active'
            })
        }
    
    # Handle main app request
    if request.method == 'GET':
        try:
            # Import and start Streamlit app
            import subprocess
            
            # Set environment variables
            port = os.environ.get('PORT', '8501')
            os.environ['PORT'] = port
            
            # Start Streamlit in background
            subprocess.Popen([
                sys.executable, '-m', 'streamlit', 'run', 
                'dashboards/pro_trading_dashboard.py',
                '--server.port', port,
                '--server.address', '0.0.0.0',
                '--server.headless', 'true'
            ])
            
            # Return redirect response
            return {
                'statusCode': 302,
                'headers': {
                    'Location': f'/',
                    'Content-Type': 'text/html'
                },
                'body': 'Redirecting to QuantumTrade Engine...'
            }
            
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': f'Startup failed: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            }
    
    # Handle other methods
    return {
        'statusCode': 405,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'error': 'Method not allowed',
            'timestamp': datetime.now().isoformat()
        })
    }

# Vercel expects the handler to be named 'handler'
# This is the main entry point for the serverless function
