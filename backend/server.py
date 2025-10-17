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
from typing import List, Optional, Dict, Any, Set
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import subprocess
import json
import shutil
import re
import httpx
from passlib.hash import bcrypt
import jwt
from collections import defaultdict

ROOT_DIR = Path(__file__).parent
if os.getenv("ENVIRONMENT", "production") != "production":
    try:
        load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)
    except Exception:
        pass

PERSISTENT_DB_PATH = os.getenv("PERSISTENT_DB_PATH", "/data/airsenal/data.db")
LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "/tmp/airsenal.db")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=8000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    retryWrites=True,
)
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
        self.active_process = None
        self.cancelled_jobs: Set[str] = set()

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
        self.active_process = None
        self.cancelled_jobs: Set[str] = set()

    async def _hydrate_local_db(self, job_id: str):
        try:
            if Path(PERSISTENT_DB_PATH).exists():
                shutil.copyfile(PERSISTENT_DB_PATH, LOCAL_DB_PATH)
                await self.log_to_job(job_id, f"Hydrated local DB from {PERSISTENT_DB_PATH}")
            else:
                await self.log_to_job(job_id, "No persisted DB found; starting fresh local DB.")
        except Exception as exc:
            await self.log_to_job(job_id, f"Hydrate failed: {exc}")
            raise

    async def _persist_sqlite(self, job_id: str):
        try:
            Path(PERSISTENT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
            tmp_target = f"{PERSISTENT_DB_PATH}.tmp"
            shutil.copyfile(LOCAL_DB_PATH, tmp_target)
            with open(tmp_target, 'rb') as handle:
                os.fsync(handle.fileno())
            os.replace(tmp_target, PERSISTENT_DB_PATH)
            await self.log_to_job(job_id, f"Persisted DB to {PERSISTENT_DB_PATH}")
        except FileNotFoundError:
            await self.log_to_job(job_id, "No local DB to persist (skipping).")
        except Exception as exc:
            await self.log_to_job(job_id, f"Persist DB failed: {exc}")
            raise

    async def cancel_job(self, job_id: str):
        """Cancel the currently running job if it matches job_id."""
        if self.current_job_id != job_id:
            raise ValueError("Job is not currently running")
        if not self.active_process:
            raise ValueError("No active process to cancel")
        if job_id in self.cancelled_jobs:
            return

        self.cancelled_jobs.add(job_id)
        await self.log_to_job(job_id, "Cancellation requested by user. Attempting to terminate process...")
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "cancelling"}}
        )
        await manager.broadcast(job_id, {"type": "status", "status": "cancelling"})
        try:
            self.active_process.terminate()
        except ProcessLookupError:
            pass

    async def execute_job(self, job_id: str, command: str, parameters: Dict[str, Any]):
        """Execute AIrsenal command with safe SQLite handling (local write -> persist)."""
        # Get secrets
        ALLOWED_SECRET_KEYS = {
            "APP_ADMIN_EMAIL", "APP_ADMIN_PASSWORD_HASH",
            "FPL_TEAM_ID", "FPL_LOGIN", "FPL_PASSWORD", "AIRSENAL_HOME"
        }
        secrets = await db.secrets.find({"key": {"$in": list(ALLOWED_SECRET_KEYS)}}).to_list(None)

        env_vars = os.environ.copy()
        for secret in secrets:
            if secret["key"] in ["FPL_TEAM_ID", "FPL_LOGIN", "FPL_PASSWORD", "AIRSENAL_HOME"]:
                env_vars[secret["key"]] = secret["value"]

        # Defaults
        env_vars.setdefault("AIRSENAL_HOME", "/data/airsenal")

        # Always write locally to avoid Azure Files locking
        env_vars["AIRSENAL_DB_FILE"] = LOCAL_DB_PATH

        # Build command
        cmd_parts: List[str] = []
        if command == "setup_db":
            cmd_parts = ["airsenal_setup_initial_db"]
        elif command == "update_db":
            cmd_parts = ["airsenal_update_db"]
        elif command == "predict":
            weeks = parameters.get("weeks_ahead", 3)
            cmd_parts = ["airsenal_run_prediction", "--weeks_ahead", str(weeks)]
        elif command == "optimize":
            weeks = parameters.get("weeks_ahead", 3)
            cmd_parts = ["airsenal_run_optimization", "--weeks_ahead", str(weeks)]
            if parameters.get("wildcard_week"):
                cmd_parts += ["--wildcard_week", str(parameters["wildcard_week"])]
            if parameters.get("free_hit_week"):
                cmd_parts += ["--free_hit_week", str(parameters["free_hit_week"])]
            if parameters.get("triple_captain_week"):
                cmd_parts += ["--triple_captain_week", str(parameters["triple_captain_week"])]
            if parameters.get("bench_boost_week"):
                cmd_parts += ["--bench_boost_week", str(parameters["bench_boost_week"])]
        elif command == "pipeline":
            cmd_parts = ["airsenal_run_pipeline"]
        else:
            raise ValueError(f"Unknown command: {command}")

        # Log command
        await self.log_to_job(job_id, f"Executing: {' '.join(cmd_parts)}")

        # Hydrate local DB from persisted (if present)
        await self._hydrate_local_db(job_id)

        captured_logs: List[str] = []
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env_vars,
        )
        self.active_process = process

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                captured_logs.append(decoded)
                if len(captured_logs) > 2000:
                    captured_logs.pop(0)
                await self.log_to_job(job_id, decoded)
        finally:
            await process.wait()
            self.active_process = None

        returncode = process.returncode

        if job_id in self.cancelled_jobs:
            self.cancelled_jobs.discard(job_id)
            await self.log_to_job(job_id, "Job cancelled by user.")
            await db.jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "cancelled",
                    "error": "Cancelled by user request",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            await manager.broadcast(job_id, {"type": "status", "status": "cancelled"})
            return

        if returncode == 0:
            output_payload = self._extract_command_output(command, parameters, captured_logs)
            if output_payload:
                await db.jobs.update_one(
                    {"id": job_id},
                    {"$set": {"output": output_payload}}
                )
                await manager.broadcast(job_id, {"type": "output", "payload": output_payload})

            # Persist the updated local DB back to the share
            try:
                await self._persist_sqlite(job_id)
            except Exception as e:
                await db.jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "status": "failed",
                        "error": f"Persist failed: {e}",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                await manager.broadcast(job_id, {"type": "status", "status": "failed", "error": f"Persist failed: {e}"})
                return

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

    def _extract_command_output(self, command: str, parameters: Dict[str, Any], logs: List[str]) -> Optional[Dict[str, Any]]:
        if command == "predict":
            return self._parse_prediction_output(parameters, logs)
        if command == "optimize":
            return self._parse_optimization_output(parameters, logs)
        return None

    def _collect_section(self, logs: List[str], start_keywords: List[str], stop_keywords: List[str]) -> List[str]:
        if not logs:
            return []
        start_lower = [kw.lower() for kw in start_keywords]
        stop_lower = [kw.lower() for kw in stop_keywords]
        collecting = False
        section: List[str] = []

        for line in logs:
            lower = line.lower()
            if not collecting and any(keyword in lower for keyword in start_lower):
                collecting = True
            if collecting:
                if any(keyword in lower for keyword in stop_lower):
                    break
                section.append(line)
        return section

    def _parse_prediction_output(self, parameters: Dict[str, Any], logs: List[str]) -> Optional[Dict[str, Any]]:
        section = self._collect_section(
            logs,
            start_keywords=["top predicted players"],
            stop_keywords=["predictions saved", "prediction saved", "optimization complete", "optimisation complete"]
        )
        if not section:
            return None

        player_pattern = re.compile(r"^\s*(\d+)\.\s+(?P<player>.+?)\s+-\s+Expected points:\s+(?P<points>[-+]?\d+(?:\.\d+)?)", re.IGNORECASE)
        players = []
        for line in section[1:]:
            match = player_pattern.match(line)
            if match:
                players.append({
                    "rank": int(match.group(1)),
                    "player": match.group("player").strip(),
                    "expected_points": float(match.group("points"))
                })

        summary_text = "\n".join(section).strip()
        return {
            "type": "prediction",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "parameters": parameters,
            "headline": section[0].strip() if section else "",
            "players": players,
            "summary_text": summary_text,
        }

    def _parse_optimization_output(self, parameters: Dict[str, Any], logs: List[str]) -> Optional[Dict[str, Any]]:
        section = self._collect_section(
            logs,
            start_keywords=["recommended transfers"],
            stop_keywords=["optimization complete", "optimisation complete", "pipeline completed"]
        )
        transfers = []
        transfer_pattern = re.compile(
            r"OUT:\s*(?P<out>.+?)\s*(?:\u2192|->)\s*IN:\s*(?P<in>.+?)\s*\|\s*Cost:\s*(?P<cost>[^|]+)\|\s*Gain:\s*(?P<gain>.+)",
            re.IGNORECASE
        )
        for line in section[1:]:
            match = transfer_pattern.search(line)
            if match:
                transfers.append({
                    "out": match.group("out").strip(),
                    "in": match.group("in").strip(),
                    "cost": match.group("cost").strip(),
                    "gain": match.group("gain").strip(),
                })

        captain = next((line.split(":", 1)[1].strip() for line in logs if "captain" in line.lower() and "recommended captain" in line.lower()), None)
        vice_captain = next((line.split(":", 1)[1].strip() for line in logs if "vice" in line.lower() and "captain" in line.lower()), None)
        expected_points_line = next((line for line in logs if "expected points" in line.lower()), None)
        expected_points = None
        if expected_points_line and ":" in expected_points_line:
            expected_points = expected_points_line.split(":", 1)[1].strip()

        summary_text = "\n".join(section).strip() if section else ""

        return {
            "type": "optimisation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "parameters": parameters,
            "transfers": transfers,
            "captain": captain,
            "vice_captain": vice_captain,
            "expected_points": expected_points,
            "summary_text": summary_text,
        }
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

@api_router.post("/jobs/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str, current_user: str = Depends(get_current_user)):
    try:
        await job_queue.cancel_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"success": True, "job_id": job_id}


@api_router.delete("/jobs/{job_id}/logs")
async def clear_job_logs(job_id: str, current_user: str = Depends(get_current_user)):
    result = await db.jobs.update_one({"id": job_id}, {"$set": {"logs": []}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "job_id": job_id}


@api_router.delete("/jobs/logs")
async def clear_all_job_logs(current_user: str = Depends(get_current_user)):
    result = await db.jobs.update_many({}, {"$set": {"logs": []}})
    return {"success": True, "cleared": result.modified_count}


@api_router.get("/jobs/{job_id}/output")
async def get_job_output(job_id: str, current_user: str = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0, "id": 1, "command": 1, "status": 1, "parameters": 1, "completed_at": 1, "output": 1})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@api_router.get("/reports/latest")
async def get_latest_reports(current_user: str = Depends(get_current_user)):
    prediction_job = await db.jobs.find_one(
        {"command": "predict", "status": "completed", "output": {"$exists": True}},
        sort=[("completed_at", -1)],
        projection={"_id": 0, "id": 1, "completed_at": 1, "output": 1}
    )
    optimisation_job = await db.jobs.find_one(
        {"command": "optimize", "status": "completed", "output": {"$exists": True}},
        sort=[("completed_at", -1)],
        projection={"_id": 0, "id": 1, "completed_at": 1, "output": 1}
    )

    def _format(job_doc):
        if not job_doc:
            return None
        payload = job_doc.get("output") or {}
        payload["job_id"] = job_doc.get("id")
        payload["completed_at"] = job_doc.get("completed_at")
        return payload

    return {"prediction": _format(prediction_job), "optimisation": _format(optimisation_job)}


@api_router.get("/team/current")
async def get_current_team(current_user: str = Depends(get_current_user)):
    team_id_doc = await db.secrets.find_one({"key": "FPL_TEAM_ID"})
    if not team_id_doc or not team_id_doc.get("value"):
        raise HTTPException(status_code=404, detail="FPL team ID not configured")

    team_id = str(team_id_doc.get("value")).strip()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            bootstrap_resp = await client.get('https://fantasy.premierleague.com/api/bootstrap-static/')
            bootstrap_resp.raise_for_status()
            bootstrap_data = bootstrap_resp.json()

            current_event = next((event for event in bootstrap_data.get('events', []) if event.get('is_current')), None)
            if not current_event:
                current_event = next((event for event in bootstrap_data.get('events', []) if event.get('is_next')), None)
            if not current_event and bootstrap_data.get('events'):
                current_event = bootstrap_data['events'][-1]

            if not current_event:
                raise HTTPException(status_code=502, detail="Unable to determine current gameweek")

            event_id = current_event['id']
            picks_resp = await client.get(f'https://fantasy.premierleague.com/api/entry/{team_id}/event/{event_id}/picks/')
            picks_resp.raise_for_status()
            picks_data = picks_resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f'Failed to fetch FPL data: {exc}') from exc

    elements = {element['id']: element for element in bootstrap_data.get('elements', [])}
    teams = {team['id']: team for team in bootstrap_data.get('teams', [])}
    position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    picks = sorted(picks_data.get('picks', []), key=lambda item: item.get('position', 0))
    players = []
    for pick in picks:
        element = elements.get(pick.get('element'))
        if not element:
            continue
        team_info = teams.get(element.get('team'), {})
        try:
            points_per_game = float(element.get('points_per_game', '0') or 0)
        except ValueError:
            points_per_game = 0.0
        player_entry = {
            'position_slot': pick.get('position'),
            'player_id': pick.get('element'),
            'name': element.get('web_name'),
            'team': team_info.get('short_name'),
            'position': position_map.get(element.get('element_type'), str(element.get('element_type'))),
            'multiplier': pick.get('multiplier', 0),
            'is_captain': pick.get('is_captain', False),
            'is_vice_captain': pick.get('is_vice_captain', False),
            'now_cost': element.get('now_cost', 0) / 10 if element.get('now_cost') is not None else None,
            'points_per_game': points_per_game,
            'event_points': element.get('event_points'),
        }
        players.append(player_entry)

    history = picks_data.get('entry_history', {})
    def _to_value(raw):
        return raw / 10 if isinstance(raw, (int, float)) else None

    entry_summary = {
        'bank': _to_value(history.get('bank')),
        'team_value': _to_value(history.get('value')),
        'total_points': history.get('total_points'),
        'event_points': history.get('points'),
        'event_transfers': history.get('event_transfers'),
        'event_transfers_cost': history.get('event_transfers_cost'),
        'points_on_bench': history.get('points_on_bench'),
    }

    return {
        'team_id': team_id,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'gameweek': {
            'id': current_event.get('id'),
            'name': current_event.get('name'),
            'deadline': current_event.get('deadline_time'),
            'is_current': current_event.get('is_current'),
        },
        'players': players,
        'entry_summary': entry_summary,
    }



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
