"""
External Vercel Keep-Alive Service
Run this anywhere to keep your Vercel app alive 24/7
"""

import requests
import time
import threading
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VercelKeepAliveService:
    def __init__(self, app_url: str, ping_interval: int = 25):
        self.app_url = app_url.rstrip('/')
        self.ping_interval = ping_interval
        self.running = False
        self.stats = {
            'total_pings': 0,
            'successful_pings': 0,
            'failed_pings': 0,
            'last_success': None,
            'last_failure': None
        }
    
    def ping_app(self):
        """Send a ping to keep the app awake"""
        try:
            # Ping health endpoint
            response = requests.get(f"{self.app_url}/health", timeout=10)
            
            self.stats['total_pings'] += 1
            
            if response.status_code == 200:
                self.stats['successful_pings'] += 1
                self.stats['last_success'] = datetime.now()
                logger.info(f"Keep-alive ping successful: {response.json()}")
                return True
            else:
                self.stats['failed_pings'] += 1
                self.stats['last_failure'] = datetime.now()
                logger.warning(f"Ping failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.stats['failed_pings'] += 1
            self.stats['last_failure'] = datetime.now()
            logger.error(f"Keep-alive ping error: {e}")
            return False
    
    def start_keep_alive(self):
        """Start the keep-alive service"""
        self.running = True
        logger.info(f"Starting Vercel keep-alive service for {self.app_url}")
        logger.info(f"Ping interval: {self.ping_interval} seconds")
        
        while self.running:
            try:
                self.ping_app()
                time.sleep(self.ping_interval)
            except KeyboardInterrupt:
                logger.info("Keep-alive service stopped by user")
                break
            except Exception as e:
                logger.error(f"Keep-alive service error: {e}")
                time.sleep(5)  # Quick retry on error
    
    def stop_keep_alive(self):
        """Stop the keep-alive service"""
        self.running = False
        logger.info("Vercel keep-alive service stopped")
    
    def get_stats(self):
        """Get keep-alive statistics"""
        success_rate = (self.stats['successful_pings'] / self.stats['total_pings'] * 100) if self.stats['total_pings'] > 0 else 0
        
        return {
            'total_pings': self.stats['total_pings'],
            'successful_pings': self.stats['successful_pings'],
            'failed_pings': self.stats['failed_pings'],
            'success_rate': f"{success_rate:.1f}%",
            'last_success': self.stats['last_success'],
            'last_failure': self.stats['last_failure'],
            'app_url': self.app_url
        }


def main():
    """Main function to run keep-alive service"""
    print("=== Vercel Keep-Alive Service ===")
    print("This service keeps your Vercel app awake 24/7")
    print()
    
    # Get app URL from user
    app_url = input("Enter your Vercel app URL (e.g., https://your-app.vercel.app): ").strip()
    if not app_url:
        print("No URL provided. Using default...")
        app_url = "https://stocks-xxxx.vercel.app"  # Replace with your actual URL
    
    # Create and start service
    keeper = VercelKeepAliveService(app_url)
    
    try:
        keeper.start_keep_alive()
    except KeyboardInterrupt:
        print("\nStopping service...")
        keeper.stop_keep_alive()
        
        # Show final stats
        stats = keeper.get_stats()
        print("\n=== Final Statistics ===")
        print(f"Total pings: {stats['total_pings']}")
        print(f"Successful: {stats['successful_pings']}")
        print(f"Failed: {stats['failed_pings']}")
        print(f"Success rate: {stats['success_rate']}")
        if stats['last_success']:
            print(f"Last success: {stats['last_success']}")
        print("\nService stopped.")


if __name__ == "__main__":
    main()
