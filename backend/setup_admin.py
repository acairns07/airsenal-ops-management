#!/usr/bin/env python3
"""
Setup initial admin credentials for AIrsenal Control Room
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def setup_admin():
    # MongoDB connection
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Default admin credentials
    admin_email = "acairns07@gmail.com"
    admin_password = "Madmoo60!!1212"  # Change this!
    
    # Generate password hash
    password_hash = bcrypt.hash(admin_password)
    
    # Insert admin email
    await db.secrets.update_one(
        {"key": "APP_ADMIN_EMAIL"},
        {"$set": {"value": admin_email, "key": "APP_ADMIN_EMAIL"}},
        upsert=True
    )
    
    # Insert admin password hash
    await db.secrets.update_one(
        {"key": "APP_ADMIN_PASSWORD_HASH"},
        {"$set": {"value": password_hash, "key": "APP_ADMIN_PASSWORD_HASH"}},
        upsert=True
    )
    
    # Set default AIRSENAL_HOME
    await db.secrets.update_one(
        {"key": "AIRSENAL_HOME"},
        {"$set": {"value": "/data/airsenal", "key": "AIRSENAL_HOME"}},
        upsert=True
    )
    
    print("✓ Admin credentials set up successfully!")
    print(f"  Email: {admin_email}")
    print(f"  Password: {admin_password}")
    print("\n⚠️  Please change these credentials immediately via the Settings page!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(setup_admin())
