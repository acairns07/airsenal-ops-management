"""Pytest configuration and fixtures."""
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
import os

# Set test environment variables before imports
os.environ['MONGO_URL'] = 'mongodb://localhost:27017'
os.environ['DB_NAME'] = 'airsenal_control_test'
os.environ['JWT_SECRET'] = 'test-secret-key-for-testing-only'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000'
os.environ['ENCRYPTION_KEY'] = 'test-encryption-key-32-bytes-long!!'
os.environ['RATE_LIMIT_ENABLED'] = 'false'


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db():
    """Create a test database connection."""
    from database import client, db as database
    yield database

    # Cleanup: drop test database after tests
    await client.drop_database(os.environ['DB_NAME'])


@pytest.fixture
async def clean_db(db):
    """Clean database before each test."""
    # Drop all collections
    for collection_name in await db.list_collection_names():
        await db[collection_name].delete_many({})
    yield db


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from server_new import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def admin_credentials(clean_db):
    """Create test admin credentials."""
    from auth import hash_password
    from utils.encryption import encrypt_secret

    email = "admin@test.com"
    password = "testpassword123"
    password_hash = hash_password(password)

    # Store in database
    await clean_db.secrets.insert_one({
        "key": "APP_ADMIN_EMAIL",
        "value": email,
        "updated_at": "2025-01-01T00:00:00Z"
    })
    await clean_db.secrets.insert_one({
        "key": "APP_ADMIN_PASSWORD_HASH",
        "value": password_hash,
        "updated_at": "2025-01-01T00:00:00Z"
    })

    return {"email": email, "password": password}


@pytest.fixture
async def auth_token(test_client, admin_credentials):
    """Get authentication token for tests."""
    response = test_client.post(
        "/api/auth/login",
        json={
            "email": admin_credentials["email"],
            "password": admin_credentials["password"]
        }
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers with valid token."""
    return {"Authorization": f"Bearer {auth_token}"}
