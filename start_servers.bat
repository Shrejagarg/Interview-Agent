@echo off
echo Starting AI Interview Simulator...

echo Starting Backend API (FastAPI)...
start /b cmd /c "venv\Scripts\activate && python -m uvicorn backend.app.main:app --reload --port 8000"

echo Starting Frontend (Next.js)...
start /b cmd /c "cd frontend\web && npm run dev"

echo Both servers are running in this terminal! Press Ctrl+C to terminate them.
