#!/bin/bash

# QuantumTrade Engine v3.1 - Quick Deployment Script
# This script automates the deployment process

echo "=== QuantumTrade Engine v3.1 Deployment Script ==="
echo ""

# Check if Docker is installed
if command -v docker &> /dev/null; then
    echo "Docker found - using Docker deployment..."
    
    # Create Dockerfile if it doesn't exist
    if [ ! -f "Dockerfile" ]; then
        echo "Creating Dockerfile..."
        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "dashboards/pro_trading_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF
    fi
    
    # Build Docker image
    echo "Building Docker image..."
    docker build -t quantumtrade .
    
    # Check if .env file exists
    if [ ! -f "config/.env" ]; then
        echo "WARNING: config/.env not found. Please configure your environment variables."
        echo "Creating template .env file..."
        cp config/.env.example config/.env 2>/dev/null || cat > config/.env << 'EOF'
# MongoDB Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/quantumtrade_social
MONGODB_DATABASE_NAME=quantumtrade_social

# Twitter API (Optional)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Reddit API (Optional)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
EOF
        echo "Please edit config/.env with your actual credentials."
    fi
    
    # Run Docker container
    echo "Starting QuantumTrade Engine..."
    docker run -d -p 8501:8501 --name quantumtrade --restart unless-stopped --env-file config/.env quantumtrade
    
    echo ""
    echo "=== Deployment Complete! ==="
    echo "Access your QuantumTrade Engine at: http://localhost:8501"
    echo ""
    echo "To check logs: docker logs quantumtrade"
    echo "To stop: docker stop quantumtrade"
    echo "To restart: docker restart quantumtrade"
    
else
    echo "Docker not found - using local deployment..."
    
    # Check Python version
    python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
        echo "ERROR: Python 3.8+ required. Found Python $python_version"
        exit 1
    fi
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Check .env file
    if [ ! -f "config/.env" ]; then
        echo "WARNING: config/.env not found. Please configure your environment variables."
    fi
    
    # Run the application
    echo "Starting QuantumTrade Engine..."
    echo "Access at: http://localhost:8501"
    echo "Press Ctrl+C to stop"
    echo ""
    
    streamlit run dashboards/pro_trading_dashboard.py --server.port=8501
fi

echo ""
echo "=== Post-Deployment Checklist ==="
echo "1. Configure your MongoDB connection in config/.env"
echo "2. Add Twitter Bearer Token for real social signals"
echo "3. Test all features in the dashboard"
echo "4. Set up SSL/HTTPS for production"
echo "5. Configure monitoring and backups"
echo ""
echo "For detailed deployment options, see: DEPLOYMENT_GUIDE.md"
echo "For marketing materials, see: MARKETING_OVERVIEW.md"
echo "For API documentation, see: docs/QuantumTrade.md"
