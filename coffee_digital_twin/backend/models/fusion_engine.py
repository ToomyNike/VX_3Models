from services.llm_service import generate_advice
from services.risk_service import combine_risk


def merge(apsim_result, hydrus_result, beps_result, task_id=None, plot_id=None):
    risk_level = combine_risk(apsim_result, hydrus_result, beps_result)
    advice = generate_advice(apsim_result, hydrus_result, beps_result)

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
        "apsim": apsim_result,
        "hydrus": hydrus_result,
        "beps": beps_result,
        "advice": advice,
    }
