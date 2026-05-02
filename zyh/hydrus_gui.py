import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path

# 将当前目录加入系统路径，确保能找到 backend 模块
sys.path.append(str(Path(__file__).resolve().parent))
from backend.models.hydrus_adapter import run_hydrus_model

# --- 页面配置 ---
st.set_page_config(page_title="HYDRUS-1D 土壤水分机理推演验证台", layout="wide")
st.title("💧 HYDRUS-1D 机理推演验证台 (张源皓专属)")
st.markdown("严格对照 **表2.8** 给前端支撑的图表规范，并实时解答开发文档中规定的 **6大土壤水分核心问题**。")

# --- 侧边栏：客户输入控制 ---
st.sidebar.header("🛠️ 农事与气象输入")
irrigation_input = st.sidebar.slider("今日灌溉量 (mm)", min_value=0.0, max_value=100.0, value=25.0, step=1.0)
rain_input = st.sidebar.slider("今日降雨量 (mm)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)


if st.sidebar.button("🚀 运行物理模型", type="primary"):
    with st.spinner("HYDRUS H1D_CALC.EXE 引擎正在后台进行数值求解..."):
        test_input = {
            "task_id": "gui_test_run",
            "plot_id": "plot_001",
            "atmospheric_boundary": [
                {
                    "date": "2026-04-30",
                    "rain_mm": rain_input,
                    "irrigation_mm": irrigation_input,
                    "potential_evaporation_mm": 1.5,
                    "potential_transpiration_mm": 2.2
                }
            ]
        }
        
        try:
            # 调用底层适配器
            result = run_hydrus_model(test_input)
            st.success("✅ 模型推演完成！底层 JSON 数据已实时生成。")
            
            # 提取后续判断需要的关键指标
            water_status = result.get("water_status", "未知")
            uptake_ratio = result.get("root_uptake_ratio", 0)
            inf_depth = result.get("infiltration_depth_cm", 0)
            profile_data = result.get("soil_profile_current", [])
            
            # 获取 10cm(表层) 和 40cm(主根区) 的含水率
            theta_10 = next((p['theta'] for p in profile_data if p['depth_cm'] == 10), 0)
            theta_40 = next((p['theta'] for p in profile_data if p['depth_cm'] == 40), 0)

            # ==========================================
            # 🎯 优化版：HYDRUS 核心业务问题诊断 (明确预测属性)
            # ==========================================
            st.markdown("### 🎯 HYDRUS 业务机理推演 (基于今日操作预测未来7天)")
            diag_col1, diag_col2, diag_col3 = st.columns(3)
            
            with diag_col1:
                # 1 & 2. 入渗评价
                if inf_depth > 0:
                    st.info(f"**1 & 2. 本次水分入渗评价**\n\n💧 物理推演显示，今日灌溉/降雨产生的湿润锋最终可到达地下 **{inf_depth} cm**。")
                else:
                    st.warning(f"**1 & 2. 本次水分入渗评价**\n\n🏜️ 今日无有效水分输入，地表水分未向下入渗。")
                    
                # 3. 根系吸水预测
                if uptake_ratio > 0.8:
                    st.success(f"**3. 7天内根系吸水预测**\n\n🌿 预计未来一周根系吸水效率可维持在 **{uptake_ratio*100:.0f}%**，水分供应充足。")
                else:
                    st.error(f"**3. 7天内根系吸水预测**\n\n⚠️ 预计受土壤水分限制，未来一周根系吸水效率将降至 **{uptake_ratio*100:.0f}%**。")

            with diag_col2:
                # 4. 未来缺水部位预测
                if theta_40 < 0.19:
                    st.error(f"**4. 一周后预计状态：真缺水？**\n\n🔥 推演显示 7 天后主根区(40cm)含水率({theta_40})极低，属于**真缺水**状态。")
                elif theta_10 < 0.19 and theta_40 >= 0.19:
                    st.warning(f"**4. 一周后预计状态：真缺水？**\n\n🌞 7 天后表层(10cm)预计干旱，但深层(40cm)尚有存水。")
                else:
                    st.success(f"**4. 一周后预计状态：真缺水？**\n\n🌊 7 天后表层与深层水分预计仍处于理想区间。")
                
                # 5. 未来灌溉建议
                if "干旱" in water_status:
                    st.error(f"**5. 未来 7 天灌溉建议**\n\n🚨 模拟结束时状态为“{water_status}”，建议在 **7 天内** 安排补充灌溉。")
                else:
                    st.success(f"**5. 未来 7 天灌溉建议**\n\n✅ 模拟结束时状态良好，未来一周**无需**额外灌溉。")

            with diag_col3:
                # 6. 深层渗漏风险
                if inf_depth > 70:
                    st.error(f"**6. 本次操作风险评估**\n\n📉 **存在深层渗漏风险！** 入渗深度({inf_depth}cm)已穿透 70cm 主根区。建议减小单次水量，采用“少量多次”策略。")
                else:
                    st.success(f"**6. 本次操作风险评估**\n\n🛡️ **水分利用率极高。** 本次入渗被精准控制在主根区({inf_depth}cm)内，无淋失风险。")
                    
                st.info(f"**🤖 物理机理综合解释**：\n\n{result['hydrus_explain']['what']} {result['hydrus_explain']['why']}")

            # ==========================================
            # 图表展示区域 (维持上次的高级质感)
            # ==========================================
            st.markdown("### 📊 底层数据可视化图表")
            
            # 根系吸水仪表盘
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = uptake_ratio * 100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "根系实际吸水效率 (%)", 'font': {'size': 16}},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 40], 'color': "lightcoral"},
                        {'range': [40, 70], 'color': "khaki"},
                        {'range': [70, 100], 'color': "lightgreen"}
                    ],
                }
            ))
            fig_gauge.update_layout(height=250, margin=dict(t=50, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown("#### 📉 土壤剖面水分图")
                if profile_data:
                    df_profile = pd.DataFrame(profile_data)
                    df_profile.sort_values(by="depth_cm", inplace=True)
                    
                    fig_profile = go.Figure()
                    fig_profile.add_trace(go.Scatter(
                        x=df_profile["theta"], 
                        y=df_profile["depth_cm"],
                        mode='lines+markers',
                        line=dict(color='#00BFFF', width=3, shape='spline'),
                        marker=dict(size=10, color='white', line=dict(color='#00BFFF', width=2)),
                        fill='tozerox',
                        fillcolor='rgba(0, 191, 255, 0.2)',
                        name="体积含水率",
                        hovertemplate="深度: %{y} cm<br>含水率: %{x}<extra></extra>"
                    ))
                    fig_profile.update_layout(
                        xaxis_title="体积含水率 (Theta, cm³/cm³)",
                        yaxis_title="土壤深度 (cm)",
                        yaxis=dict(autorange="reversed", tickmode='array', tickvals=df_profile["depth_cm"].tolist(), gridcolor='rgba(200, 200, 200, 0.2)'),
                        xaxis=dict(range=[0.0, 0.45], gridcolor='rgba(200, 200, 200, 0.2)'),
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=20, r=20, t=30, b=20),
                    )
                    st.plotly_chart(fig_profile, use_container_width=True)

            with col_chart2:
                st.markdown("#### 📈 多深度含水率时间序列")
                series_data = result.get("soil_moisture_series", [])
                if series_data:
                    df_series = pd.DataFrame(series_data)
                    df_series.set_index("date", inplace=True)
                    st.line_chart(df_series, y_label="含水率 (Theta)", x_label="模拟日期")

        except Exception as e:
            st.error(f"模型运行出错: {str(e)}")
else:
    st.info("👈 请在侧边栏输入参数，点击运行以验证表 2.8 的图表支撑能力及 6 大机理问题诊断。")