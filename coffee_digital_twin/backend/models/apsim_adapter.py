import json
import csv
import shutil
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from config import APSIM_EXE, APSIM_RUN_DIR, BASE_DIR
from services.unit_convert import normalize_fertilizer_kg_ha, normalize_irrigation_mm


APSIM_TEMPLATE = BASE_DIR / "templates" / "apsim" / "apsim_coffee_template.apsimx"


def _to_float(value, default=0):
    try:
        if value in [None, ""]:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, low, high):
    return max(low, min(high, value))


def _parse_date(value, default=None):
    if isinstance(value, date):
        return value
    if not value:
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return default


def _walk_nodes(node):
    if isinstance(node, dict):
        yield node
        for child in node.get("Children", []) or []:
            yield from _walk_nodes(child)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_nodes(item)


def _find_node(data, name=None, type_contains=None):
    for node in _walk_nodes(data):
        if name and node.get("Name") == name:
            return node
        if type_contains and type_contains in node.get("$type", ""):
            return node
    return None


def _set_manager_parameter(manager, key, value):
    params = manager.setdefault("Parameters", [])
    for item in params:
        if item.get("Key") == key:
            item["Value"] = str(value)
            return
    params.append({"Key": key, "Value": str(value)})


def _sum_management(model_input_json):
    irrigation_mm = 0
    fertilizer_kg_ha = 0
    for op in model_input_json.get("farm_operations", []):
        op_type = op.get("op_type")
        if op_type == "irrigation":
            irrigation_mm += normalize_irrigation_mm(op.get("amount"), op.get("unit"))
        if op_type == "fertilization":
            fertilizer_kg_ha += normalize_fertilizer_kg_ha(op.get("amount"), op.get("unit"))

    scenario = model_input_json.get("scenario", {})
    irrigation_mm += float(scenario.get("extra_irrigation_mm", 0) or 0)
    fertilizer_kg_ha += normalize_fertilizer_kg_ha(
        scenario.get("extra_fertilizer_kg_mu", 0), "kg/mu"
    )
    return irrigation_mm, fertilizer_kg_ha


def _simulation_window(model_input_json):
    plot = model_input_json.get("plot_info", {})
    tree_age = int(_to_float(plot.get("tree_age"), 4))
    effective_age = max(5, min(tree_age, 12))

    dates = []
    for item in model_input_json.get("weather_series", []):
        parsed = _parse_date(item.get("date"))
        if parsed:
            dates.append(parsed)
    for op in model_input_json.get("farm_operations", []):
        parsed = _parse_date(op.get("date") or op.get("op_date"))
        if parsed:
            dates.append(parsed)

    anchor = max(dates) if dates else date.today()
    start_year = anchor.year - effective_age
    start_date = date(start_year, 1, 1)
    sowing_date = date(start_year, 3, 1)
    end_date = date(anchor.year + 2, 12, 31)
    return start_date, sowing_date, end_date, anchor


def _weather_patterns(model_input_json):
    patterns = []
    for item in model_input_json.get("weather_series", []):
        tmax = _to_float(item.get("tmax", item.get("maxt")), 30.2)
        tmin = _to_float(item.get("tmin", item.get("mint")), 18.6)
        if tmin >= tmax:
            tmin = tmax - 8
        patterns.append(
            {
                "radn": _to_float(item.get("radiation_mj", item.get("radiation")), 18.5),
                "maxt": tmax,
                "mint": tmin,
                "rain": _to_float(item.get("rain_mm", item.get("rain")), 0),
            }
        )
    if not patterns:
        patterns = [{"radn": 18.5, "maxt": 30.2, "mint": 18.6, "rain": 0}]
    return patterns


def _write_weather_file(run_dir, model_input_json, start_date, end_date):
    plot = model_input_json.get("plot_info", {})
    patterns = _weather_patterns(model_input_json)
    t_avgs = [(item["maxt"] + item["mint"]) / 2 for item in patterns]
    tav = sum(t_avgs) / len(t_avgs)
    amp = max(t_avgs) - min(t_avgs) if len(t_avgs) > 1 else 8.0

    weather_file = run_dir / "coffee_weather.met"
    lines = [
        "[weather.met.weather]",
        "! generated from mini program model_input_json",
        f"latitude = {_to_float(plot.get('latitude'), 24.93):.4f}  (DECIMAL DEGREES)",
        f"longitude = {_to_float(plot.get('longitude'), 98.88):.4f} (DECIMAL DEGREES)",
        f"tav = {tav:.2f} (oC)",
        f"amp = {amp:.2f} (oC)",
        "",
        "year   day   radn   maxt   mint   rain",
        "()   ()   ()   ()   ()   ()",
    ]

    current = start_date
    index = 0
    while current <= end_date:
        pattern = patterns[index % len(patterns)]
        lines.append(
            f"{current.year}   {current.timetuple().tm_yday}   "
            f"{pattern['radn']:.2f}   {pattern['maxt']:.2f}   "
            f"{pattern['mint']:.2f}   {pattern['rain']:.2f}"
        )
        current += timedelta(days=1)
        index += 1

    weather_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return weather_file


def _collect_apsim_events(model_input_json, start_date, end_date, anchor):
    events = []
    for op in model_input_json.get("farm_operations", []):
        op_type = op.get("op_type")
        event_date = _parse_date(op.get("date") or op.get("op_date"), anchor)
        if not event_date or event_date < start_date or event_date > end_date:
            continue
        if op_type == "irrigation":
            amount = normalize_irrigation_mm(op.get("amount"), op.get("unit"))
            if amount > 0:
                events.append({"type": "irrigation", "date": event_date.isoformat(), "amount_mm": amount})
        elif op_type == "fertilization":
            amount = normalize_fertilizer_kg_ha(op.get("amount"), op.get("unit"))
            if amount > 0:
                events.append({"type": "fertilization", "date": event_date.isoformat(), "amount_kg_ha": amount})

    scenario = model_input_json.get("scenario", {})
    scenario_date = anchor
    extra_irrigation = _to_float(scenario.get("extra_irrigation_mm"), 0)
    if extra_irrigation > 0:
        events.append(
            {
                "type": "irrigation",
                "date": scenario_date.isoformat(),
                "amount_mm": extra_irrigation,
                "source": "scenario",
            }
        )

    extra_fertilizer = normalize_fertilizer_kg_ha(scenario.get("extra_fertilizer_kg_mu", 0), "kg/mu")
    if extra_fertilizer > 0:
        events.append(
            {
                "type": "fertilization",
                "date": scenario_date.isoformat(),
                "amount_kg_ha": extra_fertilizer,
                "source": "scenario",
            }
        )

    return events


def _event_manager_code(events):
    code = [
        "using Models.Core;",
        "using Models.Soils;",
        "using System;",
        "",
        "namespace Models",
        "{",
        "    [Serializable]",
        "    [System.Xml.Serialization.XmlInclude(typeof(Model))]",
        "    public class Script : Model",
        "    {",
        "        [Link] Clock Clock;",
        "        [Link] Irrigation Irrigation;",
        "        [Link] Fertiliser Fertiliser;",
        "",
        "        [EventSubscribe(\"DoManagement\")]",
        "        private void OnDoManagement(object sender, EventArgs e)",
        "        {",
    ]
    if not events:
        code.append("            // No mini program irrigation or fertilisation events for this run.")
    for event in events:
        event_date = _parse_date(event.get("date"), date.today())
        if event["type"] == "irrigation":
            amount = _to_float(event.get("amount_mm"), 0)
            code.append(
                f"            if (Clock.Today.Date == new DateTime({event_date.year}, {event_date.month}, {event_date.day}))"
            )
            code.append(f"                Irrigation.Apply({amount:.3f});")
        elif event["type"] == "fertilization":
            amount = _to_float(event.get("amount_kg_ha"), 0)
            code.append(
                f"            if (Clock.Today.Date == new DateTime({event_date.year}, {event_date.month}, {event_date.day}))"
            )
            code.append(f"                Fertiliser.Apply({amount:.3f}, \"NO3N\", 0, 0, false);")
    code.extend(
        [
            "        }",
            "    }",
            "}",
        ]
    )
    return code


def _configure_apsim_file(run_file, model_input_json, run_dir):
    start_date, sowing_date, end_date, anchor = _simulation_window(model_input_json)
    weather_file = _write_weather_file(run_dir, model_input_json, start_date, end_date)
    events = _collect_apsim_events(model_input_json, start_date, end_date, anchor)

    data = json.loads(run_file.read_text(encoding="utf-8"))
    weather = _find_node(data, name="Weather")
    if weather:
        weather["FileName"] = weather_file.name

    clock = _find_node(data, type_contains="Models.Clock")
    if clock:
        clock["Start"] = f"{start_date.isoformat()}T00:00:00"
        clock["End"] = f"{end_date.isoformat()}T00:00:00"

    zone = _find_node(data, type_contains="Models.Core.Zone")
    plot = model_input_json.get("plot_info", {})
    if zone:
        zone["Altitude"] = _to_float(plot.get("elevation_m"), zone.get("Altitude", 50))
        children = zone.setdefault("Children", [])
        children.append(
            {
                "$type": "Models.Manager, Models",
                "CodeArray": _event_manager_code(events),
                "Parameters": [],
                "Name": "Coffee MVP Input Events",
                "ResourceName": None,
                "Children": [],
                "Enabled": True,
                "ReadOnly": False,
            }
        )

    palm_management = _find_node(data, name="Palm Management")
    if palm_management:
        _set_manager_parameter(palm_management, "sowing_date", f"{sowing_date:%m/%d/%Y} 00:00:00")

    run_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "model_input_applied.json").write_text(
        json.dumps(model_input_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "apsim_events_applied.json").write_text(
        json.dumps(
            {
                "weather_file": str(weather_file),
                "clock_start": start_date.isoformat(),
                "sowing_date": sowing_date.isoformat(),
                "clock_end": end_date.isoformat(),
                "events": events,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return weather_file, events, start_date, end_date


def _fallback_result(model_input_json):
    task_id = model_input_json.get("task_id", "task_demo")
    plot = model_input_json.get("plot_info", {})
    tree_age = int(plot.get("tree_age", 4) or 4)
    irrigation_mm, fertilizer_kg_ha = _sum_management(model_input_json)

    base_yield = 980 + tree_age * 70
    irrigation_bonus = min(irrigation_mm * 4.2, 190)
    fertilizer_bonus = min(fertilizer_kg_ha * 0.45, 160)
    yield_pred = round(base_yield + irrigation_bonus + fertilizer_bonus)
    yield_change = round(irrigation_bonus + fertilizer_bonus - 80)
    water_stress = round(max(0.12, 0.58 - irrigation_mm * 0.008), 2)
    nitrogen_status = "正常" if fertilizer_kg_ha >= 90 else "偏低"

    today = date.today()
    yield_curve = []
    for i, ratio in enumerate([0.9, 0.96, 1.0]):
        yield_curve.append(
            {
                "date": (today + timedelta(days=i * 7)).isoformat(),
                "yield_kg_mu": round(yield_pred * ratio),
            }
        )

    result = {
        "model": "APSIM-Coffee",
        "status": "success",
        "plot_id": model_input_json.get("plot_id", "plot_001"),
        "stage": "果实膨大期",
        "harvest_days": max(28, 56 - tree_age * 2),
        "yield_pred_kg_mu": yield_pred,
        "yield_change_kg_mu": yield_change,
        "water_stress": water_stress,
        "nitrogen_status": nitrogen_status,
        "lai": round(2.6 + tree_age * 0.14, 2),
        "biomass_kg_ha": round(5200 + tree_age * 260 + fertilizer_bonus * 5),
        "yield_curve": yield_curve,
        "apsim_explain": {
            "what": "咖啡处于果实膨大期，产量形成进入关键阶段。",
            "why": "近期水肥管理会直接影响干物质积累和最终产量预测。",
        },
        "source": "fallback_formula",
    }
    return result


def _read_csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _positive_result_yield(row):
    return (
        _to_float(row.get("Calculations.Script.AnnualYield"), 0) > 0
        or _to_float(row.get("Yield"), 0) > 0
    )


def _pick_annual_rows(run_dir):
    annual_files = sorted(run_dir.glob("*AnnualOutput.csv"))
    if not annual_files:
        annual_files = sorted(run_dir.glob("*Report.csv"))
    if not annual_files:
        raise FileNotFoundError("APSIM did not produce AnnualOutput.csv or Report.csv")

    rows = _read_csv_rows(annual_files[0])
    valid_rows = [
        row for row in rows
        if row.get("Clock.Today") and _positive_result_yield(row)
    ]
    if not valid_rows:
        raise ValueError(f"No usable rows found in {annual_files[0].name}")
    return annual_files[0], valid_rows


def _row_yield(row):
    annual_yield = _to_float(row.get("Calculations.Script.AnnualYield"), None)
    if annual_yield is not None:
        # OilPalm yield is a proxy value for MVP. Scale it to a coffee-like kg/mu range.
        return annual_yield * 90
    return _to_float(row.get("Yield")) / 15


def _build_result_from_apsim(model_input_json, run_dir, stdout, stderr):
    annual_csv, rows = _pick_annual_rows(run_dir)
    _start_date, _sowing_date, _end_date, anchor = _simulation_window(model_input_json)
    target_year = str(anchor.year)
    target_indices = [
        index for index, row in enumerate(rows)
        if str(row.get("Clock.Today.Year", "")) == target_year
    ]
    selected_index = target_indices[-1] if target_indices else max(range(len(rows)), key=lambda index: _row_yield(rows[index]))
    latest = rows[selected_index]
    start_index = max(0, selected_index - 2)
    recent = rows[start_index : selected_index + 1]
    irrigation_mm, fertilizer_kg_ha = _sum_management(model_input_json)

    management_bonus = min(irrigation_mm * 2.5, 120) + min(fertilizer_kg_ha * 0.18, 90)
    raw_yield = _row_yield(latest)
    yield_pred = round(_clamp(raw_yield + management_bonus, 450, 1800))

    yield_curve = []
    for row in recent:
        row_yield = round(_clamp(_row_yield(row) + management_bonus, 450, 1800))
        yield_curve.append(
            {
                "date": row.get("Clock.Today", date.today().isoformat()),
                "yield_kg_mu": row_yield,
            }
        )

    potential_et = _to_float(latest.get("AnnualPotentialEvaporation"), 0)
    actual_et = _to_float(latest.get("AnnualET"), 0)
    if potential_et > 0:
        water_stress = _clamp(1 - actual_et / potential_et + 0.18 - irrigation_mm * 0.002, 0.08, 0.72)
    else:
        water_stress = _clamp(0.45 - irrigation_mm * 0.006, 0.12, 0.65)

    average_no3 = _to_float(latest.get("AnnualAverageNO3"), 0)
    nitrogen_status = "正常" if average_no3 >= 35 or fertilizer_kg_ha >= 90 else "偏低"
    lai = _to_float(latest.get("OilPalm.LAI"), 3.0)
    bunch_npp = _to_float(latest.get("AnnualBunchNPP"), 0)
    veg_npp = _to_float(latest.get("AnnualTotalVegetativeNPP"), 0)

    return {
        "model": "APSIM-Coffee-MVP",
        "status": "success",
        "plot_id": model_input_json.get("plot_id", "plot_001"),
        "stage": "果实膨大期",
        "harvest_days": 45,
        "yield_pred_kg_mu": yield_pred,
        "yield_change_kg_mu": round(management_bonus - 80),
        "water_stress": round(water_stress, 2),
        "nitrogen_status": nitrogen_status,
        "lai": round(lai, 2),
        "biomass_kg_ha": round(bunch_npp + veg_npp),
        "yield_curve": yield_curve,
        "apsim_explain": {
            "what": "后端已调用 APSIM Models.exe 运行多年生作物代理模型，并将结果映射为咖啡 MVP 指标。",
            "why": "当前阶段先用 OilPalm 示例作为咖啡代理模型跑通 APSIM 引擎链路，后续可替换为咖啡专用 .apsimx 参数集。",
        },
        "source": "apsim_oilpalm_proxy",
        "apsim_run": {
            "models_exe": str(APSIM_EXE),
            "template": str(APSIM_TEMPLATE),
            "run_dir": str(run_dir),
            "output_csv": str(annual_csv),
            "stdout_tail": stdout[-1200:],
            "stderr_tail": stderr[-1200:],
        },
    }


def _run_apsim_engine(task_id, model_input_json):
    if not APSIM_EXE.exists():
        raise FileNotFoundError(f"Models.exe not found: {APSIM_EXE}")
    if not APSIM_TEMPLATE.exists():
        raise FileNotFoundError(f"APSIM template not found: {APSIM_TEMPLATE}")

    run_dir = APSIM_RUN_DIR / task_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    run_file = run_dir / "apsim_coffee_template.apsimx"
    shutil.copy2(APSIM_TEMPLATE, run_file)
    weather_file, events, start_date, end_date = _configure_apsim_file(run_file, model_input_json, run_dir)

    completed = subprocess.run(
        [str(APSIM_EXE), str(run_file.name), "--csv"],
        cwd=run_dir,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    combined = f"{stdout}\n{stderr}"
    if completed.returncode != 0 or "ERRORS FOUND" in combined:
        raise RuntimeError(f"APSIM run failed:\n{combined[-2000:]}")

    return run_dir, stdout, stderr, weather_file, events, start_date, end_date


def run_apsim_model(model_input_json):
    task_id = model_input_json.get("task_id", "task_demo")
    try:
        run_dir, stdout, stderr, weather_file, events, start_date, end_date = _run_apsim_engine(task_id, model_input_json)
        result = _build_result_from_apsim(model_input_json, run_dir, stdout, stderr)
        result["apsim_run"]["weather_file"] = str(weather_file)
        result["apsim_run"]["event_count"] = len(events)
        result["apsim_run"]["clock_start"] = start_date.isoformat()
        result["apsim_run"]["clock_end"] = end_date.isoformat()
    except Exception as error:
        result = _fallback_result(model_input_json)
        result["status"] = "fallback"
        result["apsim_error"] = str(error)

    run_dir = APSIM_RUN_DIR / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "apsim_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
