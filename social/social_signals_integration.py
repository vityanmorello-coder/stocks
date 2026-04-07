"""
Integration patch for Social Signals Dashboard
This file contains the code to add the Social + Market Signals tab to the main dashboard.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import the social signals dashboard
from social_signals_dashboard import render_social_signals_tab

def add_social_signals_tab():
    """Add the social signals tab to the main dashboard"""
    # This function will be called from the main dashboard
    return render_social_signals_tab()

# Tab content for Social + Market Signals
def render_tab_content():
    """Render the Social + Market Signals tab content"""
    try:
        render_social_signals_tab()
    except Exception as e:
        import streamlit as st
        st.error(f"Error loading social signals: {e}")
        st.info("Please ensure all dependencies are installed and configured.")
