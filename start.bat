@echo off
echo ========================================================
echo Starting Amber Alert OS Services...
echo ========================================================

:: 1. Start Redis Database in a popup window
start "Redis Engine" cmd /k "docker-compose up"

:: 2. Start Python Backend FastAPI in a popup window
start "Backend API" cmd /k ".\.venv\Scripts\activate && set PYTHONPATH=%cd% && cd backend && uvicorn app.main:app --reload --port 8000"

:: 3. Start Celery Worker (Pool Solo since it's Windows) in a popup window
start "Celery Task Worker" cmd /k ".\.venv\Scripts\activate && set PYTHONPATH=%cd%\backend && cd backend && celery -A app.tasks worker --loglevel=info --pool=solo"

:: 4. Start React Frontend Server in a popup window
start "React Dashboard" cmd /k "cd frontend && npm run dev"

echo All 5 processes have been launched in separate terminal windows!
echo Once they all finish loading, open your browser and go to http://localhost:5173
pause
