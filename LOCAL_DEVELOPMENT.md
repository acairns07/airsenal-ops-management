# Local Development Setup Guide

## Prerequisites

### Required Software
- **Docker Desktop** (for Mac/Windows) or Docker + Docker Compose (for Linux)
- **Git** (for version control)
- **Code Editor** (VS Code recommended)

### Optional (for native development without Docker)
- **Python 3.11+** (backend)
- **Node.js 20+** (frontend)
- **MongoDB 7** (database)

---

## Quick Start (Docker - Recommended)

### 1. Clone the Repository
```bash
git clone https://github.com/acairns07/airsenal-ops-management.git
cd airsenal-ops-management
```

### 2. Set Up Environment Variables

**Backend:**
```bash
cd backend
cp .env.example .env
```

**Edit `backend/.env`** with your configuration:
```bash
# MongoDB (leave as-is for Docker)
MONGO_URL=mongodb://mongodb:27017
DB_NAME=airsenal_control

# Security (REQUIRED - generate secure keys)
JWT_SECRET=your-secure-jwt-secret-here
ENCRYPTION_KEY=your-32-byte-encryption-key-here

# CORS
CORS_ORIGINS=http://localhost:3000

# AI Features (NEW - get these from respective services)
OPENAI_API_KEY=sk-your-openai-api-key-here
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_USER_AGENT=AIrsenalOps/1.0

# News API (optional)
NEWS_API_KEY=your-newsapi-key

# Rate Limiting
RATE_LIMIT_ENABLED=false  # Disable for local dev
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text  # Use 'text' for local dev (colored), 'json' for production

# Job Queue
MAX_JOB_RETRIES=3
JOB_RETRY_DELAY_SECONDS=60

# Database Paths (Docker managed)
PERSISTENT_DB_PATH=/data/airsenal/data.db
LOCAL_DB_PATH=/tmp/airsenal.db
```

**Frontend:**
```bash
cd ../frontend
cp .env.example .env
```

**Edit `frontend/.env`:**
```bash
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 3. Generate Secure Keys

**JWT Secret:**
```bash
# Generate a random 32-character string
openssl rand -base64 32
```

**Encryption Key (must be 32 bytes):**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Get API Keys

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign up / Log in
3. Create new API key
4. Copy to `OPENAI_API_KEY` in `.env`
5. **Cost**: GPT-4 is ~$0.03 per analysis, GPT-3.5-Turbo is ~$0.001

#### Reddit API Credentials
1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app..."
3. Fill in:
   - **Name**: AIrsenal Ops Console
   - **Type**: Script
   - **Description**: FPL intelligence gathering
   - **Redirect URI**: http://localhost:8001 (required but not used)
4. Click "create app"
5. Copy:
   - **Client ID** (under app name)
   - **Secret** (labeled as "secret")
6. Add to `.env`:
   ```bash
   REDDIT_CLIENT_ID=your_14_char_id
   REDDIT_CLIENT_SECRET=your_27_char_secret
   REDDIT_USER_AGENT=AIrsenalOps/1.0
   ```

#### NewsAPI Key (Optional)
1. Go to https://newsapi.org/register
2. Sign up (free tier: 100 requests/day)
3. Copy API key to `NEWS_API_KEY` in `.env`

### 5. Start the Application

**Using Docker Compose (Recommended):**
```bash
# From project root
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

This will start:
- **MongoDB** on `localhost:27017`
- **Backend** on `http://localhost:8001`
- **Frontend** on `http://localhost:3000`

**Check logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 6. Initialize Admin User

**First time only:**
```bash
# Create admin credentials
docker-compose exec backend python setup_admin.py
```

Follow the prompts to set up your admin email and password.

### 7. Access the Application

Open your browser to:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs (Swagger UI)

---

## Native Development (Without Docker)

### Prerequisites
- Python 3.11+
- Node.js 20+
- MongoDB 7 (running on localhost:27017)

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install AIrsenal
pip install "git+https://github.com/alan-turing-institute/AIrsenal.git@v0.5.3"

# Copy and configure .env
cp .env.example .env
# Edit .env with your keys (see above)
# Set MONGO_URL=mongodb://localhost:27017

# Initialize admin
python setup_admin.py

# Run backend
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Copy and configure .env
cp .env.example .env
# Edit .env: REACT_APP_BACKEND_URL=http://localhost:8001

# Run frontend
yarn start
```

**Access**: http://localhost:3000

---

## Testing

### Run Backend Tests

**With Docker:**
```bash
docker-compose exec backend ./test_runner.sh
```

**Native:**
```bash
cd backend
source venv/bin/activate
./test_runner.sh
```

### Run Specific Tests

```bash
# Authentication tests
pytest tests/test_auth.py -v

# AI module tests (after implementation)
pytest tests/test_ai.py -v

# With coverage
pytest --cov=backend --cov-report=html
```

### Test Coverage Report

After running tests, view coverage:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

---

## Development Workflow

### Making Changes

**Backend changes:**
```bash
# Edit files in backend/
# Changes hot-reload automatically with uvicorn --reload
```

**Frontend changes:**
```bash
# Edit files in frontend/src/
# React will hot-reload automatically
```

**Database changes:**
```bash
# View MongoDB data
docker-compose exec mongodb mongosh airsenal_control

# Or use MongoDB Compass: mongodb://localhost:27017
```

### Adding Dependencies

**Backend (Python):**
```bash
# Add to requirements.txt
pip install <package>
pip freeze > requirements.txt

# Rebuild Docker image
docker-compose up -d --build backend
```

**Frontend (Node):**
```bash
cd frontend
yarn add <package>

# Rebuild Docker image
docker-compose up -d --build frontend
```

### Debugging

**Backend debugging:**
```bash
# View logs
docker-compose logs -f backend

# Or add print statements / use logger
from utils.logging import get_logger
logger = get_logger(__name__)
logger.debug("Debug message")
```

**Frontend debugging:**
- Open browser DevTools (F12)
- Check Console tab for errors
- Network tab for API calls

**Database debugging:**
```bash
# Connect to MongoDB
docker-compose exec mongodb mongosh airsenal_control

# List collections
show collections

# Query data
db.jobs.find().pretty()
db.secrets.find().pretty()
```

---

## Common Issues & Solutions

### Issue: "MongoDB connection refused"
```bash
# Check if MongoDB is running
docker-compose ps

# Restart MongoDB
docker-compose restart mongodb

# Check logs
docker-compose logs mongodb
```

### Issue: "Port already in use"
```bash
# Find process using port
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows

# Stop docker-compose and restart
docker-compose down
docker-compose up
```

### Issue: "JWT_SECRET not set"
```bash
# Make sure .env file exists
ls backend/.env

# Generate a secret
openssl rand -base64 32

# Add to backend/.env:
JWT_SECRET=<generated-secret>
```

### Issue: "Module not found" in Python
```bash
# Rebuild backend container
docker-compose up -d --build backend

# Or reinstall dependencies
docker-compose exec backend pip install -r requirements.txt
```

### Issue: Frontend won't connect to backend
```bash
# Check frontend .env
cat frontend/.env
# Should have: REACT_APP_BACKEND_URL=http://localhost:8001

# Check backend is running
curl http://localhost:8001/api/health

# Restart frontend
docker-compose restart frontend
```

### Issue: "OpenAI API key invalid"
```bash
# Verify key is set
docker-compose exec backend printenv OPENAI_API_KEY

# Check key is valid at https://platform.openai.com/api-keys
# Regenerate if needed
```

---

## Production vs Development

| Feature | Development | Production (Azure) |
|---------|-------------|-------------------|
| MongoDB | Docker container | Azure Cosmos DB / Atlas |
| Secrets | `.env` file | Azure Key Vault / Env vars |
| Logging | Text (colored) | JSON |
| Rate Limiting | Disabled | Enabled |
| CORS | localhost only | Specific origins |
| HTTPS | Not required | Required |
| Error Detail | Full stack traces | Limited detail |

---

## Useful Commands

### Docker Compose
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# View logs
docker-compose logs -f

# Execute command in container
docker-compose exec backend bash
docker-compose exec backend python setup_admin.py

# Remove all data (CAUTION: deletes database)
docker-compose down -v
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/ai-intelligence

# Stage changes
git add .

# Commit
git commit -m "Add AI intelligence layer"

# Push
git push -u origin feature/ai-intelligence
```

### Database Management
```bash
# Backup MongoDB
docker-compose exec mongodb mongodump --out=/tmp/backup
docker-compose cp mongodb:/tmp/backup ./backup

# Restore MongoDB
docker-compose cp ./backup mongodb:/tmp/backup
docker-compose exec mongodb mongorestore /tmp/backup
```

---

## Environment Variables Reference

### Required
- `MONGO_URL` - MongoDB connection string
- `DB_NAME` - Database name
- `JWT_SECRET` - JWT signing secret (32+ chars)
- `ENCRYPTION_KEY` - Fernet encryption key (32 bytes)
- `OPENAI_API_KEY` - OpenAI API key for AI features

### AI & Intelligence (New)
- `REDDIT_CLIENT_ID` - Reddit API client ID
- `REDDIT_CLIENT_SECRET` - Reddit API secret
- `REDDIT_USER_AGENT` - User agent string
- `NEWS_API_KEY` - NewsAPI key (optional)
- `AI_MODEL` - OpenAI model (default: gpt-4o-mini)
- `AI_TEMPERATURE` - Model temperature (default: 0.7)
- `INTELLIGENCE_CACHE_HOURS` - Cache duration (default: 1)

### Optional
- `CORS_ORIGINS` - Comma-separated allowed origins
- `RATE_LIMIT_ENABLED` - Enable rate limiting (true/false)
- `RATE_LIMIT_PER_MINUTE` - Requests per minute (default: 60)
- `MAX_JOB_RETRIES` - Job retry attempts (default: 3)
- `JOB_RETRY_DELAY_SECONDS` - Delay between retries (default: 60)
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)
- `LOG_FORMAT` - Log format (text/json)
- `PERSISTENT_DB_PATH` - AIrsenal DB path
- `LOCAL_DB_PATH` - Temp DB path

---

## Next Steps

1. ✅ Set up environment variables
2. ✅ Start Docker Compose
3. ✅ Initialize admin user
4. ✅ Access frontend at http://localhost:3000
5. ✅ Test basic functionality (login, create job)
6. ✅ Test AI features (after implementation)
7. 🚀 Start building!

---

## Support

**Documentation:**
- Architecture: `backend/ARCHITECTURE.md`
- API Docs: http://localhost:8001/docs
- Refactoring Summary: `REFACTORING_SUMMARY.md`

**Troubleshooting:**
- Check logs: `docker-compose logs -f`
- Run tests: `docker-compose exec backend ./test_runner.sh`
- Verify config: `docker-compose exec backend printenv`

**Get Help:**
- Review logs for error messages
- Check environment variables are set correctly
- Ensure all required API keys are valid
- Try rebuilding containers: `docker-compose up -d --build`
