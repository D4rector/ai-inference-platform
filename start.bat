@echo off
chcp 65001 >nul
title AI 推理平台

echo ════════════════════════════════════════════
echo   AI 推理平台 — 一键启动
echo ════════════════════════════════════════════
echo.

cd /d "%~dp0"

REM ── 1. 启动 Django 后端 ──────────────────────
echo [1/2] 启动 Django 后端 (:8000)...
start "Django API" cmd /c ".venv\Scripts\python manage.py runserver 0.0.0.0:8000"
timeout /t 3 /nobreak >nul

REM ── 2. 启动 Vue 前端 ─────────────────────────
echo [2/2] 启动 Vue 前端 (:5173)...
start "Vue Frontend" cmd /c "cd frontend && npx vite --host 0.0.0.0 --port 5173"
timeout /t 4 /nobreak >nul

echo.
echo ════════════════════════════════════════════
echo   启动完成！
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API:  http://localhost:5173/api/abilities/
echo ════════════════════════════════════════════
echo.
echo 测试账号: admin / admin123
echo           testuser / test1234
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:5173
