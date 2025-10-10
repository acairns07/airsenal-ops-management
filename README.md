# AIrsenal Control Room

A production-ready web application for managing Fantasy Premier League predictions and optimizations using the AIrsenal open-source project.

## Features

- 🔐 **Single-User Authentication** - Secure email/password login with bcrypt hashing
- 📊 **Setup & Initialization** - Create and update AIrsenal database
- 🎯 **Predictions** - Run player predictions for upcoming gameweeks
- ⚡ **Optimisation** - Multi-week team optimization with chip planning
- 📝 **Jobs & Logs** - View job history with live log streaming
- ⚙️ **Settings** - Manage FPL credentials and app configuration

## Tech Stack

- **Frontend**: React 19, Tailwind CSS, Shadcn UI, Axios
- **Backend**: FastAPI, Motor (async MongoDB), WebSocket
- **Database**: MongoDB
- **Authentication**: JWT with bcrypt password hashing
- **AI Engine**: AIrsenal (Python 3.11)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11 (for local development)

### Local Development with Docker Compose

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd airsenal-control-room
   ```

2. **Set up environment variables**
   ```bash
   # Copy example env files
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   
   # Edit backend/.env
   MONGO_URL=mongodb://mongodb:27017
   DB_NAME=airsenal_control
   JWT_SECRET=your-secret-key-here
   
   # Edit frontend/.env
   REACT_APP_BACKEND_URL=http://localhost:8001
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Initialize admin credentials**
   ```bash
   docker-compose exec backend python3 setup_admin.py
   ```
   
   Default credentials:
   - Email: `admin@airsenal.com`
   - Password: `admin123`
   
   ⚠️ **Change these immediately via the Settings page!**

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001/api

### Local Development (without Docker)

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start MongoDB (ensure MongoDB is running)
# Update MONGO_URL in backend/.env

python3 setup_admin.py
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

#### Frontend Setup
```bash
cd frontend
yarn install

# Update REACT_APP_BACKEND_URL in frontend/.env
REACT_APP_BACKEND_URL=http://localhost:8001

yarn start
```

## Deployment to Railway

### 1. Create Railway Project

1. Go to [Railway.app](https://railway.app) and create a new project
2. Add three services: MongoDB, Backend, Frontend

### 2. Deploy MongoDB

1. Add MongoDB from Railway template
2. Note the connection string from MongoDB variables

### 3. Deploy Backend

1. **Connect your GitHub repository**
2. **Set Root Directory**: `/backend`
3. **Set Environment Variables**:
   ```
   MONGO_URL=<mongodb-connection-string-from-railway>
   DB_NAME=airsenal_control
   JWT_SECRET=<generate-a-secure-random-string>
   CORS_ORIGINS=https://your-frontend-url.railway.app
   ```
4. **Add volume** for persistent data:
   - Mount path: `/data/airsenal`
5. **Deploy command**: Leave default or use
   ```
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

### 4. Deploy Frontend

1. **Connect your GitHub repository**
2. **Set Root Directory**: `/frontend`
3. **Set Environment Variables**:
   ```
   REACT_APP_BACKEND_URL=https://your-backend-url.railway.app
   ```
4. **Build command**: `yarn build`
5. **Start command**: `yarn start`

### 5. Initialize Admin Credentials

Run this command in Railway backend shell:
```bash
python3 setup_admin.py
```

## Usage

### 1. Setup

- Navigate to **Setup** page
- Click "Update DB" to fetch latest FPL data
- Monitor live logs during execution

### 2. Configure FPL Credentials

- Go to **Settings**
- Add your FPL credentials:
  - FPL_TEAM_ID (your team ID from FPL website)
  - FPL_LOGIN (your FPL email)
  - FPL_PASSWORD (your FPL password)
  - AIRSENAL_HOME (default: `/data/airsenal`)

### 3. Run Predictions

- Navigate to **Predictions**
- Select weeks ahead (1-6)
- Click "Run Prediction"
- View live logs and results

### 4. Run Optimisation

- Navigate to **Optimisation**
- Select weeks ahead
- (Optional) Set chip weeks for strategic planning
- Click "Run Optimisation"
- View transfer suggestions and lineup recommendations

### 5. View Job History

- Navigate to **Jobs & Logs**
- View all past job executions
- Click "View Logs" to see detailed execution logs

## Security Notes

### Password Management

1. **Generate Password Hash**:
   - Go to Settings → Password Hash Generator
   - Enter your desired password
   - Click "Generate Hash"
   - Copy the generated hash

2. **Update Admin Password**:
   - Paste the hash in "Admin Password Hash" field
   - Click "Save Secrets"

### Environment Variables

Never commit these to version control:
- `JWT_SECRET` - Use a strong random string
- `FPL_PASSWORD` - Your FPL account password
- `APP_ADMIN_PASSWORD_HASH` - Bcrypt hash of admin password

## Architecture

```
┌─────────────────┐
│   React App     │
│  (Port 3000)    │
└────────┬────────┘
         │ HTTP/WebSocket
         ↓
┌─────────────────┐
│  FastAPI Server │
│  (Port 8001)    │
└────────┬────────┘
         │
    ┌────┴─────┬──────────────┐
    ↓          ↓              ↓
┌────────┐ ┌────────┐  ┌──────────────┐
│ MongoDB│ │AIrsenal│  │Job Queue     │
│ (27017)│ │ CLI    │  │(Async Tasks) │
└────────┘ └────────┘  └──────────────┘
```

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Troubleshooting

### Python Version Error

AIrsenal requires Python < 3.13. Check version:
```bash
python3 --version
```

### MongoDB Connection Issues

Ensure MongoDB is running and MONGO_URL is correct:
```bash
# Test connection
mongosh "$MONGO_URL"
```

### WebSocket Connection Issues

Ensure CORS_ORIGINS includes your frontend URL and WebSocket connections are allowed.

### Job Not Running

Check backend logs:
```bash
# Docker
docker-compose logs backend

# Railway
# View logs in Railway dashboard
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [AIrsenal](https://github.com/alan-turing-institute/AIrsenal) - The AI-powered FPL assistant
- [Fantasy Premier League](https://fantasy.premierleague.com/) - The official FPL API
- [Shadcn UI](https://ui.shadcn.com/) - Beautiful React components

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions

---

**Made with ❤️ for FPL managers worldwide**
