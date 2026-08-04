@echo off 
echo ======================================== 
echo ?? AI Data Analyst Project Setup 
echo ======================================== 
echo. 
echo Step 1: Creating Python virtual environment... 
cd backend 
python -m venv venv 
echo ? Virtual environment created 
 
echo Step 2: Installing Python dependencies... 
call venv\Scripts\activate 
pip install -r requirements.txt 
echo ? Python dependencies installed 
cd .. 
 
echo Step 3: Installing Node.js dependencies... 
cd frontend 
call npm install 
echo ? Node.js dependencies installed 
cd .. 
 
echo Step 4: Starting Docker containers... 
docker-compose up -d 
echo ? Docker containers started 
 
echo ======================================== 
echo ? Setup Complete! 
echo Backend: http://localhost:8000 
echo Frontend: http://localhost:3000 
echo API Docs: http://localhost:8000/docs 
echo ======================================== 
pause 
