import json

from flask import Blueprint, jsonify

from database.init_db import get_connection


result_bp = Blueprint("result_api", __name__, url_prefix="/api")


def _latest_result():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT result_json FROM model_results ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    return json.loads(row["result_json"]) if row else None


@result_bp.get("/model/result/<task_id>")
def model_result(task_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT result_json FROM model_results WHERE task_id = ?", (task_id,)
        ).fetchone()
    if not row:
        return jsonify({"status": "not_found", "task_id": task_id}), 404
    return jsonify(json.loads(row["result_json"]))


@result_bp.get("/dashboard")
def dashboard():
    # AI辅助生成-DeepSeek-V3 - 2026年4月30日 11:15:00 - 返回数字孪生控制台的综合聚合数据
    result = _latest_result()
    if not result:
        return jsonify(
            {
                "status": "empty",
                "task_id": None,
                "dashboard": {
                    "stage": "待建园",
                    "harvest_days": "-",
                    "yield_pred_kg_mu": "-",
                    "risk_level": "低",
                    "growth_score": "-",
                },
                "advice": {
                    "what": "请先完成建园初始化并运行一次模型。",
                    "how": "从建园初始化页面录入地块信息，再到情景模拟页点击运行模型。",
                    "why": "系统需要地块、农事和气象数据生成统一模型输入。",
                },
            }
        )
    return jsonify(
        {
            "status": "success",
            "task_id": result.get("task_id"),
            "dashboard": result.get("dashboard", {}),
            "advice": result.get("advice", {}),
            "apsim": result.get("apsim", {}),
            "hydrus": result.get("hydrus", {}),
            "beps": result.get("beps", {}),
        }
    )
