#!/usr/bin/env python3
import os
import subprocess
import sys

# Install dependencies
print("Installing dependencies...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

# Start Streamlit app
print("Starting QuantumTrade Engine...")
os.system(f"streamlit run dashboards/pro_trading_dashboard.py --server.port={os.environ.get('PORT', 8501)} --server.address=0.0.0.0")
