@echo off
setlocal
cd /d "%~dp0..\backend"
echo Starting backend at http://0.0.0.0:5000
call D:\AAACODE\PYTHON\anaconda\Scripts\activate.bat pyweb
python app.py
endlocal
