"""
QuantumTrade Engine - MongoDB Database Manager
================================================
Handles all data persistence: users, positions, trades, settings, alerts, audit logs.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import secrets

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    MongoDB Database Manager for QuantumTrade Engine.
    
    Collections:
        - users: User accounts with hashed passwords and roles
        - positions: Open and closed trading positions
        - trades: Complete trade history with P&L
        - settings: Per-user settings (capital, alerts, preferences)
        - alerts: Signal alert history
        - sessions: Login session tokens
    """
    
    def __init__(self, connection_string: str = None):
        """
        Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB Atlas connection URI.
                              Falls back to MONGO_URI env var or local.
        """
        # Load from .env file if exists (look in config folder)
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()
        
        self.connection_string = (
            connection_string 
            or os.environ.get('MONGO_URI') 
            or ''
        )
        self.client = None
        self.db = None
        self._connected = False
        
    def connect(self) -> bool:
        """Establish MongoDB connection and set up indexes."""
        try:
            self.client = MongoClient(
                self.connection_string, 
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                tlsAllowInvalidCertificates=True
            )
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client['quantumtrade']
            self._connected = True
            
            # Create indexes for performance
            self._setup_indexes()
            
            logger.info("MongoDB connected successfully")
            print("[DB] MongoDB connected successfully")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            print(f"[DB ERROR] MongoDB connection failed: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"MongoDB unexpected error: {e}")
            print(f"[DB ERROR] Unexpected: {e}")
            self._connected = False
            return False
    
    def _setup_indexes(self):
        """Create database indexes for fast queries."""
        if not self._connected:
            return

        self.db.users.create_index('username', unique=True)
        self.db.positions.create_index([('user_id', ASCENDING), ('status', ASCENDING)])
        self.db.positions.create_index([('user_id', ASCENDING), ('created_at', DESCENDING)])
        self.db.trades.create_index([('user_id', ASCENDING), ('timestamp', DESCENDING)])
        self.db.settings.create_index('user_id', unique=True)
        self.db.alerts.create_index([('user_id', ASCENDING), ('timestamp', DESCENDING)])
        self.db.sessions.create_index('token', unique=True)
        self.db.sessions.create_index('expires_at', expireAfterSeconds=0)
        # Audit logs: by user, event type, timestamp
        self.db.audit_logs.create_index([('user_id', ASCENDING), ('timestamp', DESCENDING)])
        self.db.audit_logs.create_index([('event', ASCENDING), ('timestamp', DESCENDING)])
        self.db.audit_logs.create_index([('ip_address', ASCENDING), ('timestamp', DESCENDING)])
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, username: str, password: str, role: str = 'user',
                    display_name: str = '', email: str = '') -> Optional[str]:
        """
        Create a new user. Only admin should call this.
        Uses bcrypt if available, salted SHA-256 as fallback.
        """
        if not self._connected:
            return None

        # Use security layer for hashing
        try:
            from auth.security import get_password_manager
            pw_data = get_password_manager().hash(password)
        except ImportError:
            import hashlib
            salt = secrets.token_hex(32)
            pw_data = {
                'hash': hashlib.sha256((password + salt).encode()).hexdigest(),
                'algorithm': 'sha256',
                'salt': salt,
            }

        user_doc = {
            'username': username.lower().strip(),
            'password_hash': pw_data['hash'],
            'password_salt': pw_data.get('salt', ''),
            'password_algorithm': pw_data.get('algorithm', 'sha256'),
            'role': role,
            'display_name': display_name or username,
            'email': email,
            'created_at': datetime.utcnow(),
            'last_login': None,
            'is_active': True,
            'login_count': 0,
            'totp_secret': None,
            'totp_enabled': False,
            'failed_attempts': 0,
            'locked_until': None,
        }

        try:
            result = self.db.users.insert_one(user_doc)
            user_id = str(result.inserted_id)
            self._create_default_settings(user_id)
            print(f"[DB] User created: {username} (role: {role}, algo: {pw_data['algorithm']})")
            return user_id
        except Exception as e:
            if 'duplicate key' in str(e).lower():
                print(f"[DB] User '{username}' already exists")
            else:
                print(f"[DB ERROR] Create user failed: {e}")
            return None
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user from the database.
        Returns True if successful, False otherwise.
        """
        if not self._connected:
            return False
        
        try:
            # Delete user's sessions
            self.db.sessions.delete_many({'username': username.lower().strip()})
            
            # Delete user record
            result = self.db.users.delete_one({'username': username.lower().strip()})
            
            if result.deleted_count > 0:
                print(f"[DB] User deleted: {username}")
                return True
            else:
                print(f"[DB] User not found: {username}")
                return False
                
        except Exception as e:
            print(f"[DB ERROR] Delete user failed: {e}")
            return False
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Verify login credentials using bcrypt or SHA-256.
        Automatically upgrades SHA-256 hashes to bcrypt on successful login.
        Returns user dict or None.
        """
        if not self._connected:
            return None

        user = self.db.users.find_one({
            'username': username.lower().strip(),
            'is_active': True
        })

        if not user:
            return None

        # Verify using security layer
        try:
            from auth.security import get_password_manager
            pm = get_password_manager()
            stored = {
                'hash': user['password_hash'],
                'algorithm': user.get('password_algorithm', 'sha256'),
                'salt': user.get('password_salt', user.get('salt', '')),
            }
            if not pm.verify(password, stored):
                return None
            # Upgrade hash algorithm if needed
            if pm.needs_upgrade(stored):
                new_pw = pm.hash(password)
                self.db.users.update_one(
                    {'_id': user['_id']},
                    {'$set': {
                        'password_hash': new_pw['hash'],
                        'password_algorithm': new_pw['algorithm'],
                        'password_salt': new_pw.get('salt', ''),
                    }}
                )
                print(f"[DB] Password upgraded to bcrypt for: {username}")
        except ImportError:
            import hashlib
            salt = user.get('password_salt', user.get('salt', ''))
            pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            if pw_hash != user['password_hash']:
                return None

        # Update last login
        self.db.users.update_one(
            {'_id': user['_id']},
            {
                '$set': {'last_login': datetime.utcnow(), 'failed_attempts': 0},
                '$inc': {'login_count': 1}
            }
        )

        return {
            'user_id': str(user['_id']),
            'username': user['username'],
            'role': user['role'],
            'display_name': user['display_name'],
            'email': user.get('email', ''),
            'totp_enabled': user.get('totp_enabled', False),
        }
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user info by ID."""
        if not self._connected:
            return None
        from bson import ObjectId
        try:
            user = self.db.users.find_one({'_id': ObjectId(user_id)})
            if user:
                return {
                    'user_id': str(user['_id']),
                    'username': user['username'],
                    'role': user['role'],
                    'display_name': user['display_name'],
                    'email': user.get('email', ''),
                    'created_at': user['created_at'],
                    'last_login': user.get('last_login'),
                    'login_count': user.get('login_count', 0),
                }
        except Exception:
            pass
        return None
    
    def list_users(self) -> List[Dict]:
        """List all users (admin only)."""
        if not self._connected:
            return []
        users = []
        for user in self.db.users.find({}, {'password_hash': 0, 'salt': 0}):
            users.append({
                'user_id': str(user['_id']),
                'username': user['username'],
                'role': user['role'],
                'display_name': user['display_name'],
                'is_active': user.get('is_active', True),
                'last_login': user.get('last_login'),
                'login_count': user.get('login_count', 0),
            })
        return users
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_session(self, user_id: str, username: str = '',
                       role: str = 'user', hours: int = 24,
                       remember: bool = False) -> str:
        """
        Create a JWT session token (or secure random fallback).
        Also stores in DB for revocation support.
        """
        if not self._connected:
            return ''

        try:
            from auth.security import get_jwt_manager
            token = get_jwt_manager().create_token(
                user_id=user_id, username=username,
                role=role, remember=remember
            )
        except ImportError:
            token = secrets.token_urlsafe(64)

        expire_hours = (168 if remember else hours)
        self.db.sessions.insert_one({
            'token': token,
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=expire_hours),
        })

        return token

    def validate_session(self, token: str) -> Optional[str]:
        """
        Validate session. Tries JWT decode first, then DB lookup.
        Returns user_id if valid.
        """
        if not self._connected or not token:
            return None

        # Try JWT decode first (stateless, fast)
        try:
            from auth.security import get_jwt_manager
            user_info = get_jwt_manager().get_user_from_token(token)
            if user_info:
                # Also verify not revoked in DB
                session = self.db.sessions.find_one({
                    'token': token,
                    'expires_at': {'$gt': datetime.utcnow()}
                })
                return session['user_id'] if session else None
        except ImportError:
            pass

        # Fallback: DB-only lookup
        session = self.db.sessions.find_one({
            'token': token,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        return session['user_id'] if session else None
    
    def delete_session(self, token: str):
        """Logout — delete session."""
        if self._connected:
            self.db.sessions.delete_one({'token': token})
    
    # ==================== SETTINGS ====================
    
    def _create_default_settings(self, user_id: str):
        """Create default settings for a new user."""
        self.db.settings.update_one(
            {'user_id': user_id},
            {'$setOnInsert': {
                'user_id': user_id,
                'initial_capital': 100.0,
                'selected_symbols': [
                    'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD',
                    'XAU/USD', 'XAG/USD', 'OIL/USD', 'AAPL', 'SPX500', 'BTC/USD'
                ],
                'alert_threshold': 70,
                'alerts_enabled': True,
                'sound_alerts': True,
                'auto_refresh': False,
                'refresh_interval': 30,
                'theme': 'dark',
                'updated_at': datetime.utcnow(),
            }},
            upsert=True
        )
    
    def get_settings(self, user_id: str) -> Dict:
        """Get user settings."""
        if not self._connected:
            return {}
        
        settings = self.db.settings.find_one({'user_id': user_id})
        if settings:
            settings.pop('_id', None)
            return settings
        return {}
    
    def save_settings(self, user_id: str, settings: Dict):
        """Save/update user settings."""
        if not self._connected:
            return
        
        settings['user_id'] = user_id
        settings['updated_at'] = datetime.utcnow()
        
        self.db.settings.update_one(
            {'user_id': user_id},
            {'$set': settings},
            upsert=True
        )
    
    # ==================== POSITIONS ====================
    
    def save_position(self, user_id: str, position: Dict) -> Optional[str]:
        """Save an open position."""
        if not self._connected:
            return None
        
        pos_doc = {
            'user_id': user_id,
            'order_id': position.get('order_id', ''),
            'symbol': position['symbol'],
            'side': position['side'],
            'entry_price': position['entry_price'],
            'quantity': position.get('quantity', 0),
            'stop_loss': position.get('stop_loss'),
            'take_profit': position.get('take_profit'),
            'strategy': position.get('strategy', ''),
            'confidence': position.get('confidence', 0),
            'status': 'open',  # 'open' or 'closed'
            'pnl': 0.0,
            'close_price': None,
            'created_at': datetime.utcnow(),
            'closed_at': None,
        }
        
        result = self.db.positions.insert_one(pos_doc)
        return str(result.inserted_id)
    
    def get_open_positions(self, user_id: str) -> List[Dict]:
        """Get all open positions for a user."""
        if not self._connected:
            return []
        
        positions = []
        for pos in self.db.positions.find({'user_id': user_id, 'status': 'open'}).sort('created_at', DESCENDING):
            pos['_id'] = str(pos['_id'])
            positions.append(pos)
        return positions
    
    def close_position(self, user_id: str, order_id: str, close_price: float, pnl: float):
        """Close a position."""
        if not self._connected:
            return
        
        self.db.positions.update_one(
            {'user_id': user_id, 'order_id': order_id, 'status': 'open'},
            {'$set': {
                'status': 'closed',
                'close_price': close_price,
                'pnl': pnl,
                'closed_at': datetime.utcnow(),
            }}
        )
    
    def get_position_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get closed position history."""
        if not self._connected:
            return []
        
        positions = []
        for pos in self.db.positions.find(
            {'user_id': user_id, 'status': 'closed'}
        ).sort('closed_at', DESCENDING).limit(limit):
            pos['_id'] = str(pos['_id'])
            positions.append(pos)
        return positions
    
    # ==================== TRADES ====================
    
    def save_trade(self, user_id: str, trade: Dict):
        """Save a trade to history."""
        if not self._connected:
            return
        
        trade_doc = {
            'user_id': user_id,
            'symbol': trade['symbol'],
            'action': trade['action'],
            'price': trade['price'],
            'quantity': trade.get('quantity', 0),
            'pnl': trade.get('pnl', 0),
            'strategy': trade.get('strategy', ''),
            'confidence': trade.get('confidence', 0),
            'timestamp': datetime.utcnow(),
        }
        
        self.db.trades.insert_one(trade_doc)
    
    def get_trade_history(self, user_id: str, limit: int = 200) -> List[Dict]:
        """Get trade history for a user."""
        if not self._connected:
            return []
        
        trades = []
        for trade in self.db.trades.find(
            {'user_id': user_id}
        ).sort('timestamp', DESCENDING).limit(limit):
            trade['_id'] = str(trade['_id'])
            trades.append(trade)
        return trades
    
    def get_trade_stats(self, user_id: str) -> Dict:
        """Get trade statistics for a user."""
        if not self._connected:
            return {}
        
        trades = list(self.db.trades.find({'user_id': user_id}))
        if not trades:
            return {'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0, 'total_pnl': 0}
        
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losses = sum(1 for t in trades if t.get('pnl', 0) < 0)
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        return {
            'total': len(trades),
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / len(trades) * 100) if trades else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(trades) if trades else 0,
        }
    
    # ==================== ALERTS ====================
    
    def save_alert(self, user_id: str, alert: Dict):
        """Save an alert to history."""
        if not self._connected:
            return
        
        alert_doc = {
            'user_id': user_id,
            'symbol': alert['symbol'],
            'action': alert['action'],
            'confidence': alert['confidence'],
            'price': alert['price'],
            'strategy': alert.get('strategy', ''),
            'timestamp': datetime.utcnow(),
        }
        
        self.db.alerts.insert_one(alert_doc)
    
    def get_alerts(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get alert history."""
        if not self._connected:
            return []
        
        alerts = []
        for alert in self.db.alerts.find(
            {'user_id': user_id}
        ).sort('timestamp', DESCENDING).limit(limit):
            alert['_id'] = str(alert['_id'])
            alerts.append(alert)
        return alerts
    
    # ==================== PORTFOLIO ====================
    
    def save_portfolio_snapshot(self, user_id: str, balance: float, equity: float):
        """Save daily portfolio snapshot for equity curve."""
        if not self._connected:
            return
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        self.db.portfolio_snapshots.update_one(
            {'user_id': user_id, 'date': today},
            {'$set': {
                'user_id': user_id,
                'date': today,
                'balance': balance,
                'equity': equity,
                'timestamp': datetime.utcnow(),
            }},
            upsert=True
        )
    
    def get_equity_curve(self, user_id: str, days: int = 90) -> List[Dict]:
        """Get equity curve data."""
        if not self._connected:
            return []

        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        snapshots = list(self.db.portfolio_snapshots.find(
            {'user_id': user_id, 'date': {'$gte': cutoff}}
        ).sort('date', ASCENDING))
        for s in snapshots:
            s['_id'] = str(s['_id'])
        return snapshots

    # ==================== AUDIT LOGS ====================

    def log_event(self, event: str, user_id: str = None, username: str = None,
                  ip_address: str = None, details: Dict = None, success: bool = True):
        """
        Write an audit log entry.

        Events: LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, TRADE_EXECUTED,
                POSITION_CLOSED, PASSWORD_CHANGED, USER_CREATED,
                SETTINGS_CHANGED, 2FA_ENABLED, LOCKOUT
        """
        if not self._connected:
            return

        log_doc = {
            'event': event,
            'user_id': user_id,
            'username': username,
            'ip_address': ip_address or 'unknown',
            'success': success,
            'details': details or {},
            'timestamp': datetime.utcnow(),
        }

        try:
            self.db.audit_logs.insert_one(log_doc)
            level = logging.INFO if success else logging.WARNING
            logger.log(level, f"[AUDIT] {event} | user={username} | ip={ip_address} | ok={success}")
        except Exception as e:
            logger.error(f"[AUDIT] Failed to write log: {e}")

    def get_audit_logs(self, user_id: str = None, event: str = None,
                       limit: int = 100) -> List[Dict]:
        """Query audit logs. Admin can query all users."""
        if not self._connected:
            return []

        query = {}
        if user_id:
            query['user_id'] = user_id
        if event:
            query['event'] = event

        logs = []
        for log in self.db.audit_logs.find(query).sort('timestamp', DESCENDING).limit(limit):
            log['_id'] = str(log['_id'])
            logs.append(log)
        return logs

    # ==================== 2FA MANAGEMENT ====================

    def enable_totp(self, user_id: str, secret: str):
        """Save TOTP secret and mark 2FA as enabled."""
        if not self._connected:
            return
        from bson import ObjectId
        self.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'totp_secret': secret, 'totp_enabled': True}}
        )

    def disable_totp(self, user_id: str):
        """Disable 2FA for a user."""
        if not self._connected:
            return
        from bson import ObjectId
        self.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'totp_secret': None, 'totp_enabled': False}}
        )

    def get_totp_secret(self, user_id: str) -> Optional[str]:
        """Get stored TOTP secret for a user."""
        if not self._connected:
            return None
        from bson import ObjectId
        try:
            user = self.db.users.find_one(
                {'_id': ObjectId(user_id)},
                {'totp_secret': 1}
            )
            return user.get('totp_secret') if user else None
        except Exception:
            return None

    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._connected = False


# ==================== SINGLETON ====================

_db_instance = None

def get_database(connection_string: str = None) -> DatabaseManager:
    """Get or create the singleton database instance."""
    global _db_instance
    if _db_instance is None or not _db_instance.is_connected:
        _db_instance = DatabaseManager(connection_string)
        _db_instance.connect()
    return _db_instance
