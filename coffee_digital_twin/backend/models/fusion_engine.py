"""
三模型结果融合引擎（机理互证升级版）
融合规则整合自 JGY（江桂源）的联合规则集 + 蔡济远原始框架

升级内容：
  - 引入机理解释层 mechanism_explainer，每次融合都生成三模型机理证据
  - 风险规则细化为"机理互证规则"（APSIM + HYDRUS + BEPS 联合判断）
  - 返回结构增加 mechanism_explanation 和 model_basis 字段
"""
from services.llm_service import generate_advice
from services.risk_service import combine_risk
from services.mechanism_explainer import build_mechanism_evidence


def merge(apsim_result, hydrus_result, beps_result, task_id=None, plot_id=None):
    """
    三模型结果融合。
    APSIM-Coffee : 作物生长、生育期、产量、水分胁迫、氮素状态、LAI
    HYDRUS-1D    : 土壤剖面水分、根系吸水效率、入渗深度
    BEPS-Lite    : GPP、NPP、ET、碳汇、长势评分、生态风险

    返回结果包含：
      - dashboard  : 仪表盘摘要（供首页展示）
      - fusion     : 融合风险结论
      - mechanism_explanation : 三模型机理证据（核心亮点）
      - apsim / hydrus / beps : 原始模型结果
      - advice     : AI 农技建议（含 model_basis）
    """
    risk_level, risk_reasons, suggestions = _fuse_risk(apsim_result, hydrus_result, beps_result)

    # 构建机理解释
    mechanism = build_mechanism_evidence(
        apsim_result, hydrus_result, beps_result, risk_level
    )

    # 构建分模型简短依据（供 fusion 层和 LLM 使用）
    model_basis = _build_model_basis(apsim_result, hydrus_result, beps_result)

    # 生成 AI 建议（携带机理证据）
    advice = generate_advice(
        apsim_result,
        hydrus_result,
        beps_result,
        mechanism_evidence=mechanism,
    )

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
            "why": mechanism.get("integrated_reason", ""),
            "model_basis": model_basis,
        },
        "mechanism_explanation": mechanism,
        "apsim": apsim_result,
        "hydrus": hydrus_result,
        "beps": beps_result,
        "advice": advice,
    }


def _build_model_basis(apsim: dict, hydrus: dict, beps: dict) -> dict:
    """构建三模型简短机理依据（单句，供 fusion 层和 LLM prompt 使用）。"""
    stage = apsim.get("stage", "关键生长期")
    water_stress = float(apsim.get("water_stress", 0.0))
    nitrogen_status = apsim.get("nitrogen_status", "正常")

    root_uptake = float(hydrus.get("root_uptake_ratio", 0.8))
    water_status = hydrus.get("water_status", "未知")
    infiltration = hydrus.get("infiltration_depth_cm", "-")

    summary_data = beps.get("summary", {})
    growth_score = float(beps.get("growth_score", summary_data.get("growth_score", 75)))
    gpp = beps.get("gpp_today", summary_data.get("gpp_today", "-"))

    return {
        "apsim": (
            f"APSIM-Coffee 预测：当前生育期「{stage}」，"
            f"水分胁迫指数 {water_stress:.2f}，氮素状态「{nitrogen_status}」。"
        ),
        "hydrus": (
            f"HYDRUS-1D 解析：土壤水分「{water_status}」，"
            f"入渗深度约 {infiltration} cm，根系吸水效率 {root_uptake:.0%}。"
        ),
        "beps": (
            f"BEPS-Lite 评估：当日 GPP {gpp} gC/m²，"
            f"冠层长势评分 {growth_score:.0f}/100。"
        ),
    }


def _fuse_risk(apsim_result, hydrus_result, beps_result):
    """
    多模型机理互证风险规则。
    每条规则都明确写出"是哪两个/三个模型的联合证据"。
    返回 (risk_level_str, risk_reasons_list, suggestions_list)
    """
    _order = {"低": 1, "中等": 2, "高": 3}

    water_stress = float(apsim_result.get("water_stress", 0.0))
    nitrogen_status = apsim_result.get("nitrogen_status", "正常")
    stage = apsim_result.get("stage", "")

    root_uptake = float(hydrus_result.get("root_uptake_ratio", 0.8))
    hydrus_status = hydrus_result.get("water_status", "")
    infiltration = hydrus_result.get("infiltration_depth_cm", 50)

    beps_summary = beps_result.get("summary", {})
    growth_score = float(beps_summary.get("growth_score", beps_result.get("growth_score", 75)))
    beps_risk_en = beps_summary.get("risk_level", "low")
    beps_risk_cn = {"low": "低", "medium": "中等", "high": "高"}.get(beps_risk_en, "低")
    gpp = beps_result.get("gpp_today", beps_summary.get("gpp_today", 0))

    risk_level = "低"
    risk_reasons = []
    suggestions = []

    # ── 机理互证规则 1：APSIM 水分胁迫高 + HYDRUS 根系吸水低 ──
    # 场景：作物层和土壤层共同指向根区缺水
    if water_stress > 0.6 and root_uptake < 0.5:
        risk_level = "高"
        risk_reasons.append(
            "【APSIM×HYDRUS 联合】APSIM 显示水分胁迫严重（>{:.2f}），"
            "HYDRUS 解析根系吸水效率仅 {:.0%}——作物层和土壤层共同指向根区严重缺水".format(
                water_stress, root_uptake
            )
        )
        suggestions.append("建议立即安排补灌，重点保证 20-60 cm 根区土壤水分，灌溉量不低于 30 mm")

    # ── 机理互证规则 2：APSIM 水分胁迫中等 + HYDRUS 中度干旱 ──
    # 场景：果实膨大期出现水分风险，应提高灌溉频率
    elif water_stress > 0.3 and ("中度" in hydrus_status or "偏干" in hydrus_status):
        if _order.get(risk_level, 1) < 2:
            risk_level = "中等"
        fruit_stage = any(k in stage for k in ["果实", "膨大", "灌浆", "成熟"])
        if fruit_stage:
            risk_reasons.append(
                "【APSIM×HYDRUS 联合】当前处于产量形成敏感期「{}」，"
                "APSIM 水分胁迫上升（{:.2f}），HYDRUS 显示根区「{}」——"
                "产量对水分敏感，需提高灌溉频率".format(stage, water_stress, hydrus_status)
            )
            suggestions.append("建议本周内安排补灌，产量形成期保持根区水分充足，可适当缩短灌溉间隔")
        else:
            risk_reasons.append(
                "【APSIM×HYDRUS 联合】APSIM 水分胁迫升高（{:.2f}），"
                "HYDRUS 显示土壤「{}」——根区水分不足需关注".format(water_stress, hydrus_status)
            )
            suggestions.append("建议本周内安排补灌，优先保证 20-40 cm 根区水分")

    # ── 机理互证规则 3：氮素偏低 + HYDRUS 根区偏干（施肥效率受限）──
    if nitrogen_status in ("偏低", "不足") and root_uptake < 0.6:
        if _order.get(risk_level, 1) < 2:
            risk_level = "中等"
        risk_reasons.append(
            "【APSIM×HYDRUS 联合】APSIM 显示氮素状态「{}」，"
            "但 HYDRUS 根系吸水效率仅 {:.0%}——"
            "土壤水分不足会限制养分溶解和根系吸收，直接追肥效果有限".format(
                nitrogen_status, root_uptake
            )
        )
        suggestions.append("建议先补水，待根区水分恢复（根系吸水效率 > 70%）后再少量追肥")

    # ── 机理互证规则 4：BEPS GPP 下降 + HYDRUS 缺水 ──
    # 场景：冠层光合受到水分限制
    try:
        gpp_val = float(gpp)
    except (TypeError, ValueError):
        gpp_val = 10.0
    if gpp_val < 7.0 and ("干旱" in hydrus_status or root_uptake < 0.6):
        if _order.get(risk_level, 1) < 2:
            risk_level = "中等"
        risk_reasons.append(
            "【BEPS×HYDRUS 联合】BEPS-Lite 监测到当日 GPP 偏低（{} gC/m²），"
            "结合 HYDRUS 根区水分不足——冠层光合生产力受到水分限制".format(gpp)
        )
        suggestions.append("补水后持续观察 GPP 和长势评分恢复情况，若 3 天内未改善需进一步排查")

    # ── 机理互证规则 5：BEPS 长势低 + APSIM 水肥正常（可能是遮阴/病虫害）──
    if growth_score < 60 and water_stress < 0.3 and nitrogen_status == "正常":
        if _order.get(risk_level, 1) < 2:
            risk_level = "中等"
        risk_reasons.append(
            "【BEPS×APSIM 联合】BEPS-Lite 长势评分偏低（{:.0f}/100），"
            "但 APSIM 水肥胁迫不明显——水肥不能解释当前长势下降，"
            "可能存在遮阴、病虫害或冠层结构问题".format(growth_score)
        )
        suggestions.append("建议增加巡园频率，检查遮阴情况、病虫害征兆和冠层修剪需求")

    # ── 规则 6：HYDRUS 重度干旱 ──
    if "重度" in hydrus_status or "严重" in hydrus_status:
        if _order.get(risk_level, 1) < 3:
            risk_level = "高"
        risk_reasons.append(
            "【HYDRUS】土壤重度干旱，深层根区严重缺水（水分状态：{}）".format(hydrus_status)
        )
        suggestions.append("建议立即安排补灌，单次灌溉量不低于 30 mm，优先保障深层根区供水")

    # ── 规则 7：BEPS 生态风险高 ──
    if beps_risk_en == "high":
        risk_level = "高"
        risk_reasons.append("【BEPS-Lite】生态风险评估为高，冠层生产力显著下降")
        suggestions.append("建议增加巡园频率，结合冠层、土壤和病虫害情况全面排查原因")

    # 正常情况
    if not risk_reasons:
        risk_reasons.append(
            "【三模型综合】APSIM 水肥胁迫正常、HYDRUS 根区水分充足、"
            "BEPS 冠层长势良好，当前咖啡园整体风险较低"
        )
        suggestions.append("维持现有水肥管理和常规巡园频率，持续记录农事操作")

    return risk_level, risk_reasons, suggestions
