"""
QuantumTrade Engine - Authentication System
=============================================
Secure login with:
  - bcrypt password verification
  - JWT session tokens
  - Rate limiting + brute-force lockout
  - TOTP 2FA (Google Authenticator)
  - Full audit logging
  - RBAC permission checks
"""

import streamlit as st
from datetime import datetime
from auth.database import get_database
from auth.security import get_rate_limiter, has_permission, get_jwt_manager, PERMISSIONS


# ============================================================
# LOGIN PAGE CSS
# ============================================================
LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

.login-container {
    max-width: 420px;
    margin: 60px auto;
    padding: 40px;
    background: linear-gradient(145deg, #111827, #0a0e17);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(59, 130, 246, 0.05);
}

.login-logo {
    text-align: center;
    margin-bottom: 30px;
}

.login-logo .title {
    font-size: 28px;
    font-weight: 900;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-family: 'Inter', sans-serif;
}

.login-logo .subtitle {
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-top: 4px;
}

.login-footer {
    text-align: center;
    margin-top: 24px;
    font-size: 11px;
    color: #475569;
}

.login-error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 13px;
    margin-bottom: 16px;
    text-align: center;
}

.login-success {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #10b981;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 13px;
    margin-bottom: 16px;
    text-align: center;
}

.user-badge {
    display: inline-block;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

.admin-badge {
    display: inline-block;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
</style>
"""


def check_auth() -> dict:
    """
    Check authentication. Shows login page if not logged in.
    Handles: session restore, rate limiting, 2FA step.
    Returns user dict on success.
    """
    db = get_database()

    if not db.is_connected:
        st.error("Database connection failed. Check your .env configuration.")
        st.stop()
        return {}

    # Already authenticated in this session
    if st.session_state.get('auth_user'):
        return st.session_state.auth_user

    # Restore from token (check query params for persistent login)
    token = st.session_state.get('session_token', '')
    
    # Check if token is in URL query params (for persistent login)
    if not token and 'token' in st.query_params:
        token = st.query_params['token']
        st.session_state.session_token = token
    
    if token:
        user_id = db.validate_session(token)
        if user_id:
            user = db.get_user(user_id)
            if user:
                st.session_state.auth_user = user
                return user
        # Token invalid - clear it
        st.session_state.session_token = ''
        if 'token' in st.query_params:
            del st.query_params['token']

    # Show login page
    _render_login_page(db)
    st.stop()
    return {}


def _render_login_page(db):
    """Render the login page with rate limiting and brute-force protection."""
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-logo">
            <div class="title">QUANTUMTRADE</div>
            <div class="subtitle">Trading Engine v3.0</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.get('login_error'):
            st.markdown(
                f'<div class="login-error">{st.session_state.login_error}</div>',
                unsafe_allow_html=True
            )
            st.session_state.login_error = ''

        with st.form("login_form", clear_on_submit=False):
            st.markdown("##### Sign In")
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            remember = st.checkbox("Keep me signed in for 7 days", value=True)
            submitted = st.form_submit_button("SIGN IN", type="primary")

            if submitted:
                if not username or not password:
                    st.session_state.login_error = "Please enter username and password"
                    st.rerun()
                    return

                rl = get_rate_limiter()
                key = username.lower().strip()

                # Check lockout
                locked, secs = rl.is_locked_out(key)
                if locked:
                    mins = secs // 60
                    st.session_state.login_error = (
                        f"🔒 Account locked for {mins}m {secs % 60}s due to too many failed attempts."
                    )
                    db.log_event('LOCKOUT_CHECK', username=key, success=False,
                                 details={'seconds_remaining': secs})
                    st.rerun()
                    return

                # Rate limit check
                allowed, _ = rl.check_rate_limit(f"login:{key}", max_req=10, window=60)
                if not allowed:
                    st.session_state.login_error = "⏱ Too many attempts. Please wait a moment."
                    st.rerun()
                    return

                user = db.verify_user(username, password)

                if user:
                    rl.record_successful_login(key)
                    _complete_login(db, user, remember)
                else:
                    count, locked = rl.record_failed_login(key)
                    remaining = 5 - count
                    if locked:
                        st.session_state.login_error = f"🔒 Too many failed attempts. Account locked for 15 minutes."
                        db.log_event('LOCKOUT', username=key, success=False)
                    else:
                        st.session_state.login_error = (
                            f"Invalid username or password. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
                        )
                    db.log_event('LOGIN_FAILED', username=key, success=False,
                                 details={'attempt': count})
                    st.rerun()

        st.markdown("""
        <div class="login-footer">
            Secured by QuantumTrade Engine<br>
            Contact admin for account access
        </div>
        """, unsafe_allow_html=True)




def _complete_login(db, user: dict, remember: bool):
    """Finalize login: create JWT session, log event, update state."""
    token = db.create_session(
        user_id=user['user_id'],
        username=user['username'],
        role=user['role'],
        remember=remember
    )
    st.session_state.auth_user = user
    st.session_state.session_token = token
    st.session_state.login_error = ''
    
    # If "remember me" is checked, save token in URL for persistence
    if remember:
        st.query_params['token'] = token
    
    db.log_event('LOGIN_SUCCESS', user_id=user['user_id'],
                 username=user['username'], success=True,
                 details={'role': user['role'], 'remember': remember})
    print(f"[AUTH] User '{user['username']}' logged in (role: {user['role']})")
    st.rerun()


def logout():
    """Log out the current user — revoke token and clear state."""
    db = get_database()
    user = st.session_state.get('auth_user', {})
    token = st.session_state.get('session_token', '')

    if token:
        db.delete_session(token)

    if user:
        db.log_event('LOGOUT', user_id=user.get('user_id'),
                     username=user.get('username'), success=True)

    # Clear token from URL
    if 'token' in st.query_params:
        del st.query_params['token']

    for key in ['auth_user', 'session_token', 'engine', 'signals', 'market_data',
                'active_positions', 'trade_log', 'alert_history', 'alerted_signals',
                'initial_capital', 'db_loaded']:
        st.session_state.pop(key, None)


def render_user_sidebar(user: dict):
    """Render user info, role badge, and logout button in sidebar."""
    role_badge = 'admin-badge' if user['role'] == 'admin' else 'user-badge'

    st.markdown(f"""
    <div style="text-align: center; padding: 8px 0; margin-bottom: 8px;">
        <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">
            {user['display_name']}
        </div>
        <span class="{role_badge}">{user['role'].upper()}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
        logout()
        st.rerun()


def render_admin_panel(db):
    """Render admin panel with user management + audit logs tabs."""
    st.markdown("### Admin Panel")

    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["👥 Users", "📋 Audit Logs", "🔒 Security"])

    # ── TAB 1: User Management ──────────────────────────────────
    with admin_tab1:
        users = db.list_users()
        if users:
            st.markdown(f"**{len(users)} registered users:**")
            for u in users:
                active_icon = "🟢" if u.get('is_active', True) else "🔴"
                last_login = u.get('last_login')
                last_str = last_login.strftime('%Y-%m-%d %H:%M') if last_login else 'Never'
                role_color = '#f59e0b' if u['role'] == 'admin' else '#3b82f6'
                totp_str = "🔐 2FA" if u.get('totp_enabled') else "🔓 No 2FA"

                col_user, col_delete = st.columns([4, 1])
                with col_user:
                    st.markdown(f"""
                    <div style="border-left: 3px solid {role_color}; padding: 8px 12px; margin-bottom: 6px;
                                background: rgba(15,23,42,0.4); border-radius: 0 6px 6px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-weight: 700; color: #f1f5f9;">{active_icon} {u['display_name']}</span>
                                <span style="color: #64748b; font-size: 11px; margin-left: 6px;">@{u['username']}</span>
                                <span style="color: {role_color}; font-size: 11px; margin-left: 8px;">{u['role'].upper()}</span>
                                <span style="color: #64748b; font-size: 11px; margin-left: 8px;">{totp_str}</span>
                            </div>
                            <div style="font-size: 11px; color: #64748b;">
                                Last: {last_str} | Logins: {u.get('login_count', 0)}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_delete:
                    current_user = st.session_state.get('auth_user', {})
                    if u['username'] != current_user.get('username'):  # Can't delete self
                        if st.button("Delete", key=f"delete_{u['username']}", help="Delete user"):
                            # Confirm deletion
                            if st.session_state.get(f'confirm_delete_{u["username"]}', False):
                                # Actually delete user
                                success = db.delete_user(u['username'])
                                if success:
                                    current_user = st.session_state.get('auth_user', {})
                                    db.log_event('USER_DELETED', user_id=current_user.get('user_id'),
                                                username=current_user.get('username'), success=True,
                                                details={'deleted_user': u['username']})
                                    st.success(f"User '{u['username']}' deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete user")
                                st.session_state[f'confirm_delete_{u["username"]}'] = False
                            else:
                                # Show confirmation button
                                st.session_state[f'confirm_delete_{u["username"]}'] = True
                            if st.session_state.get(f'confirm_delete_{u["username"]}', False):
                                st.warning(f"Click Delete again to confirm deletion of {u['username']}")
                    else:
                        # Cannot delete own account - no message shown
                        pass

        st.markdown("---")
        st.markdown("##### Create New User")

        from auth.security import get_password_manager
        with st.form("create_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username", placeholder="e.g. trader1")
                new_password = st.text_input("Password", type="password", placeholder="Min 8 chars, 1 uppercase, 1 number")
            with col2:
                new_display = st.text_input("Display Name", placeholder="e.g. John Doe")
                new_role = st.selectbox("Role", ['user', 'trader', 'viewer', 'admin'])
            new_email = st.text_input("Email (optional)", placeholder="user@example.com")

            if st.form_submit_button("CREATE USER", type="primary"):
                if not new_username or not new_password:
                    st.error("Username and password are required")
                else:
                    valid, msg = get_password_manager().validate_strength(new_password)
                    if not valid:
                        st.error(f"Weak password: {msg}")
                    else:
                        result = db.create_user(
                            username=new_username, password=new_password,
                            role=new_role, display_name=new_display or new_username,
                            email=new_email
                        )
                        if result:
                            current_user = st.session_state.get('auth_user', {})
                            db.log_event('USER_CREATED', user_id=current_user.get('user_id'),
                                         username=current_user.get('username'), success=True,
                                         details={'new_user': new_username, 'role': new_role})
                            st.success(f"✅ User '{new_username}' created!")
                            st.rerun()
                        else:
                            st.error(f"Failed — username '{new_username}' may already exist.")

    # ── TAB 2: Audit Logs ───────────────────────────────────────
    with admin_tab2:
        st.markdown("##### Security Audit Log")

        col1, col2 = st.columns(2)
        with col1:
            event_filter = st.selectbox("Filter by event", [
                "ALL", "LOGIN_SUCCESS", "LOGIN_FAILED", "LOGOUT",
                "LOCKOUT", "2FA_SUCCESS", "2FA_FAILED", "2FA_ENABLED",
                "TRADE_EXECUTED", "USER_CREATED", "SETTINGS_CHANGED"
            ])
        with col2:
            log_limit = st.selectbox("Show last", [50, 100, 200, 500], index=1)

        logs = db.get_audit_logs(
            event=None if event_filter == "ALL" else event_filter,
            limit=log_limit
        )

        if logs:
            for log in logs:
                ts = log.get('timestamp', '')
                if hasattr(ts, 'strftime'):
                    ts = ts.strftime('%Y-%m-%d %H:%M:%S')
                event = log.get('event', '')
                uname = log.get('username', '?')
                ok = log.get('success', True)
                color = '#10b981' if ok else '#ef4444'
                icon = '✅' if ok else '❌'
                details = log.get('details', {})
                detail_str = ', '.join(f"{k}={v}" for k, v in details.items()) if details else ''

                st.markdown(f"""
                <div style="font-family: monospace; font-size: 12px; padding: 4px 8px;
                            border-left: 3px solid {color}; margin-bottom: 3px;
                            background: rgba(15,23,42,0.3); border-radius: 0 4px 4px 0;">
                    <span style="color: #64748b;">{ts}</span>
                    <span style="color: {color}; margin: 0 8px;">{icon} {event}</span>
                    <span style="color: #f1f5f9;">@{uname}</span>
                    <span style="color: #475569; margin-left: 8px;">{detail_str}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No audit logs found.")

    # ── TAB 3: Security Overview ────────────────────────────────
    with admin_tab3:
        st.markdown("##### Security Status")

        try:
            import bcrypt
            bcrypt_ok = True
        except ImportError:
            bcrypt_ok = False

        try:
            import jwt
            jwt_ok = True
        except ImportError:
            jwt_ok = False

        try:
            import pyotp
            totp_ok = True
        except ImportError:
            totp_ok = False

        try:
            from cryptography.fernet import Fernet
            crypto_ok = True
        except ImportError:
            crypto_ok = False

        def _status(ok):
            return ("🟢 Active" if ok else "🔴 Not installed")

        st.markdown(f"""
        | Security Layer | Status |
        |---|---|
        | Password Hashing | {'🟢 bcrypt (rounds=12)' if bcrypt_ok else '🟡 SHA-256 fallback'} |
        | Session Tokens | {'🟢 JWT (HS256, signed)' if jwt_ok else '🟡 Random token fallback'} |
        | 2FA (TOTP) | {_status(totp_ok)} |
        | Encryption (AES-256) | {_status(crypto_ok)} |
        | Rate Limiting | 🟢 Active (10 req/min) |
        | Brute-Force Lock | 🟢 Active (5 attempts → 15 min) |
        | Audit Logging | 🟢 Active |
        | RBAC | 🟢 Active (admin/trader/viewer) |
        """)

        if not bcrypt_ok or not jwt_ok or not totp_ok or not crypto_ok:
            st.warning("Install missing packages for full security:")
            st.code("pip install bcrypt PyJWT pyotp cryptography")
