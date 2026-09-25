# Conduit FarmGuard — visual polish build

This version is configured around the **actual Conduit export supplied for the hackathon** (`backend/data/conduit_weather_sep1_23.csv`).

## What the uploaded data contains

The file has **2,184 readings** from **Sep 1 through Sep 23, 2026** with 22 raw fields, including:

- `temp_sht`, `humidity_sht`
- `rg1`, `rg2`, `rg1tt`, `rg2tt`, `rg1tp`, `rg2tp`
- `press_bmx`
- `si1145_vis`, `si1145_ir`, `si1145_uv`
- `wind_spd`, `wind_dir`, `wind_gust`, `wind_gust_dir`
- `heat_idx`, `wet_bulb_temp`, `wet_bulb_globe_temp`

This export **does not contain a soil-moisture field**, so FarmGuard does not claim that irrigation is required. It converts weather-station signals into an agricultural heat/drying stress score and recommends field/soil verification before irrigation decisions.

## Run

Terminal 1:

```bash
cd ~/Downloads/conduit-farmguard-visuals
./run_backend.sh
```

Terminal 2:

```bash
cd ~/Downloads/conduit-farmguard-visuals
./run_frontend.sh
```

Open `http://localhost:5173`.

The backend defaults to:

```env
DATA_MODE=csv
CONDUIT_CSV_PATH=./data/conduit_weather_sep1_23.csv
```

## Risk logic

The deterministic engine evaluates the **latest 24-hour window**, using whichever fields are present:

- 24h peak SHT temperature
- recent rain-gauge total signal
- 24h minimum SHT humidity
- 24h peak WBGT (or heat index as fallback)

The score is transparent in the “Why this score?” panel. Gemini, if enabled, only explains the already-calculated result and cannot alter the score.

## Rainfall handling

The Conduit public documentation describes two rain gauges with instantaneous, “Total Today,” and “Total Prior” values. The loader maps the six exported rain fields accordingly. To avoid double-counting repeated/cross-gauge totals, the risk engine uses the maximum recent total signal rather than summing both gauges.

## Optional Gemini

Edit `backend/.env` after first run:

```env
GEMINI_API_KEY=YOUR_KEY
```

Without a key, the built-in local explanation still works.

## Final dashboard refinements

This build uses a timestamp-based **latest 24-hour** chart window rather than assuming a fixed observation count. The top metric row also surfaces the risk-engine's **24h rain signal** and **24h peak WBGT** values so the summary cards match the signals used in the explainability panel.


## Added visual decision-support modules

This build adds two presentation-focused features without changing the core risk formula:

- **Recommended field action card** with four visual field-check steps: crop leaf stress, manual moisture confirmation, irrigation-need inspection, and a next-morning recheck.
- **Recent conditions timeline** generated from the actual latest 24-hour Conduit readings. It surfaces the latest station state, peak heat pressure, strongest rain-gauge signal, and a humidity-recovery event when the data supports one.

The timeline is descriptive only. It does **not** change the agricultural weather-stress score.
