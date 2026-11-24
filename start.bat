@echo off
echo ========================================================
echo               Starting Lyftr AI Full Stack
echo ========================================================

start "Lyftr AI Backend" cmd /k "python run_backend.py"
start "Lyftr AI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers have been launched in separate windows!
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo.
pause
