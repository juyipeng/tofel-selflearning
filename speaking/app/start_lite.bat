@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动口语刷题站（轻量模式）...
echo 不加载 whisper 模型，无需 GPU，评分功能禁用；跟读 / 录音回放可用。
echo 就绪后浏览器打开 http://localhost:8766/practice.html
echo.
E:\conda_envs\pytorch\python.exe server.py --lite
pause
