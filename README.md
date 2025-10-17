# AIrsenal Ops Console

## Overview
AIrsenal Ops Console is a full-stack "control room" for running the AIrsenal Fantasy Premier League analytics toolkit. The FastAPI backend wraps the official AIrsenal CLI commands, persists state in MongoDB plus a mounted SQLite file, and exposes a single-admin JWT-authenticated API. A React 19 + Tailwind UI drives job execution (database setup, updates, predictions, optimisation, full pipeline), streams live logs over WebSockets, and lets the operator manage secrets such as FPL credentials.

## Key Features
- Single admin login backed by bcrypt-hashed credentials stored in MongoDB secrets
- Job queue that shells out to the AIrsenal CLI (`airsenal_setup_initial_db`, `airsenal_update_db`, etc.) with SQLite hydration and persistence between runs
- Real-time log streaming over `/ws/jobs/{id}` WebSocket with status updates
- Setup dashboard for health checks and one-click execution of setup/update/pipeline jobs
- Predictions and optimisation screens to schedule multi-week runs with chip planning parameters
- Secrets management UI for updating admin login, FPL credentials, and AIrsenal home directory

## Architecture
```
+------------------+      +---------------------------+      +---------------------+
| React 19 frontend| <--> | FastAPI backend (JWT auth) | <--> | MongoDB (secrets &   |
| CRA + Tailwind   |      | Async job queue + WebSocket|      | job metadata)        |
+------------------+      +---------------------------+      +---------------------+
                                     |
                                     v
                         AIrsenal CLI subprocess commands
                                     |
                                     v
                     SQLite database persisted to mounted storage
```

Supporting infrastructure files (`backend.yaml`, `envstorage.json`) show an Azure Container Apps deployment that mounts Azure Files for the AIrsenal SQLite database.

## Repository Layout
- `backend/` FastAPI application, job queue, MongoDB access, CLI integration, admin bootstrap script
- `frontend/` Create React App with CRACO overrides, shadcn/ui components, routing, WebSocket log viewer
- `Dockerfile.backend` & `Dockerfile.frontend` production images (backend installs AIrsenal from GitHub)
- `docker-compose.yml` local orchestration for MongoDB, backend API, and frontend UI
- `.emergent/`, `backend.yaml`, `envstorage.json` deployment aids for Azure Container Apps
- `tests/` currently empty placeholder for future backend test suite

## Local Development
### Prerequisites
- Docker Desktop (for the Compose workflow)
- Python 3.11 with `pip` if running the backend directly
- Node.js 20 + Yarn 1.x for local frontend development

### Quick Start with Docker Compose
1. Copy env templates:
   ```powershell
   Copy-Item backend/.env.example backend/.env
   Copy-Item frontend/.env.example frontend/.env
   ```
2. Edit `backend/.env` with your Mongo connection string, database name, CORS origins, and a long random `JWT_SECRET`.
3. Edit `frontend/.env` so `REACT_APP_BACKEND_URL` matches where the backend will run (`http://localhost:8001` by default).
4. Launch the stack:
   ```powershell
   docker-compose up --build
   ```
5. Seed admin credentials (stores bcrypt hash + email in MongoDB):
   ```powershell
   docker-compose exec backend python setup_admin.py
   ```
6. Sign in at `http://localhost:3000` using the credentials printed by the setup script, then change them in **Settings → Update Secrets**.

### Running the Backend Without Docker
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
pip install "git+https://github.com/alan-turing-institute/AIrsenal.git@v0.5.3"
copy .env.example .env        # populate Mongo URL, DB name, JWT secret, CORS origins
python setup_admin.py         # seeds admin email + password hash
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```
Set `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `CORS_ORIGINS`, and optional `LOCAL_DB_PATH`/`PERSISTENT_DB_PATH` in the environment or `.env`. The default SQLite persistence location is `/data/airsenal/data.db`; in development it falls back to `/tmp/airsenal.db` if unavailable.

### Running the Frontend Without Docker
```powershell
cd frontend
yarn install
yarn start
```
Ensure `frontend/.env` has `REACT_APP_BACKEND_URL=http://localhost:8001`. The CRA dev server proxies API calls via that URL and uses the same origin for the WebSocket connection.

## Secrets & Admin Credentials
- Secrets are stored in the `secrets` collection of MongoDB. Keys currently used: `APP_ADMIN_EMAIL`, `APP_ADMIN_PASSWORD_HASH`, `FPL_TEAM_ID`, `FPL_LOGIN`, `FPL_PASSWORD`, `AIRSENAL_HOME`.
- Use the **Password Hash Generator** in the Settings page or call `POST /api/auth/hash-password` to produce a bcrypt hash before saving a new admin password.
- Avoid storing raw FPL credentials in source control; the UI writes them straight to MongoDB via the backend.

## Job Queue & AIrsenal CLI
The backend queues jobs in MongoDB (`jobs` collection) and processes them sequentially:
- `setup_db` → runs `airsenal_setup_initial_db`
- `update_db` → runs `airsenal_update_db`
- `predict` → runs `airsenal_run_prediction --weeks_ahead <n>`
- `optimize` → runs `airsenal_run_optimization` with optional chip parameters
- `pipeline` → runs the full AIrsenal pipeline (update + prediction + optimisation)

Before each run the worker hydrates a local SQLite database from the persisted path, injects secrets as environment variables, streams stdout to MongoDB + WebSocket listeners, and persists the SQLite file back to the mounted storage once the command succeeds.

## Utilities
- `backend/setup_admin.py` seeds initial admin credentials in MongoDB.
- `backend/airsenal_mock.py` offers a lightweight stand-in for AIrsenal CLI commands; you can symlink or rename it to mimic the real executables during demos or on machines without AIrsenal installed.
- `test_result.md` captures previous CI output for reference.

## Deployment Notes
- `Dockerfile.backend` installs AIrsenal from GitHub at build time (pinned via the `AIRSENAL_REF` build arg) and runs `uvicorn`.
- `Dockerfile.frontend` builds the React bundle with a baked-in `REACT_APP_BACKEND_URL` and serves it through Nginx.
- `backend.yaml` and `envstorage.json` document a working Azure Container Apps deployment that mounts Azure Files (`/data/airsenal`) to persist the AIrsenal SQLite database and uses Container Registry images `opsconsole-backend` / `opsconsole-frontend`.
- Scale-to-zero is disabled (`minReplicas: 1`) so the job queue and WebSocket remain available.

## Testing
The repository currently lacks automated tests. Suggested starting points:
- Backend unit tests for authentication, job queue transitions, and WebSocket broadcasting (pytest + httpx + Starlette test client).
- Contract tests around AIrsenal CLI invocation using the mock script.
- Frontend component tests for pages that orchestrate jobs and secrets.

## Contributing
1. Fork the repository and create a feature branch.
2. Run linting (`flake8`, `black`, `isort`, `mypy`, CRA `yarn lint` if configured) before submitting changes.
3. Open a pull request describing the feature or fix.
