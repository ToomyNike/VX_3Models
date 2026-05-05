# 面向云南小粒咖啡的多机理模型（APSIM/HYDRUS/BEPS）协同智能决策系统

基于 APSIM / HYDRUS / BEPS 三模型机理证据的智能农技解释平台

## 系统简介

本系统面向云南小粒咖啡种植场景，通过整合三个专业机理模型，实现从"作物生长—土壤水分—冠层生态"的多层协同分析，并借助大语言模型（GLM-4-Flash）将机理证据转化为可解释的农技建议。

| 模型 | 全称 | 模拟层 | 主要输出 |
|------|------|--------|----------|
| APSIM-Coffee | Agricultural Production Systems sIMulator | 作物生长层 | 生育期、产量、水分胁迫、氮素状态、LAI |
| HYDRUS-1D | Hydrological Research Unit Soil | 土壤水分层 | 剖面含水率、入渗深度、根系吸水效率 |
| BEPS-Lite | Boreal Ecosystem Productivity Simulator | 冠层生态层 | GPP、NPP、ET、碳汇、长势评分 |

系统亮点：**机理解释**——不仅告诉果农"发生了什么（what）"，更解释"怎么做（how）"和"为什么这样做（why）"，且每条建议均有 APSIM / HYDRUS / BEPS 三模型证据支撑。

## 项目结构

- `miniprogram/`：微信小程序前端
- `backend/`：Flask 后端、SQLite、三模型适配器、融合引擎、机理解释层
- `server/`：本地部署脚本和模型可执行路径
- `docs/`：接口说明、模型说明、演示脚本

## 快速启动

**PowerShell：**

```powershell
cd D:\AAACODE\PYTHON\VX_3Models\coffee_digital_twin
.\server\start_all.ps1
```

如果 PowerShell 限制本地脚本，先运行一次：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**CMD：**

```bat
cd backend
call D:\AAACODE\PYTHON\anaconda\Scripts\activate.bat pyweb
python -m pip install -r requirements.txt
python app.py
```

然后在微信开发者工具中打开 `miniprogram/` 目录。

手机测试时，将 `miniprogram/utils/config.js` 中的 `127.0.0.1` 替换为后端电脑的局域网 IP。

## 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/model/run` | POST | 运行三模型并返回融合结果（含机理解释） |
| `/api/model/result/<task_id>` | GET | 查询历史结果 |
| `/api/advice/generate` | POST | 生成三段式建议（what/how/why/model_basis） |
| `/api/advice/chat` | POST | 多轮 AI 农技对话 |
| `/api/model/info` | GET | 查询三模型说明 |
