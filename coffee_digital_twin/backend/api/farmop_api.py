import json

from flask import Blueprint, jsonify, request

from database.init_db import get_connection, now_iso


farmop_bp = Blueprint("farmop_api", __name__, url_prefix="/api/farmop")


def _latest_plot_id(conn):
    row = conn.execute("SELECT plot_id FROM plots ORDER BY updated_at DESC LIMIT 1").fetchone()
    return row["plot_id"] if row else "plot_001"


@farmop_bp.post("/add")
def add_farm_operation():
    payload = request.get_json(silent=True) or {}
    with get_connection() as conn:
        plot_id = payload.get("plot_id") or _latest_plot_id(conn)
        op_type = payload.get("op_type", "irrigation")
        op_date = payload.get("date") or payload.get("op_date") or now_iso()[:10]
        cursor = conn.execute(
            """
            INSERT INTO farm_operations (
                plot_id, op_type, op_date, amount, unit, fertilizer_type,
                operation_type, severity, remark, raw_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plot_id,
                op_type,
                op_date,
                payload.get("amount"),
                payload.get("unit"),
                payload.get("fertilizer_type"),
                payload.get("operation_type"),
                payload.get("severity"),
                payload.get("remark"),
                json.dumps(payload, ensure_ascii=False),
                now_iso(),
            ),
        )
        op_id = cursor.lastrowid

    return jsonify({"status": "success", "id": op_id, "plot_id": plot_id})


@farmop_bp.get("/list")
def list_farm_operations():
    plot_id = request.args.get("plot_id")
    sql = "SELECT * FROM farm_operations"
    args = []
    if plot_id:
        sql += " WHERE plot_id = ?"
        args.append(plot_id)
    sql += " ORDER BY op_date DESC, id DESC"

    with get_connection() as conn:
        rows = conn.execute(sql, args).fetchall()
    return jsonify({"status": "success", "items": [dict(row) for row in rows]})
