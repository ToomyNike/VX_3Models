# BEPS 模型说明

文件位置：`backend/models/beps_adapter.py`

统一接口：

```python
run_beps_model(model_input_json) -> beps_result_json
```

简光耀后续对接时，保持返回字段不变即可：

- `growth_score`
- `gpp_today`
- `npp_today`
- `et_today`
- `carbon_sink_kgC_mu`
- `gpp_series`
- `npp_series`
- `et_series`
- `beps_risk`
