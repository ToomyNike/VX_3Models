# APSIM 模型说明

文件位置：`backend/models/apsim_adapter.py`

统一接口：

```python
run_apsim_model(model_input_json) -> apsim_result_json
```

当前 MVP 版本采用“APSIM-Coffee-MVP 代理模型”路线：

1. 使用 APSIM Next Generation 自带的 `OilPalm.apsimx` 作为多年生经济作物代理模型。
2. 每次运行时，后端根据小程序输入动态生成 `coffee_weather.met`。
3. 每次运行时，后端向本次 `.apsimx` 写入 `Coffee MVP Input Events` 管理脚本。
4. 灌溉打卡会转成 `Irrigation.Apply(...)`。
5. 施肥打卡会转成 `Fertiliser.Apply(...)`。
6. 后端真实调用 `Models.exe` 运行 `.apsimx`。
7. 读取 APSIM 生成的 `AnnualOutput.csv`。
8. 将 APSIM 输出映射成小程序需要的咖啡指标。

这样做的目的，是先跑通真实 APSIM 引擎调用链路，而不是停留在假数据。后续如果获得咖啡专用 `.apsimx` 或完成咖啡参数标定，只需要替换 `backend/templates/apsim/apsim_coffee_template.apsimx` 和字段映射逻辑。

当前本机 APSIM 路径：

```text
D:\APP\APSIM\APSIM2025.12.7950.0\bin\Models.exe
```

后续接入咖啡专用模型时，adapter 内部仍遵循以下流程：

1. 写入 `.apsimx` 模板参数。
2. 生成或更新 `.met` 气象文件。
3. 通过 `subprocess` 调用 `Models.exe`。
4. 读取 APSIM 输出 `.db` / `.csv`。
5. 返回字段保持不变。

每次运行后可以在以下目录检查本次 APSIM 输入与输出：

```text
backend/runtime/apsim_runs/<task_id>/
```

关键文件：

- `model_input_applied.json`：后端收到的小程序统一输入。
- `coffee_weather.met`：由小程序/后端气象数据生成的 APSIM 气象文件。
- `apsim_events_applied.json`：写入 APSIM 的灌溉和施肥事件。
- `apsim_coffee_template.apsimx`：本次实际运行的 APSIM 文件。
- `apsim_coffee_template.AnnualOutput.csv`：APSIM 输出。
