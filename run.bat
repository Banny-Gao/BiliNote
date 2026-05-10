@echo off
cd /d "%~dp0"

:: 停止 Docker 后端避免端口冲突
docker stop bilinote-backend >nul 2>&1

start "Backend" cmd /k "cd /d %~dp0backend & C:\Users\Administrator\.venv\bili\Scripts\python.exe main.py"
start "Frontend" cmd /k "cd /d %~dp0BillNote_frontend & pnpm run dev"

start http://localhost:3015/