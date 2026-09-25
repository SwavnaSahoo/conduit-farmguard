from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class SignalRisk:
    key: str
    label: str
    risk: float
    weight: float
    value: float | None
    unit: str
    reason: str


def _clip(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


def _linear(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    if x1 == x0:
        return y1
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)


def temperature_risk(value: float) -> float:
    if value < 24: return 10
    if value < 28: return _clip(_linear(value, 24, 28, 15, 40))
    if value < 33: return _clip(_linear(value, 28, 33, 40, 75))
    if value < 38: return _clip(_linear(value, 33, 38, 75, 95))
    return 100


def humidity_dryness_risk(value: float) -> float:
    if value < 25: return 95
    if value < 40: return _clip(_linear(value, 25, 40, 95, 65))
    if value < 55: return _clip(_linear(value, 40, 55, 65, 35))
    if value < 70: return _clip(_linear(value, 55, 70, 35, 15))
    return 8


def rainfall_dryness_risk(recent_mm: float) -> float:
    if recent_mm <= 0.1: return 95
    if recent_mm <= 2: return 75
    if recent_mm <= 5: return 50
    if recent_mm <= 10: return 28
    return 10


def wbgt_risk(value: float) -> float:
    if value < 20: return 10
    if value < 24: return _clip(_linear(value, 20, 24, 15, 35))
    if value < 28: return _clip(_linear(value, 24, 28, 35, 60))
    if value < 31: return _clip(_linear(value, 28, 31, 60, 82))
    return 95


def heat_index_risk(value: float) -> float:
    return temperature_risk(value)


def _risk_level(score: float) -> str:
    if score < 31: return "LOW"
    if score < 61: return "MODERATE"
    if score < 81: return "HIGH"
    return "CRITICAL"


def _window_24h(df: pd.DataFrame) -> pd.DataFrame:
    latest_ts = df["timestamp"].max()
    window = df[df["timestamp"] >= latest_ts - pd.Timedelta(hours=24)]
    return window if len(window) >= 3 else df.tail(min(len(df), 96))


def _anomalies(df: pd.DataFrame) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    fields = {
        "temperature_c": ("Temperature", "°C"),
        "humidity_pct": ("Humidity", "%"),
        "wind_speed_ms": ("Wind speed", "m/s"),
        "pressure_hpa": ("Pressure", "hPa"),
        "heat_index_c": ("Heat index", "°C"),
        "wbgt_c": ("WBGT", "°C"),
    }
    for key, (label, unit) in fields.items():
        if key not in df.columns: continue
        s = df[key].dropna()
        if len(s) < 12: continue
        current = float(s.iloc[-1])
        baseline = s.iloc[:-1].tail(96)
        std = float(baseline.std(ddof=0))
        mean = float(baseline.mean())
        if std <= 1e-9: continue
        z = (current - mean) / std
        if abs(z) >= 2.0:
            direction = "above" if z > 0 else "below"
            output.append({
                "field": key, "label": label, "value": round(current, 2), "unit": unit,
                "z_score": round(float(z), 2),
                "message": f"{label} is unusually {direction} its recent baseline.",
            })
    return output


def assess(df: pd.DataFrame) -> dict[str, Any]:
    window = _window_24h(df)
    signals: list[SignalRisk] = []

    if "temperature_c" in window.columns and window["temperature_c"].notna().any():
        v = float(window["temperature_c"].max())
        signals.append(SignalRisk("temperature_c", "24h peak temperature", temperature_risk(v), 0.30, v, "°C",
                                  "Higher temperatures increase evaporative demand and can raise crop heat stress."))

    rain_col = "rainfall_today_mm" if "rainfall_today_mm" in window.columns else "rainfall_instant_mm" if "rainfall_instant_mm" in window.columns else None
    if rain_col and window[rain_col].notna().any():
        # Conduit documents separate rain gauges and daily/cumulative totals. Using the
        # maximum recent total avoids double-counting two gauges or repeated totals.
        v = float(window[rain_col].max())
        signals.append(SignalRisk(rain_col, "Recent rain signal", rainfall_dryness_risk(v), 0.35, v, "mm",
                                  "Low recent rainfall increases the need to verify field moisture before irrigation decisions."))

    if "humidity_pct" in window.columns and window["humidity_pct"].notna().any():
        v = float(window["humidity_pct"].min())
        signals.append(SignalRisk("humidity_pct", "24h minimum humidity", humidity_dryness_risk(v), 0.20, v, "%",
                                  "Low humidity increases atmospheric drying pressure."))

    if "wbgt_c" in window.columns and window["wbgt_c"].notna().any():
        v = float(window["wbgt_c"].max())
        signals.append(SignalRisk("wbgt_c", "24h peak WBGT", wbgt_risk(v), 0.15, v, "°C",
                                  "WBGT combines heat, moisture, wind and solar conditions into a heat-stress indicator."))
    elif "heat_index_c" in window.columns and window["heat_index_c"].notna().any():
        v = float(window["heat_index_c"].max())
        signals.append(SignalRisk("heat_index_c", "24h peak heat index", heat_index_risk(v), 0.15, v, "°C",
                                  "Heat index summarizes the combined effect of temperature and humidity."))

    if not signals:
        raise ValueError("No supported environmental fields found in the dataset.")

    total_weight = sum(s.weight for s in signals)
    score = round(_clip(sum(s.risk * s.weight for s in signals) / total_weight), 1)
    level = _risk_level(score)

    drivers = []
    for s in signals:
        nw = s.weight / total_weight
        drivers.append({
            "key": s.key, "label": s.label, "value": round(s.value, 2) if s.value is not None else None,
            "unit": s.unit, "risk": round(s.risk, 1), "weight": round(nw, 3),
            "contribution": round(s.risk * nw, 1), "reason": s.reason,
        })
    drivers.sort(key=lambda x: x["contribution"], reverse=True)

    has_soil = "soil_moisture_pct" in df.columns and df["soil_moisture_pct"].notna().any()
    if level == "LOW":
        action = "Continue monitoring"
        recommendation = "Recent weather signals do not show strong agricultural heat or drying stress. Continue routine field checks."
    elif level == "MODERATE":
        action = "Inspect field conditions"
        recommendation = "Weather signals suggest some drying or heat pressure. Check crop condition and soil moisture before deciding whether irrigation is needed."
    else:
        action = "Prioritize field inspection"
        recommendation = "Recent weather signals indicate elevated agricultural stress. Inspect crop condition and soil moisture promptly, then prioritize irrigation only where field checks confirm moisture deficit."

    if any(d["key"] in {"temperature_c", "wbgt_c", "heat_index_c"} and d["risk"] >= 70 for d in drivers):
        recommendation += " If irrigation is needed, cooler morning or evening hours may reduce evaporative losses."

    caveat = (
        "Prototype decision support using Conduit weather-station observations. Thresholds are transparent hackathon rules, not locally validated agronomic prescriptions."
    )
    if not has_soil:
        caveat += " This export contains no soil-moisture field, so FarmGuard recommends field verification rather than asserting that irrigation is required."

    return {
        "score": score, "level": level, "action": action, "recommendation": recommendation,
        "drivers": drivers, "anomalies": _anomalies(df), "has_soil_moisture": has_soil,
        "caveat": caveat, "window": "latest 24 hours",
    }
