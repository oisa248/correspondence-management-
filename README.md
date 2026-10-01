# Correspondence management
React (Vite) + FastAPI (Python) + PostgreSQL, deployable on Vercel.

Local: `pip install -r requirements.txt && npm install`, copy `.env.example` to `.env`, then
`export DATABASE_URL=... && python scripts/seed.py`, `npm run api` (port 8000) and `npm run dev` (port 5173).
Demo users (password `Passw0rd!`): record@, ceo@, cto@, coo@, cco@, director@, finance@, hr@ + `demo.local`.
Workflow rules live in `lib/workflow.py`.
