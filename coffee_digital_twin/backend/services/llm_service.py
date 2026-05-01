def generate_advice(apsim_result, hydrus_result, beps_result):
    stage = apsim_result.get("stage", "关键生长期")
    water_status = hydrus_result.get("water_status", "土壤水分正常")
    nitrogen_status = apsim_result.get("nitrogen_status", "正常")
    growth_score = beps_result.get("growth_score", 75)

    if "干旱" in water_status or float(apsim_result.get("water_stress", 0)) > 0.3:
        how = "建议未来2天内补充滴灌，优先保证40cm以下根区水分，施肥暂缓。"
    elif nitrogen_status in ["偏低", "不足"]:
        how = "建议本周安排一次少量追肥，并在浇水后观察长势变化。"
    else:
        how = "建议维持当前管理节奏，继续记录灌溉、施肥和异常情况。"

    return {
        "what": f"当前咖啡处于{stage}，综合长势评分约为{growth_score}分，{water_status}。",
        "how": how,
        "why": "APSIM用于判断生育期、产量和水肥胁迫，HYDRUS用于解释土壤剖面水分与根系吸水，BEPS用于补充冠层生产力和生态风险。",
    }
