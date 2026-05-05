"""
HYDRUS-1D 适配器（集成版）
原始实现：张源皓（zyh）
集成适配：蔡济远

功能：
  1. 将主系统统一 model_input_json 转换为 HYDRUS 所需的 atmospheric_boundary 格式
  2. 调用 H1D_CALC.EXE 真实物理引擎
  3. 解析 Nod_Inf.out / T_Level.out 输出文件
  4. 任意环节失败时自动 fallback 到 demo_data，保证前端链路不断
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from config import HYDRUS_EXE, HYDRUS_RUN_DIR, DEMO_DATA_DIR
from services.unit_convert import normalize_irrigation_mm


# HYDRUS 模板目录（从主系统 backend/templates/hydrus/ 读取）
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "hydrus"
_DEMO_RESULT_PATH = DEMO_DATA_DIR / "hydrus_result_demo.json"


# ---------------------------------------------------------------------------
# 输入格式转换层：把主系统 model_input_json → atmospheric_boundary
# ---------------------------------------------------------------------------

def _build_atmospheric_boundary(model_input_json):
    """
    将主系统的农事操作列表转换为 HYDRUS 需要的大气边界条件格式。
    主系统：farm_operations[{op_type, amount, unit, date}]
    HYDRUS：atmospheric_boundary[{rain_mm, irrigation_mm, potential_evaporation_mm, ...}]
    """
    irrigation_mm = 0.0
    for op in model_input_json.get("farm_operations", []):
        if op.get("op_type") == "irrigation":
            irrigation_mm += normalize_irrigation_mm(op.get("amount"), op.get("unit"))

    # 叠加情景额外灌溉
    irrigation_mm += float(
        model_input_json.get("scenario", {}).get("extra_irrigation_mm", 0) or 0
    )

    # 从 weather_series 取第一条降雨
    rain_mm = 0.0
    for w in model_input_json.get("weather_series", []):
        rain_mm = float(w.get("rain_mm", w.get("rain", 0)) or 0)
        break

    return [
        {
            "date": str(model_input_json.get("task_id", "2026-01-01"))[:10],
            "rain_mm": rain_mm,
            "irrigation_mm": irrigation_mm,
            "potential_evaporation_mm": 2.8,
            "potential_transpiration_mm": 3.6,
        }
    ]


# ---------------------------------------------------------------------------
# 文件准备
# ---------------------------------------------------------------------------

def _prepare_input_files(model_input, run_dir):
    """将模板文件和动态参数写入运行目录"""
    # 1. 复制静态模板
    for file_name in ["SELECTOR.IN", "PROFILE.DAT"]:
        src = _TEMPLATE_DIR / file_name
        dst = run_dir / file_name
        if src.exists():
            shutil.copy(src, dst)
        else:
            raise FileNotFoundError(f"找不到模板文件: {src}")

    # 2. 动态填充 ATMOSPH.IN
    atm_src = _TEMPLATE_DIR / "ATMOSPH.IN"
    atm_dst = run_dir / "ATMOSPH.IN"

    if atm_src.exists():
        with open(atm_src, "r", encoding="utf-8") as f:
            atm_content = f.read()

        weather_data = model_input.get("atmospheric_boundary", [{}])
        if weather_data:
            today = weather_data[0]
            # mm → cm（HYDRUS 内部单位为 cm）
            prec_cm = (today.get("rain_mm", 0) + today.get("irrigation_mm", 0)) / 10.0
            evap_cm = today.get("potential_evaporation_mm", 0) / 10.0
            trans_cm = today.get("potential_transpiration_mm", 0) / 10.0

            atm_content = atm_content.replace("{{prec}}", f"{prec_cm:.3f}")
            atm_content = atm_content.replace("{{evap}}", f"{evap_cm:.3f}")
            atm_content = atm_content.replace("{{trans}}", f"{trans_cm:.3f}")

        with open(atm_dst, "w", encoding="utf-8") as f:
            f.write(atm_content)
    else:
        raise FileNotFoundError(f"找不到模板文件: {atm_src}")

    # 3. 生成绝对路径的 LEVEL_01.DIR（核心！解决 HYDRUS EXE 闪退的关键）
    level_file_path = run_dir / "LEVEL_01.DIR"
    with open(level_file_path, "w", encoding="utf-8") as f:
        f.write(str(run_dir.absolute()) + "\n")


# ---------------------------------------------------------------------------
# 引擎调用
# ---------------------------------------------------------------------------

def _execute_engine(run_dir):
    """调用 H1D_CALC.EXE"""
    if not HYDRUS_EXE.exists():
        raise FileNotFoundError(f"找不到 HYDRUS 执行引擎: {HYDRUS_EXE}")

    # 删除上一次的 Error.msg
    error_msg_path = run_dir / "Error.msg"
    if error_msg_path.exists():
        os.remove(error_msg_path)

    # 静默运行，自动发送回车防止死锁
    subprocess.run(
        [str(HYDRUS_EXE)],
        cwd=str(run_dir),
        capture_output=True,
        text=True,
        input="\n",
    )

    if error_msg_path.exists():
        with open(error_msg_path, "r", encoding="utf-8", errors="ignore") as f:
            err_content = f.read().strip()
        raise RuntimeError(f"HYDRUS 计算失败，Error.msg: {err_content}")

    if not (run_dir / "T_Level.out").exists():
        raise RuntimeError("模型未生成 T_Level.out，可能运行崩溃。")


# ---------------------------------------------------------------------------
# 输出解析
# ---------------------------------------------------------------------------

def _parse_output(run_dir):
    """解析 HYDRUS 生成的 Nod_Inf.out 和 T_Level.out"""
    nod_file = run_dir / "Nod_Inf.out"
    if not nod_file.exists():
        raise FileNotFoundError("找不到 Nod_Inf.out，模型可能未成功写入数据")

    lines = nod_file.read_text(encoding="utf-8").splitlines()
    depth_theta = {}
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            try:
                depth = abs(float(parts[1]))
                theta = float(parts[3])
                depth_theta[depth] = theta
            except ValueError:
                continue

    if not depth_theta:
        raise RuntimeError("Nod_Inf.out 数据格式异常")

    target_depths = [10.0, 20.0, 40.0, 60.0, 100.0]
    profile = []
    for d in target_depths:
        closest = min(depth_theta.keys(), key=lambda x: abs(x - d))
        theta = round(depth_theta[closest], 3)
        status = (
            "适宜" if theta > 0.24
            else "略低" if theta > 0.20
            else "偏低" if theta > 0.16
            else "干旱"
        )
        profile.append({"depth_cm": int(d), "theta": theta, "status": status})

    # 动态计算湿润锋（入渗深度）
    inf_depth = 0
    for depth in sorted(depth_theta.keys()):
        if depth_theta[depth] > 0.18:
            inf_depth = int(depth)
        else:
            break
    if depth_theta.get(0.0, 0) < 0.18:
        inf_depth = 0

    # 解析根系吸水效率
    tlevel_file = run_dir / "T_Level.out"
    root_uptake_ratio = 1.0
    if tlevel_file.exists():
        t_lines = tlevel_file.read_text(encoding="utf-8").splitlines()
        for line in reversed(t_lines):
            parts = line.split()
            if len(parts) > 10 and parts[0].replace(".", "", 1).isdigit():
                try:
                    sum_rroot = float(parts[7])
                    sum_vroot = float(parts[9])
                    if sum_rroot > 0:
                        root_uptake_ratio = round(sum_vroot / sum_rroot, 2)
                    break
                except ValueError:
                    continue

    # 判断水分状态与解释
    d40 = next((p["theta"] for p in profile if p["depth_cm"] == 40), 0.0)
    if d40 > 0.24:
        water_status = "水分适宜"
        irrigation_effect = f"入渗达到 {inf_depth}cm，水分状况良好"
        what = "当前表层及深层土壤水分充足。"
        why = "前期水分有效入渗，充分满足咖啡根系当前的吸水需求。"
    elif d40 > 0.19:
        water_status = "轻度偏干"
        irrigation_effect = f"入渗仅 {inf_depth}cm，深层略干"
        what = "表层土壤水分开始下降，深层水分略低。"
        why = "近期冠层蒸腾消耗较大，但尚未造成明显的水分胁迫。"
    elif d40 > 0.16:
        water_status = "中度干旱"
        irrigation_effect = f"根区缺水，吸水效率降至 {root_uptake_ratio * 100:.0f}%"
        what = "40cm 主要根区含水率偏低，根系吸水效率开始下降。"
        why = f"物理模型显示累积实际吸水率已降至潜在能力的 {root_uptake_ratio * 100:.0f}%。"
    else:
        water_status = "重度干旱"
        irrigation_effect = "深层严重缺水，存在生产风险"
        what = "0-60cm 土层整体极度干燥，发生严重水分胁迫！"
        why = "土壤含水率持续偏低，强烈建议立即进行补充灌溉。"

    series = [
        {
            "date": "today",
            "d10": next((p["theta"] for p in profile if p["depth_cm"] == 10), 0.0),
            "d20": next((p["theta"] for p in profile if p["depth_cm"] == 20), 0.0),
            "d40": next((p["theta"] for p in profile if p["depth_cm"] == 40), 0.0),
            "d60": next((p["theta"] for p in profile if p["depth_cm"] == 60), 0.0),
        }
    ]

    return {
        "model": "HYDRUS-1D",
        "status": "success",
        "water_status": water_status,
        "root_uptake_ratio": root_uptake_ratio,
        "infiltration_depth_cm": inf_depth,
        "irrigation_effect": irrigation_effect,
        "soil_profile_current": profile,
        "soil_moisture_series": series,
        "hydrus_explain": {"what": what, "why": why},
    }


# ---------------------------------------------------------------------------
# 兜底 demo 数据
# ---------------------------------------------------------------------------

def _load_demo():
    if _DEMO_RESULT_PATH.exists():
        with open(_DEMO_RESULT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "model": "HYDRUS-1D",
        "status": "fallback",
        "water_status": "水分适宜",
        "root_uptake_ratio": 0.85,
        "infiltration_depth_cm": 35,
        "irrigation_effect": "灌溉主要补充 0-40cm 土层",
        "soil_profile_current": [
            {"depth_cm": 10, "theta": 0.27, "status": "适宜"},
            {"depth_cm": 20, "theta": 0.25, "status": "适宜"},
            {"depth_cm": 40, "theta": 0.22, "status": "略低"},
            {"depth_cm": 60, "theta": 0.19, "status": "略低"},
            {"depth_cm": 100, "theta": 0.16, "status": "偏低"},
        ],
        "soil_moisture_series": [
            {"date": "today", "d10": 0.27, "d20": 0.25, "d40": 0.22, "d60": 0.19}
        ],
        "hydrus_explain": {
            "what": "系统启用了安全兜底策略。",
            "why": "保证演示环节前后端图表不断链。",
        },
    }


# ---------------------------------------------------------------------------
# 主入口（与主系统 model_api.py 的调用签名保持一致）
# ---------------------------------------------------------------------------

def run_hydrus_model(model_input_json):
    # AI辅助生成-DeepSeek-V3 - 2026年4月26日 09:22:15 - HYDRUS-1D模型调用与土壤水分状态解析
    """
    HYDRUS-1D 主调用接口。
    接收主系统标准 model_input_json，内部自动转换为 HYDRUS 格式。
    """
    task_id = model_input_json.get("task_id", "task_demo")
    plot_id = model_input_json.get("plot_id", "plot_001")

    run_dir = HYDRUS_RUN_DIR / task_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # 转换主系统输入格式 → HYDRUS atmospheric_boundary 格式
    hydrus_input = {
        "task_id": task_id,
        "plot_id": plot_id,
        "atmospheric_boundary": _build_atmospheric_boundary(model_input_json),
    }

    try:
        _prepare_input_files(hydrus_input, run_dir)
        _execute_engine(run_dir)
        result = _parse_output(run_dir)
    except Exception as e:
        print(f"[HYDRUS][{task_id}] 运行失败: {e}，启动兜底机制")
        result = _load_demo()
        result["status"] = "success_with_fallback"
        result["hydrus_error"] = str(e)

    result["task_id"] = task_id
    result["plot_id"] = plot_id

    # 写入运行目录留档
    (run_dir / "hydrus_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
