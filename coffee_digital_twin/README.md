# Coffee Digital Twin MVP

This project follows the agreed development document structure:

- `miniprogram/`: WeChat mini program frontend
- `backend/`: Flask backend, SQLite, model adapters and fusion engine
- `server/`: local deployment scripts and model executable paths
- `docs/`: interface and presentation notes

## Quick Start

PowerShell:

```powershell
cd D:\AAACODE\PYTHON\VX_3Models\coffee_digital_twin
.\server\start_all.ps1
```

If PowerShell blocks local scripts, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

CMD:

```bat
cd backend
call D:\AAACODE\PYTHON\anaconda\Scripts\activate.bat pyweb
python -m pip install -r requirements.txt
python app.py
```

Then open `miniprogram/` in WeChat Developer Tools.

For phone testing, change `miniprogram/utils/config.js` from `127.0.0.1` to the backend computer's LAN IP.
