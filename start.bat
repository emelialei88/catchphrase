@echo off
cd /d "%~dp0"
echo Starting Catchphrase at http://localhost:7823
python -m uvicorn main:app --port 7823 --reload
