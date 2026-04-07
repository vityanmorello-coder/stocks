"""
QuantumTrade Engine - Create Admin User
========================================
Run this script ONCE to create your superadmin account.

Usage:
    python create_admin.py

You will need your MongoDB Atlas connection string.
"""

import os
import sys
import getpass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.database import DatabaseManager


def main():
    print("=" * 60)
    print("  QUANTUMTRADE ENGINE - Admin Setup")
    print("=" * 60)
    print()
    
    # Get MongoDB connection string
    print("Enter your MongoDB Atlas connection string.")
    print("Example: mongodb+srv://user:pass@cluster.mongodb.net/")
    print()
    
    mongo_uri = input("MongoDB URI: ").strip()
    
    if not mongo_uri:
        print("ERROR: MongoDB URI is required.")
        return
    
    # Connect to database
    db = DatabaseManager(mongo_uri)
    if not db.connect():
        print("\nERROR: Could not connect to MongoDB. Check your URI.")
        return
    
    print("\n✅ Connected to MongoDB successfully!\n")
    
    # Get admin credentials
    print("Create your SUPERADMIN account:")
    print("-" * 40)
    
    username = input("Username: ").strip()
    if not username:
        print("ERROR: Username is required.")
        return
    
    display_name = input("Display Name (optional): ").strip() or username
    email = input("Email (optional): ").strip()
    
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")
    
    if password != password_confirm:
        print("\nERROR: Passwords don't match!")
        return
    
    if len(password) < 6:
        print("\nERROR: Password must be at least 6 characters.")
        return
    
    # Create admin user
    user_id = db.create_user(
        username=username,
        password=password,
        role='admin',
        display_name=display_name,
        email=email
    )
    
    if user_id:
        print(f"\n✅ Admin user '{username}' created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Role: ADMIN (superadmin)")
        
        # Save the MongoDB URI to .env file
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        with open(env_path, 'w') as f:
            f.write(f"MONGO_URI={mongo_uri}\n")
        
        print(f"\n✅ MongoDB URI saved to .env file")
        print(f"\n{'=' * 60}")
        print(f"  Setup Complete!")
        print(f"  Run the dashboard: python -m streamlit run pro_trading_dashboard.py")
        print(f"  Login with: {username} / [your password]")
        print(f"{'=' * 60}")
    else:
        print(f"\nERROR: Failed to create user. Username may already exist.")
    
    db.close()


if __name__ == "__main__":
    main()
