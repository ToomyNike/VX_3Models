"""
三模型结果融合引擎（集成版）
融合规则整合自 JGY（江桂源）的联合规则集 + 蔡济远原始框架
"""
from services.llm_service import generate_advice
from services.risk_service import combine_risk


def merge(apsim_result, hydrus_result, beps_result, task_id=None, plot_id=None):
    """
    三模型结果融合。
    APSIM-Coffee : 作物生长、生育期、产量、水分胁迫、氮素状态、LAI
    HYDRUS-1D    : 土壤剖面水分、根系吸水效率、入渗深度
    BEPS-Lite    : GPP、NPP、ET、碳汇、长势评分、生态风险
    """
    risk_level, risk_reasons, suggestions = _fuse_risk(apsim_result, hydrus_result, beps_result)
    advice = generate_advice(apsim_result, hydrus_result, beps_result)

    beps_summary = beps_result.get("summary", {})

    return {
        "task_id": task_id,
        "plot_id": plot_id or apsim_result.get("plot_id"),
        "status": "success",
        "dashboard": {
            "stage": apsim_result.get("stage"),
            "harvest_days": apsim_result.get("harvest_days"),
            "yield_pred_kg_mu": apsim_result.get("yield_pred_kg_mu"),
            "risk_level": risk_level,
            "growth_score": beps_result.get("growth_score"),
        },
        "fusion": {
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
            "suggestions": suggestions,
            "what": risk_reasons[0] if risk_reasons else "",
            "how": suggestions[0] if suggestions else "",
            "why": (
                "该判断由 APSIM-Coffee 的作物胁迫结果、"
                "HYDRUS-1D 的根区水分结果和 BEPS-Lite 的冠层生态指标共同给出。"
            ),
        },
        "apsim": apsim_result,
        "hydrus": hydrus_result,
        "beps": beps_result,
        "advice": advice,
    }


def _fuse_risk(apsim_result, hydrus_result, beps_result):
    """
    多模型联合风险规则（来自 JGY 融合引擎，比原版更丰富）。
    返回 (risk_level_str, risk_reasons_list, suggestions_list)
    """
    # 使用中文 risk 等级
    _order = {"低": 1, "中等": 2, "高": 3}

    water_stress = float(apsim_result.get("water_stress", 0.0))
    nitrogen_status = apsim_result.get("nitrogen_status", "正常")
    root_uptake = float(hydrus_result.get("root_uptake_ratio", 0.8))
    hydrus_status = hydrus_result.get("water_status", "")
    beps_summary = beps_result.get("summary", {})
    growth_score = float(beps_summary.get("growth_score", beps_result.get("growth_score", 75)))
    beps_risk_en = beps_summary.get("risk_level", "low")
    beps_risk_cn = {"low": "低", "medium": "中等", "high": "高"}.get(beps_risk_en, "低")

    risk_level = "低"
    risk_reasons = []
    suggestions = []

    # 规则 1：APSIM 水分胁迫高 + HYDRUS 根系吸水低
    if water_stress > 0.6 and root_uptake < 0.5:
        risk_level = "高"
        risk_reasons.append("APSIM 显示水分胁迫升高，HYDRUS 显示根系吸水效率下降")
        suggestions.append("建议优先补灌，重点检查 20-60cm 根区土壤水分")

    # 规则 2：氮素偏低 + 土壤偏干（施肥效率受限）
    if nitrogen_status in ("偏低", "不足") and root_uptake < 0.5:
        if _order.get(risk_level, 1) < 2:
            risk_level = "中等"
        risk_reasons.append("氮素状态偏低，但土壤水分不足可能限制肥效释放")
        suggestions.append("建议先补水，待土壤水分恢复后再考虑追肥")

    # 规则 3：BEPS-Lite 长势评分偏低
    if growth_score < 60:
        if _order.get(risk_level, 1) < 2:
            risk_level = "中等"
        risk_reasons.append(f"BEPS-Lite 显示冠层长势评分偏低（{growth_score:.0f} 分）")
        suggestions.append("建议检查遮阴、病虫害、水分和修剪情况")

    # 规则 4：BEPS-Lite 生态风险高
    if beps_risk_en == "high":
        risk_level = "高"
        risk_reasons.append("BEPS-Lite 判断生态风险较高")
        suggestions.append("建议增加巡园频率，结合冠层、土壤和病虫害情况排查原因")

    # 规则 5：HYDRUS 水分状态（兼容中文字段）
    if "重度" in hydrus_status or "严重" in hydrus_status:
        if _order.get(risk_level, 1) < 3:
            risk_level = "高"
        risk_reasons.append("HYDRUS 显示土壤重度干旱，深层根区严重缺水")
        suggestions.append("建议立即安排补灌，单次灌溉量不低于 30mm")
    elif "中度" in hydrus_status and risk_level == "低":
        risk_level = "中等"
        risk_reasons.append("HYDRUS 显示土壤中度干旱")
        suggestions.append("建议本周内安排补灌")

    # 正常情况
    if not risk_reasons:
        risk_reasons.append("三模型结果总体正常，当前咖啡园风险较低")
        suggestions.append("维持现有水肥管理和常规巡园频率")

    return risk_level, risk_reasons, suggestions
