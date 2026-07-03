@echo off
chcp 65001 >nul
title AI 推理平台 Docker

echo ════════════════════════════════════════════
echo   AI 推理平台 — Docker 一键部署
echo ════════════════════════════════════════════
echo.
echo 前置条件: Docker Desktop 已启动
echo.

cd /d "%~dp0"

REM ── 检查 Docker ─────────────────────────────
docker info >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker Desktop 未运行！
    echo 请先启动 Docker Desktop，然后重新运行。
    pause
    exit /b 1
)

echo [1/2] 构建并启动容器...
docker compose up -d --build

echo.
echo [2/2] 等待服务就绪...
timeout /t 8 /nobreak >nul

echo.
echo ════════════════════════════════════════════
echo   部署完成！
echo   访问: http://localhost
echo   Admin: http://localhost/admin/
echo ════════════════════════════════════════════
echo.
echo 首次使用:
echo   1. 创建管理员: docker compose exec web python manage.py createsuperuser
echo   2. 访问 http://localhost 登录
echo.
pause
start http://localhost
