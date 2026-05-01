from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "coffee_demo.db"

RUNTIME_DIR = BASE_DIR / "runtime"
APSIM_RUN_DIR = RUNTIME_DIR / "apsim_runs"
HYDRUS_RUN_DIR = RUNTIME_DIR / "hydrus_runs"
BEPS_RUN_DIR = RUNTIME_DIR / "beps_runs"
RESULT_JSON_DIR = RUNTIME_DIR / "result_json"

DEMO_DATA_DIR = BASE_DIR / "demo_data"

SERVER_DIR = PROJECT_DIR / "server"
LOCAL_APSIM_EXE = Path("D:/APP/APSIM/APSIM2025.12.7950.0/bin/Models.exe")
DEFAULT_APSIM_EXE = LOCAL_APSIM_EXE if LOCAL_APSIM_EXE.exists() else SERVER_DIR / "apsim_engine" / "Models.exe"
APSIM_EXE = Path(os.getenv("APSIM_EXE", DEFAULT_APSIM_EXE))
HYDRUS_EXE = Path(os.getenv("HYDRUS_EXE", SERVER_DIR / "hydrus_engine" / "H1D_CALC.EXE"))

HOST = os.getenv("FLASK_HOST", "0.0.0.0")
PORT = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"


def ensure_dirs():
    for path in [
        DATABASE_DIR,
        APSIM_RUN_DIR,
        HYDRUS_RUN_DIR,
        BEPS_RUN_DIR,
        RESULT_JSON_DIR,
        DEMO_DATA_DIR,
        SERVER_DIR / "logs",
        SERVER_DIR / "backup" / "final_result_json",
    ]:
        path.mkdir(parents=True, exist_ok=True)
