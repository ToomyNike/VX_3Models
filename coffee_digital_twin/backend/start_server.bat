@echo off
setlocal
cd /d "%~dp0"
echo Starting Coffee Digital Twin Flask backend...
call D:\AAACODE\PYTHON\anaconda\Scripts\activate.bat pyweb
python app.py
endlocal
