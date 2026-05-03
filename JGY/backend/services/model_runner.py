import json
import os
from datetime import datetime
from pathlib import Path

from adapters.beps_lite_adapter import run_beps_lite


BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_WEATHER_PATH = BASE_DIR / "demo_data" / "beps_demo_weather.json"
BEPS_RESULT_DIR = BASE_DIR / "runtime" / "beps_results"


def load_demo_weather():
    """读取 BEPS-Lite 样例气象数据。"""
    with open(DEMO_WEATHER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_beps_result(result):
    """保存 BEPS-Lite 运行结果。"""
    BEPS_RESULT_DIR.mkdir(parents=True, exist_ok=True)

    plot_id = result.get("plot_id", "demo_plot")
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"beps_result_{plot_id}_{now}.json"
    output_path = BEPS_RESULT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    result["saved_path"] = str(output_path)
    return result


def build_beps_payload(raw_payload):
    """
    构建 BEPS-Lite 输入。

    关键逻辑：
    1. LAI 优先使用 APSIM 输出；
    2. water_factor 优先使用 HYDRUS 根系吸水效率；
    3. weather 缺失时使用 demo_data；
    4. NDVI 缺失时允许为空。
    """

    payload = dict(raw_payload)

    apsim_result = payload.get("apsim_result", {})
    hydrus_result = payload.get("hydrus_result", {})

    # LAI 优先使用 APSIM 输出
    if payload.get("lai") is None:
        if apsim_result.get("lai") is not None:
            payload["lai"] = apsim_result["lai"]
        else:
            payload["lai"] = 2.5

    # 水分限制因子优先使用 HYDRUS 输出
    if payload.get("water_factor") is None:
        if hydrus_result.get("root_uptake_efficiency") is not None:
            payload["water_factor"] = hydrus_result["root_uptake_efficiency"]
        elif hydrus_result.get("water_factor") is not None:
            payload["water_factor"] = hydrus_result["water_factor"]
        else:
            payload["water_factor"] = 0.8

    # 气象缺失时使用演示气象数据
    if not payload.get("weather"):
        payload["weather"] = load_demo_weather()

    # 遮阴程度缺失时使用默认值
    if payload.get("shade_degree") is None:
        payload["shade_degree"] = 0.3

    return payload


def fallback_beps_result(error_message):
    """
    BEPS-Lite 失败时返回兜底结果。
    文件中明确要求：模型失败时不能中断系统展示链路。
    """
    return {
        "module": "BEPS-Lite",
        "status": "fallback",
        "message": "BEPS-Lite 计算失败，已返回兜底生态结果",
        "error": str(error_message),
        "plot_id": "fallback_plot",
        "summary": {
            "avg_gpp_gc_m2_day": 5.6,
            "avg_npp_gc_m2_day": 2.52,
            "avg_et_mm_day": 3.1,
            "total_carbon_sink_kg_ha": 25.2,
            "growth_score": 72.0,
            "risk_level": "low",
            "risk_reasons": [
                "当前使用 BEPS-Lite 兜底数据，请检查输入气象、LAI、NDVI 或水分因子是否完整"
            ]
        },
        "series": []
    }


def run_beps_lite_task(raw_payload):
    """
    对外提供的 BEPS-Lite 任务入口。
    """
    try:
        beps_payload = build_beps_payload(raw_payload)
        result = run_beps_lite(beps_payload)
        result = save_beps_result(result)
        return result

    except Exception as e:
        result = fallback_beps_result(e)
        result = save_beps_result(result)
        return result