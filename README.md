# 🌱 Conduit FarmGuard

### Turning environmental sensor data into explainable agricultural decisions.

Conduit FarmGuard is a decision-support dashboard that transforms real Conduit weather-station data into an interpretable agricultural heat and drying stress signal, explains what is driving that score, and recommends what to check in the field next.

Instead of stopping at raw sensor readings, FarmGuard asks:

**What does this environmental data mean for the field, and what should I check next?**

---

## The Problem

Environmental sensors generate useful data, but raw measurements do not automatically translate into useful agricultural decisions.

Temperature, humidity, rainfall, wind, and heat-stress indicators can all matter together. Someone still has to interpret those signals and decide whether conditions require attention.

FarmGuard helps bridge the gap between:

**Data → Signal → Explanation → Action**

The goal is not to replace agronomic judgment. It is to make environmental data easier to interpret before a field decision is made.

---

## What FarmGuard Does

FarmGuard processes the supplied Conduit weather-station export and converts recent conditions into a simple agricultural weather-stress assessment.

The dashboard provides:

* Weather Stress Score
* Low / Moderate / High classification
* Latest environmental snapshot
* 24-hour heat and moisture trends
* Temperature, humidity, rainfall and WBGT signals
* Explainable “Why this score?” breakdown
* Recommended next field checks
* Recent conditions timeline
* Optional Gemini-generated explanation

---

## From Data to Action

CONDUIT SENSOR DATA
↓
NORMALIZE + PROCESS
↓
LATEST 24-HOUR SIGNALS
↓
DETERMINISTIC RISK ENGINE
↓
WEATHER STRESS SCORE
↓
EXPLAIN WHY
↓
RECOMMENDED FIELD CHECK

FarmGuard separates the core score from the AI explanation.

The numerical risk assessment is calculated deterministically from sensor data. Gemini, when enabled, explains the already-calculated result in natural language but cannot change the score.

---

## Real Conduit Data

This project is configured around the actual Conduit export supplied for the hackathon:

backend/data/conduit_weather_sep1_23.csv

The dataset contains:

* 2,184 readings
* Sep 1 through Sep 23, 2026
* 22 raw fields

Including:

* temp_sht, humidity_sht
* rg1, rg2, rg1tt, rg2tt, rg1tp, rg2tp
* press_bmx
* si1145_vis, si1145_ir, si1145_uv
* wind_spd, wind_dir, wind_gust, wind_gust_dir
* heat_idx
* wet_bulb_temp
* wet_bulb_globe_temp

FarmGuard evaluates the latest timestamp-based 24-hour window instead of assuming a fixed observation count.

---

## Risk Logic

The deterministic engine evaluates the latest 24-hour conditions using whichever supported fields are available.

Signals include:

* 24-hour peak SHT temperature
* 24-hour minimum SHT humidity
* Recent rain-gauge signal
* 24-hour peak Wet Bulb Globe Temperature
* Heat index as a fallback where appropriate

The dashboard exposes these contributors through the “Why this score?” panel so the assessment can be inspected instead of operating as a black box.

---

## Rainfall Handling

The Conduit data contains readings from two rain gauges with instantaneous and cumulative values.

To avoid double-counting repeated or cross-gauge totals, FarmGuard uses the maximum recent total rain signal rather than simply summing both gauges.

This keeps the rainfall contribution to the stress score conservative and transparent.

---

## An Important Design Decision

The supplied Conduit export does not contain a soil-moisture field.

Because of that, FarmGuard does not make unsupported claims such as:

“Irrigation is required.”

Instead, it evaluates available weather signals for potential heat or drying pressure and recommends verifying crop condition and soil moisture before deciding whether irrigation is necessary.

For example:

**Weather signals suggest some drying or heat pressure. Check crop condition and soil moisture before deciding whether irrigation is needed.**

FarmGuard is designed as decision support, not an automated agronomic prescription.

---

## Recommended Field Actions

Rather than stopping at a score, FarmGuard translates the result into practical field checks.

The current prototype can recommend actions such as:

1. Inspect crop leaves for visible heat or water stress
2. Check field or soil moisture manually
3. Assess whether irrigation is actually needed
4. Recheck conditions as the environment changes

---

## Recent Conditions Timeline

FarmGuard also generates a descriptive timeline from the latest 24 hours of Conduit readings.

It can surface:

* Latest station condition
* Peak heat pressure
* Strongest recent rain-gauge signal
* Humidity-recovery events when supported by the data

The timeline provides context only and does not alter the weather-stress score.

---

## Tech Stack

### Backend

* Python
* FastAPI
* Pandas
* NumPy
* Uvicorn
* Google GenAI SDK

### Frontend

* React
* TypeScript
* Vite
* Recharts
* Lucide React

### AI

* Gemini

### Data

* Conduit weather-station CSV export

---

## Architecture

Conduit Weather Data
↓
Python + Pandas Data Processing
↓
Deterministic Risk Engine
↓
Temperature + Humidity + Rain + WBGT / Heat Index
↓
FastAPI
↓
React Dashboard
↓
Risk Score + Environmental Snapshot + 24h Trends + Why This Score? + Recommended Action
↓
Optional Gemini Explanation

---

## Run Locally

### Backend

cd ~/Downloads/conduit-farmguard-visuals
./run_backend.sh

### Frontend

Open a second terminal:

cd ~/Downloads/conduit-farmguard-visuals
./run_frontend.sh

Then open:

[http://localhost:5173](http://localhost:5173)

---

## Environment Variables

The backend defaults to:

DATA_MODE=csv
CONDUIT_CSV_PATH=./data/conduit_weather_sep1_23.csv

Gemini is optional.

Add your key locally in:

backend/.env

GEMINI_API_KEY=YOUR_KEY

Without a Gemini API key, FarmGuard’s deterministic analysis still works and a local explanation can be used.

Real .env files should never be committed.

---

## Current Limitations

FarmGuard is a hackathon prototype and is not a validated agronomic recommendation system.

Current limitations include:

* No soil-moisture field in the supplied Conduit export
* Risk thresholds are prototype rules rather than locally validated agronomic thresholds
* Recommendations require field verification
* The system currently evaluates environmental stress rather than crop-specific physiology
* It does not replace professional agronomic advice

These limitations are surfaced intentionally.

---

## Future Scope

FarmGuard could be extended with:

* Live Conduit sensor ingestion
* Soil-moisture sensors
* Crop-specific thresholds
* Locally calibrated agronomic models
* Forecast integration
* Automated alerts
* Field-level sensor networks
* Historical comparisons
* Farmer feedback loops
* Mobile-first field experience
* Multilingual explanations

---

## Why FarmGuard?

A weather station tells us:

**What was measured?**

FarmGuard tries to answer the next question:

**What should I pay attention to because of those measurements?**

### Data → Signal → Explanation → Action

---

## Built for the Conduit Hackathon

Conduit FarmGuard was created as a hackathon prototype exploring how environmental sensor data can become clearer, more explainable, and more actionable for agricultural decision-making.

### Built by

**Swavna Sahoo**

GitHub:
[https://github.com/SwavnaSahoo/conduit-farmguard](https://github.com/SwavnaSahoo/conduit-farmguard)
