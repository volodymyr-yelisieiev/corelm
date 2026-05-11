@echo off
setlocal
cd /d %~dp0..
if not exist .venv python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
set PYTHON=.venv\Scripts\python.exe
npm run desktop:dev
