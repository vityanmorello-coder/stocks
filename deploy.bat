@echo off
REM QuantumTrade Engine v3.1 - Quick Deployment Script for Windows
REM This script automates the deployment process

echo === QuantumTrade Engine v3.1 Deployment Script ===
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% == 0 (
    echo Docker found - using Docker deployment...
    
    REM Create Dockerfile if it doesn't exist
    if not exist "Dockerfile" (
        echo Creating Dockerfile...
        (
            echo FROM python:3.11-slim
            echo WORKDIR /app
            echo.
            echo # Install system dependencies
            echo RUN apt-get update ^&^& apt-get install -y ^
            echo     gcc ^
            echo     g++ ^
            echo     ^&^& rm -rf /var/lib/apt/lists/*
            echo.
            echo # Copy requirements and install Python dependencies
            echo COPY requirements.txt .
            echo RUN pip install --no-cache-dir -r requirements.txt
            echo.
            echo # Copy application code
            echo COPY . .
            echo.
            echo # Expose port
            echo EXPOSE 8501
            echo.
            echo # Run the application
            echo CMD ["streamlit", "run", "dashboards/pro_trading_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
        ) > Dockerfile
    )
    
    REM Build Docker image
    echo Building Docker image...
    docker build -t quantumtrade .
    
    REM Check if .env file exists
    if not exist "config\.env" (
        echo WARNING: config\.env not found. Please configure your environment variables.
        echo Creating template .env file...
        if not exist "config" mkdir config
        (
            echo # MongoDB Configuration
            echo MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname
            echo MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/quantumtrade_social
            echo MONGODB_DATABASE_NAME=quantumtrade_social
            echo.
            echo # Twitter API ^(Optional^)
            echo TWITTER_BEARER_TOKEN=your_twitter_bearer_token
            echo.
            echo # Reddit API ^(Optional^)
            echo REDDIT_CLIENT_ID=your_reddit_client_id
            echo REDDIT_CLIENT_SECRET=your_reddit_client_secret
        ) > config\.env
        echo Please edit config\.env with your actual credentials.
    )
    
    REM Run Docker container
    echo Starting QuantumTrade Engine...
    docker run -d -p 8501:8501 --name quantumtrade --restart unless-stopped --env-file config\.env quantumtrade
    
    echo.
    echo === Deployment Complete! ===
    echo Access your QuantumTrade Engine at: http://localhost:8501
    echo.
    echo To check logs: docker logs quantumtrade
    echo To stop: docker stop quantumtrade
    echo To restart: docker restart quantumtrade
    
) else (
    echo Docker not found - using local deployment...
    
    REM Install dependencies
    echo Installing Python dependencies...
    pip install streamlit
    if exist requirements.txt (
        pip install -r requirements.txt
    ) else (
        echo Installing core dependencies...
        pip install pandas numpy requests pymongo streamlit-authenticator python-dotenv
    )
    
    REM Check .env file
    if not exist "config\.env" (
        echo WARNING: config\.env not found. Please configure your environment variables.
    )
    
    REM Run the application
    echo Starting QuantumTrade Engine...
    echo Access at: http://localhost:8501
    echo Press Ctrl+C to stop
    echo.
    
    streamlit run dashboards\pro_trading_dashboard.py --server.port=8501
)

echo.
echo === Post-Deployment Checklist ===
echo 1. Configure your MongoDB connection in config\.env
echo 2. Add Twitter Bearer Token for real social signals
echo 3. Test all features in the dashboard
echo 4. Set up SSL/HTTPS for production
echo 5. Configure monitoring and backups
echo.
echo For detailed deployment options, see: DEPLOYMENT_GUIDE.md
echo For marketing materials, see: MARKETING_OVERVIEW.md
echo For API documentation, see: docs\QuantumTrade.md

pause
