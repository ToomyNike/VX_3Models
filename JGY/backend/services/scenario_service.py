from copy import deepcopy

from services.model_runner import run_beps_lite_task


def build_scenario_payloads(base_payload):
    """
    基于基础输入构建多个 BEPS-Lite 情景。
    """

    scenarios = []

    # 场景 1：正常管理
    normal = deepcopy(base_payload)
    normal["scenario_name"] = "正常管理情景"
    normal["water_factor"] = 0.82
    normal["shade_degree"] = 0.30
    normal["ndvi"] = 0.72
    scenarios.append(normal)

    # 场景 2：根区缺水
    drought = deepcopy(base_payload)
    drought["scenario_name"] = "根区缺水情景"
    drought["water_factor"] = 0.38
    drought["shade_degree"] = base_payload.get("shade_degree", 0.35)
    drought["ndvi"] = base_payload.get("ndvi", 0.68)
    scenarios.append(drought)

    # 场景 3：遮阴过高
    high_shade = deepcopy(base_payload)
    high_shade["scenario_name"] = "遮阴过高情景"
    high_shade["water_factor"] = base_payload.get("water_factor", 0.78)
    high_shade["shade_degree"] = 0.75
    high_shade["ndvi"] = base_payload.get("ndvi", 0.68)
    scenarios.append(high_shade)

    # 场景 4：NDVI 偏低
    low_ndvi = deepcopy(base_payload)
    low_ndvi["scenario_name"] = "NDVI 偏低情景"
    low_ndvi["water_factor"] = base_payload.get("water_factor", 0.78)
    low_ndvi["shade_degree"] = base_payload.get("shade_degree", 0.35)
    low_ndvi["ndvi"] = 0.46
    scenarios.append(low_ndvi)

    # 场景 5：综合胁迫
    combined = deepcopy(base_payload)
    combined["scenario_name"] = "综合胁迫情景"
    combined["water_factor"] = 0.35
    combined["shade_degree"] = 0.75
    combined["ndvi"] = 0.45
    scenarios.append(combined)

    return scenarios


def compare_beps_scenarios(base_payload):
    """
    运行多个 BEPS-Lite 情景，并返回对比结果。
    """

    scenario_payloads = build_scenario_payloads(base_payload)

    results = []

    for payload in scenario_payloads:
        beps_result = run_beps_lite_task(payload)
        summary = beps_result.get("summary", {})

        results.append({
            "scenario_name": payload.get("scenario_name", "未命名情景"),
            "input": {
                "water_factor": payload.get("water_factor"),
                "shade_degree": payload.get("shade_degree"),
                "ndvi": payload.get("ndvi"),
                "lai": payload.get("lai")
            },
            "summary": {
                "gpp": summary.get("avg_gpp_gc_m2_day"),
                "npp": summary.get("avg_npp_gc_m2_day"),
                "et": summary.get("avg_et_mm_day"),
                "carbon_sink": summary.get("total_carbon_sink_kg_ha"),
                "growth_score": summary.get("growth_score"),
                "risk_level": summary.get("risk_level"),
                "risk_reasons": summary.get("risk_reasons")
            }
        })

    return {
        "status": "ok",
        "message": "BEPS-Lite 情景模拟对比完成",
        "scenario_count": len(results),
        "results": results
    }