# Frontend Setup Guide

Complete setup instructions for the NYC Data Assistant React frontend.

## Quick Start (5 minutes)

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Start dev server
npm run dev

# 3. Open browser
# Visit http://localhost:5173
```

## Prerequisites

- **Node.js**: 16.13.0 or later
- **npm**: 7.0.0 or later (or yarn/pnpm)
- **Backend Running**: FastAPI server on `http://localhost:8000`

Check versions:
```bash
node --version    # v18.0.0+
npm --version     # 8.0.0+
```

## Installation Steps

### 1. Install Node.js

**macOS:**
```bash
brew install node
```

**Windows:**
- Download from https://nodejs.org
- Or use `winget install OpenJS.NodeJS`

**Linux (Ubuntu/Debian):**
```bash
curl -sL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Clone or Navigate to Frontend

```bash
cd nyc_data/frontend
```

### 3. Install Dependencies

```bash
npm install
```

This reads `package.json` and installs all required packages:
- react & react-dom
- TypeScript & related tools
- TailwindCSS
- Zustand (state management)
- Axios (HTTP client)
- And more...

Monitor: Watch for any warnings or errors. Some warnings are safe to ignore.

## Development

### Start Dev Server

```bash
npm run dev
```

Output will show:
```
Local: http://localhost:5173
```

Visit in browser - the app will auto-reload on code changes (HMR).

### Environment Configuration

Create `.env.local` in `frontend/`:

```bash
VITE_API_URL=http://localhost:8000/api/v1/llm
```

Or keep default - the dev server proxies `/api` to `http://localhost:8000`.

### File Structure for Development

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # ← Modify API endpoints here
│   ├── components/
│   │   ├── ChatInterface.tsx   # ← Chatbot UI
│   │   └── QueryBuilder.tsx    # ← Query builder UI
│   ├── store/
│   │   └── store.ts           # ← App state
│   └── App.tsx                # ← Main layout & navigation
├── src/index.css              # ← Global styles
├── index.html                 # ← HTML template
└── vite.config.ts             # ← Build config
```

## Building

### Production Build

```bash
npm run build
```

Creates optimized `dist/` folder with:
- Minified JavaScript
- Optimized CSS
- Source maps
- Ready for deployment

### Preview Build Locally

```bash
npm run build
npm run preview
```

Serves the built version at `http://localhost:5173`.

## Development Commands

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Check code style |
| `npm run type-check` | TypeScript type checking |

## Code Style

The project uses:
- **ESLint** for code quality
- **TypeScript** for type safety

Check code:
```bash
npm run lint
npm run type-check
```

## Backend Connection

Frontend connects to backend FastAPI server.

### Backend Must Be Running

```bash
# In another terminal, from nyc_data/
python -m socrata_toolkit.api
# or
uvicorn socrata_toolkit.api:app --reload
```

Server should be accessible at:
```
http://localhost:8000
http://localhost:8000/api/v1/llm/health
```

### Health Check

Frontend automatically checks backend health on load. Look for status indicator in sidebar:
- 🟢 Green = Connected
- 🔴 Red = Disconnected

### API Endpoints Used

Frontend makes requests to:
- `/api/v1/llm/chat` - Chat messages
- `/api/v1/llm/query` - SQL queries
- `/api/v1/llm/health` - Health check

See [`src/api/client.ts`](src/api/client.ts) for all endpoints.

## Debugging

### Browser DevTools

1. Open Chrome/Firefox DevTools (F12)
2. **Console** tab - JavaScript errors/logs
3. **Network** tab - API requests
4. **Elements** tab - DOM inspection
5. **React DevTools** - Component inspection

### Common Issues

#### "Cannot GET /"
- Dev server not running
- Wrong URL (use `http://localhost:5173`)

#### API Requests Failing
- Backend not running on `http://localhost:8000`
- Check: `curl http://localhost:8000/api/v1/llm/health`
- Check CORS headers in backend

#### Module Not Found
- Clear cache: `rm -rf node_modules && npm install`
- Restart dev server

#### Port Already in Use
- Vite will try port 5173, then 5174, etc.
- Or kill process: `lsof -ti:5173 | xargs kill -9`

## Package Management

### Adding Dependencies

```bash
npm install package-name
```

Updates `package.json` and `package-lock.json`.

### Updating Dependencies

```bash
npm update                    # Update to compatible versions
npm outdated                  # Show outdated packages
npm audit                     # Security audit
npm audit fix                 # Fix vulnerabilities
```

### Removing Dependencies

```bash
npm uninstall package-name
```

## Git Workflow

### Before Committing

```bash
npm run lint
npm run type-check
npm run build
```

### Staging Frontend Changes

```bash
git add frontend/
git commit -m "feat: Add feature description"
```

### Including Frontend in Main Project

Frontend is part of the monorepo. Commits affect both Python and TypeScript code:

```bash
git status          # See all changes
git add .           # Stage all changes
git commit -m "feat: Multi-language support with chatbot and query builder"
git push origin main
```

## Deployment

### Docker

See [`frontend/Dockerfile`](Dockerfile) - builds optimized image.

```bash
docker build -t nyc-data-frontend .
docker run -p 3000:3000 \
  -e VITE_API_URL=http://backend:8000/api/v1/llm \
  nyc-data-frontend
```

### Vercel / Netlify

Create `vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist"
}
```

Then deploy with your hosting provider.

### Static Hosting (S3 / CloudFront / Azure Static Web Apps)

```bash
npm run build
# Upload dist/ folder to your CDN/static hosting
# Configure API_URL environment variable
```

## Performance

### Measure Bundle Size

```bash
npm run build -- --analyze
```

### Optimize

- Code splitting: Automatic with Vite
- Lazy loading: Use React.lazy()
- Images: Optimize before adding
- Dependencies: Keep count low

Current bundle: ~150KB gzipped (includes React, TailwindCSS, Zustand)

## Testing (Future)

Add testing:
```bash
npm install --save-dev vitest @testing-library/react
```

Then:
```bash
npm run test
npm run test:coverage
```

## Support

Having issues? Check:

1. **Backend running?** - `curl http://localhost:8000/health`
2. **Port available?** - Try `lsof -i :5173`
3. **Dependencies installed?** - Run `npm install` again
4. **Node version ok?** - Check with `node --version`
5. **Cache issues?** - `npm cache clean --force`

## Next Steps

1. Read [`README.md`](README.md) for architecture overview
2. Check component code in [`src/components/`](src/components/)
3. Explore API client in [`src/api/client.ts`](src/api/client.ts)
4. Review store in [`src/store/store.ts`](src/store/store.ts)
5. Look at main app in [`src/App.tsx`](src/App.tsx)
