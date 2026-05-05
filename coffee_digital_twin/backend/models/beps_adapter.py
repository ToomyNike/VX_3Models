"""
BEPS-Lite 咖啡生态模型适配器（集成版）
原始实现：江桂源（JGY）—— BepsLiteAdapter 计算核心
集成适配：蔡济远

功能：
  1. 将主系统统一 model_input_json 转换为 BEPS-Lite 所需格式
  2. 优先使用 APSIM 输出的 LAI、HYDRUS 输出的 root_uptake_ratio 作为水分因子
  3. 气象缺失时自动加载 demo_data
  4. 输出字段做双层映射，兼容主系统 risk_service / llm_service 读取方式
"""
import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import BEPS_RUN_DIR, DEMO_DATA_DIR


_DEMO_WEATHER_PATH = DEMO_DATA_DIR / "beps_demo_weather.json"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _load_demo_weather() -> List[Dict]:
    if _DEMO_WEATHER_PATH.exists():
        with open(_DEMO_WEATHER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # 硬编码兜底气象
    today = date.today().isoformat()
    return [
        {"date": today, "tmin": 18.6, "tmax": 30.2, "radiation_mj": 18.5, "wind_ms": 1.5},
        {"date": (date.today() + timedelta(1)).isoformat(), "tmin": 18.0, "tmax": 29.8, "radiation_mj": 17.8, "wind_ms": 1.5},
        {"date": (date.today() + timedelta(2)).isoformat(), "tmin": 18.3, "tmax": 30.0, "radiation_mj": 18.2, "wind_ms": 1.5},
    ]


# ---------------------------------------------------------------------------
# BepsLiteAdapter（江桂源原始核心，无改动）
# ---------------------------------------------------------------------------

class BepsLiteAdapter:
    """
    BEPS-Lite 区域生态扩展模型。
    1. 根据气象、LAI、NDVI、遮阴程度、水分限制因子估算 GPP
    2. 根据 GPP 估算 NPP
    3. 简化估算 ET
    4. 根据 NPP 估算碳汇
    5. 综合生成长势评分和生态风险等级
    """

    def __init__(self):
        self.lue_max = 2.2       # 最大光能利用率
        self.par_ratio = 0.48    # PAR 占总太阳辐射比例
        self.npp_ratio = 0.45    # NPP/GPP 比例
        self.k = 0.55            # Beer-Lambert 冠层光截获系数

    def temperature_factor(self, tmean: float) -> float:
        t_base, t_opt, t_max = 8.0, 24.0, 38.0
        if tmean <= t_base or tmean >= t_max:
            return 0.05
        if tmean <= t_opt:
            return _clamp((tmean - t_base) / (t_opt - t_base), 0.05, 1.0)
        return _clamp((t_max - tmean) / (t_max - t_opt), 0.05, 1.0)

    def calculate_fpar(self, lai: Optional[float], ndvi: Optional[float]) -> float:
        values = []
        if lai is not None:
            lai = max(lai, 0.01)
            values.append(_clamp(1.0 - math.exp(-self.k * lai), 0.05, 0.95))
        if ndvi is not None:
            values.append(_clamp(1.24 * ndvi - 0.168, 0.05, 0.95))
        return sum(values) / len(values) if values else 0.65

    def shade_factor(self, shade_degree: float) -> float:
        return _clamp(1.0 - 0.45 * _clamp(shade_degree, 0.0, 1.0), 0.55, 1.0)

    def estimate_et(self, radiation_mj, fpar, temp_factor, water_factor, wind_ms) -> float:
        wind_factor = _clamp(0.85 + 0.08 * wind_ms, 0.8, 1.2)
        et0 = 0.408 * radiation_mj * 0.65 * (0.4 + 0.6 * temp_factor) * wind_factor
        return round(max(et0 * (0.2 + 0.8 * fpar) * (0.5 + 0.5 * water_factor), 0.0), 3)

    def growth_score(self, gpp, ndvi, water_factor, temp_factor, fpar) -> float:
        gpp_score = _clamp(gpp / 8.0 * 100.0, 0, 100)
        ndvi_score = (
            _clamp((ndvi - 0.35) / (0.85 - 0.35) * 100.0, 0, 100)
            if ndvi is not None
            else _clamp(fpar / 0.9 * 100.0, 0, 100)
        )
        water_score = _clamp(water_factor * 100.0, 0, 100)
        temp_score = _clamp(temp_factor * 100.0, 0, 100)
        score = 0.35 * gpp_score + 0.25 * ndvi_score + 0.25 * water_score + 0.15 * temp_score
        return round(_clamp(score, 0, 100), 2)

    def risk_level(self, score, water_factor, temp_factor) -> str:
        if score < 45 or water_factor < 0.35 or temp_factor < 0.25:
            return "high"
        if score < 65 or water_factor < 0.55 or temp_factor < 0.5:
            return "medium"
        return "low"

    def risk_reasons(self, score, water_factor, temp_factor, shade_degree, ndvi) -> List[str]:
        reasons = []
        if water_factor < 0.45:
            reasons.append("根区水分限制明显，可能降低冠层光合生产力")
        if temp_factor < 0.5:
            reasons.append("当前温度条件偏离咖啡适宜生长区间")
        if shade_degree > 0.65:
            reasons.append("遮阴程度较高，有效辐射输入下降")
        if ndvi is not None and ndvi < 0.5:
            reasons.append("NDVI 偏低，提示冠层长势可能下降")
        if score < 60:
            reasons.append("综合长势评分偏低，建议检查水分、病虫害和遮阴状态")
        if not reasons:
            reasons.append("冠层生态状态总体正常，维持当前管理")
        return reasons

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        plot_id = payload.get("plot_id", "demo_plot")
        weather = payload.get("weather", [])
        if not weather:
            raise ValueError("weather 不能为空")

        lai = payload.get("lai") or 2.5
        ndvi = payload.get("ndvi")
        shade_degree = float(payload.get("shade_degree", 0.3))
        water_factor = _clamp(float(payload.get("water_factor", 0.8)), 0.2, 1.0)

        fpar = self.calculate_fpar(lai, ndvi)
        shade = self.shade_factor(shade_degree)
        series = []

        for day in weather:
            tmin = float(day["tmin"])
            tmax = float(day["tmax"])
            radiation_mj = float(day["radiation_mj"])
            wind_ms = float(day.get("wind_ms", 1.5))
            tmean = (tmin + tmax) / 2.0
            temp_factor = self.temperature_factor(tmean)

            par = radiation_mj * self.par_ratio
            gpp = par * fpar * self.lue_max * temp_factor * water_factor * shade
            npp = gpp * self.npp_ratio
            et = self.estimate_et(radiation_mj, fpar, temp_factor, water_factor, wind_ms)
            carbon_sink = npp * 10.0
            score = self.growth_score(gpp, ndvi, water_factor, temp_factor, fpar)
            risk = self.risk_level(score, water_factor, temp_factor)

            series.append({
                "date": day["date"],
                "tmean": round(tmean, 2),
                "lai": round(lai, 3),
                "ndvi": round(ndvi, 3) if ndvi is not None else None,
                "fpar": round(fpar, 3),
                "gpp_gc_m2_day": round(gpp, 3),
                "npp_gc_m2_day": round(npp, 3),
                "et_mm_day": round(et, 3),
                "carbon_sink_kg_ha_day": round(carbon_sink, 3),
                "growth_score": score,
                "risk_level": risk,
            })

        avg_gpp = sum(item["gpp_gc_m2_day"] for item in series) / len(series)
        avg_npp = sum(item["npp_gc_m2_day"] for item in series) / len(series)
        avg_et = sum(item["et_mm_day"] for item in series) / len(series)
        total_carbon = sum(item["carbon_sink_kg_ha_day"] for item in series)
        avg_score = sum(item["growth_score"] for item in series) / len(series)

        avg_temp_factor = sum(
            self.temperature_factor((float(d["tmin"]) + float(d["tmax"])) / 2.0)
            for d in weather
        ) / len(weather)

        final_risk = self.risk_level(avg_score, water_factor, avg_temp_factor)
        reasons = self.risk_reasons(avg_score, water_factor, avg_temp_factor, shade_degree, ndvi)

        return {
            "module": "BEPS-Lite",
            "status": "ok",
            "plot_id": plot_id,
            "input_summary": {
                "lai": lai,
                "ndvi": ndvi,
                "shade_degree": shade_degree,
                "water_factor": water_factor,
                "fpar": round(fpar, 3),
            },
            "summary": {
                "avg_gpp_gc_m2_day": round(avg_gpp, 3),
                "avg_npp_gc_m2_day": round(avg_npp, 3),
                "avg_et_mm_day": round(avg_et, 3),
                "total_carbon_sink_kg_ha": round(total_carbon, 3),
                "growth_score": round(avg_score, 2),
                "risk_level": final_risk,
                "risk_reasons": reasons,
            },
            "series": series,
        }


# ---------------------------------------------------------------------------
# 主入口（与主系统 model_api.py 的调用签名保持一致）
# ---------------------------------------------------------------------------

def run_beps_model(model_input_json, apsim_result=None, hydrus_result=None):
    # AI辅助生成-DeepSeek-V3 - 2026年4月27日 15:10:45 - 耦合APSIM与HYDRUS因子，计算冠层生态GPP/NPP
    """
    BEPS-Lite 主调用接口。
    接收主系统标准 model_input_json，以及可选的 APSIM/HYDRUS 前序结果用于提取 LAI 和水分因子。
    """
    task_id = model_input_json.get("task_id", "task_demo")

    # --- 构建气象数据 ---
    weather = []
    for w in model_input_json.get("weather_series", []):
        weather.append({
            "date": w.get("date", date.today().isoformat()),
            "tmin": float(w.get("tmin", w.get("mint", 18.6))),
            "tmax": float(w.get("tmax", w.get("maxt", 30.2))),
            "radiation_mj": float(w.get("radiation_mj", w.get("radiation", 18.5))),
            "wind_ms": float(w.get("wind_ms", 1.5)),
        })
    if not weather:
        weather = _load_demo_weather()

    # --- LAI：优先使用 APSIM 结果 ---
    lai = None
    if apsim_result:
        lai = apsim_result.get("lai")

    # --- 水分因子：优先使用 HYDRUS root_uptake_ratio ---
    water_factor = None
    if hydrus_result:
        water_factor = hydrus_result.get("root_uptake_ratio") or hydrus_result.get("root_uptake_efficiency")

    plot_info = model_input_json.get("plot_info", {})
    shade_map = {"无遮阴": 0.0, "轻度遮阴": 0.2, "中等遮阴": 0.4, "重度遮阴": 0.7}
    shade_degree = shade_map.get(str(plot_info.get("shade_level", "")), 0.3)

    payload = {
        "plot_id": model_input_json.get("plot_id", "plot_001"),
        "weather": weather,
        "lai": lai,
        "ndvi": None,
        "shade_degree": shade_degree,
        "water_factor": water_factor,
    }

    try:
        adapter = BepsLiteAdapter()
        result = adapter.run(payload)
    except Exception as e:
        print(f"[BEPS][{task_id}] 计算失败: {e}，启动兜底机制")
        result = _fallback_result(model_input_json)
        result["beps_error"] = str(e)

    # --- 字段映射：兼容主系统 risk_service.py 和 llm_service.py ---
    _risk_cn = {"low": "低", "medium": "中等", "high": "高"}
    summary = result.get("summary", {})
    result["model"] = "BEPS-Lite"
    result["plot_id"] = model_input_json.get("plot_id", "plot_001")
    result["growth_score"] = summary.get("growth_score", 75)
    result["gpp_today"] = summary.get("avg_gpp_gc_m2_day", 0)
    result["npp_today"] = summary.get("avg_npp_gc_m2_day", 0)
    result["et_today"] = summary.get("avg_et_mm_day", 0)
    result["carbon_sink_kgC_mu"] = round(summary.get("total_carbon_sink_kg_ha", 0) / 15, 3)
    result["beps_risk"] = _risk_cn.get(summary.get("risk_level", "low"), "低")
    result["canopy_status"] = "，".join(summary.get("risk_reasons", ["冠层状态正常"]))
    result["beps_explain"] = {
        "what": f"咖啡园冠层综合长势评分 {result['growth_score']} 分，生态风险：{result['beps_risk']}。",
        "why": "由 BEPS-Lite 基于气象、LAI、NDVI、遮阴和土壤水分因子实时推算。",
    }

    # --- 图表系列数组：兼容小程序 result.js 读取格式 ---
    # 小程序读: beps.gpp_series[].gpp / beps.npp_series[].npp / beps.et_series[].et
    _series = result.get("series", [])
    result["gpp_series"] = [{"date": s["date"], "gpp": s["gpp_gc_m2_day"]} for s in _series]
    result["npp_series"] = [{"date": s["date"], "npp": s["npp_gc_m2_day"]} for s in _series]
    result["et_series"]  = [{"date": s["date"], "et":  s["et_mm_day"]}     for s in _series]

    # --- 保存结果 ---
    run_dir = BEPS_RUN_DIR / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "beps_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def _fallback_result(model_input_json):
    return {
        "module": "BEPS-Lite",
        "status": "fallback",
        "plot_id": model_input_json.get("plot_id", "plot_001"),
        "summary": {
            "avg_gpp_gc_m2_day": 5.6,
            "avg_npp_gc_m2_day": 2.52,
            "avg_et_mm_day": 3.1,
            "total_carbon_sink_kg_ha": 25.2,
            "growth_score": 72.0,
            "risk_level": "low",
            "risk_reasons": ["当前使用 BEPS-Lite 兜底数据，请检查输入参数是否完整"],
        },
        "series": [],
    }
