@echo off
setlocal
echo [1/4] Python
call D:\AAACODE\PYTHON\anaconda\Scripts\activate.bat pyweb
python --version

echo.
echo [2/4] Flask requirements
python -m pip show Flask Flask-Cors Werkzeug

echo.
echo [3/4] APSIM
if exist "%~dp0apsim_engine\Models.exe" (
  echo APSIM Models.exe found
) else (
  echo APSIM Models.exe not found, backend will use MVP fallback adapter
)

echo.
echo [4/4] HYDRUS
if exist "%~dp0hydrus_engine\H1D_CALC.EXE" (
  echo HYDRUS H1D_CALC.EXE found
) else (
  echo HYDRUS executable not found, backend will use MVP fallback adapter
)
endlocal
