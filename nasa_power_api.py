# nasa_power_api.py
# Converted from your Tkinter app to a FastAPI API exposing POWER fetch, forecasting, geocode, and single-date classification.
# Run with: uvicorn nasa_power_api:app --reload

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import urllib.request, urllib.error, urllib.parse, json, csv, datetime, os, math
import numpy as np
from fastapi.middleware.cors import CORSMiddleware

# ---------------- Utilities ----------------
def day_of_year(d): return (d - datetime.date(d.year, 1, 1)).days + 1
def add_months(dt, months):
    m = dt.month - 1 + months; y = dt.year + m // 12; mo = m % 12 + 1
    d = min(dt.day, __import__("calendar").monthrange(y, mo)[1]); return datetime.date(y, mo, d)

# ---------------- HTTP helpers ----------------
def _download_url_bytes(url, token=None, timeout=60):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "NASA-Power-API/1.0 (+https://example.org)")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.getcode()

# ---------------- POWER JSON parsing & robust selection ----------------
def parse_power_json_to_series(j, parameter_key):
    try:
        pdata = j['properties']['parameter'][parameter_key]
    except Exception:
        raise ValueError(f"No parameter {parameter_key} in POWER JSON response.")
    dates, vals = [], []
    for k, v in sorted(pdata.items()):
        if len(k) != 8:
            continue
        try:
            dt = datetime.date(int(k[:4]), int(k[4:6]), int(k[6:8]))
        except Exception:
            continue
        try:
            val = float(v)
            if val == -999 or math.isnan(val):
                val = np.nan
        except:
            val = np.nan
        dates.append(dt); vals.append(val)
    if len(dates) == 0:
        raise ValueError("No numeric date rows found in POWER JSON for parameter " + parameter_key)
    return dates, np.array(vals, dtype=float)

def choose_best_key_for_target(j, desired_target):
    try:
        keys = list(j['properties']['parameter'].keys())
    except Exception:
        return None
    lower_keys = [k.lower() for k in keys]
    for k in keys:
        if k.upper() == desired_target.upper():
            return k
    target = desired_target.lower()
    if 'prec' in target or 'prectot' in target:
        for i, k in enumerate(lower_keys):
            if 'prec' in k or 'prectot' in k: return keys[i]
    if 'aod' in target:
        for i, k in enumerate(lower_keys):
            if 'aod' in k or 'aerosol' in k or 'aod550' in k: return keys[i]
    if 't2m' in target or 't2' in target or 'temp' in target:
        for i, k in enumerate(lower_keys):
            if 't2m' in k or k.endswith('t2m') or 'temp' in k or 'air_temperature' in k: return keys[i]
    if 'ws' in target or 'wind' in target:
        for i, k in enumerate(lower_keys):
            if 'ws2m' in k or 'wind' in k or 'ws' in k: return keys[i]
    for i, k in enumerate(lower_keys):
        if desired_target.lower() in k:
            return keys[i]
    return None

def fetch_power_json_with_fallback_and_key_mapping(lat, lon, desired_params, start_yyyymmdd, end_yyyymmdd, token=None, timeout=60):
    base = "https://power.larc.nasa.gov/api/temporal/daily/point"
    candidate_names = set()
    for p in desired_params:
        candidate_names.add(p)
    extra = [
        'PRECTOTCORR', 'PRECTOTCORR8', 'PRECTOT_C', 'PRECTOT_CORR',
        'AOD550', 'AOD_550', 'AOD_470', 'AOD550_AEROSOL', 'AOD',
        'T2M', 'T2', 'T2M_AVG', 'TMP', 'AIR_TEMPERATURE',
        'WS2M', 'WIND', 'WS'
    ]
    for e in extra: candidate_names.add(e)
    paramstr = ",".join(sorted(candidate_names))
    url_multi = f"{base}?parameters={paramstr}&community=AG&longitude={lon:.6f}&latitude={lat:.6f}&start={start_yyyymmdd}&end={end_yyyymmdd}&format=JSON&header=true"
    out = {p: (None, None) for p in desired_params}
    try:
        raw, _ = _download_url_bytes(url_multi, token=token, timeout=timeout)
        j = json.loads(raw.decode('utf-8'))
        for p in desired_params:
            key = choose_best_key_for_target(j, p)
            if key:
                try:
                    dates, vals = parse_power_json_to_series(j, key)
                    out[p] = (dates, vals)
                except Exception:
                    out[p] = (None, None)
        for p in desired_params:
            if out[p][0] is not None:
                continue
            tries = [p]
            if p.upper() == 'PRECTOT':
                tries += ['PRECTOTCORR', 'PRECTOTCORR8', 'PRECTOT_C', 'PRECTOT_CORR']
            if p.upper() == 'AOD':
                tries += ['AOD550', 'AOD_550', 'AOD_470', 'AOD550_AEROSOL', 'AOD']
            if p.upper() == 'T2M':
                tries += ['T2M', 'T2', 'T2M_AVG', 'TMP', 'AIR_TEMPERATURE']
            if p.upper() == 'WS2M':
                tries += ['WS2M', 'WIND', 'WS']
            fetched = False
            for pr in tries:
                try:
                    url_p = f"{base}?parameters={pr}&community=AG&longitude={lon:.6f}&latitude={lat:.6f}&start={start_yyyymmdd}&end={end_yyyymmdd}&format=JSON&header=true"
                    raw_p, _ = _download_url_bytes(url_p, token=token, timeout=timeout)
                    jp = json.loads(raw_p.decode('utf-8'))
                    key = choose_best_key_for_target(jp, p) or pr
                    dates, vals = parse_power_json_to_series(jp, key)
                    out[p] = (dates, vals)
                    fetched = True
                    break
                except Exception:
                    continue
            if not fetched:
                out[p] = (None, None)
        return out
    except urllib.error.HTTPError as he:
        per = {}
        for p in desired_params:
            per[p] = (None, None)
            tries = [p]
            if p.upper() == 'PRECTOT':
                tries += ['PRECTOTCORR', 'PRECTOTCORR8']
            if p.upper() == 'AOD':
                tries += ['AOD550', 'AOD_550', 'AOD']
            for pr in tries:
                try:
                    url_p = f"{base}?parameters={pr}&community=AG&longitude={lon:.6f}&latitude={lat:.6f}&start={start_yyyymmdd}&end={end_yyyymmdd}&format=JSON&header=true"
                    raw_p, _ = _download_url_bytes(url_p, token=token, timeout=timeout)
                    jp = json.loads(raw_p.decode('utf-8'))
                    key = choose_best_key_for_target(jp, p) or pr
                    dates, vals = parse_power_json_to_series(jp, key)
                    per[p] = (dates, vals)
                    break
                except Exception:
                    continue
        return per
    except Exception as e:
        per = {}
        for p in desired_params:
            per[p] = (None, None)
            tries = [p]
            if p.upper() == 'PRECTOT':
                tries += ['PRECTOTCORR', 'PRECTOTCORR8']
            if p.upper() == 'AOD':
                tries += ['AOD550', 'AOD_550', 'AOD']
            for pr in tries:
                try:
                    url_p = f"{base}?parameters={pr}&community=AG&longitude={lon:.6f}&latitude={lat:.6f}&start={start_yyyymmdd}&end={end_yyyymmdd}&format=JSON&header=true"
                    raw_p, _ = _download_url_bytes(url_p, token=token, timeout=timeout)
                    jp = json.loads(raw_p.decode('utf-8'))
                    key = choose_best_key_for_target(jp, p) or pr
                    dates, vals = parse_power_json_to_series(jp, key)
                    per[p] = (dates, vals)
                    break
                except Exception:
                    continue
        return per

# ---------------- Forecast helpers ----------------
def compute_daily_forecast_from_hist(hist_dates, hist_values, start_date, ndays, window=7, threshold=1.0):
    hist_doy = np.array([day_of_year(d) for d in hist_dates])
    future_dates = [start_date + datetime.timedelta(days=i) for i in range(ndays)]
    means = np.full(ndays, np.nan); probs = np.full(ndays, np.nan); nsamps = np.zeros(ndays, dtype=int)
    for k, fd in enumerate(future_dates):
        qdoy = day_of_year(fd)
        diffs = np.abs(hist_doy - qdoy)
        diffs = np.minimum(diffs, 365 - diffs)
        mask = diffs <= window
        samples = hist_values[mask]
        samples = samples[~np.isnan(samples)]
        nsamps[k] = len(samples)
        if len(samples) > 0:
            means[k] = float(np.mean(samples)); probs[k] = float(np.sum(samples > threshold) / len(samples))
    return {'dates': future_dates, 'mean': means, 'prob': probs, 'nsamples': nsamps}

def aggregate_to_monthly(hist_dates, hist_values):
    pairs = [(d.year, d.month) for d in hist_dates]
    unique = sorted(list(set(pairs)))
    monthly, centers = [], []
    for yr, mo in unique:
        idx = [i for i, (y, m) in enumerate(pairs) if y == yr and m == mo]
        total = np.nansum(hist_values[idx])
        monthly.append(float(total)); centers.append(datetime.date(yr, mo, 15))
    return centers, np.array(monthly, dtype=float)

# ---------------- Single-date classification ----------------
def classify_conditions_for_date_from_hist(hist_map, lon, lat, date_obj, window=7, thresholds=None, token=None):
    """
    hist_map: dict param -> (dates_list or None, numpy array or None)
    This function won't attempt to fetch on-the-fly; caller may fetch missing data.
    Returns (summary_str, details_dict)
    """
    if thresholds is None:
        thresholds = {'hot_c': 35.0, 'cold_c': 5.0, 'wind_ms': 10.0, 'rain_mm': 5.0, 'aod': 0.3}
    res = {}
    problems = []
    def compute_prob_for_series(hist_dates, hist_vals, target_date, window, thresh=None, greater=True):
        if hist_dates is None: return None
        hdoy = np.array([day_of_year(d) for d in hist_dates])
        qdoy = day_of_year(target_date)
        diffs = np.abs(hdoy - qdoy)
        diffs = np.minimum(diffs, 365 - diffs)
        mask = diffs <= window
        samples = hist_vals[mask]
        samples = samples[~np.isnan(samples)]
        n = len(samples)
        if n == 0: return {'n':0, 'mean':None, 'prob':None}
        meanv = float(np.mean(samples))
        if thresh is None:
            prob = None
        else:
            if greater:
                prob = float(np.sum(samples > thresh) / n)
            else:
                prob = float(np.sum(samples < thresh) / n)
        return {'n':n, 'mean':meanv, 'prob':prob}
    need_params = ['T2M','PRECTOT','WS2M','AOD']
    # Temperature
    td = hist_map.get('T2M', (None, None))
    tp = compute_prob_for_series(td[0], td[1], date_obj, window, thresh=thresholds['hot_c'], greater=True) if td[0] is not None else None
    tc = compute_prob_for_series(td[0], td[1], date_obj, window, thresh=thresholds['cold_c'], greater=False) if td[0] is not None else None
    if tp is None or tc is None:
        res['Temperature'] = 'No data'
    else:
        res['Temperature_samples'] = f"{tp['n']}"
        res['Temp_mean_degC'] = f"{tp['mean']:.2f}" if tp['mean'] is not None else 'n/a'
        res['Prob_hot_>{:.1f}C'.format(thresholds['hot_c'])] = f"{tp['prob']:.3f}" if tp['prob'] is not None else 'n/a'
        res['Prob_cold_<{:.1f}C'.format(thresholds['cold_c'])] = f"{tc['prob']:.3f}" if tc['prob'] is not None else 'n/a'
        if tp['prob'] is not None and tp['prob'] >= 0.6:
            problems.append(f"Very likely HOT (>{thresholds['hot_c']} °C): {tp['prob']*100:.0f}%")
        if tc['prob'] is not None and tc['prob'] >= 0.6:
            problems.append(f"Very likely COLD (<{thresholds['cold_c']} °C): {tc['prob']*100:.0f}%")
    # Precipitation
    pd = hist_map.get('PRECTOT', (None, None))
    pp = compute_prob_for_series(pd[0], pd[1], date_obj, window, thresh=thresholds['rain_mm'], greater=True) if pd[0] is not None else None
    if pp is None:
        res['Precipitation'] = 'No data'
    else:
        res['Precip_samples'] = f"{pp['n']}"
        res['Precip_mean_mm'] = f"{pp['mean']:.2f}" if pp['mean'] is not None else 'n/a'
        res['Prob_rain_>={:.1f}mm'.format(thresholds['rain_mm'])] = f"{pp['prob']:.3f}" if pp['prob'] is not None else 'n/a'
        if pp['prob'] is not None and pp['prob'] >= 0.5:
            problems.append(f"Likely rainy (≥{thresholds['rain_mm']} mm/day): {pp['prob']*100:.0f}%")
    # Wind
    wd = hist_map.get('WS2M', (None, None))
    wp = compute_prob_for_series(wd[0], wd[1], date_obj, window, thresh=thresholds['wind_ms'], greater=True) if wd[0] is not None else None
    if wp is None:
        res['Wind'] = 'No data'
    else:
        res['Wind_samples'] = f"{wp['n']}"
        res['Wind_mean_mps'] = f"{wp['mean']:.2f}" if wp['mean'] is not None else 'n/a'
        res['Prob_wind_>={:.1f}m/s'.format(thresholds['wind_ms'])] = f"{wp['prob']:.3f}" if wp['prob'] is not None else 'n/a'
        if wp['prob'] is not None and wp['prob'] >= 0.5:
            problems.append(f"Likely windy (≥{thresholds['wind_ms']} m/s): {wp['prob']*100:.0f}%")
    # AOD
    ad = hist_map.get('AOD', (None, None))
    ap = compute_prob_for_series(ad[0], ad[1], date_obj, window, thresh=thresholds['aod'], greater=True) if ad[0] is not None else None
    if ap is None:
        res['AOD'] = 'No data'
    else:
        res['AOD_samples'] = f"{ap['n']}"
        res['AOD_mean'] = f"{ap['mean']:.3f}" if ap['mean'] is not None else 'n/a'
        res['Prob_aod_>={:.2f}'.format(thresholds['aod'])] = f"{ap['prob']:.3f}" if ap['prob'] is not None else 'n/a'
        if ap['prob'] is not None and ap['prob'] >= 0.5:
            problems.append(f"High aerosol (AOD ≥ {thresholds['aod']}): {ap['prob']*100:.0f}%")
    if not problems:
        summary = "Conditions are not strongly unfavorable based on historical probabilities for that date. You may still want to check short-term forecasts near the date."
    else:
        summary = "Potential issues based on historical probabilities:\n" + "\n".join([" - " + p for p in problems])
        if any("Very likely" in p for p in problems) or len(problems) >= 2:
            summary += "\n\nOverall: NOT FAVOURABLE to go out (based on historical probabilities)."
        else:
            summary += "\n\nOverall: CAUTION recommended."
    return summary, res

# ---------------- Utilities for JSON serialization ----------------
def series_to_json(dates_vals_tuple):
    d, v = dates_vals_tuple
    if d is None or v is None:
        return None
    return {'dates': [dt.isoformat() for dt in d], 'values': [None if (isinstance(x, float) and math.isnan(x)) else float(x) for x in v.tolist()]}

# ---------------- Geocode ----------------
def geocode_address(addr, timeout=15):
    q = urllib.parse.quote(addr)
    url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "NASA-Power-API/1.0 (+https://example.org)")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    j = json.loads(data.decode('utf-8'))
    if not j: return None
    return {"lat": float(j[0]['lat']), "lon": float(j[0]['lon']), "display_name": j[0].get('display_name', '')}

# ---------------- FastAPI app & models ----------------
app = FastAPI(title="NASA POWER Backend API - converted from Tkinter app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # or ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PowerDataRequest(BaseModel):
    lat: float = Field(..., example=27.0)
    lon: float = Field(..., example=77.0)
    start: Optional[str] = Field(None, example="20010101")  # YYYYMMDD
    end: Optional[str] = Field(None, example=(datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d"))
    parameters: Optional[List[str]] = Field(default_factory=lambda: ['T2M','PRECTOT','WS2M','AOD'])
    token: Optional[str] = None
    timeout: Optional[int] = 60

class ForecastRequest(BaseModel):
    lat: float
    lon: float
    start: Optional[str] = None
    end: Optional[str] = None
    parameters: Optional[List[str]] = Field(default_factory=lambda: ['T2M','PRECTOT','WS2M','AOD'])
    window: Optional[int] = 7
    token: Optional[str] = None
    timeout: Optional[int] = 60


class ForecastSimpleRequest(BaseModel):
    lat: float
    lon: float
    date: str  # YYYY-MM-DD start date for forecast
    ndays: int = 7
    parameters: Optional[List[str]] = Field(default_factory=lambda: ['T2M','PRECTOT','WS2M','AOD'])
    window: Optional[int] = 7
    token: Optional[str] = None
    timeout: Optional[int] = 60

class CheckDateRequest(BaseModel):
    lat: float
    lon: float
    date: str  # YYYY-MM-DD
    window: Optional[int] = 7
    thresholds: Optional[Dict[str, float]] = None
    token: Optional[str] = None
    timeout: Optional[int] = 30

@app.post("/power-data")
def power_data(req: PowerDataRequest):
    start = req.start or "20010101"
    end = req.end or (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
    try:
        results = fetch_power_json_with_fallback_and_key_mapping(req.lat, req.lon, req.parameters, start, end, token=req.token, timeout=req.timeout or 60)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch POWER data: {e}")
    out = {}
    for p, (d, v) in results.items():
        out[p] = series_to_json((d, v))
    available = [p for p, val in out.items() if val is not None]
    return {"available": available, "data": out}

@app.post("/forecast")
def forecast(req: ForecastRequest):
    start = req.start or "20010101"
    end = req.end or (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
    try:
        hist = fetch_power_json_with_fallback_and_key_mapping(req.lat, req.lon, req.parameters, start, end, token=req.token, timeout=req.timeout or 60)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch POWER data: {e}")
    daily_forecast = {}
    monthly_forecast = {}
    try:
        start_date = datetime.date.today() + datetime.timedelta(days=1)
        window = int(req.window or 7)
        for p in req.parameters:
            dates_vals = hist.get(p, (None, None))
            if dates_vals[0] is None:
                daily_forecast[p] = None
                monthly_forecast[p] = None
                continue
            hist_dates, hist_vals = dates_vals
            df = compute_daily_forecast_from_hist(hist_dates, hist_vals, start_date, 183, window=window, threshold=1.0)
            daily_forecast[p] = {'dates': [d.isoformat() for d in df['dates']],
                                 'mean': [None if math.isnan(x) else float(x) for x in df['mean'].tolist()],
                                 'prob': [None if math.isnan(x) else float(x) for x in df['prob'].tolist()],
                                 'nsamples': df['nsamples'].tolist()}
            # monthly
            try:
                m_dates, m_vals = aggregate_to_monthly(hist_dates, hist_vals)
                if len(m_vals) >= 2:
                    idx = np.arange(1, len(m_vals) + 1)
                    pfit = np.polyfit(idx, m_vals, 1)
                    future_idx = np.arange(len(m_vals) + 1, len(m_vals) + 7)
                    trend_f = np.polyval(pfit, future_idx)
                else:
                    trend_f = np.full(6, np.nan)
                months_of_hist = np.array([d.month for d in m_dates])
                clim_f = np.zeros(6)
                lastdv = m_dates[-1] if m_dates else datetime.date.today()
                startmon = lastdv.month + 1; startyr = lastdv.year
                for k in range(6):
                    monnum = ((startmon + k - 1) % 12) + 1
                    vals = m_vals[months_of_hist == monnum]
                    clim_f[k] = np.mean(vals) if len(vals) > 0 else (np.nanmean(m_vals) if len(m_vals) > 0 else 0.0)
                combined = 0.5 * trend_f + 0.5 * clim_f
                forecast_dates = []
                for k in range(6):
                    m = startmon + k; yr = startyr + (m - 1) // 12; mo = ((m - 1) % 12) + 1
                    forecast_dates.append(datetime.date(yr, mo, 15))
                monthly_forecast[p] = {
                    'hist_dates': [d.isoformat() for d in m_dates],
                    'hist_values': [None if math.isnan(x) else float(x) for x in m_vals.tolist()],
                    'forecast_dates': [d.isoformat() for d in forecast_dates],
                    'trend': [None if math.isnan(x) else float(x) for x in trend_f.tolist()],
                    'clim': [None if math.isnan(x) else float(x) for x in clim_f.tolist()],
                    'combined': [None if math.isnan(x) else float(x) for x in combined.tolist()]
                }
            except Exception:
                monthly_forecast[p] = None
        return {'daily_forecast': daily_forecast, 'monthly_forecast': monthly_forecast, 'available': [p for p in req.parameters if daily_forecast.get(p) is not None]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build forecasts: {e}")


@app.post("/forecast-simple")
def forecast_simple(req: ForecastSimpleRequest):
    # parse start date
    try:
        start_date = datetime.datetime.strptime(req.date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format; use YYYY-MM-DD")
    # build historical start/end for fetch (use long history)
    hist_start = "20010101"
    hist_end = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
    try:
        hist = fetch_power_json_with_fallback_and_key_mapping(req.lat, req.lon, req.parameters, hist_start, hist_end, token=req.token, timeout=req.timeout or 60)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch POWER data: {e}")

    out = {}
    for p in req.parameters:
        dates_vals = hist.get(p, (None, None))
        if dates_vals[0] is None:
            out[p] = None
            continue
        df = compute_daily_forecast_from_hist(dates_vals[0], dates_vals[1], start_date, req.ndays or 7, window=req.window or 7)
        out[p] = {
            'dates': [d.isoformat() for d in df['dates']],
            'mean': [None if math.isnan(x) else float(x) for x in df['mean'].tolist()],
            'prob': [None if math.isnan(x) else float(x) for x in df['prob'].tolist()],
            'nsamples': df['nsamples'].tolist()
        }
    return {'start': start_date.isoformat(), 'ndays': req.ndays, 'forecast': out}

@app.post("/check-date")
def check_date(req: CheckDateRequest):
    try:
        dt = datetime.datetime.strptime(req.date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
    # fetch hist data if needed
    params = ['T2M','PRECTOT','WS2M','AOD']
    start = "20010101"
    end = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
    try:
        hist = fetch_power_json_with_fallback_and_key_mapping(req.lat, req.lon, params, start, end, token=req.token, timeout=req.timeout or 30)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch historical data: {e}")
    # classify
    summary, details = classify_conditions_for_date_from_hist(hist, req.lon, req.lat, dt, window=req.window or 7, thresholds=req.thresholds)
    return {'summary': summary, 'details': details}

@app.get("/geocode")
def geocode(q: str = Query(..., description="Address to geocode")):
    try:
        out = geocode_address(q)
        if out is None:
            raise HTTPException(status_code=404, detail="Address not found")
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocode failed: {e}")

# Root
@app.get("/")
def root():
    return {"message": "NASA POWER backend API. See /docs for interactive API UI."}
