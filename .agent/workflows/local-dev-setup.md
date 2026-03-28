---
description: Run the frontend and backend servers concurrently for local development
---
# Local Development Setup
1. Open a terminal and navigate to exactly `e:\Projects\ImmersiveRAG\backend`
2. Start Uvicorn: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
3. Open another terminal and navigate to exactly `e:\Projects\ImmersiveRAG\frontend`
4. Make sure path has node: `$env:PATH += ";C:\Program Files\nodejs"`
5. Start NextJS dev server: `npm run dev -- -p 3000`
6. The app is available at `http://localhost:3000`
