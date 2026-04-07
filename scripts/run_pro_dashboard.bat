@echo off
echo.
echo    ========================================
echo       FORTRADE PRO Trading Terminal v3.0
echo    ========================================
echo.
echo    Starting Professional Dashboard...
echo    Dashboard will open in your browser
echo.
python -m streamlit run pro_trading_dashboard.py --server.port 8501
pause
