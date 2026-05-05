"""
机理解释层（Mechanism Explainer）
负责将 APSIM / HYDRUS / BEPS 三模型的原始结果整理成结构化"机理证据"。

这是系统的核心亮点：
  - APSIM 负责作物生长层（生育期、产量、水肥胁迫）
  - HYDRUS 负责土壤水分层（入渗、根区水分、根系吸水）
  - BEPS   负责冠层生态层（GPP、NPP、ET、长势评分）

build_mechanism_evidence() 被 fusion_engine.py 调用，输出结构供前端直接渲染。
"""
from typing import Optional


# ---------------------------------------------------------------------------
# APSIM 机理证据
# ---------------------------------------------------------------------------

def _apsim_evidence(apsim: dict) -> dict:
    stage = apsim.get("stage", "关键生长期")
    water_stress = float(apsim.get("water_stress", 0.0))
    nitrogen_status = apsim.get("nitrogen_status", "正常")
    yield_pred = apsim.get("yield_pred_kg_mu", "-")
    lai = apsim.get("lai", "-")

    # 水分胁迫描述
    if water_stress >= 0.6:
        stress_desc = f"水分胁迫严重（{water_stress:.2f}），当前作物生长受到显著抑制。"
    elif water_stress >= 0.3:
        stress_desc = f"水分胁迫升高（{water_stress:.2f}），处于产量形成的敏感阶段。"
    else:
        stress_desc = f"水分胁迫较低（{water_stress:.2f}），当前水分供应较为充足。"

    # 氮素描述
    if nitrogen_status in ("偏低", "不足"):
        n_desc = f"氮素状态{nitrogen_status}，施肥效果可能受当前水分条件限制。"
    else:
        n_desc = f"氮素状态{nitrogen_status}，当前水肥供应基本正常。"

    summary = f"当前处于{stage}，{stress_desc}{n_desc}"

    return {
        "title": "APSIM-Coffee 作物层机理证据",
        "summary": summary,
        "predicts": ["生育期", "产量趋势", "水分胁迫", "氮素状态", "LAI"],
        "key_metrics": {
            "stage": stage,
            "yield_pred_kg_mu": yield_pred,
            "water_stress": round(water_stress, 2),
            "nitrogen_status": nitrogen_status,
            "lai": lai,
        },
        "interpretation": (
            f"APSIM-Coffee 模拟了咖啡从播种到采收的全生育期动态。"
            f"当前生育期为「{stage}」，预计亩产 {yield_pred} kg，"
            f"水分胁迫指数 {water_stress:.2f}（0=无胁迫，1=严重胁迫），"
            f"氮素状态：{nitrogen_status}，叶面积指数（LAI）：{lai}。"
        ),
    }


# ---------------------------------------------------------------------------
# HYDRUS 机理证据
# ---------------------------------------------------------------------------

def _hydrus_evidence(hydrus: dict) -> dict:
    water_status = hydrus.get("water_status", "未知")
    infiltration_depth = hydrus.get("infiltration_depth_cm", "-")
    root_uptake = float(hydrus.get("root_uptake_ratio", 0.8))

    # 入渗描述
    if isinstance(infiltration_depth, (int, float)) and infiltration_depth < 30:
        infil_desc = f"入渗深度仅 {infiltration_depth} cm，水分主要停留在表层，未充分到达主根区。"
    elif isinstance(infiltration_depth, (int, float)) and infiltration_depth < 50:
        infil_desc = f"入渗深度约 {infiltration_depth} cm，部分水分到达浅层根区，深层根系供水偏弱。"
    else:
        infil_desc = f"入渗深度约 {infiltration_depth} cm，水分能到达主根区范围。"

    # 根系吸水描述
    if root_uptake < 0.5:
        uptake_desc = f"根系吸水效率偏低（{root_uptake:.0%}），说明根区有效水分供给不足。"
    elif root_uptake < 0.75:
        uptake_desc = f"根系吸水效率中等（{root_uptake:.0%}），水分供给有一定压力。"
    else:
        uptake_desc = f"根系吸水效率较好（{root_uptake:.0%}），根区水分状态正常。"

    summary = f"土壤水分状态：{water_status}。{infil_desc}{uptake_desc}"

    return {
        "title": "HYDRUS-1D 土壤水分机理证据",
        "summary": summary,
        "predicts": ["土壤剖面水分", "入渗深度", "根系吸水效率"],
        "key_metrics": {
            "water_status": water_status,
            "infiltration_depth_cm": infiltration_depth,
            "root_uptake_ratio": round(root_uptake, 2),
        },
        "interpretation": (
            f"HYDRUS-1D 模拟了土壤中水分的运动过程和根系吸水。"
            f"当前土壤水分状态为「{water_status}」，"
            f"灌溉水入渗深度约 {infiltration_depth} cm，"
            f"根系吸水效率 {root_uptake:.0%}（越接近100%说明根区供水越充足）。"
            f"这一模型解释了水是否真正到达了咖啡根系，而非仅停留在土壤表层。"
        ),
    }


# ---------------------------------------------------------------------------
# BEPS 机理证据
# ---------------------------------------------------------------------------

def _beps_evidence(beps: dict) -> dict:
    summary_data = beps.get("summary", {})
    gpp = beps.get("gpp_today", summary_data.get("gpp_today", "-"))
    npp = beps.get("npp_today", summary_data.get("npp_today", "-"))
    et = beps.get("et_today", summary_data.get("et_today", "-"))
    carbon_sink = beps.get("carbon_sink_kgC_mu", summary_data.get("carbon_sink_kgC_mu", "-"))
    growth_score = float(beps.get("growth_score", summary_data.get("growth_score", 75)))
    canopy_status = beps.get("canopy_status", summary_data.get("canopy_status", "-"))

    # 长势描述
    if growth_score < 60:
        growth_desc = f"长势评分偏低（{growth_score:.0f}/100），冠层光合生产力受到明显限制。"
    elif growth_score < 80:
        growth_desc = f"长势评分中等（{growth_score:.0f}/100），冠层生态存在一定压力。"
    else:
        growth_desc = f"长势评分良好（{growth_score:.0f}/100），冠层光合生产力正常。"

    summary = f"冠层状态：{canopy_status}。GPP 当日 {gpp} gC/m²，{growth_desc}"

    return {
        "title": "BEPS-Lite 冠层生态机理证据",
        "summary": summary,
        "predicts": ["GPP", "NPP", "ET", "碳汇", "长势评分"],
        "key_metrics": {
            "gpp_today": gpp,
            "npp_today": npp,
            "et_today": et,
            "carbon_sink_kgC_mu": carbon_sink,
            "growth_score": round(growth_score, 1),
        },
        "interpretation": (
            f"BEPS-Lite 从冠层生态视角评估咖啡的光合生产力和生态健康。"
            f"当日总初级生产力（GPP）{gpp} gC/m²，净初级生产力（NPP）{npp} gC/m²，"
            f"蒸散发（ET）{et} mm，生态碳汇 {carbon_sink} kgC/亩，"
            f"冠层长势评分 {growth_score:.0f}/100。"
            f"GPP/NPP 下降通常是水分或光照不足的早期预警信号。"
        ),
    }


# ---------------------------------------------------------------------------
# 综合机理解释（三模型互证）
# ---------------------------------------------------------------------------

def _build_integrated_reason(
    apsim: dict,
    hydrus: dict,
    beps: dict,
    risk_level: str,
) -> str:
    water_stress = float(apsim.get("water_stress", 0.0))
    root_uptake = float(hydrus.get("root_uptake_ratio", 0.8))
    stage = apsim.get("stage", "关键生长期")
    nitrogen_status = apsim.get("nitrogen_status", "正常")
    summary_data = beps.get("summary", {})
    growth_score = float(beps.get("growth_score", summary_data.get("growth_score", 75)))
    hydrus_status = hydrus.get("water_status", "")

    # 场景一：水分联合缺水
    if water_stress > 0.3 and root_uptake < 0.6 and ("干旱" in hydrus_status or "偏干" in hydrus_status):
        return (
            f"APSIM 显示咖啡处于「{stage}」水分胁迫升高（{water_stress:.2f}），"
            f"HYDRUS 解析根区土壤水分状态为「{hydrus_status}」、根系吸水效率仅 {root_uptake:.0%}，"
            f"BEPS 监测到冠层长势评分下降至 {growth_score:.0f} 分——"
            f"三模型机理证据共同指向当前主要限制因子是根区缺水，建议优先补灌。"
        )
    # 场景二：氮素偏低 + 土壤偏干
    if nitrogen_status in ("偏低", "不足") and root_uptake < 0.6:
        return (
            f"APSIM 显示氮素状态「{nitrogen_status}」，但 HYDRUS 解析根区水分不足（根系吸水效率 {root_uptake:.0%}）——"
            f"土壤缺水会限制养分溶解和根系吸收，此时直接追肥效果有限。"
            f"建议先补水，待根区水分恢复后再少量追肥。"
        )
    # 场景三：BEPS 长势偏低但水肥正常
    if growth_score < 65 and water_stress < 0.3:
        return (
            f"APSIM 显示水分胁迫较低（{water_stress:.2f}），HYDRUS 显示根区水分基本正常（{root_uptake:.0%}），"
            f"但 BEPS 监测到冠层长势评分偏低（{growth_score:.0f} 分）——"
            f"水肥状态不能完全解释当前长势下降，可能存在遮阴、病虫害或冠层结构问题，建议巡园排查。"
        )
    # 正常情况
    if risk_level == "低":
        return (
            f"APSIM 显示作物生育期正常、水肥胁迫较低，"
            f"HYDRUS 显示根区水分充足（根系吸水效率 {root_uptake:.0%}），"
            f"BEPS 评估冠层长势良好（{growth_score:.0f} 分）——"
            f"三模型机理证据均未发现显著风险，维持当前管理即可。"
        )
    # 通用
    return (
        f"APSIM 评估作物层（水分胁迫 {water_stress:.2f}，生育期「{stage}」），"
        f"HYDRUS 解析土壤层（根系吸水效率 {root_uptake:.0%}），"
        f"BEPS 评价冠层生态（长势评分 {growth_score:.0f}/100）——"
        f"三模型协同判断当前综合风险等级为「{risk_level}」。"
    )


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def build_mechanism_evidence(
    apsim_result: dict,
    hydrus_result: dict,
    beps_result: dict,
    risk_level: str = "低",
) -> dict:
    """
    整合三模型输出，构建结构化机理证据。
    被 fusion_engine.merge() 调用，返回的字典直接嵌入融合结果并透传至前端。

    返回结构：
    {
      "mechanism_explanation": {
        "apsim_evidence": {...},
        "hydrus_evidence": {...},
        "beps_evidence": {...},
        "integrated_reason": "..."
      }
    }
    """
    return {
        "apsim_evidence": _apsim_evidence(apsim_result),
        "hydrus_evidence": _hydrus_evidence(hydrus_result),
        "beps_evidence": _beps_evidence(beps_result),
        "integrated_reason": _build_integrated_reason(
            apsim_result, hydrus_result, beps_result, risk_level
        ),
    }
