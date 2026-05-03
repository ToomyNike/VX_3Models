def fuse_model_results(apsim_result, hydrus_result, beps_result):
    """
    三模型结果融合。

    APSIM-Coffee：作物生长、生育期、产量、水分胁迫、氮素状态、LAI
    HYDRUS-1D：土壤剖面水分、根系吸水效率、入渗深度
    BEPS-Lite：GPP、NPP、ET、碳汇、长势评分、生态风险
    """

    stage = apsim_result.get("stage", "未知生育期")
    yield_prediction = apsim_result.get("yield_prediction", None)

    water_stress = float(apsim_result.get("water_stress", 0.0))
    nitrogen_stress = float(apsim_result.get("nitrogen_stress", 0.0))

    root_uptake = float(hydrus_result.get("root_uptake_efficiency", 0.8))
    infiltration_depth = hydrus_result.get("infiltration_depth_cm", None)

    beps_summary = beps_result.get("summary", {})
    growth_score = float(beps_summary.get("growth_score", 75.0))
    beps_risk = beps_summary.get("risk_level", "low")

    risk_level = "low"
    risk_reasons = []
    suggestions = []

    # 规则 1：APSIM 水分胁迫高 + HYDRUS 根系吸水低
    if water_stress > 0.6 and root_uptake < 0.5:
        risk_level = "high"
        risk_reasons.append("APSIM 显示水分胁迫升高，HYDRUS 显示根系吸水效率下降")
        suggestions.append("建议优先补灌，重点检查 20-60 cm 根区土壤水分")

    # 规则 2：APSIM 氮素偏低 + HYDRUS 土壤偏干
    if nitrogen_stress > 0.6 and root_uptake < 0.5:
        if risk_level != "high":
            risk_level = "medium"
        risk_reasons.append("氮素状态偏低，但土壤水分不足可能限制肥效释放")
        suggestions.append("建议先补水，待土壤水分恢复后再考虑追肥")

    # 规则 3：BEPS-Lite 长势下降
    if growth_score < 60:
        if risk_level == "low":
            risk_level = "medium"
        risk_reasons.append("BEPS-Lite 显示冠层长势评分偏低")
        suggestions.append("建议检查遮阴、病虫害、水分和修剪情况")

    # 规则 4：BEPS-Lite 生态风险高
    if beps_risk == "high":
        risk_level = "high"
        risk_reasons.append("BEPS-Lite 判断生态风险较高")
        suggestions.append("建议增加巡园频率，并结合冠层、土壤和病虫害情况排查原因")

    # 正常情况
    if not risk_reasons:
        risk_reasons.append("三模型结果总体正常，当前咖啡园风险较低")
        suggestions.append("维持现有水肥管理和常规巡园频率")

    return {
        "status": "ok",
        "risk_level": risk_level,
        "stage": stage,
        "yield_prediction": yield_prediction,
        "cards": {
            "growth_score": growth_score,
            "gpp": beps_summary.get("avg_gpp_gc_m2_day"),
            "npp": beps_summary.get("avg_npp_gc_m2_day"),
            "et": beps_summary.get("avg_et_mm_day"),
            "carbon_sink": beps_summary.get("total_carbon_sink_kg_ha"),
            "root_uptake_efficiency": root_uptake,
            "water_stress": water_stress,
            "nitrogen_stress": nitrogen_stress
        },
        "risk_reasons": risk_reasons,
        "suggestions": suggestions,
        "what": risk_reasons[0],
        "how": suggestions[0],
        "why": "该判断由 APSIM-Coffee 的作物胁迫结果、HYDRUS-1D 的根区水分结果和 BEPS-Lite 的冠层生态指标共同给出。"
    }