from flask import Flask, request, jsonify, render_template
from services.result_service import get_latest_beps_result, list_beps_results
from services.model_runner import run_beps_lite_task
from services.fusion_engine import fuse_model_results
from services.scenario_service import compare_beps_scenarios

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "Coffee Digital Twin Backend is running",
        "modules": [
            "APSIM-Coffee",
            "HYDRUS-1D",
            "BEPS-Lite"
        ]
    })


@app.route("/api/beps-lite/run", methods=["POST"])
def api_run_beps_lite():
    """
    单独运行 BEPS-Lite。
    小程序或测试工具可以调用这个接口。
    """
    payload = request.get_json(force=True)
    result = run_beps_lite_task(payload)
    return jsonify(result)


@app.route("/api/model/fuse-demo", methods=["POST"])
def api_fuse_demo():
    """
    演示三模型融合。
    当前 APSIM 和 HYDRUS 可以先用前端传入的模拟结果。
    """
    payload = request.get_json(force=True)

    apsim_result = payload.get("apsim_result", {
        "stage": "果实膨大期",
        "yield_prediction": 1350,
        "lai": 2.8,
        "water_stress": 0.65,
        "nitrogen_stress": 0.35
    })

    hydrus_result = payload.get("hydrus_result", {
        "root_uptake_efficiency": 0.45,
        "infiltration_depth_cm": 35
    })

    beps_payload = dict(payload)
    beps_payload["apsim_result"] = apsim_result
    beps_payload["hydrus_result"] = hydrus_result

    beps_result = run_beps_lite_task(beps_payload)

    fused_result = fuse_model_results(
        apsim_result=apsim_result,
        hydrus_result=hydrus_result,
        beps_result=beps_result
    )

    return jsonify({
        "apsim_result": apsim_result,
        "hydrus_result": hydrus_result,
        "beps_result": beps_result,
        "fused_result": fused_result
    })

@app.route("/api/beps-lite/latest", methods=["GET"])
def api_get_latest_beps_result():
    """
    获取最近一次 BEPS-Lite 运行结果。
    """
    result = get_latest_beps_result()
    return jsonify(result)


@app.route("/api/beps-lite/history", methods=["GET"])
def api_get_beps_history():
    """
    获取 BEPS-Lite 历史结果文件列表。
    """
    limit = request.args.get("limit", default=10, type=int)
    result = list_beps_results(limit=limit)

    return jsonify({
        "status": "ok",
        "count": len(result),
        "results": result
    })

@app.route("/api/beps-lite/scenario-compare", methods=["POST"])
def api_beps_scenario_compare():
    """
    BEPS-Lite 多情景模拟对比。
    """
    payload = request.get_json(force=True)
    result = compare_beps_scenarios(payload)
    return jsonify(result)

@app.route("/beps-dashboard", methods=["GET"])
def beps_dashboard():
    return render_template("beps_dashboard.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)