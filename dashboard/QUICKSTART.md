# ZeroLocal Dashboard - Quick Start

Get the dashboard running in under 5 minutes.

## Prerequisites

- Node.js 20+
- npm or yarn
- ZeroDB Local API running on `localhost:8000`

## Option 1: Development Mode (Fast)

```bash
# Navigate to dashboard directory
cd /Users/aideveloper/core/zerodb-local/dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Open browser
open http://localhost:3000
```

## Option 2: Docker Compose (Recommended)

```bash
# Navigate to zerodb-local
cd /Users/aideveloper/core/zerodb-local

# Start all services including dashboard
docker-compose up

# Or just the dashboard
docker-compose up dashboard

# Open browser
open http://localhost:3000
```

## Option 3: Production Build

```bash
# Navigate to dashboard
cd /Users/aideveloper/core/zerodb-local/dashboard

# Install dependencies
npm install

# Build for production
npm run build

# Start production server
npm start

# Open browser
open http://localhost:3000
```

## Verify Installation

1. **Dashboard loads**: You should see the ZeroLocal Dashboard homepage
2. **System Status**: All 5 services should show "healthy" status
3. **Navigation works**: Click through Projects, Vectors, Tables, Logs
4. **API Connected**: No connection errors displayed

## Troubleshooting

### Dashboard won't start

```bash
# Check if port 3000 is available
lsof -i :3000

# Kill process if needed
kill -9 <PID>
```

### API Connection Error

```bash
# Verify API is running
curl http://localhost:8000/health

# Should return JSON with status "healthy"
```

### Docker Issues

```bash
# Check if containers are running
docker ps | grep zerodb

# View logs
docker-compose logs dashboard

# Rebuild if needed
docker-compose build dashboard
docker-compose up dashboard
```

### Module Not Found Errors

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
```

## Environment Variables

Create `.env.local` if needed:

```env
VITE_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Default Ports

- **Dashboard**: http://localhost:3000
- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Qdrant**: localhost:6333
- **MinIO Console**: localhost:9001
- **RedPanda**: localhost:9092
- **Embeddings**: localhost:8001

## Next Steps

1. **Create a Project**: Go to Projects → New Project
2. **Upload Vectors**: Use the API to add vector embeddings
3. **Browse Data**: Navigate through Vectors and Tables
4. **Monitor Health**: Watch real-time system status
5. **View Logs**: Check logs for debugging

## Getting Help

- **Documentation**: See `README.md`
- **Tests**: Run `npm test`
- **API Docs**: http://localhost:8000/docs
- **Issue Tracker**: GitHub Issue #1129

## Feature Overview

| Feature | Status | Description |
|---------|--------|-------------|
| Dashboard Home | ✅ Complete | System health monitoring |
| Projects | ✅ Complete | Project management |
| Vectors | ✅ Complete | Vector search browser |
| Tables | ✅ Complete | NoSQL data browser |
| Files | 🚧 Placeholder | File storage (coming soon) |
| Logs | ✅ Complete | Real-time log viewer |
| Settings | 🚧 Basic | Configuration panel |

## Development Tips

```bash
# Run tests while developing
npm run test:watch

# Type checking
npm run type-check

# Linting
npm run lint

# Build check
npm run build
```

That's it! You're ready to use the ZeroLocal Dashboard.
