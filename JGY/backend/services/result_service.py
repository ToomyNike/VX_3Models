import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
BEPS_RESULT_DIR = BASE_DIR / "runtime" / "beps_results"


def get_latest_beps_result():
    """
    读取最近一次 BEPS-Lite 运行结果。
    """
    if not BEPS_RESULT_DIR.exists():
        return {
            "status": "empty",
            "message": "BEPS 结果目录不存在",
            "data": None
        }

    files = list(BEPS_RESULT_DIR.glob("beps_result_*.json"))

    if not files:
        return {
            "status": "empty",
            "message": "暂无 BEPS-Lite 运行结果",
            "data": None
        }

    latest_file = max(files, key=lambda p: p.stat().st_mtime)

    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "status": "ok",
        "file": str(latest_file),
        "data": data
    }


def list_beps_results(limit=10):
    """
    列出最近若干条 BEPS-Lite 结果文件。
    """
    if not BEPS_RESULT_DIR.exists():
        return []

    files = sorted(
        BEPS_RESULT_DIR.glob("beps_result_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    result = []

    for file in files[:limit]:
        result.append({
            "filename": file.name,
            "path": str(file),
            "modified_time": file.stat().st_mtime
        })

    return result