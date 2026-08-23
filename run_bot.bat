@echo off
REM StudyAI Ghana bot launcher (self-healing via run_forever.py).
cd /d "%~dp0"
call .venv\Scripts\activate.bat >nul 2>&1
python scripts\run_forever.py
