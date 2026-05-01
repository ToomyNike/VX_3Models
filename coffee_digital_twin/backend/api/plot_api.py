import json
import uuid

from flask import Blueprint, jsonify, request

from database.init_db import get_connection, now_iso


plot_bp = Blueprint("plot_api", __name__, url_prefix="/api/plot")


def _default_plot(payload):
    plot_id = payload.get("plot_id") or f"plot_{uuid.uuid4().hex[:8]}"
    return {
        "plot_id": plot_id,
        "crop": payload.get("crop", "coffee"),
        "coffee_variety": payload.get("coffee_variety", "云南小粒咖啡"),
        "plot_name": payload.get("plot_name", "潞江坝咖啡示范园"),
        "area_mu": float(payload.get("area_mu", 12.5) or 12.5),
        "tree_age": int(payload.get("tree_age", 4) or 4),
        "latitude": float(payload.get("latitude", 24.93) or 24.93),
        "longitude": float(payload.get("longitude", 98.88) or 98.88),
        "elevation_m": float(payload.get("elevation_m", 850) or 850),
        "soil_type": payload.get("soil_type", "赤红壤"),
        "shade_level": payload.get("shade_level", "中等遮阴"),
        "plant_density": float(payload.get("plant_density", 330) or 330),
        "row_spacing_m": float(payload.get("row_spacing_m", 2.0) or 2.0),
        "plant_spacing_m": float(payload.get("plant_spacing_m", 1.5) or 1.5),
    }


@plot_bp.post("/init")
def init_plot():
    payload = request.get_json(silent=True) or {}
    plot = _default_plot(payload)
    timestamp = now_iso()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO plots (
                plot_id, plot_name, crop, coffee_variety, area_mu, tree_age,
                latitude, longitude, elevation_m, soil_type, shade_level,
                plant_density, row_spacing_m, plant_spacing_m, raw_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plot_id) DO UPDATE SET
                plot_name=excluded.plot_name,
                crop=excluded.crop,
                coffee_variety=excluded.coffee_variety,
                area_mu=excluded.area_mu,
                tree_age=excluded.tree_age,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                elevation_m=excluded.elevation_m,
                soil_type=excluded.soil_type,
                shade_level=excluded.shade_level,
                plant_density=excluded.plant_density,
                row_spacing_m=excluded.row_spacing_m,
                plant_spacing_m=excluded.plant_spacing_m,
                raw_json=excluded.raw_json,
                updated_at=excluded.updated_at
            """,
            (
                plot["plot_id"],
                plot["plot_name"],
                plot["crop"],
                plot["coffee_variety"],
                plot["area_mu"],
                plot["tree_age"],
                plot["latitude"],
                plot["longitude"],
                plot["elevation_m"],
                plot["soil_type"],
                plot["shade_level"],
                plot["plant_density"],
                plot["row_spacing_m"],
                plot["plant_spacing_m"],
                json.dumps(plot, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )

    return jsonify({"status": "success", "plot_id": plot["plot_id"], "plot": plot})


@plot_bp.get("/latest")
def latest_plot():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT raw_json FROM plots ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        return jsonify({"status": "empty", "plot": None})
    return jsonify({"status": "success", "plot": json.loads(row["raw_json"])})
