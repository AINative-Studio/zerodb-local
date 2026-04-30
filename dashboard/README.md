# ZeroLocal Dashboard

A modern Next.js dashboard for managing your self-hosted ZeroDB Local instance.

## Features

- **System Health Monitoring** - Real-time status of all services (PostgreSQL, Qdrant, MinIO, RedPanda, Embeddings)
- **Project Management** - Create, view, and manage ZeroDB projects
- **Vector Collections Browser** - Search and explore vector embeddings
- **NoSQL Tables** - Browse and query document-based data
- **File Storage** - Manage files in MinIO object storage
- **Real-time Logs** - Stream logs from all services
- **Settings** - Configure your ZeroLocal instance

## Tech Stack

- **Next.js 14** (App Router)
- **React 18** with TypeScript
- **TanStack Query** for data fetching
- **Tailwind CSS** for styling
- **shadcn/ui** components
- **Vitest** for testing
- **Axios** for API client

## Getting Started

### Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

### Docker

The dashboard is included in the docker-compose stack:

```bash
# From zerodb-local directory
docker-compose up dashboard

# Open http://localhost:3000
```

### Environment Variables

```env
VITE_API_URL=http://localhost:8000           # External API URL
VITE_API_INTERNAL_URL=http://zerodb-api:8000 # Docker internal URL
```

## Project Structure

```
dashboard/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Dashboard home
│   ├── projects/          # Projects management
│   ├── vectors/           # Vector collections
│   ├── tables/            # NoSQL tables
│   ├── files/             # File storage
│   ├── logs/              # System logs
│   └── settings/          # Configuration
├── components/
│   ├── ui/                # shadcn/ui components
│   ├── layout/            # Layout components
│   └── providers/         # React providers
├── services/
│   └── api-client.ts      # API client
├── types/
│   └── index.ts           # TypeScript types
├── lib/
│   └── utils.ts           # Utility functions
└── tests/                 # Vitest tests
```

## Testing

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run test:coverage
```

## API Integration

The dashboard connects to the ZeroDB Local API at `localhost:8000`. All API endpoints are defined in `/services/api-client.ts`.

### Available Endpoints

- `GET /health` - System health check
- `GET /v1/projects` - List projects
- `GET /v1/projects/:id` - Get project details
- `POST /v1/projects` - Create project
- `GET /v1/projects/:id/stats` - Project statistics
- `GET /v1/projects/:id/database/vectors` - List vectors
- `GET /v1/projects/:id/database/tables` - List tables
- `GET /v1/projects/:id/database/files` - List files
- `GET /v1/projects/:id/database/events` - List events

## Docker Compose Integration

The dashboard service is configured in `docker-compose.yml`:

```yaml
dashboard:
  build: ./dashboard
  ports:
    - "3000:3000"
  environment:
    - VITE_API_URL=http://localhost:8000
    - VITE_API_INTERNAL_URL=http://zerodb-api:8000
  depends_on:
    - zerodb-api
```

## Development

### Adding New Pages

1. Create page in `app/` directory
2. Add route to sidebar navigation in `components/layout/sidebar.tsx`
3. Create API methods in `services/api-client.ts` if needed
4. Add TypeScript types in `types/index.ts`

### Adding New Components

1. Create component in `components/ui/` for reusable UI
2. Create component in `components/` for feature-specific components
3. Write tests in `tests/components/`

## Building for Production

```bash
# Build optimized production bundle
npm run build

# Start production server
npm start
```

## Issue Tracking

Refs #1129 - ZeroLocal Dashboard UI Implementation
