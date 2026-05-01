import json
from datetime import date, timedelta

from config import HYDRUS_RUN_DIR
from services.unit_convert import normalize_irrigation_mm


def run_hydrus_model(model_input_json):
    task_id = model_input_json.get("task_id", "task_demo")
    irrigation_mm = 0
    for op in model_input_json.get("farm_operations", []):
        if op.get("op_type") == "irrigation":
            irrigation_mm += normalize_irrigation_mm(op.get("amount"), op.get("unit"))
    irrigation_mm += float(model_input_json.get("scenario", {}).get("extra_irrigation_mm", 0) or 0)

    dryness = max(0, 42 - irrigation_mm)
    water_status = "中度干旱" if dryness > 18 else "轻度偏干" if dryness > 8 else "水分适宜"
    root_uptake_ratio = round(min(0.93, 0.58 + irrigation_mm * 0.008), 2)

    depths = [10, 20, 40, 60, 100]
    profile = []
    for depth in depths:
        moisture = 0.28 - depth * 0.0009 + min(irrigation_mm, 35) * 0.0015
        profile.append({"depth_cm": depth, "theta": round(max(0.12, moisture), 3)})

    today = date.today()
    series = []
    for i in range(3):
        series.append(
            {
                "date": (today + timedelta(days=i)).isoformat(),
                "d10": round(profile[0]["theta"] - i * 0.006, 3),
                "d20": round(profile[1]["theta"] - i * 0.005, 3),
                "d40": round(profile[2]["theta"] - i * 0.004, 3),
                "d60": round(profile[3]["theta"] - i * 0.003, 3),
            }
        )

    result = {
        "model": "HYDRUS-1D",
        "status": "success",
        "plot_id": model_input_json.get("plot_id", "plot_001"),
        "water_status": water_status,
        "root_uptake_ratio": root_uptake_ratio,
        "irrigation_effect": "灌溉主要补充0-40cm土层" if irrigation_mm > 0 else "近期无灌溉记录",
        "soil_profile_current": profile,
        "soil_moisture_series": series,
        "hydrus_explain": {
            "what": "当前表层土壤水分恢复较快，深层根区仍需持续观察。",
            "why": "MVP阶段先使用标准JSON占位，后续可替换为HYDRUS真实输出解析。",
        },
    }

    run_dir = HYDRUS_RUN_DIR / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "hydrus_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
