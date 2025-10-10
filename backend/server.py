from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import sys
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import subprocess
import json
from passlib.hash import bcrypt
import jwt
from collections import defaultdict

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# JWT settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 12

security = HTTPBearer()

# Python version check
PYTHON_VERSION = sys.version_info
PYTHON_VERSION_VALID = PYTHON_VERSION < (3, 13)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[job_id].append(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket):
        if websocket in self.active_connections[job_id]:
            self.active_connections[job_id].remove(websocket)

    async def broadcast(self, job_id: str, message: dict):
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    email: str

class HashPasswordRequest(BaseModel):
    password: str

class HashPasswordResponse(BaseModel):
    hash: str

class SecretUpdate(BaseModel):
    key: str
    value: str

class Secret(BaseModel):
    key: str
    value: str
    is_set: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class JobCreate(BaseModel):
    command: str
    parameters: Dict[str, Any] = {}

class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    command: str
    parameters: Dict[str, Any] = {}
    status: str = "pending"  # pending, running, completed, failed
    logs: List[str] = []
    output: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None

# Auth helpers
def create_token(email: str) -> str:
    payload = {
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('email')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    email = verify_token(credentials.credentials)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Check if user email matches admin email
    admin_email = await db.secrets.find_one({"key": "APP_ADMIN_EMAIL"})
    if not admin_email or email != admin_email.get('value'):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    return email

# Job queue management
class JobQueue:
    def __init__(self):
        self.is_processing = False
        self.current_job_id = None

    async def add_job(self, job: Job):
        # Save job to database
        job_dict = job.model_dump()
        job_dict['created_at'] = job_dict['created_at'].isoformat()
        if job_dict.get('started_at'):
            job_dict['started_at'] = job_dict['started_at'].isoformat()
        if job_dict.get('completed_at'):
            job_dict['completed_at'] = job_dict['completed_at'].isoformat()
        
        await db.jobs.insert_one(job_dict)
        
        # Start processing if not already processing
        if not self.is_processing:
            asyncio.create_task(self.process_queue())
        
        return job.id

    async def process_queue(self):
        if self.is_processing:
            return
        
        self.is_processing = True
        
        while True:
            # Get next pending job
            job_doc = await db.jobs.find_one({"status": "pending"}, sort=[("created_at", 1)])
            
            if not job_doc:
                break
            
            job_id = job_doc['id']
            self.current_job_id = job_id
            
            # Update job status to running
            await db.jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            # Broadcast status update
            await manager.broadcast(job_id, {"type": "status", "status": "running"})
            
            # Execute job
            try:
                await self.execute_job(job_id, job_doc['command'], job_doc['parameters'])
            except Exception as e:
                logger.error(f"Job {job_id} failed: {str(e)}")
                await db.jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                await manager.broadcast(job_id, {"type": "status", "status": "failed", "error": str(e)})
        
        self.is_processing = False
        self.current_job_id = None

    async def execute_job(self, job_id: str, command: str, parameters: Dict[str, Any]):
        """Execute AIrsenal command"""
        # Get secrets
        secrets = await db.secrets.find({}).to_list(None)
        env_vars = os.environ.copy()
        
        for secret in secrets:
            if secret['key'] in ['FPL_TEAM_ID', 'FPL_LOGIN', 'FPL_PASSWORD', 'AIRSENAL_HOME']:
                env_vars[secret['key']] = secret['value']
        
        # Set default AIRSENAL_HOME if not set
        if 'AIRSENAL_HOME' not in env_vars:
            env_vars['AIRSENAL_HOME'] = '/data/airsenal'
        
        # Build command
        cmd_parts = []
        
        if command == 'setup_db':
            cmd_parts = ['airsenal_setup_initial_db']
        elif command == 'update_db':
            cmd_parts = ['airsenal_update_db']
        elif command == 'predict':
            weeks = parameters.get('weeks_ahead', 3)
            cmd_parts = ['airsenal_run_prediction', '--weeks_ahead', str(weeks)]
        elif command == 'optimize':
            weeks = parameters.get('weeks_ahead', 3)
            cmd_parts = ['airsenal_run_optimization', '--weeks_ahead', str(weeks)]
            
            # Add chip parameters if provided
            if parameters.get('wildcard_week'):
                cmd_parts.extend(['--wildcard_week', str(parameters['wildcard_week'])])
            if parameters.get('free_hit_week'):
                cmd_parts.extend(['--free_hit_week', str(parameters['free_hit_week'])])
            if parameters.get('triple_captain_week'):
                cmd_parts.extend(['--triple_captain_week', str(parameters['triple_captain_week'])])
            if parameters.get('bench_boost_week'):
                cmd_parts.extend(['--bench_boost_week', str(parameters['bench_boost_week'])])
        elif command == 'pipeline':
            cmd_parts = ['airsenal_run_pipeline']
        else:
            raise ValueError(f"Unknown command: {command}")
        
        # Log command
        await self.log_to_job(job_id, f"Executing: {' '.join(cmd_parts)}")
        
        # Execute command
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env_vars
        )
        
        # Stream output
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8').rstrip()
            await self.log_to_job(job_id, line_str)
        
        # Wait for process to complete
        await process.wait()
        
        if process.returncode == 0:
            await db.jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            await manager.broadcast(job_id, {"type": "status", "status": "completed"})
        else:
            await db.jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "failed",
                    "error": f"Command exited with code {process.returncode}",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            await manager.broadcast(job_id, {"type": "status", "status": "failed", "error": f"Exit code {process.returncode}"})

    async def log_to_job(self, job_id: str, message: str):
        """Add log message to job"""
        await db.jobs.update_one(
            {"id": job_id},
            {"$push": {"logs": message}}
        )
        
        # Broadcast log to WebSocket clients
        await manager.broadcast(job_id, {"type": "log", "message": message})

job_queue = JobQueue()

# Routes
@api_router.get("/")
async def root():
    return {"message": "AIrsenal Control Room API"}

@api_router.get("/health")
async def health():
    return {
        "status": "ok",
        "python_version": f"{PYTHON_VERSION.major}.{PYTHON_VERSION.minor}.{PYTHON_VERSION.micro}",
        "python_version_valid": PYTHON_VERSION_VALID
    }

# Auth routes
@api_router.post("/auth/hash-password", response_model=HashPasswordResponse)
async def hash_password(request: HashPasswordRequest):
    """Generate bcrypt hash for password (utility endpoint)"""
    hashed = bcrypt.hash(request.password)
    return HashPasswordResponse(hash=hashed)

@api_router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Get admin email and password hash from secrets
    admin_email_doc = await db.secrets.find_one({"key": "APP_ADMIN_EMAIL"})
    admin_password_doc = await db.secrets.find_one({"key": "APP_ADMIN_PASSWORD_HASH"})
    
    if not admin_email_doc or not admin_password_doc:
        raise HTTPException(status_code=401, detail="Admin credentials not configured")
    
    admin_email = admin_email_doc['value']
    admin_password_hash = admin_password_doc['value']
    
    # Verify email
    if request.email != admin_email:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not bcrypt.verify(request.password, admin_password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate token
    token = create_token(request.email)
    
    return LoginResponse(token=token, email=request.email)

@api_router.get("/auth/check")
async def check_auth(current_user: str = Depends(get_current_user)):
    return {"email": current_user, "authenticated": True}

# Secrets routes
@api_router.get("/secrets")
async def get_secrets(current_user: str = Depends(get_current_user)):
    secrets = await db.secrets.find({}).to_list(None)
    
    # Don't return actual values, just whether they're set
    secret_status = []
    for secret in secrets:
        secret_status.append({
            "key": secret['key'],
            "is_set": bool(secret.get('value')),
            "masked_value": "***" if secret.get('value') else ""
        })
    
    return secret_status

@api_router.post("/secrets")
async def update_secret(secret: SecretUpdate, current_user: str = Depends(get_current_user)):
    # Update or insert secret
    await db.secrets.update_one(
        {"key": secret.key},
        {"$set": {"value": secret.value, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return {"success": True, "key": secret.key}

# Job routes
@api_router.post("/jobs", response_model=Job)
async def create_job(job_create: JobCreate, current_user: str = Depends(get_current_user)):
    job = Job(command=job_create.command, parameters=job_create.parameters)
    job_id = await job_queue.add_job(job)
    return job

@api_router.get("/jobs", response_model=List[Job])
async def get_jobs(current_user: str = Depends(get_current_user)):
    jobs = await db.jobs.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    
    # Convert ISO strings back to datetime
    for job in jobs:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job.get('started_at'), str):
            job['started_at'] = datetime.fromisoformat(job['started_at'])
        if isinstance(job.get('completed_at'), str):
            job['completed_at'] = datetime.fromisoformat(job['completed_at'])
    
    return jobs

@api_router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, current_user: str = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Convert ISO strings back to datetime
    if isinstance(job.get('created_at'), str):
        job['created_at'] = datetime.fromisoformat(job['created_at'])
    if isinstance(job.get('started_at'), str):
        job['started_at'] = datetime.fromisoformat(job['started_at'])
    if isinstance(job.get('completed_at'), str):
        job['completed_at'] = datetime.fromisoformat(job['completed_at'])
    
    return job

# WebSocket for live logs
@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    
    try:
        # Send existing logs
        job = await db.jobs.find_one({"id": job_id})
        if job and job.get('logs'):
            for log in job['logs']:
                await websocket.send_json({"type": "log", "message": log})
        
        # Send current status
        if job:
            await websocket.send_json({"type": "status", "status": job.get('status', 'pending')})
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
