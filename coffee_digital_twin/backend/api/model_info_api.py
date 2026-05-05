"""
模型说明接口
GET /api/model/info             —— 返回 APSIM / HYDRUS / BEPS 三模型的功能说明
GET /api/model/validation_cases —— 返回示范验证案例
"""
import json
import os

from flask import Blueprint, jsonify

model_info_bp = Blueprint("model_info_api", __name__, url_prefix="/api/model")

_DEMO_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "demo_data")

_MODEL_INFO = {
    "apsim": {
        "name": "APSIM-Coffee",
        "full_name": "Agricultural Production Systems sIMulator (Coffee)",
        "layer": "作物生长层",
        "predicts": ["生育期", "产量趋势", "水分胁迫指数", "氮素状态", "叶面积指数(LAI)"],
        "explains": (
            "APSIM-Coffee 模拟咖啡从种植到采收的完整生育期动态，"
            "判断当前处于哪个生育阶段（营养生长期、花芽分化期、果实膨大期等），"
            "预测产量趋势，并量化水分胁迫和氮素状态对产量形成的影响。"
            "当水分胁迫指数升高时，说明作物已感受到水分压力，产量形成面临风险。"
        ),
        "icon": "🌱",
    },
    "hydrus": {
        "name": "HYDRUS-1D",
        "full_name": "Hydrological Research Unit Soil Water Flow Model",
        "layer": "土壤水分层",
        "predicts": ["土壤剖面含水率", "灌溉水入渗深度", "根系吸水效率"],
        "explains": (
            "HYDRUS-1D 模拟水分在土壤剖面中的运动过程，"
            "解释灌溉水能入渗多深、主根区（20-60 cm）是否缺水、"
            "以及根系是否真正吸收到了足够的水分。"
            "这能区分'表层湿润'和'根区供水充足'两种不同情况，"
            "避免因表层假湿而忽略深层根区缺水的风险。"
        ),
        "icon": "💧",
    },
    "beps": {
        "name": "BEPS-Lite",
        "full_name": "Boreal Ecosystem Productivity Simulator (Lite)",
        "layer": "冠层生态层",
        "predicts": ["总初级生产力(GPP)", "净初级生产力(NPP)", "蒸散发(ET)", "生态碳汇", "长势评分"],
        "explains": (
            "BEPS-Lite 从冠层生态视角评估咖啡的光合生产力和生态健康状态。"
            "GPP（总初级生产力）反映冠层整体光合能力，"
            "GPP/NPP 下降通常是水分或光照不足的早期预警信号。"
            "长势评分综合了 GPP、ET 等指标，直观反映咖啡园当前的生长状态。"
            "若长势评分下降而水肥正常，则提示可能存在遮阴、病虫害等非水肥因素。"
        ),
        "icon": "🌳",
    },
}

@model_info_bp.get("/info")
def get_model_info():
    """
    返回三模型功能说明。
    供前端"模型说明"区域静态展示，也可在答辩时演示。
    """
    return jsonify({
        "status": "success",
        "system_name": "面向云南小粒咖啡的多机理模型（APSIM/HYDRUS/BEPS）协同智能决策系统",
        "models": _MODEL_INFO,
    })


@model_info_bp.get("/validation_cases")
def get_validation_cases():
    """
    返回示范验证案例（来自 demo_data/validation_cases.json）。
    供前端结果页展示"典型情景 × 机理证据 × 系统判断"的一致性验证。
    """
    cases_file = os.path.join(_DEMO_DATA_DIR, "validation_cases.json")
    try:
        with open(cases_file, "r", encoding="utf-8") as f:
            cases = json.load(f)
        return jsonify(cases)
    except FileNotFoundError:
        return jsonify([])

