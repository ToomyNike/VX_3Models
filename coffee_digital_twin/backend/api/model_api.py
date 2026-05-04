import json
import uuid

from flask import Blueprint, jsonify, request

from config import RESULT_JSON_DIR
from database.init_db import get_connection, now_iso
from models.apsim_adapter import run_apsim_model
from models.beps_adapter import run_beps_model
from models.fusion_engine import merge
from models.hydrus_adapter import run_hydrus_model
from services.weather_service import get_weather_series


model_bp = Blueprint("model_api", __name__, url_prefix="/api/model")


def _row_json(row, key="raw_json"):
    return json.loads(row[key]) if row and row[key] else None


def _latest_plot(conn, plot_id=None):
    if plot_id:
        row = conn.execute("SELECT raw_json FROM plots WHERE plot_id = ?", (plot_id,)).fetchone()
    else:
        row = conn.execute("SELECT raw_json FROM plots ORDER BY updated_at DESC LIMIT 1").fetchone()
    return _row_json(row) or {
        "plot_id": "plot_001",
        "crop": "coffee",
        "plot_name": "潞江坝咖啡示范园",
        "area_mu": 12.5,
        "tree_age": 4,
        "coffee_variety": "云南小粒咖啡",
        "latitude": 24.93,
        "longitude": 98.88,
        "elevation_m": 850,
        "soil_type": "赤红壤",
        "shade_level": "中等遮阴",
    }


def _farm_operations(conn, plot_id):
    rows = conn.execute(
        "SELECT * FROM farm_operations WHERE plot_id = ? ORDER BY op_date ASC, id ASC",
        (plot_id,),
    ).fetchall()
    items = []
    for row in rows:
        items.append(
            {
                "op_type": row["op_type"],
                "date": row["op_date"],
                "amount": row["amount"],
                "unit": row["unit"],
                "fertilizer_type": row["fertilizer_type"],
                "operation_type": row["operation_type"],
                "severity": row["severity"],
                "remark": row["remark"],
            }
        )
    if not items:
        items = [
            {"op_type": "irrigation", "date": now_iso()[:10], "amount": 25, "unit": "mm"},
            {
                "op_type": "fertilization",
                "date": now_iso()[:10],
                "fertilizer_type": "尿素",
                "amount": 10,
                "unit": "kg/mu",
            },
        ]
    return items


def build_model_input(task_id, plot_id=None, scenario=None):
    with get_connection() as conn:
        plot = _latest_plot(conn, plot_id)
        operations = _farm_operations(conn, plot["plot_id"])

    return {
        "task_id": task_id,
        "plot_id": plot["plot_id"],
        "crop": "coffee",
        "plot_info": plot,
        "weather_series": get_weather_series(plot.get("latitude"), plot.get("longitude")),
        "farm_operations": operations,
        "scenario": scenario or {
            "scenario_name": "当前管理方案",
            "extra_irrigation_mm": 0,
            "extra_fertilizer_kg_mu": 0,
        },
    }


@model_bp.post("/run")
def run_model():
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("task_id") or f"task_{uuid.uuid4().hex[:8]}"
    scenario = payload.get("scenario") or {}
    scenario.setdefault("scenario_name", payload.get("scenario_name", "当前管理方案"))
    scenario.setdefault("extra_irrigation_mm", payload.get("extra_irrigation_mm", 0))
    scenario.setdefault("extra_fertilizer_kg_mu", payload.get("extra_fertilizer_kg_mu", 0))

    model_input = build_model_input(task_id, payload.get("plot_id"), scenario)
    timestamp = now_iso()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO model_tasks
            (task_id, plot_id, scenario_name, status, message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                model_input["plot_id"],
                scenario.get("scenario_name"),
                "running",
                "model task started",
                timestamp,
                timestamp,
            ),
        )

    try:
        apsim_result = run_apsim_model(model_input)
        hydrus_result = run_hydrus_model(model_input)
        beps_result = run_beps_model(model_input, apsim_result=apsim_result, hydrus_result=hydrus_result)
        result = merge(
            apsim_result,
            hydrus_result,
            beps_result,
            task_id=task_id,
            plot_id=model_input["plot_id"],
        )
        result["model_input"] = model_input
        result_path = RESULT_JSON_DIR / f"{task_id}.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO model_results
                (task_id, plot_id, result_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    task_id,
                    model_input["plot_id"],
                    json.dumps(result, ensure_ascii=False),
                    now_iso(),
                ),
            )
            conn.execute(
                """
                UPDATE model_tasks
                SET status = ?, message = ?, updated_at = ?
                WHERE task_id = ?
                """,
                ("success", "model task finished", now_iso(), task_id),
            )
    except Exception as error:
        with get_connection() as conn:
            conn.execute(
                "UPDATE model_tasks SET status = ?, message = ?, updated_at = ? WHERE task_id = ?",
                ("failed", str(error), now_iso(), task_id),
            )
        raise

    return jsonify(result)


@model_bp.get("/status/<task_id>")
def model_status(task_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM model_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        return jsonify({"status": "not_found", "task_id": task_id}), 404
    return jsonify(dict(row))
