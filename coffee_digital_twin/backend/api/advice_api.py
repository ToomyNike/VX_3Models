import json

from flask import Blueprint, jsonify, request

from database.init_db import get_connection, now_iso
from services.llm_service import generate_advice


advice_bp = Blueprint("advice_api", __name__, url_prefix="/api/advice")


@advice_bp.post("/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    result = payload.get("result")
    task_id = payload.get("task_id")

    if not result and task_id:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT result_json FROM model_results WHERE task_id = ?", (task_id,)
            ).fetchone()
        result = json.loads(row["result_json"]) if row else None

    if not result:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT result_json FROM model_results ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        result = json.loads(row["result_json"]) if row else {}

    advice = generate_advice(result.get("apsim", {}), result.get("hydrus", {}), result.get("beps", {}))
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO advice_logs (task_id, advice_json, created_at) VALUES (?, ?, ?)",
            (task_id or result.get("task_id"), json.dumps(advice, ensure_ascii=False), now_iso()),
        )
    return jsonify({"status": "success", "task_id": task_id or result.get("task_id"), "advice": advice})
