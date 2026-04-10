@echo off
echo ========================================================
echo  Starting Amber Alert AI - Cloud Edition
echo ========================================================
echo.

:: 1. Start Redis Database
echo [1/4] Launching Redis via Docker...
start "Redis Engine" cmd /k "docker-compose up"

:: 2. Start Python Backend FastAPI
echo [2/4] Launching FastAPI Backend (port 8000)...
start "Backend API" cmd /k ".\.venv\Scripts\activate && set PYTHONPATH=%cd% && cd backend && uvicorn app.main:app --reload --port 8000"

:: 3. Start Celery Worker
:: dotenv in database.py loads backend/.env automatically with override=True
echo [3/4] Launching Celery AI Task Worker...
start "Celery Task Worker" cmd /k ".\.venv\Scripts\activate && set PYTHONPATH=%cd%\backend && cd backend && celery -A app.tasks worker --loglevel=info --pool=solo"

:: 4. Start React Frontend Server
echo [4/4] Launching React Dashboard (port 5173)...
start "React Dashboard" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo  All 4 services launched in separate terminal windows!
echo  Frontend:  http://localhost:5173
echo  Backend:   http://localhost:8000
echo ========================================================
pause
