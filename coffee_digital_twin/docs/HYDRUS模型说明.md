# HYDRUS 模型说明

文件位置：`backend/models/hydrus_adapter.py`

统一接口：

```python
run_hydrus_model(model_input_json) -> hydrus_result_json
```

张源皓后续对接时，保持返回字段不变即可：

- `water_status`
- `root_uptake_ratio`
- `irrigation_effect`
- `soil_profile_current`
- `soil_moisture_series`
