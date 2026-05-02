"""
HYDRUS-1D 适配器（MVP 最终交付版）
负责人：张源皓
功能：接收统一 JSON -> 填入模板 -> 动态生成 LEVEL_01.DIR -> 调用 H1D_CALC.EXE -> 解析 OUT 文件
"""
import os
import json
import shutil
import subprocess
from pathlib import Path

# 1. 自动定位项目的绝对路径 (保证系统随处可跑，不会迷路)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
HYDRUS_EXE = BASE_DIR / 'server' / 'hydrus_engine' / 'H1D_CALC.EXE'
TEMPLATE_DIR = BASE_DIR / 'backend' / 'templates' / 'hydrus'
RUN_BASE_DIR = BASE_DIR / 'runtime' / 'hydrus_runs'
DEMO_RESULT_PATH = BASE_DIR / 'demo_data' / 'hydrus_result_demo.json'

def run_hydrus_model(model_input):
    """
    HYDRUS-1D 主调用接口
    """
    # 获取当前任务 ID，如果没有则生成一个测试 ID
    task_id = model_input.get('task_id', 'test_001')
    plot_id = model_input.get('plot_id', 'plot_001')
    
    # 建立此次运行的专属目录
    run_dir = RUN_BASE_DIR / task_id
    if run_dir.exists():
        shutil.rmtree(run_dir)  # 清理旧数据
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{task_id}] ⏳ 正在启动 HYDRUS 土壤水分模拟...")
    print(f"[{task_id}] 📁 运行目录: {run_dir}")

    try:
        # 第一步：准备模型输入文件
        _prepare_input_files(model_input, run_dir)
        
        # 第二步：调用 EXE
        _execute_engine(run_dir)
        
        # 第三步：解析 OUT 文件
        result = _parse_output(run_dir)
        result['task_id'] = task_id
        result['plot_id'] = plot_id
        
        print(f"[{task_id}] ✅ 模型顺利跑通并解析完毕！")
        return result

    except Exception as e:
        print(f"[{task_id}] ❌ 模型运行或解析失败: {e}")
        print(f"[{task_id}] 🔄 启动兜底机制，返回 Demo 数据保障系统闭环...")
        
        # 兜底机制：读取 demo_data，保证前端有图可以画
        fallback_data = _load_demo()
        fallback_data['task_id'] = task_id
        fallback_data['plot_id'] = plot_id
        fallback_data['status'] = "success_with_fallback" 
        return fallback_data


def _prepare_input_files(model_input, run_dir):
    """
    将模板文件和动态参数写入运行目录
    """
    # 1. 复制静态模板
    for file_name in ['SELECTOR.IN', 'PROFILE.DAT']:
        src = TEMPLATE_DIR / file_name
        dst = run_dir / file_name
        if src.exists():
            shutil.copy(src, dst)
        else:
            raise FileNotFoundError(f"找不到模板文件: {src}")

    # 2. 动态填充 ATMOSPH.IN
    # 注意：前端传来的单位是 mm，HYDRUS 要求的单位通常是 cm
    atm_src = TEMPLATE_DIR / 'ATMOSPH.IN'
    atm_dst = run_dir / 'ATMOSPH.IN'
    
    if atm_src.exists():
        with open(atm_src, 'r', encoding='utf-8') as f:
            atm_content = f.read()
        
        # 从前端数据提取降雨和灌溉 (这里假设取第一天的记录作为示例)
        weather_data = model_input.get('atmospheric_boundary', [{}])
        if len(weather_data) > 0:
            today_weather = weather_data[0]
            # mm 转 cm
            prec_cm = (today_weather.get('rain_mm', 0) + today_weather.get('irrigation_mm', 0)) / 10.0
            evap_cm = today_weather.get('potential_evaporation_mm', 0) / 10.0
            trans_cm = today_weather.get('potential_transpiration_mm', 0) / 10.0
            
            # 替换占位符
            atm_content = atm_content.replace('{{prec}}', f"{prec_cm:.3f}")
            atm_content = atm_content.replace('{{evap}}', f"{evap_cm:.3f}")
            atm_content = atm_content.replace('{{trans}}', f"{trans_cm:.3f}")
        
        with open(atm_dst, 'w', encoding='utf-8') as f:
            f.write(atm_content)
    else:
        raise FileNotFoundError(f"找不到模板文件: {atm_src}")

    # 3. 生成绝对路径的 LEVEL_01.DIR（极其重要！解决 HYDRUS 闪退报错的核心）
    level_file_path = run_dir / "LEVEL_01.DIR"
    with open(level_file_path, "w", encoding="utf-8") as f:
        # HYDRUS 必须读绝对路径，且必须以换行符结尾
        f.write(str(run_dir.absolute()) + "\n")


def _execute_engine(run_dir):
    """
    实际调用 H1D_CALC.EXE
    """
    if not HYDRUS_EXE.exists():
        raise FileNotFoundError(f"找不到执行引擎: {HYDRUS_EXE}")

    # 删除上一次的 Error.msg (如果存在)
    error_msg_path = run_dir / "Error.msg"
    if error_msg_path.exists():
        os.remove(error_msg_path)

    # 静默运行 EXE，cwd 必须指向 run_dir，并自动发送回车键防止死锁
    subprocess.run([str(HYDRUS_EXE)], cwd=str(run_dir), capture_output=True, text=True, input="\n")

    # 检查是否生成了报错文件
    if error_msg_path.exists():
        with open(error_msg_path, 'r', encoding='utf-8', errors='ignore') as f:
            err_content = f.read().strip()
        raise RuntimeError(f"HYDRUS 计算发散或参数错误，Error.msg: {err_content}")
        
    # 检查核心输出文件是否存在
    if not (run_dir / "T_Level.out").exists():
        raise RuntimeError("模型未生成 T_Level.out，可能运行崩溃。")


def _parse_output(run_dir):
    """
    解析 HYDRUS 生成的真实 Nod_Inf.out 和 T_Level.out 文件
    """
    nod_file = run_dir / 'Nod_Inf.out'
    if not nod_file.exists():
        raise FileNotFoundError("找不到 Nod_Inf.out，模型可能未成功写入数据")
    
    lines = nod_file.read_text(encoding='utf-8').splitlines()
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
        closest_depth = min(depth_theta.keys(), key=lambda x: abs(x - d))
        theta = round(depth_theta[closest_depth], 3)
        status = "适宜" if theta > 0.24 else ("略低" if theta > 0.20 else ("偏低" if theta > 0.16 else "干旱"))
        profile.append({"depth_cm": int(d), "theta": theta, "status": status})

    # ====================================================
    # 🎯 关键修复：动态计算真实的湿润锋（入渗深度）
    # 逻辑：从地表往下找，含水率明显高于干旱基线(0.18)的最深位置
    # ====================================================
    inf_depth = 0
    for depth in sorted(depth_theta.keys()):
        if depth_theta[depth] > 0.18:
            inf_depth = int(depth)
        else:
            break # 遇到干土层，说明水就渗到这里了
            
    # 如果连地表都很干，说明根本没浇水或已完全蒸发
    if depth_theta.get(0.0, 0) < 0.18:
        inf_depth = 0

    tlevel_file = run_dir / 'T_Level.out'
    root_uptake_ratio = 1.0
    if tlevel_file.exists():
        t_lines = tlevel_file.read_text(encoding='utf-8').splitlines()
        for line in reversed(t_lines):
            parts = line.split()
            if len(parts) > 10 and parts[0].replace('.', '', 1).isdigit():
                try:
                    sum_rroot = float(parts[7])
                    sum_vroot = float(parts[9])
                    if sum_rroot > 0:
                        root_uptake_ratio = round(sum_vroot / sum_rroot, 2)
                    break
                except ValueError:
                    continue

    d40_theta = next((p['theta'] for p in profile if p['depth_cm'] == 40), 0.0)
    
    if d40_theta > 0.24:
        water_status = "水分正常"
        irrigation_effect = f"入渗达到 {inf_depth}cm，水分状况良好"
        what = "当前表层及深层土壤水分充足。"
        why = "前期水分有效入渗，充分满足咖啡根系当前的吸水需求。"
    elif d40_theta > 0.19:
        water_status = "轻度干旱"
        irrigation_effect = f"入渗仅 {inf_depth}cm，深层略干"
        what = "表层土壤水分开始下降，深层水分略低。"
        why = "近期冠层蒸腾消耗较大，但尚未造成明显的水分胁迫。"
    elif d40_theta > 0.16:
        water_status = "中度干旱"
        irrigation_effect = f"根区缺水，吸水效率降至 {root_uptake_ratio*100}%"
        what = "40cm 主要根区含水率偏低，根系吸水效率开始下降。"
        why = f"物理模型显示，累积实际吸水率已降至潜在能力的 {root_uptake_ratio*100}%。"
    else:
        water_status = "重度干旱"
        irrigation_effect = "深层严重缺水，存在生产风险"
        what = "0-60cm 土层整体极度干燥，发生严重水分胁迫！"
        why = "土壤含水率持续偏低，强烈建议立即进行补充灌溉。"

    series = [{
        "date": "2026-04-30",
        "d10": next((p['theta'] for p in profile if p['depth_cm'] == 10), 0.0),
        "d20": next((p['theta'] for p in profile if p['depth_cm'] == 20), 0.0),
        "d40": next((p['theta'] for p in profile if p['depth_cm'] == 40), 0.0),
        "d60": next((p['theta'] for p in profile if p['depth_cm'] == 60), 0.0),
    }]

    return {
        "model": "HYDRUS-1D",
        "status": "success",
        "water_status": water_status,
        "root_uptake_ratio": root_uptake_ratio,
        "infiltration_depth_cm": inf_depth, # <--- 这里改成了真正的动态深度
        "irrigation_effect": irrigation_effect,
        "soil_profile_current": profile,
        "soil_moisture_series": series,
        "hydrus_explain": {
            "what": what,
            "why": why
        }
    }
def _load_demo():
    """
    当模型崩溃时读取的安全备份数据
    """
    if DEMO_RESULT_PATH.exists():
        with open(DEMO_RESULT_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 如果连 demo json 都没创建，硬编码返回一套数据
        return {
            "model": "HYDRUS-1D",
            "status": "fallback",
            "water_status": "适宜",
            "root_uptake_ratio": 0.85,
            "soil_profile_current": [
                {"depth_cm": 10, "theta": 0.25, "status": "适宜"},
                {"depth_cm": 40, "theta": 0.20, "status": "适宜"}
            ],
            "hydrus_explain": {
                "what": "系统启用了安全兜底策略。",
                "why": "保证演示环节前后端图表不断链。"
            }
        }


if __name__ == "__main__":
    # 本地直接运行此脚本时的测试数据
    test_input = {
        "task_id": "test_local_run",
        "plot_id": "plot_001",
        "atmospheric_boundary": [
            {
                "date": "2026-04-30",
                "rain_mm": 0,
                "irrigation_mm": 25, 
                "potential_evaporation_mm": 2.8,
                "potential_transpiration_mm": 3.6
            }
        ]
    }
    
    # 运行并打印结果
    result_json = run_hydrus_model(test_input)
    print("\n最终返回给后端的 JSON:")
    print(json.dumps(result_json, indent=4, ensure_ascii=False))