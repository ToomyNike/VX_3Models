import json
from datetime import date, timedelta

from config import BEPS_RUN_DIR


def run_beps_model(model_input_json):
    task_id = model_input_json.get("task_id", "task_demo")
    scenario = model_input_json.get("scenario", {})
    extra_irrigation = float(scenario.get("extra_irrigation_mm", 0) or 0)

    growth_score = round(min(92, 76 + extra_irrigation * 0.25), 1)
    gpp_today = round(7.8 + growth_score / 100, 2)
    npp_today = round(gpp_today * 0.48, 2)
    et_today = round(3.1 + extra_irrigation * 0.015, 2)
    carbon_sink = round(npp_today * 0.47, 2)
    beps_risk = "低" if growth_score >= 82 else "中等"

    today = date.today()
    gpp_series = []
    npp_series = []
    et_series = []
    for i in range(3):
        current = (today + timedelta(days=i)).isoformat()
        gpp = round(gpp_today - i * 0.18, 2)
        npp = round(gpp * 0.48, 2)
        et = round(et_today + i * 0.12, 2)
        gpp_series.append({"date": current, "gpp": gpp})
        npp_series.append({"date": current, "npp": npp})
        et_series.append({"date": current, "et": et})

    result = {
        "model": "BEPS-Lite",
        "status": "success",
        "plot_id": model_input_json.get("plot_id", "plot_001"),
        "growth_score": growth_score,
        "canopy_status": "长势正常，轻度受水分条件影响",
        "gpp_today": gpp_today,
        "npp_today": npp_today,
        "et_today": et_today,
        "carbon_sink_kgC_mu": carbon_sink,
        "beps_risk": beps_risk,
        "gpp_series": gpp_series,
        "npp_series": npp_series,
        "et_series": et_series,
        "beps_explain": {
            "what": "当前咖啡园冠层光合生产力处于中等偏上水平。",
            "why": "MVP阶段先使用BEPS-Lite标准JSON占位，后续可替换为真实生态模型。",
        },
    }

    run_dir = BEPS_RUN_DIR / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "beps_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
