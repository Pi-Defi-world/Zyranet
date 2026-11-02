# Zyranet frontend

React + TypeScript + Vite + Tailwind admin dashboard for the Zyranet campus
network platform.

## Commands

```bash
npm install
npm run dev        # http://localhost:5173 (proxies /api to localhost:8000)
npm run lint       # oxlint
npm run typecheck  # tsc -b
npm run test       # vitest
npm run build      # production build into dist/
```

API calls go to `/api/v1/*`; in development the Vite proxy forwards them to
the FastAPI backend on port 8000. The JWT is stored in `localStorage` under
`zyranet_token`.
