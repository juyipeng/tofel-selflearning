@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动口语刷题站...
echo 使用 conda 环境: pytorch (E:\conda_envs\pytorch) —— faster-whisper 所在环境
echo 首次启动加载模型约 1-2 分钟，请稍候。
echo 就绪后浏览器打开 http://localhost:8766/practice.html
echo.
E:\conda_envs\pytorch\python.exe server.py
pause
