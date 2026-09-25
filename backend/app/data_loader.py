from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .config import CONDUIT_API_TOKEN, CONDUIT_API_URL, CONDUIT_CSV_PATH, DATA_MODE


COLUMN_ALIASES = {
    "timestamp": ["timestamp", "datetime", "date_time", "time", "date", "recorded_at", "created_at", "last_update_time", "ts"],
    "temperature_c": ["temperature_c", "temperature", "temp", "temp_c", "air_temperature", "sht_temperature", "temp_sht", "bmx_temperature_1", "mcp_temperature_1"],
    "humidity_pct": ["humidity_pct", "humidity", "relative_humidity", "sht_humidity", "humidity_sht", "rh"],
    "uv_index": ["uv_index", "uvi", "ultraviolet_index"],
    "uv_raw": ["uv_raw", "uv", "ultraviolet", "si1145_uv", "si1145_ultraviolet"],
    "visible_raw": ["visible_raw", "si1145_vis", "visible", "visible_light"],
    "infrared_raw": ["infrared_raw", "si1145_ir", "infrared", "ir"],
    "soil_moisture_pct": ["soil_moisture_pct", "soil_moisture", "soil moisture", "soilmoisture", "soil_water_content", "vwc"],
    "wind_speed_ms": ["wind_speed_ms", "wind_speed", "windspeed", "wind_m_s", "wind", "wind_spd"],
    "wind_direction_deg": ["wind_direction_deg", "wind_direction", "wind_dir"],
    "wind_gust_ms": ["wind_gust_ms", "wind_gust", "gust_speed"],
    "pressure_hpa": ["pressure_hpa", "pressure", "press_bmx", "bmx_pressure_1"],
    "heat_index_c": ["heat_index_c", "heat_index", "heat_idx"],
    "wet_bulb_c": ["wet_bulb_c", "wet_bulb", "wet_bulb_temp"],
    "wbgt_c": ["wbgt_c", "wbgt", "wet_bulb_globe_temp"],
    "rain_gauge_1_mm": ["rg1", "rain_gauge_1", "rain_gauge_1_mm"],
    "rain_gauge_2_mm": ["rg2", "rain_gauge_2", "rain_gauge_2_mm"],
    "rain_total_today_1_mm": ["rg1tt", "rain_gauge_1_total_today", "rain_total_today_1"],
    "rain_total_today_2_mm": ["rg2tt", "rain_gauge_2_total_today", "rain_total_today_2"],
    "rain_total_prior_1_mm": ["rg1tp", "rain_gauge_1_total_prior", "rain_total_prior_1"],
    "rain_total_prior_2_mm": ["rg2tp", "rain_gauge_2_total_prior", "rain_total_prior_2"],
}


def _canonicalize_name(name: str) -> str:
    return (
        name.strip().lower()
        .replace("%", "pct")
        .replace("°", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
    )


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    original = list(df.columns)
    normalized_map = {_canonicalize_name(c): c for c in original}

    rename: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _canonicalize_name(alias)
            if key in normalized_map:
                rename[normalized_map[key]] = canonical
                break

    df = df.rename(columns=rename).copy()

    if "timestamp" not in df.columns:
        df["timestamp"] = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("h"), periods=len(df), freq="h")
    else:
        parsed = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        if parsed.notna().sum() == 0:
            parsed = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("h"), periods=len(df), freq="h")
        df["timestamp"] = parsed

    numeric_cols = [c for c in COLUMN_ALIASES if c != "timestamp"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # The public Conduit station documentation describes two rain gauges plus
    # "Total Today" and "Total Prior" values. Keep both gauges visible and
    # derive conservative combined fields without summing duplicate gauge totals.
    if any(c in df.columns for c in ["rain_gauge_1_mm", "rain_gauge_2_mm"]):
        cols = [c for c in ["rain_gauge_1_mm", "rain_gauge_2_mm"] if c in df.columns]
        df["rainfall_instant_mm"] = df[cols].max(axis=1, skipna=True)
    if any(c in df.columns for c in ["rain_total_today_1_mm", "rain_total_today_2_mm"]):
        cols = [c for c in ["rain_total_today_1_mm", "rain_total_today_2_mm"] if c in df.columns]
        df["rainfall_today_mm"] = df[cols].max(axis=1, skipna=True)
    if any(c in df.columns for c in ["rain_total_prior_1_mm", "rain_total_prior_2_mm"]):
        cols = [c for c in ["rain_total_prior_1_mm", "rain_total_prior_2_mm"] if c in df.columns]
        df["rainfall_prior_mm"] = df[cols].max(axis=1, skipna=True)

    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def _load_csv(path_or_url: str) -> pd.DataFrame:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        resp = requests.get(path_or_url, timeout=20)
        resp.raise_for_status()
        return pd.read_csv(StringIO(resp.text))
    path = Path(path_or_url)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path)


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("Unsupported API response. Expected JSON object or list.")
    for key in ("data", "results", "records", "readings", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    if payload and all(not isinstance(v, (list, dict)) for v in payload.values()):
        return [payload]
    raise ValueError("Could not find a list of readings in API response.")


def _load_api() -> pd.DataFrame:
    if not CONDUIT_API_URL:
        raise ValueError("DATA_MODE=api but CONDUIT_API_URL is empty.")
    headers = {"Accept": "application/json"}
    if CONDUIT_API_TOKEN:
        headers["Authorization"] = f"Bearer {CONDUIT_API_TOKEN}"
    resp = requests.get(CONDUIT_API_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    return pd.DataFrame(_extract_records(resp.json()))


def load_conduit_data() -> tuple[pd.DataFrame, dict[str, Any]]:
    if DATA_MODE == "sample":
        raw = _load_csv(CONDUIT_CSV_PATH)
        source = {"mode": "sample", "label": "Demo dataset (Conduit-shaped)", "is_live": False}
    elif DATA_MODE == "csv":
        raw = _load_csv(CONDUIT_CSV_PATH)
        source = {"mode": "csv", "label": "JKUAT Conduit CSV export", "is_live": False}
    elif DATA_MODE == "api":
        raw = _load_api()
        source = {"mode": "api", "label": "JKUAT Conduit API", "is_live": True}
    else:
        raise ValueError("DATA_MODE must be sample, csv, or api")

    df = _normalize_columns(raw)
    if len(df) < 3:
        raise ValueError("Need at least 3 readings to calculate trends.")

    supported_candidates = [
        "temperature_c", "humidity_pct", "rainfall_instant_mm", "rainfall_today_mm",
        "uv_index", "uv_raw", "soil_moisture_pct", "wind_speed_ms", "pressure_hpa",
        "heat_index_c", "wet_bulb_c", "wbgt_c", "visible_raw", "infrared_raw",
    ]
    source["supported_fields"] = [c for c in supported_candidates if c in df.columns and df[c].notna().any()]
    source["row_count"] = len(df)
    source["coverage_start"] = df["timestamp"].min().isoformat()
    source["coverage_end"] = df["timestamp"].max().isoformat()
    return df, source
