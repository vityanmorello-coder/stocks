"""
QuantumTrade Engine - Admin Setup
Run this once to create your .env and first admin account.
No credentials are stored in this file.
"""
import os
import sys
import getpass
from urllib.parse import quote_plus
sys.path.append(os.path.dirname(__file__))

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

# Step 1: Set up .env if missing
if os.path.exists(env_path):
    print("✅ .env already exists — using existing MongoDB URI")
else:
    print("=" * 50)
    print("  MongoDB Atlas Setup")
    print("=" * 50)
    print("Enter your MongoDB Atlas database user credentials:")
    db_username = input("DB Username: ").strip()
    db_password = getpass.getpass("DB Password: ")
    cluster = input("Cluster host (e.g. cluster0.xxxxx.mongodb.net): ").strip()

    encoded_pass = quote_plus(db_password)
    mongo_uri = f"mongodb+srv://{db_username}:{encoded_pass}@{cluster}/?appName=Cluster0"

    with open(env_path, 'w') as f:
        f.write(f"MONGO_URI={mongo_uri}\n")
    print(f"✅ .env file created (credentials stored securely)")

# Step 2: Connect using URI from .env
from auth.database import DatabaseManager

db = DatabaseManager()  # reads from .env automatically
if not db.connect():
    print("❌ MongoDB connection failed!")
    print("   Check: Database Access (user/pass) and Network Access (0.0.0.0/0)")
    sys.exit(1)

print("✅ MongoDB connected!")

# Step 3: Create admin account
print()
print("=" * 50)
print("  Create Admin Account")
print("=" * 50)
admin_username = input("Admin username: ").strip()
admin_display = input("Display name (optional, press Enter to skip): ").strip() or admin_username
admin_password = getpass.getpass("Admin password (min 6 chars): ")
admin_password2 = getpass.getpass("Confirm password: ")

if admin_password != admin_password2:
    print("❌ Passwords don't match!")
    sys.exit(1)

if len(admin_password) < 6:
    print("❌ Password must be at least 6 characters!")
    sys.exit(1)

result = db.create_user(
    username=admin_username,
    password=admin_password,
    role='admin',
    display_name=admin_display,
)

if result:
    print()
    print("=" * 50)
    print(f"  ✅ SETUP COMPLETE!")
    print(f"  Login: {admin_username} / [your password]")
    print(f"  Run: python -m streamlit run pro_trading_dashboard.py")
    print("=" * 50)
else:
    print(f"⚠️  User '{admin_username}' may already exist.")

db.close()
