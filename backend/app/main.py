from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .ai_advisor import answer_question
from .config import FRONTEND_ORIGINS
from .data_loader import load_conduit_data
from .risk_engine import assess
from .schemas import AskRequest

app = FastAPI(
    title="Conduit FarmGuard API",
    version="1.2.0",
    description="Turns JKUAT Conduit weather-station readings into transparent agricultural stress decision support.",
)

app.add_middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _safe_value(value: Any):
    if pd.isna(value): return None
    if isinstance(value, pd.Timestamp): return value.isoformat()
    if hasattr(value, "item"):
        try: return value.item()
        except Exception: pass
    return value


def _row_to_dict(row: pd.Series) -> dict[str, Any]:
    return {str(k): _safe_value(v) for k, v in row.to_dict().items()}



def _recent_conditions(history_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Create a small, data-driven event timeline from the latest 24 hours.

    Events are descriptive summaries of observed station readings; they do not
    add new agronomic claims or change the risk score.
    """
    events: list[dict[str, Any]] = []
    if history_df.empty:
        return events

    def add_event(kind: str, title: str, detail: str, ts: Any):
        if ts is None or pd.isna(ts):
            return
        events.append({
            "kind": kind,
            "title": title,
            "detail": detail,
            "timestamp": _safe_value(ts),
        })

    latest = history_df.iloc[-1]
    humidity = latest.get("humidity_pct")
    wind = latest.get("wind_speed_ms")
    if pd.notna(humidity) and pd.notna(wind) and float(humidity) >= 75 and float(wind) <= 0.6:
        add_event(
            "conditions",
            "Calm, humid conditions",
            f"{float(humidity):.1f}% humidity • {float(wind):.1f} m/s wind",
            latest.get("timestamp"),
        )
    else:
        parts = []
        if pd.notna(humidity): parts.append(f"{float(humidity):.1f}% humidity")
        if pd.notna(wind): parts.append(f"{float(wind):.1f} m/s wind")
        temp = latest.get("temperature_c")
        if pd.notna(temp): parts.append(f"{float(temp):.1f}°C")
        add_event("conditions", "Latest station update", " • ".join(parts), latest.get("timestamp"))

    heat_col = "wbgt_c" if "wbgt_c" in history_df.columns and history_df["wbgt_c"].notna().any() else "temperature_c"
    if heat_col in history_df.columns and history_df[heat_col].notna().any():
        idx = history_df[heat_col].idxmax()
        row = history_df.loc[idx]
        parts = []
        if pd.notna(row.get("wbgt_c")): parts.append(f"WBGT {float(row['wbgt_c']):.1f}°C")
        if pd.notna(row.get("temperature_c")): parts.append(f"Temp {float(row['temperature_c']):.1f}°C")
        add_event("heat", "Peak heat pressure observed", " • ".join(parts), row.get("timestamp"))

    rain_col = "rainfall_today_mm" if "rainfall_today_mm" in history_df.columns and history_df["rainfall_today_mm"].notna().any() else "rainfall_instant_mm" if "rainfall_instant_mm" in history_df.columns and history_df["rainfall_instant_mm"].notna().any() else None
    if rain_col:
        idx = history_df[rain_col].idxmax()
        row = history_df.loc[idx]
        value = float(row[rain_col])
        add_event("rain", "Strongest rain-gauge signal", f"{value:.1f} mm signal observed", row.get("timestamp"))

    if "humidity_pct" in history_df.columns and history_df["humidity_pct"].notna().sum() >= 6:
        hs = history_df["humidity_pct"].dropna()
        min_idx = hs.idxmin()
        min_value = float(hs.loc[min_idx])
        after = history_df.loc[min_idx:]
        recovered = after[after["humidity_pct"] >= min_value + 15] if "humidity_pct" in after.columns else pd.DataFrame()
        if not recovered.empty:
            row = recovered.iloc[0]
            add_event(
                "humidity",
                "Humidity recovery detected",
                f"Humidity rose from {min_value:.1f}% to {float(row['humidity_pct']):.1f}%",
                row.get("timestamp"),
            )

    # Deduplicate events that resolve to the same title and keep the newest first.
    deduped = []
    seen = set()
    for event in sorted(events, key=lambda e: pd.Timestamp(e["timestamp"]), reverse=True):
        if event["title"] in seen:
            continue
        seen.add(event["title"])
        deduped.append(event)
    return deduped[:4]

def _dashboard_payload() -> dict[str, Any]:
    df, source = load_conduit_data()
    assessment = assess(df)
    latest = _row_to_dict(df.iloc[-1])

    history_cols = [c for c in [
        "timestamp", "temperature_c", "humidity_pct", "rainfall_instant_mm", "rainfall_today_mm",
        "soil_moisture_pct", "uv_index", "uv_raw", "wind_speed_ms", "pressure_hpa",
        "heat_index_c", "wet_bulb_c", "wbgt_c",
    ] if c in df.columns]

    # Build the chart from an actual timestamp-based 24-hour window instead of
    # assuming a fixed number of observations. The Conduit export is usually
    # close to 15-minute cadence, but the dashboard should remain correct if
    # readings are skipped or the cadence changes.
    latest_ts = df["timestamp"].max()
    history_df = df[df["timestamp"] >= latest_ts - pd.Timedelta(hours=24)][history_cols]
    if history_df.empty:
        history_df = df[history_cols].tail(96)
    history = [{k: _safe_value(v) for k, v in row.items()} for row in history_df.to_dict(orient="records")]
    recent_conditions = _recent_conditions(history_df)

    data_quality = {
        "readings_used": len(df),
        "latest_timestamp": latest.get("timestamp"),
        "fields_available": source.get("supported_fields", []),
        "soil_moisture_available": assessment["has_soil_moisture"],
        "coverage_start": source.get("coverage_start"),
        "coverage_end": source.get("coverage_end"),
    }
    return {
        "project": "Conduit FarmGuard",
        "source": source,
        "latest": latest,
        "assessment": assessment,
        "history": history,
        "recent_conditions": recent_conditions,
        "data_quality": data_quality,
    }


@app.get("/")
def root(): return {"name": "Conduit FarmGuard API", "docs": "/docs"}

@app.get("/api/health")
def health():
    try:
        df, source = load_conduit_data()
        return {"status": "ok", "rows": len(df), "source": source}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/dashboard")
def dashboard():
    try: return _dashboard_payload()
    except Exception as exc: raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/ask")
def ask(payload: AskRequest):
    try:
        dashboard = _dashboard_payload()
        return answer_question(payload.question, dashboard["assessment"], dashboard["latest"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
