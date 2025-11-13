# AIrsenal Ops Console

## Overview
AIrsenal Ops Console is a full-stack "control room" for running the AIrsenal Fantasy Premier League analytics toolkit. The FastAPI backend wraps the official AIrsenal CLI commands, persists state in MongoDB plus a mounted SQLite file, and exposes a single-admin JWT-authenticated API. A React 19 + Tailwind UI drives job execution (database setup, updates, predictions, optimisation, full pipeline), streams live logs over WebSockets, and lets the operator manage secrets such as FPL credentials.

## Key Features
- **AI Intelligence Layer**: OpenAI-powered recommendations combining ML predictions with real-time news, Reddit sentiment, and community insights
- **Modular Architecture**: Refactored backend with separated concerns (auth, jobs, API, middleware, utils)
- **Security**: Encrypted secrets at rest (Fernet), rate limiting, WebSocket authentication, JWT tokens
- **Comprehensive Testing**: 72% test coverage with pytest suite (50+ test cases)
- Single admin login backed by bcrypt-hashed credentials stored in MongoDB secrets
- Job queue with retry logic that shells out to AIrsenal CLI with SQLite hydration and persistence
- Real-time log streaming over `/ws/jobs/{id}` WebSocket with status updates
- Setup dashboard for health checks and one-click execution of setup/update/pipeline jobs
- Predictions and optimisation screens to schedule multi-week runs with chip planning parameters
- Secrets management UI for updating admin login, FPL credentials, and AIrsenal home directory
- Structured JSON logging for observability

## Architecture
```
+------------------+      +---------------------------+      +---------------------+
| React 19 frontend| <--> | FastAPI backend (JWT auth) | <--> | MongoDB (secrets,   |
| AI Recommendations|     | Rate limiting + encryption |      | jobs, AI cache)     |
| shadcn/ui        |      | Modular architecture:      |      +---------------------+
+------------------+      | - auth/ - jobs/            |
                          | - api/  - middleware/      |      +---------------------+
                          | - ai/   - intelligence/    | <--> | OpenAI API          |
                          +---------------------------+      | Reddit API (r/FPL)  |
                                     |                        | NewsAPI             |
                                     v                        +---------------------+
                         AIrsenal CLI subprocess commands
                                     |
                                     v
                     SQLite database persisted to mounted storage
```

The AI Intelligence Layer combines AIrsenal ML predictions with real-time data from multiple sources, using OpenAI to generate data-driven FPL recommendations.

Supporting infrastructure files (`backend.yaml`, `envstorage.json`) show an Azure Container Apps deployment that mounts Azure Files for the AIrsenal SQLite database.

## Repository Layout
- `backend/` - Modular FastAPI application with:
  - `auth/` - JWT authentication and password hashing
  - `jobs/` - Job queue with retry logic
  - `api/` - REST API endpoints (secrets, jobs, predictions, AI)
  - `ai/` - OpenAI integration, prompts, recommendation engine
  - `intelligence/` - Reddit scraper, news aggregator, sentiment analysis
  - `models/` - Pydantic data models
  - `middleware/` - Rate limiting and request processing
  - `utils/` - Encryption (Fernet), logging, database utilities
  - `tests/` - Pytest suite with 72% coverage (50+ test cases)
- `frontend/` - React 19 + shadcn/ui application with:
  - AI Recommendations page
  - Setup dashboard, predictions, optimisation, reports
  - Real-time WebSocket log viewer
- `LOCAL_DEVELOPMENT.md` - Comprehensive local setup guide
- `Dockerfile.backend` & `Dockerfile.frontend` - Production images
- `docker-compose.yml` - Local orchestration for MongoDB, backend API, and frontend UI
- `.emergent/`, `backend.yaml`, `envstorage.json` - Azure Container Apps deployment

## Local Development
### Prerequisites
- Docker Desktop (for the Compose workflow)
- Python 3.11 with `pip` if running the backend directly
- Node.js 20 + Yarn 1.x for local frontend development
- **API Keys** (for AI features):
  - OpenAI API key (required for AI recommendations)
  - Reddit API credentials (client ID, client secret, user agent)
  - NewsAPI key (optional, for news aggregation)

### Quick Start with Docker Compose
1. Copy env templates:
   ```powershell
   Copy-Item backend/.env.example backend/.env
   Copy-Item frontend/.env.example frontend/.env
   ```
2. Edit `backend/.env` with required configuration:
   ```bash
   # Core Settings
   MONGO_URL=mongodb://mongo:27017
   DB_NAME=airsenal_ops
   JWT_SECRET=your-long-random-secret-here
   ENCRYPTION_KEY=your-32-byte-base64-encryption-key
   CORS_ORIGINS=http://localhost:3000

   # AI Features (REQUIRED for AI Recommendations)
   OPENAI_API_KEY=sk-your-openai-api-key-here
   REDDIT_CLIENT_ID=your-reddit-client-id
   REDDIT_CLIENT_SECRET=your-reddit-client-secret
   REDDIT_USER_AGENT=AIrsenalOps/1.0

   # Optional
   NEWS_API_KEY=your-newsapi-key-here
   AI_MODEL=gpt-4o-mini
   AI_TEMPERATURE=0.7
   INTELLIGENCE_CACHE_HOURS=1
   ```
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

**📖 For detailed setup instructions, API key configuration, and troubleshooting, see [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md)**

### Running the Backend Without Docker
```bash
cd backend
python -m venv venv
source venv/bin/activate   # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
pip install "git+https://github.com/alan-turing-institute/AIrsenal.git@v0.5.3"
cp .env.example .env        # populate all required environment variables
python setup_admin.py       # seeds admin email + password hash
pytest                      # run test suite (optional)
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

**Required environment variables:**
- `MONGO_URL`, `DB_NAME` - MongoDB connection
- `JWT_SECRET` - Long random string for JWT tokens (32+ characters)
- `ENCRYPTION_KEY` - 32-byte base64 key for Fernet encryption (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `OPENAI_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` - AI features
- `CORS_ORIGINS` - Frontend URL (e.g., `http://localhost:3000`)

**Optional variables:**
- `LOCAL_DB_PATH`/`PERSISTENT_DB_PATH` - SQLite persistence (defaults to `/data/airsenal/data.db`, falls back to `/tmp/airsenal.db`)
- `NEWS_API_KEY` - NewsAPI integration
- `AI_MODEL`, `AI_TEMPERATURE`, `INTELLIGENCE_CACHE_HOURS` - AI tuning

### Running the Frontend Without Docker
```powershell
cd frontend
yarn install
yarn start
```
Ensure `frontend/.env` has `REACT_APP_BACKEND_URL=http://localhost:8001`. The CRA dev server proxies API calls via that URL and uses the same origin for the WebSocket connection.

## Secrets & Admin Credentials
- **Encrypted at Rest**: Secrets are stored in the `secrets` collection of MongoDB with Fernet encryption (AES-128-CBC).
- **Secret Keys**: `APP_ADMIN_EMAIL`, `APP_ADMIN_PASSWORD_HASH`, `FPL_TEAM_ID`, `FPL_LOGIN`, `FPL_PASSWORD`, `AIRSENAL_HOME`.
- **Password Hashing**: Use the **Password Hash Generator** in the Settings page or call `POST /api/auth/hash-password` to produce a bcrypt hash before saving a new admin password.
- **Security**:
  - `ENCRYPTION_KEY` environment variable is required (32-byte base64 key)
  - `JWT_SECRET` is required for authentication tokens
  - Rate limiting prevents brute force attacks (60 requests/minute default)
  - Avoid storing raw credentials in source control; the UI writes them encrypted to MongoDB via the backend.

## Job Queue & AIrsenal CLI
The backend queues jobs in MongoDB (`jobs` collection) and processes them sequentially:
- `setup_db` → runs `airsenal_setup_initial_db`
- `update_db` → runs `airsenal_update_db`
- `predict` → runs `airsenal_run_prediction --weeks_ahead <n>`
- `optimize` → runs `airsenal_run_optimization` with optional chip parameters
- `pipeline` → runs the full AIrsenal pipeline (update + prediction + optimisation)

Before each run the worker hydrates a local SQLite database from the persisted path, injects secrets as environment variables, streams stdout to MongoDB + WebSocket listeners, and persists the SQLite file back to the mounted storage once the command succeeds.

## AI Intelligence Layer
The AI Recommendations feature combines AIrsenal ML predictions with real-time intelligence to generate data-driven FPL recommendations:

**Data Sources:**
- **AIrsenal Predictions**: Player scores, form, expected points from ML models
- **Reddit Intelligence**: Community sentiment from r/FantasyPL (hot topics, discussions, injury news)
- **News Aggregation**: Breaking FPL news from multiple sources via NewsAPI
- **Sentiment Analysis**: Keyword-based sentiment scoring across all text sources

**AI Analysis:**
- Uses OpenAI (GPT-4o-mini by default) to reason about combined data
- Generates transfer recommendations with confidence scores and risk levels
- Provides captaincy suggestions with alternatives
- Explains reasoning based on form, fixtures, sentiment, and breaking news
- Caches intelligence data for 1 hour to reduce API costs

**API Endpoints:**
- `POST /api/ai/analyze` - Generate comprehensive AI analysis for a gameweek
- `GET /api/ai/intelligence/feed` - Get latest intelligence feed
- `GET /api/ai/player/{name}` - Get player-specific intelligence

**Frontend:**
Navigate to **AI Recommendations** in the dashboard to:
1. Select target gameweek
2. Generate AI analysis
3. View transfer recommendations with reasoning
4. See captaincy suggestions
5. Browse breaking news and community sentiment

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
The backend includes a comprehensive test suite with **72% code coverage**:

```bash
cd backend
pytest                          # run all tests
pytest --cov=. --cov-report=html  # generate coverage report
```

**Test coverage includes:**
- `test_auth.py` - JWT token generation/validation, password hashing (10 tests)
- `test_encryption.py` - Fernet encryption/decryption, key validation (8 tests)
- `test_secrets_api.py` - Secrets management API endpoints (12 tests)
- `test_jobs_api.py` - Job queue operations, status tracking (10 tests)
- `test_rate_limiting.py` - Rate limiter logic, client tracking (6 tests)
- Additional tests for WebSocket broadcasting, job retries, AI endpoints

**Future test areas:**
- AI recommendation engine integration tests
- Intelligence gathering mocks (Reddit, NewsAPI)
- Frontend component tests with React Testing Library

## Contributing
1. Fork the repository and create a feature branch.
2. Run linting (`flake8`, `black`, `isort`, `mypy`, CRA `yarn lint` if configured) before submitting changes.
3. Open a pull request describing the feature or fix.
