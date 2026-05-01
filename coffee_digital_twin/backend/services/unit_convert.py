def ton_per_mu_to_mm(value):
    return float(value or 0) * 1.5


def kg_mu_to_kg_ha(value):
    return float(value or 0) * 15


def kg_ha_to_kg_mu(value):
    return float(value or 0) / 15


def normalize_irrigation_mm(amount, unit):
    unit = (unit or "mm").lower()
    if unit in ["吨/亩", "t/mu", "ton/mu", "tons/mu"]:
        return ton_per_mu_to_mm(amount)
    return float(amount or 0)


def normalize_fertilizer_kg_ha(amount, unit):
    unit = (unit or "kg/mu").lower()
    if unit in ["kg/ha", "公斤/公顷"]:
        return float(amount or 0)
    return kg_mu_to_kg_ha(amount)
