RISK_ORDER = {"低": 1, "中等": 2, "高": 3}


def combine_risk(apsim_result, hydrus_result, beps_result):
    risks = []

    water_stress = float(apsim_result.get("water_stress", 0))
    if water_stress >= 0.5:
        risks.append("高")
    elif water_stress >= 0.28:
        risks.append("中等")
    else:
        risks.append("低")

    hydrus_status = hydrus_result.get("water_status", "")
    if "重度" in hydrus_status or "严重" in hydrus_status:
        risks.append("高")
    elif "中度" in hydrus_status or "偏干" in hydrus_status:
        risks.append("中等")
    else:
        risks.append("低")

    beps_risk = beps_result.get("beps_risk", "低")
    risks.append(beps_risk if beps_risk in RISK_ORDER else "低")

    return max(risks, key=lambda item: RISK_ORDER[item])
