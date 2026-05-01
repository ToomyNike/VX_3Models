from datetime import date, timedelta


def get_weather_series(latitude=None, longitude=None, days=7):
    today = date.today()
    base_tavg = 24.5
    series = []
    for i in range(days):
        current = today + timedelta(days=i)
        rain = 0 if i not in [2, 5] else 8 + i
        tavg = base_tavg + (i % 3 - 1) * 0.8
        series.append(
            {
                "date": current.isoformat(),
                "tmax": round(tavg + 5.8, 1),
                "tmin": round(tavg - 5.9, 1),
                "tavg": round(tavg, 1),
                "rain_mm": rain,
                "radiation_mj": round(18.5 - i * 0.25, 2),
                "vpd_kpa": round(1.2 + i * 0.04, 2),
                "wind_m_s": 1.5,
                "source": "demo",
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    return series
