# BEPS-Lite 咖啡生态模型可视化系统

## 1. 项目简介

本项目是一个面向咖啡数字孪生系统的 **BEPS-Lite 咖啡生态模型可视化演示模块**。系统基于 Flask 后端和 HTML 可视化页面，实现 BEPS-Lite 模型的调用、结果查看、情景模拟对比和历史结果读取。

当前模块主要用于展示咖啡园生态状态，包括：

- GPP：总初级生产力；
- NPP：净初级生产力；
- ET：蒸散发；
- 碳汇估计；
- 长势评分；
- 生态风险等级；
- 情景模拟对比结果。

说明：当前 BEPS-Lite 是 Python 轻量化实现，用于演示咖啡园生态指标计算。三模型融合中的 APSIM-Coffee 和 HYDRUS-1D 当前为模拟输入，BEPS-Lite 部分已经具备实际计算逻辑。

---

## 2. 项目目录结构

```text
backend/
├── adapters/
│   └── beps_lite_adapter.py
├── demo_data/
│   └── beps_demo_weather.json
├── runtime/
│   └── beps_results/
├── services/
│   ├── fusion_engine.py
│   ├── model_runner.py
│   ├── result_service.py
│   └── scenario_service.py
├── templates/
│   └── beps_dashboard.html
└── beps_gui.py
```

### 主要文件说明

| 文件/目录 | 作用 |
|---|---|
| `beps_gui.py` | Flask 后端入口文件，负责启动服务和注册接口 |
| `adapters/beps_lite_adapter.py` | BEPS-Lite 模型计算核心 |
| `services/model_runner.py` | 模型调度，负责调用 BEPS-Lite 并保存结果 |
| `services/scenario_service.py` | 情景模拟对比服务 |
| `services/result_service.py` | 最新结果和历史结果读取服务 |
| `services/fusion_engine.py` | 三模型融合演示逻辑 |
| `demo_data/beps_demo_weather.json` | 演示气象数据 |
| `runtime/beps_results/` | 保存每次模型运行结果 |
| `templates/beps_dashboard.html` | 可视化网页页面 |

---

## 3. 环境准备

### 3.1 进入项目目录

```powershell
cd D:\BEPS\backend
```

### 3.2 安装 Flask

```powershell
pip install flask
```

如果已经安装过 Flask，可以跳过这一步。

---

## 4. 启动系统

在 PowerShell 或终端中执行：

```powershell
cd D:\BEPS\backend
python beps_gui.py
```

启动成功后，终端会显示类似内容：

```text
Running on http://127.0.0.1:5000/
Running on http://192.168.x.x:5000/
```

此时不要关闭该终端，Flask 后端需要保持运行。

---

## 5. 打开可视化网页

浏览器访问：

```text
http://127.0.0.1:5000/beps-dashboard
```

如果需要在局域网其他设备访问，可以使用终端中显示的局域网地址，例如：

```text
http://192.168.2.10:5000/beps-dashboard
```

---

## 6. 网页使用流程

打开页面后，建议按下面顺序操作。

### 第一步：检测后端

点击页面右上区域的：

```text
检测后端
```

如果显示“后端连接正常”，说明 Flask 服务可访问。

如果显示连接失败，请检查：

1. `beps_gui.py` 是否正在运行；
2. 页面中的 API 地址是否为 `http://127.0.0.1:5000`；
3. 端口 `5000` 是否被其他程序占用。

---

### 第二步：填写或保留模型输入参数

页面左侧是模型输入区，默认已经填好了可运行的参数：

| 参数 | 示例值 | 含义 |
|---|---:|---|
| 地块 ID | `coffee_plot_001` | 咖啡地块编号 |
| LAI | `2.7` | 叶面积指数 |
| NDVI | `0.68` | 遥感长势指标 |
| shade_degree | `0.4` | 遮阴程度，取值 0-1 |
| water_factor | `0.78` | 水分限制因子，取值 0-1 |
| water_stress | `0.72` | APSIM 模拟水分胁迫 |
| root_uptake | `0.42` | HYDRUS 模拟根系吸水效率 |

初次使用可以不修改，直接运行。

---

### 第三步：运行 BEPS-Lite

点击：

```text
运行 BEPS-Lite
```

系统会调用接口：

```text
POST /api/beps-lite/run
```

运行成功后，页面会更新：

- 长势评分；
- 生态风险；
- GPP；
- NPP；
- ET；
- 碳汇估计；
- BEPS-Lite 时间序列图。

该功能用于单独查看 BEPS-Lite 的生态指标计算结果。

---

### 第四步：运行三模型融合演示

点击：

```text
运行三模型融合
```

系统会调用接口：

```text
POST /api/model/fuse-demo
```

该接口会把模拟的 APSIM-Coffee 输出、模拟的 HYDRUS-1D 输出和真实 BEPS-Lite 输出进行融合，生成：

- 综合风险等级；
- What：当前发生了什么；
- How：应该怎么做；
- Why：为什么这样建议。

说明：当前 APSIM-Coffee 和 HYDRUS-1D 是模拟输入，不是实际模型运行结果；BEPS-Lite 是实际计算结果。

---

### 第五步：运行情景模拟对比

点击：

```text
运行情景模拟对比
```

系统会调用接口：

```text
POST /api/beps-lite/scenario-compare
```

系统会自动生成 5 种情景：

| 情景 | 说明 |
|---|---|
| 正常管理情景 | 水分、遮阴和 NDVI 较正常 |
| 根区缺水情景 | 降低水分限制因子 |
| 遮阴过高情景 | 提高遮阴程度 |
| NDVI 偏低情景 | 降低遥感长势指标 |
| 综合胁迫情景 | 同时设置缺水、高遮阴、NDVI 偏低 |

页面会展示每种情景下的：

- GPP；
- NPP；
- ET；
- 碳汇；
- 长势评分；
- 风险等级。

该功能适合用于演示 BEPS-Lite 对不同生态胁迫情景的响应。

---

### 第六步：读取最新 BEPS 结果

点击：

```text
读取最新 BEPS 结果
```

系统会调用接口：

```text
GET /api/beps-lite/latest
```

该接口会从：

```text
runtime/beps_results/
```

中读取最近一次保存的 BEPS-Lite 结果，并显示到页面上。

---

## 7. 常用接口说明

| 接口 | 方法 | 作用 |
|---|---|---|
| `/` | GET | 检测后端是否运行 |
| `/beps-dashboard` | GET | 打开可视化网页 |
| `/api/beps-lite/run` | POST | 单独运行 BEPS-Lite |
| `/api/model/fuse-demo` | POST | 三模型融合演示 |
| `/api/beps-lite/scenario-compare` | POST | 多情景模拟对比 |
| `/api/beps-lite/latest` | GET | 获取最新 BEPS 结果 |
| `/api/beps-lite/history` | GET | 获取历史结果列表 |

---

## 8. PowerShell 接口测试示例

### 8.1 测试后端

```powershell
Invoke-RestMethod http://127.0.0.1:5000/
```

---

### 8.2 测试 BEPS-Lite

```powershell
$bodyObj = @{
    plot_id = "coffee_plot_001"
    lai = 2.7
    ndvi = 0.68
    shade_degree = 0.4
    water_factor = 0.78
}

$json = $bodyObj | ConvertTo-Json -Depth 10
$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($json)

$result = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:5000/api/beps-lite/run" `
    -ContentType "application/json; charset=utf-8" `
    -Body $utf8Body

$result | ConvertTo-Json -Depth 10
```

---

### 8.3 测试情景模拟

```powershell
$bodyObj = @{
    plot_id = "coffee_plot_001"
    lai = 2.7
    ndvi = 0.68
    shade_degree = 0.4
    water_factor = 0.78
}

$json = $bodyObj | ConvertTo-Json -Depth 10
$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($json)

$result = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:5000/api/beps-lite/scenario-compare" `
    -ContentType "application/json; charset=utf-8" `
    -Body $utf8Body

$result | ConvertTo-Json -Depth 10
```

---

## 9. 常见问题

### 9.1 页面打不开

检查是否已经启动后端：

```powershell
cd D:\BEPS\backend
python beps_gui.py
```

然后重新访问：

```text
http://127.0.0.1:5000/beps-dashboard
```

---

### 9.2 点击按钮没有反应

检查页面中的 API 地址是否为：

```text
http://127.0.0.1:5000
```

然后点击“保存”，再点击“检测后端”。

---

### 9.3 中文乱码

在 Flask 文件中确认有：

```python
app.config["JSON_AS_ASCII"] = False
```

PowerShell 测试接口时使用 UTF-8：

```powershell
$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($json)
```

---

### 9.4 端口被占用

查看 5000 端口：

```powershell
netstat -ano | findstr :5000
```

如果需要结束旧进程：

```powershell
taskkill /PID 进程号 /F
```

然后重新启动：

```powershell
python beps_gui.py
```

---

## 10. 当前完成情况

| 功能 | 状态 |
|---|---|
| Flask 后端启动 | 已完成 |
| BEPS-Lite 模型计算 | 已完成 |
| GPP/NPP/ET/碳汇输出 | 已完成 |
| 长势评分 | 已完成 |
| 生态风险判断 | 已完成 |
| 结果保存 | 已完成 |
| 最新结果读取 | 已完成 |
| 情景模拟对比 | 已完成 |
| 可视化网页 | 已完成 |
| 原始 JSON 显示区删除 | 已完成 |
| 真实 APSIM/HYDRUS 接入 | 后续扩展 |
| 真实 BEPS_Hourly_DS.exe 接入 | 后续扩展 |

---

## 11. 后续扩展

后续可以继续扩展：

1. 调用真实 `BEPS_Hourly_DS.exe`；
2. 增加真实 BEPS 输入文件生成器；
3. 增加真实 BEPS 输出解析器；
4. 接入真实 APSIM-Coffee；
5. 接入真实 HYDRUS-1D；
6. 将结果接入微信小程序；
7. 使用 SQLite 保存地块和历史结果；
8. 增加导出报告功能。

---

## 12. 一句话总结

本项目实现了一个可运行、可视化、可情景模拟的 BEPS-Lite 咖啡生态模型演示系统，可用于展示咖啡园 GPP、NPP、ET、碳汇、长势评分和生态风险，并为后续接入完整 BEPS、APSIM 和 HYDRUS 模型提供接口基础。
