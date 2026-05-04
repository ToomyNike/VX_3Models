"""
AI 农技建议服务 —— 智谱 GLM-4-Flash（完全免费）
- 一次性建议：generate_advice()，供 model_api.py 调用
- 多轮聊天：chat_with_context()，供 advice_api.py 的 /chat 接口调用

配置方式：
  backend/.env 文件中写入：ZHIPU_API_KEY=你的Key
  或环境变量：set ZHIPU_API_KEY=xxx

注册地址：https://open.bigmodel.cn  （GLM-4-Flash 完全免费）
"""
import json
import os
import re
from typing import List

import requests

_ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
_MODEL = "glm-4-flash"


# ---------------------------------------------------------------------------
# API Key 读取
# ---------------------------------------------------------------------------

def _load_api_key() -> str:
    key = os.getenv("ZHIPU_API_KEY", "")
    if key:
        return key
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ZHIPU_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return ""


# ---------------------------------------------------------------------------
# 系统提示：将三模型结果注入 System Message，整个对话共享
# ---------------------------------------------------------------------------

def build_system_prompt(apsim: dict, hydrus: dict, beps: dict) -> str:
    return f"""你是一位专业的云南咖啡种植 AI 农技顾问，精通 APSIM 作物模型、HYDRUS 土壤水分模型和 BEPS 生态模型。
用户的咖啡园当前三模型模拟结果如下，请基于这些数据回答用户的所有问题：

【APSIM-Coffee 作物生长模型】
- 生育期：{apsim.get("stage", "-")}
- 预测亩产：{apsim.get("yield_pred_kg_mu", "-")} kg/亩
- 水分胁迫指数：{apsim.get("water_stress", "-")}（0=无胁迫，1=严重）
- 氮素状态：{apsim.get("nitrogen_status", "正常")}
- 叶面积指数 LAI：{apsim.get("lai", "-")}

【HYDRUS-1D 土壤水分模型】
- 土壤水分状态：{hydrus.get("water_status", "-")}
- 根系吸水效率：{hydrus.get("root_uptake_ratio", "-")}
- 入渗深度：{hydrus.get("infiltration_depth_cm", "-")} cm

【BEPS-Lite 生态模型】
- 长势评分：{beps.get("growth_score", "-")}/100
- 生态风险：{beps.get("beps_risk", "-")}
- GPP：{beps.get("gpp_today", "-")} gC/m²/天
- NPP：{beps.get("npp_today", "-")} gC/m²/天
- 冠层状态：{beps.get("canopy_status", "-")}

请用简洁、专业、接地气的语言回答，每条建议控制在100字以内。"""


# ---------------------------------------------------------------------------
# LLM 调用（通用，接受完整 messages 列表）
# ---------------------------------------------------------------------------

def _call_glm(messages: List[dict], api_key: str) -> str:
    resp = requests.post(
        _ZHIPU_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": _MODEL, "messages": messages, "temperature": 0.5, "max_tokens": 400},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# 一次性建议（保持原有签名，model_api.py 不用改）
# ---------------------------------------------------------------------------

def generate_advice(apsim_result: dict, hydrus_result: dict, beps_result: dict) -> dict:
    api_key = _load_api_key()
    if api_key:
        try:
            system = build_system_prompt(apsim_result, hydrus_result, beps_result)
            user_msg = ("请用 what/how/why 三段式给出当前咖啡园最重要的一条农技建议，"
                        "严格按照如下 JSON 格式输出，不要输出 JSON 以外的内容：\n"
                        '{"what":"当前状态（30字）","how":"具体操作建议（50字）","why":"模型依据（50字）"}')
            content = _call_glm(
                [{"role": "system", "content": system},
                 {"role": "user",   "content": user_msg}],
                api_key,
            )
            match = re.search(r"\{[\s\S]*?\}", content)
            if match:
                advice = json.loads(match.group())
                for f in ("what", "how", "why"):
                    advice.setdefault(f, "-")
                advice["source"] = "glm-4-flash"
                return advice
        except Exception as e:
            print(f"[LLM] GLM 调用失败（{e}），使用规则兜底")

    return _rule_fallback(apsim_result, hydrus_result, beps_result)


# ---------------------------------------------------------------------------
# 多轮聊天（供 /api/advice/chat 接口调用）
# ---------------------------------------------------------------------------

def chat_with_context(
    user_message: str,
    history: List[dict],          # [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}]
    apsim_result: dict,
    hydrus_result: dict,
    beps_result: dict,
) -> str:
    api_key = _load_api_key()
    if not api_key:
        return "AI 服务未配置，请在后端 .env 文件中填写 ZHIPU_API_KEY。"

    system = build_system_prompt(apsim_result, hydrus_result, beps_result)
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        return _call_glm(messages, api_key)
    except Exception as e:
        return f"AI 回复失败（{e}），请稍后重试。"


# ---------------------------------------------------------------------------
# 规则兜底
# ---------------------------------------------------------------------------

def _rule_fallback(apsim: dict, hydrus: dict, beps: dict) -> dict:
    stage = apsim.get("stage", "关键生长期")
    water_status = hydrus.get("water_status", "")
    nitrogen_status = apsim.get("nitrogen_status", "正常")
    growth_score = beps.get("growth_score", 75)

    if "干旱" in water_status or float(apsim.get("water_stress", 0)) > 0.3:
        how = "建议未来2天内补充滴灌，优先保证40cm以下根区水分，施肥暂缓。"
    elif nitrogen_status in ("偏低", "不足"):
        how = "建议本周安排少量追肥，浇水后观察长势变化。"
    else:
        how = "维持当前管理节奏，继续记录灌溉、施肥和异常情况。"

    return {
        "what": f"当前处于{stage}，综合长势{growth_score}分，{water_status or '水分正常'}。",
        "how": how,
        "why": "APSIM 判断生育期与水肥胁迫，HYDRUS 解析根区水分，BEPS 评估冠层生态状态。",
        "source": "rule_fallback",
    }
