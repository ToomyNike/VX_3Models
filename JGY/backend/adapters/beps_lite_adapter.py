import math
from typing import Dict, Any, List, Optional


def clamp(value: float, min_value: float, max_value: float) -> float:
    """限制数值范围。"""
    return max(min_value, min(max_value, value))


class BepsLiteAdapter:
    """
    BEPS-Lite 区域生态扩展模型。

    实现目标：
    1. 根据气象、LAI、NDVI、遮阴程度、水分限制因子估算 GPP；
    2. 根据 GPP 估算 NPP；
    3. 简化估算 ET；
    4. 根据 NPP 估算碳汇；
    5. 综合生成长势评分和生态风险等级。
    """

    def __init__(self):
        # 最大光能利用率，MVP 阶段使用经验值
        self.lue_max = 2.2

        # 光合有效辐射 PAR 占总太阳辐射比例
        self.par_ratio = 0.48

        # NPP/GPP 比例，MVP 阶段简化为固定比例
        self.npp_ratio = 0.45

        # Beer-Lambert 冠层光截获系数
        self.k = 0.55

    def temperature_factor(self, tmean: float) -> float:
        """
        温度限制因子。
        云南小粒咖啡适宜温度可先设置为 18-26℃ 较优。
        """
        t_base = 8.0
        t_opt = 24.0
        t_max = 38.0

        if tmean <= t_base or tmean >= t_max:
            return 0.05

        if tmean <= t_opt:
            return clamp((tmean - t_base) / (t_opt - t_base), 0.05, 1.0)

        return clamp((t_max - tmean) / (t_max - t_opt), 0.05, 1.0)

    def calculate_fpar(self, lai: Optional[float], ndvi: Optional[float]) -> float:
        """
        计算 fPAR：冠层吸收光合有效辐射比例。
        优先综合 LAI 和 NDVI。
        """
        values = []

        if lai is not None:
            lai = max(lai, 0.01)
            fpar_lai = 1.0 - math.exp(-self.k * lai)
            values.append(clamp(fpar_lai, 0.05, 0.95))

        if ndvi is not None:
            fpar_ndvi = 1.24 * ndvi - 0.168
            values.append(clamp(fpar_ndvi, 0.05, 0.95))

        if not values:
            # 没有 LAI 和 NDVI 时使用默认冠层参数
            return 0.65

        return sum(values) / len(values)

    def shade_factor(self, shade_degree: float) -> float:
        """
        遮阴修正因子。
        shade_degree 取值 0-1。
        数值越大，遮阴越强，有效辐射越低。
        """
        shade_degree = clamp(shade_degree, 0.0, 1.0)
        return clamp(1.0 - 0.45 * shade_degree, 0.55, 1.0)

    def estimate_et(
        self,
        radiation_mj: float,
        fpar: float,
        temp_factor: float,
        water_factor: float,
        wind_ms: float
    ) -> float:
        """
        简化 ET 估算。
        注意：这里是 MVP 阶段用于系统展示的简化估算，不是严格 Penman-Monteith。
        """
        wind_factor = clamp(0.85 + 0.08 * wind_ms, 0.8, 1.2)

        et0 = 0.408 * radiation_mj * 0.65 * (0.4 + 0.6 * temp_factor) * wind_factor

        actual_et = et0 * (0.2 + 0.8 * fpar) * (0.5 + 0.5 * water_factor)

        return round(max(actual_et, 0.0), 3)

    def growth_score(
        self,
        gpp: float,
        ndvi: Optional[float],
        water_factor: float,
        temp_factor: float,
        fpar: float
    ) -> float:
        """
        综合生成咖啡园长势评分。
        """
        gpp_score = clamp(gpp / 8.0 * 100.0, 0, 100)

        if ndvi is not None:
            ndvi_score = clamp((ndvi - 0.35) / (0.85 - 0.35) * 100.0, 0, 100)
        else:
            ndvi_score = clamp(fpar / 0.9 * 100.0, 0, 100)

        water_score = clamp(water_factor * 100.0, 0, 100)
        temp_score = clamp(temp_factor * 100.0, 0, 100)

        score = (
            0.35 * gpp_score +
            0.25 * ndvi_score +
            0.25 * water_score +
            0.15 * temp_score
        )

        return round(clamp(score, 0, 100), 2)

    def risk_level(self, score: float, water_factor: float, temp_factor: float) -> str:
        """
        生态风险等级。
        """
        if score < 45 or water_factor < 0.35 or temp_factor < 0.25:
            return "high"

        if score < 65 or water_factor < 0.55 or temp_factor < 0.5:
            return "medium"

        return "low"

    def risk_reasons(
        self,
        score: float,
        water_factor: float,
        temp_factor: float,
        shade_degree: float,
        ndvi: Optional[float]
    ) -> List[str]:
        """
        风险解释，用于后续 what/how/why 建议。
        """
        reasons = []

        if water_factor < 0.45:
            reasons.append("根区水分限制明显，可能降低冠层光合生产力")

        if temp_factor < 0.5:
            reasons.append("当前温度条件偏离咖啡适宜生长区间")

        if shade_degree > 0.65:
            reasons.append("遮阴程度较高，有效辐射输入下降")

        if ndvi is not None and ndvi < 0.5:
            reasons.append("NDVI 偏低，提示冠层长势可能下降")

        if score < 60:
            reasons.append("综合长势评分偏低，建议检查水分、病虫害和遮阴状态")

        if not reasons:
            reasons.append("冠层生态状态总体正常，维持当前管理")

        return reasons

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        BEPS-Lite 主入口。
        输入 payload，输出标准 BEPS-Lite 结果。
        """

        plot_id = payload.get("plot_id", "demo_plot")

        weather = payload.get("weather", [])
        if not weather:
            raise ValueError("weather 不能为空")

        # LAI 优先来自 APSIM，缺失时用默认值
        lai = payload.get("lai")
        if lai is None:
            lai = 2.5

        # NDVI 可来自遥感或样例数据，缺失允许为空
        ndvi = payload.get("ndvi")

        # 遮阴程度，0-1
        shade_degree = float(payload.get("shade_degree", 0.3))

        # 水分限制因子，优先来自 HYDRUS，缺失时用默认值
        water_factor = float(payload.get("water_factor", 0.8))
        water_factor = clamp(water_factor, 0.2, 1.0)

        fpar = self.calculate_fpar(lai, ndvi)
        shade = self.shade_factor(shade_degree)

        series = []

        for day in weather:
            date = day["date"]
            tmin = float(day["tmin"])
            tmax = float(day["tmax"])
            radiation_mj = float(day["radiation_mj"])
            wind_ms = float(day.get("wind_ms", 1.5))

            tmean = (tmin + tmax) / 2.0
            temp_factor = self.temperature_factor(tmean)

            par = radiation_mj * self.par_ratio

            # 简化 GPP 计算
            gpp = par * fpar * self.lue_max * temp_factor * water_factor * shade

            # 简化 NPP 计算
            npp = gpp * self.npp_ratio

            # 简化 ET 计算
            et = self.estimate_et(
                radiation_mj=radiation_mj,
                fpar=fpar,
                temp_factor=temp_factor,
                water_factor=water_factor,
                wind_ms=wind_ms
            )

            # 简化碳汇估计
            carbon_sink = npp * 10.0

            score = self.growth_score(
                gpp=gpp,
                ndvi=ndvi,
                water_factor=water_factor,
                temp_factor=temp_factor,
                fpar=fpar
            )

            risk = self.risk_level(score, water_factor, temp_factor)

            series.append({
                "date": date,
                "tmean": round(tmean, 2),
                "lai": round(lai, 3),
                "ndvi": round(ndvi, 3) if ndvi is not None else None,
                "fpar": round(fpar, 3),
                "gpp_gc_m2_day": round(gpp, 3),
                "npp_gc_m2_day": round(npp, 3),
                "et_mm_day": round(et, 3),
                "carbon_sink_kg_ha_day": round(carbon_sink, 3),
                "growth_score": score,
                "risk_level": risk
            })

        avg_gpp = sum(item["gpp_gc_m2_day"] for item in series) / len(series)
        avg_npp = sum(item["npp_gc_m2_day"] for item in series) / len(series)
        avg_et = sum(item["et_mm_day"] for item in series) / len(series)
        total_carbon = sum(item["carbon_sink_kg_ha_day"] for item in series)
        avg_score = sum(item["growth_score"] for item in series) / len(series)

        avg_temp_factor = sum(
            self.temperature_factor((float(d["tmin"]) + float(d["tmax"])) / 2.0)
            for d in weather
        ) / len(weather)

        final_risk = self.risk_level(avg_score, water_factor, avg_temp_factor)

        reasons = self.risk_reasons(
            score=avg_score,
            water_factor=water_factor,
            temp_factor=avg_temp_factor,
            shade_degree=shade_degree,
            ndvi=ndvi
        )

        return {
            "module": "BEPS-Lite",
            "status": "ok",
            "plot_id": plot_id,
            "input_summary": {
                "lai": lai,
                "ndvi": ndvi,
                "shade_degree": shade_degree,
                "water_factor": water_factor,
                "fpar": round(fpar, 3)
            },
            "summary": {
                "avg_gpp_gc_m2_day": round(avg_gpp, 3),
                "avg_npp_gc_m2_day": round(avg_npp, 3),
                "avg_et_mm_day": round(avg_et, 3),
                "total_carbon_sink_kg_ha": round(total_carbon, 3),
                "growth_score": round(avg_score, 2),
                "risk_level": final_risk,
                "risk_reasons": reasons
            },
            "series": series
        }


def run_beps_lite(payload: Dict[str, Any]) -> Dict[str, Any]:
    adapter = BepsLiteAdapter()
    return adapter.run(payload)