# NYC Data Assistant - React Frontend

Modern React TypeScript web UI for the NYC Sidewalk Data Toolkit LLM Chatbot and SQL Query Engine.

## Features

- **💬 Conversational Chatbot** - Multi-turn conversations with context awareness
- **📊 SQL Query Builder** - Natural language to SQL translation with visual results
- **✓ Data Quality Check** - Assessment of data quality issues (extensible)
- **🎨 Professional Design** - NYC blue theme with dark mode support
- **⚡ Fast & Responsive** - Vite + React with instant HMR
- **🔒 Type-Safe** - Full TypeScript support

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first styling
- **Zustand** - Lightweight state management
- **React Query** - Data fetching
- **Axios** - HTTP client
- **Lucide** - Icon library

## Getting Started

### Prerequisites

- Node.js 16+ and npm/yarn/pnpm

### Installation

```bash
cd frontend
npm install
```

### Development

Start the dev server with hot module replacement:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to view the app.

The Vite dev server will proxy API requests to `http://localhost:8000/api`.

### Building

Build for production:

```bash
npm run build
```

Output goes to `dist/` directory, ready for deployment.

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # API client for backend endpoints
│   ├── components/
│   │   ├── ChatInterface.tsx   # Chat UI component
│   │   └── QueryBuilder.tsx    # SQL query builder UI
│   ├── store/
│   │   └── store.ts           # Zustand state management
│   ├── App.tsx                # Main app component
│   ├── main.tsx               # Entry point
│   └── index.css              # Global styles
├── index.html                 # HTML template
├── package.json               # Dependencies
├── tsconfig.json              # TypeScript config
├── vite.config.ts             # Vite config
├── tailwind.config.js         # TailwindCSS config
└── .gitignore                 # Git ignore
```

## Configuration

### API Endpoint

The dev server proxies to `http://localhost:8000`. For production, update the `baseURL` in [`src/api/client.ts`](src/api/client.ts):

```typescript
// Line 32 in src/api/client.ts
const client = axios.create({
  baseURL: process.env.VITE_API_URL || '/api/v1/llm',
})
```

### Environment Variables

Create `.env.local` for development:

```bash
VITE_API_URL=http://localhost:8000/api/v1/llm
```

## Component Guide

### ChatInterface

Multi-turn conversational chat with message history.

**Features:**
- Message threading with timestamps
- Auto-scroll to latest message
- Loading and error states
- Clear conversation button
- Configurable LLM provider and model

**Usage:**
```tsx
import { ChatInterface } from '@/components/ChatInterface'

<ChatInterface />
```

### QueryBuilder

Natural language to SQL translation with results visualization.

**Features:**
- Natural language input
- Generated SQL display with copy button
- Result statistics (rows, execution time)
- Result interpretation
- Results table with pagination
- Query validation

**Usage:**
```tsx
import { QueryBuilder } from '@/components/QueryBuilder'

<QueryBuilder />
```

## State Management

Using Zustand for simple, hooks-based state management:

```typescript
import { useAppStore } from '@/store/store'

const {
  messages,
  isLoading,
  activeTab,
  setActiveTab,
  addMessage,
  clearMessages,
} = useAppStore()
```

Available state:
- `messages` - Chat message history
- `isLoading` - Loading flag
- `error` - Error message
- `activeTab` - Current tab ('chat' | 'query' | 'quality')
- `darkMode` - Theme toggle
- `sidebarOpen` - Sidebar visibility
- `selectedProvider` - LLM provider
- `selectedModel` - Model name

## API Integration

The frontend connects to FastAPI backend at `/api/v1/llm` with these endpoints:

### Chat
- `POST /chat` - Send chat message
- `GET /chat/history` - Get conversation history
- `POST /chat/clear` - Clear history
- `POST /chat/suggest-analyses` - Get analysis suggestions

### Query
- `POST /query` - Execute natural language query
- `POST /query/session/{id}` - Interactive session query
- `GET /query/schema` - Get database schema

### Quality
- `POST /quality/assess` - Assess quality issue

### Analytics
- `GET /analytics/suggest-metrics` - Get metric suggestions

### Health
- `GET /health` - API health check

See [`src/api/client.ts`](src/api/client.ts) for complete API client.

## Styling

### TailwindCSS

Using Tailwind for responsive, utility-first styling.

**NYC Theme Colors:**
```javascript
// tailwind.config.js
colors: {
  'nycblue': {
    50: '#f0f7ff',
    500: '#0066cc',
    600: '#0052a3',
    700: '#003d7a',
    900: '#001a40',
  }
}
```

### Dark Mode

Toggle with moon/sun icon. App component manages `darkMode` state:

```tsx
const { darkMode, toggleDarkMode } = useAppStore()

<button onClick={toggleDarkMode}>
  {darkMode ? <Sun /> : <Moon />}
</button>
```

## Deployment

### Build for Production

```bash
npm run build
```

### Docker

Build Docker image:

```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

Build and run:

```bash
docker build -t nyc-data-assistant .
docker run -p 3000:3000 -e VITE_API_URL=http://localhost:8000/api/v1/llm nyc-data-assistant
```

### Nginx

```nginx
server {
  listen 80;
  server_name _;

  location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
  }

  location /api {
    proxy_pass http://backend:8000;
  }
}
```

## Performance

- **Vite** provides instant HMR and optimized builds
- **React Query** handles caching and background updates
- **Code splitting** automatic with route-based chunks
- **Lazy loading** components with React.lazy()

Monitor bundle size:

```bash
npm run build -- --analyze
```

## Troubleshooting

### Dev Server Not Connecting

Ensure backend is running on `http://localhost:8000` and accessible:

```bash
curl http://localhost:8000/api/v1/llm/health
```

### TypeScript Errors

Run type checking:

```bash
npm run type-check
```

### API Requests Failing

Check browser DevTools Network tab and backend logs. Common issues:
- CORS misconfiguration
- Backend not running
- Wrong API URL in `.env.local`

### Build Errors

Clear cache and reinstall:

```bash
rm -rf node_modules dist
npm install
npm run build
```

## Contributing

1. Create feature branch
2. Run linter: `npm run lint`
3. Run type check: `npm run type-check`
4. Commit with conventional messages
5. Submit PR

## License

MIT

## Support

See parent [`README.md`](../README.md) for full project documentation.
