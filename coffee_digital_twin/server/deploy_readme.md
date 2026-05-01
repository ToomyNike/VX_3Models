# Local Deployment

## Backend

1. Install Python 3.10+.
2. Start from PowerShell:

```powershell
cd D:\AAACODE\PYTHON\VX_3Models\coffee_digital_twin
.\server\start_all.ps1
```

If PowerShell blocks local scripts, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

3. Install dependencies manually if needed:

```bat
cd backend
call D:\AAACODE\PYTHON\anaconda\Scripts\activate.bat pyweb
python -m pip install -r requirements.txt
```

4. Start Flask from CMD:

```bat
server\start_all.bat
```

The backend listens on `0.0.0.0:5000`.

## Mini Program

Open `miniprogram/` in WeChat Developer Tools.

For phone testing, edit `miniprogram/utils/config.js` and replace `127.0.0.1` with the server computer's LAN IP.

## Model Engines

APSIM and HYDRUS are optional for the MVP. If the executables are missing, the adapter returns standard JSON fallback data so the demo flow remains stable.
