@echo off
cd backend
python -m venv venv 2>nul
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
pause
