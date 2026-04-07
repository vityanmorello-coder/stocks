# QuantumTrade Engine v3.1 - Complete Deployment Guide

## Quick Start Deployment Options

### Option 1: Local Development (Fastest)
```bash
# Clone the project
git clone <your-repo-url>
cd S-P-500

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with your MongoDB Atlas connection string

# Install dependencies
pip install -r requirements.txt

# Run the application
run.bat  # Windows
# or
./run.sh  # Linux/Mac

# Access at: http://localhost:8501
```

### Option 2: Docker Deployment (Recommended for Production)
```dockerfile
# Create Dockerfile
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
```

```bash
# Build and run Docker container
docker build -t quantumtrade .
docker run -p 8501:8501 --env-file config/.env quantumtrade
```

### Option 3: Cloud Deployment (Heroku)
```bash
# Create Procfile
web: streamlit run dashboards/pro_trading_dashboard.py --server.port=$PORT --server.address=0.0.0.0

# Deploy to Heroku
heroku create quantumtrade-app
heroku config:set TWITTER_BEARER_TOKEN=your_token_here
heroku config:set MONGO_URI=your_mongodb_uri
git push heroku main
```

### Option 4: Cloud Deployment (AWS EC2)
```bash
# Launch EC2 instance (Ubuntu 22.04)
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv nginx -y

# Clone and setup
git clone <your-repo-url>
cd S-P-500
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup systemd service
sudo nano /etc/systemd/system/quantumtrade.service
```

```ini
# quantumtrade.service content
[Unit]
Description=QuantumTrade Engine
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/S-P-500
Environment=PATH=/home/ubuntu/S-P-500/venv/bin
ExecStart=/home/ubuntu/S-P-500/venv/bin/streamlit run dashboards/pro_trading_dashboard.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl enable quantumtrade
sudo systemctl start quantumtrade

# Setup Nginx reverse proxy
sudo nano /etc/nginx/sites-available/quantumtrade
```

```nginx
# Nginx configuration
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/quantumtrade /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Option 5: Cloud Deployment (DigitalOcean)
```bash
# Create Droplet (Ubuntu 22.04 with Docker)
# SSH into droplet
ssh root@your-droplet-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Clone and deploy
git clone <your-repo-url>
cd S-P-500
docker build -t quantumtrade .
docker run -d -p 8501:8501 --name quantumtrade --restart unless-stopped --env-file config/.env quantumtrade
```

### Option 6: Static Website Deployment (Marketing Site Only)
```bash
# Deploy marketing site to Netlify/Vercel
cd web
# Upload quantumtrade_marketing.html to your hosting provider
# Or use Netlify CLI:
netlify deploy --prod --dir=. --site=your-site-name
```

## Environment Configuration

### Required Environment Variables
```ini
# MongoDB Atlas (Required)
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/quantumtrade_social
MONGODB_DATABASE_NAME=quantumtrade_social

# Twitter API (Optional - for real social signals)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Reddit API (Optional)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret

# Trading APIs (Optional - for real trading)
OANDA_API_KEY=your_oanda_api_key
OANDA_ACCOUNT_ID=your_oanda_account_id
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
```

## Security Configuration

### SSL/HTTPS Setup
```bash
# For Nginx/Ubuntu
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# For Docker
# Use nginx-proxy with Let's Encrypt companion
docker run -d -p 80:80 -p 443:443 \
  -v /path/to/certs:/etc/nginx/certs:ro \
  -v /var/run/docker.sock:/tmp/docker.sock:ro \
  jwilder/nginx-proxy
```

### Firewall Configuration
```bash
# Ubuntu UFW
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# AWS Security Groups
# Allow: SSH (22), HTTP (80), HTTPS (443)
```

## Performance Optimization

### Database Optimization
```python
# MongoDB Atlas optimization
# - Enable M30+ cluster for production
# - Configure proper indexes
# - Enable auto-scaling
# - Set up backup automation
```

### Caching Setup
```bash
# Install Redis for caching
sudo apt install redis-server
# Configure in your application for session storage
```

### Load Balancing
```nginx
# Nginx load balancer configuration
upstream quantumtrade {
    server 127.0.0.1:8501;
    server 127.0.0.1:8502;
    server 127.0.0.1:8503;
}

server {
    listen 80;
    location / {
        proxy_pass http://quantumtrade;
    }
}
```

## Monitoring and Logging

### Application Monitoring
```python
# Add to your application
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/quantumtrade.log'),
        logging.StreamHandler()
    ]
)
```

### System Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs
# For detailed monitoring, consider:
# - Prometheus + Grafana
# - DataDog
# - New Relic
```

## Backup Strategy

### Database Backups
```bash
# MongoDB Atlas automated backups
# Enable in Atlas dashboard:
# - Daily backups
# - Point-in-time recovery
# - Cross-region replication
```

### Application Backups
```bash
# Create backup script
#!/bin/bash
tar -czf /backups/quantumtrade-$(date +%Y%m%d).tar.gz \
    /path/to/S-P-500 \
    --exclude=node_modules \
    --exclude=.git \
    --exclude=logs

# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

## Scaling Considerations

### Horizontal Scaling
- Use Docker containers with orchestration (Kubernetes/Docker Swarm)
- Implement load balancer (Nginx/HAProxy)
- Use managed database (MongoDB Atlas)
- Implement Redis for session storage

### Vertical Scaling
- Increase CPU/RAM based on user load
- Monitor resource usage with cloud provider tools
- Auto-scale based on metrics

## Troubleshooting

### Common Issues
1. **Port conflicts**: Change Streamlit port with `--server.port=8502`
2. **MongoDB connection**: Check network access and credentials
3. **Memory issues**: Increase server RAM or optimize code
4. **SSL errors**: Verify certificate configuration

### Health Checks
```bash
# Add health check endpoint
# Monitor with:
curl -f http://localhost:8501/health || exit 1
```

## Cost Optimization

### Cloud Provider Tips
- Use reserved instances for long-term deployments
- Implement auto-scaling to handle variable load
- Use spot instances for non-critical workloads
- Monitor and optimize data transfer costs

### Database Cost
- Start with MongoDB Atlas M10 cluster
- Scale based on actual usage
- Implement data retention policies
- Use appropriate storage tier

## Support and Maintenance

### Regular Maintenance
- Weekly security updates
- Monthly performance reviews
- Quarterly backup verification
- Annual security audit

### Support Channels
- Documentation: `/docs/QuantumTrade.md`
- GitHub Issues: Create issues for bugs
- Community: Join trading communities
- Professional: Contact for enterprise support

## Compliance and Legal

### Data Protection
- GDPR compliance for EU users
- Data encryption at rest and in transit
- User data retention policies
- Privacy policy implementation

### Financial Regulations
- Risk disclosure statements
- User agreement terms
- Compliance with local trading regulations
- Anti-money laundering (AML) considerations

---

## Quick Deployment Checklist

- [ ] Environment variables configured
- [ ] Database connection tested
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Backup strategy implemented
- [ ] Monitoring setup
- [ ] Load testing performed
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Support channels established

Choose the deployment option that best fits your needs and follow the corresponding steps. For most users, **Docker deployment** provides the best balance of simplicity and scalability.
