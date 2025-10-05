# nasa_power_gui_final.py
# NASA POWER Weather GUI — robust parameter detection, token support, monthly+daily CSVs, zoom & plots
# Added: address geocoding (OSM Nominatim), single-date "check weather" dialog, more AOD fallbacks
# Requirements: Python 3.8+, pip install pillow numpy matplotlib

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
from io import BytesIO
import urllib.request, urllib.error, urllib.parse, json, csv, datetime, os, math, numpy as np, matplotlib.pyplot as plt, calendar

# ---------------- Utilities ----------------
def day_of_year(d): return (d - datetime.date(d.year, 1, 1)).days + 1
def add_months(dt, months):
    m = dt.month - 1 + months; y = dt.year + m // 12; mo = m % 12 + 1
    d = min(dt.day, calendar.monthrange(y, mo)[1]); return datetime.date(y, mo, d)

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

# ---------------- HTTP helpers ----------------
def _download_url_bytes(url, token=None, timeout=60):
    req = urllib.request.Request(url)
    # add a minimal user-agent for servers that reject empty UA
    req.add_header("User-Agent", "NASA-Power-GUI/1.0 (+https://example.org)")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.getcode()

# ---------------- POWER JSON parsing & robust selection ----------------
def parse_power_json_to_series(j, parameter_key):
    """
    Given POWER JSON and a specific parameter key (as present in j['properties']['parameter']),
    return (dates_list, numpy_array_of_values).
    """
    try:
        pdata = j['properties']['parameter'][parameter_key]
    except Exception:
        raise ValueError(f"No parameter {parameter_key} in POWER JSON response.")
    dates, vals = [], []
    for k, v in sorted(pdata.items()):
        if len(k) != 8:  # expect YYYYMMDD keys
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
    """
    j: parsed POWER JSON
    desired_target: one of 'T2M','PRECTOT','WS2M','AOD'
    Strategy:
      - exact match preferred
      - else search keys for substrings ('prec','aod','t2','ws')
      - return None if no candidate
    """
    try:
        keys = list(j['properties']['parameter'].keys())
    except Exception:
        return None
    lower_keys = [k.lower() for k in keys]
    # exact
    for k in keys:
        if k.upper() == desired_target.upper():
            return k
    # heuristics
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
    # fallback: substring match
    for i, k in enumerate(lower_keys):
        if desired_target.lower() in k:
            return keys[i]
    return None

def fetch_power_json_with_fallback_and_key_mapping(lat, lon, desired_params, start_yyyymmdd, end_yyyymmdd, token=None, timeout=60):
    """
    Attempt a robust fetch:
    - First request a broad multi-parameter set (includes common variants).
    - From returned JSON, map best keys to each desired parameter (e.g. PRECTOT -> PRECTOTCORR).
    - For parameters still missing, attempt per-parameter requests.
    Returns dict: desired_param -> (dates, vals) or (None,None)
    """
    base = "https://power.larc.nasa.gov/api/temporal/daily/point"
    # Candidate set: include desired and common variant names
    candidate_names = set()
    for p in desired_params:
        candidate_names.add(p)
    # expanded common variants (extra AOD variants included)
    extra = [
        'PRECTOTCORR', 'PRECTOTCORR8', 'PRECTOT_C', 'PRECTOT_CORR',
        'AOD550', 'AOD_550', 'AOD_470', 'AOD550_AEROSOL', 'AOD', 'AOD550_AEROSOL',
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
        # map keys
        for p in desired_params:
            key = choose_best_key_for_target(j, p)
            if key:
                try:
                    dates, vals = parse_power_json_to_series(j, key)
                    out[p] = (dates, vals)
                except Exception:
                    out[p] = (None, None)
        # For any remaining missing, attempt per-parameter fetch with common names for that target
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
        # If multi-request failed, attempt per-parameter fetches
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
        # last resort per-parameter attempts
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

# ---------------- Map wrapper ----------------
class MapImage:
    def __init__(self):
        self.img = None; self.width = 1; self.height = 1
        self.xlim = (-180.0, 180.0); self.ylim = (-90.0, 90.0)

    def load_from_bytes(self, data_bytes):
        self.img = Image.open(BytesIO(data_bytes)).convert('RGBA')
        self.width, self.height = self.img.size
        self.xlim = (-180.0, 180.0); self.ylim = (-90.0, 90.0)

    def load_from_file(self, filename):
        self.img = Image.open(filename).convert('RGBA')
        self.width, self.height = self.img.size
        self.xlim = (-180.0, 180.0); self.ylim = (-90.0, 90.0)

    def pixel_to_lonlat(self, x, y, out_w, out_h):
        xfrac = float(x) / float(out_w); yfrac = float(y) / float(out_h)
        lon = self.xlim[0] + xfrac * (self.xlim[1] - self.xlim[0])
        lat = self.ylim[1] - yfrac * (self.ylim[1] - self.ylim[0])
        return lon, lat

    def get_view_image(self, out_w, out_h):
        if self.img is None: return None
        def lon_to_x(lon): return int(round((lon + 180.0) / 360.0 * (self.width - 1)))
        def lat_to_y(lat): return int(round((90.0 - lat) / 180.0 * (self.height - 1)))
        left = lon_to_x(self.xlim[0]); right = lon_to_x(self.xlim[1])
        top = lat_to_y(self.ylim[1]); bottom = lat_to_y(self.ylim[0])
        left = max(0, min(self.width - 1, left)); right = max(0, min(self.width - 1, right))
        top = max(0, min(self.height - 1, top)); bottom = max(0, min(self.height - 1, bottom))
        if left >= right or top >= bottom:
            cropped = self.img
        else:
            cropped = self.img.crop((left, top, right + 1, bottom + 1))
        resized = cropped.resize((out_w, out_h), Image.Resampling.LANCZOS)
        return resized

# ---------------- GUI ----------------
class NASA_POWER_GUI:
    def __init__(self, root):
        self.root = root; self.root.title("NASA POWER Weather GUI (final)")
        self.map = MapImage(); self.tkimage = None; self.last_pick = None
        self.hist = {}; self.daily_forecast = {}; self.monthly_forecast = {}

        # layout frames
        self.left = ttk.Frame(root); self.left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right = ttk.Frame(root, width=400); self.right.pack(side=tk.RIGHT, fill=tk.Y)

        # canvas
        self.canvas = tk.Canvas(self.left, bg='black'); self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # bottom map controls
        bottom = ttk.Frame(self.left); bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="Load Map (WVS snapshot URL)", command=self.on_load_map_url).pack(side=tk.LEFT, padx=3, pady=3)
        ttk.Button(bottom, text="Load Local Map Image", command=self.on_load_map_file).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="Zoom In", command=self.on_zoom_in).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="Zoom Out", command=self.on_zoom_out).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="Rect Zoom", command=self.on_rect_zoom).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="Reset Zoom", command=self.on_reset_zoom).pack(side=tk.LEFT, padx=3)

        pad = {'padx':6, 'pady':4}
        ttk.Label(self.right, text="Latitude:").pack(anchor='w', **pad)
        self.lat_var = tk.StringVar(value="27.0"); ttk.Entry(self.right, textvariable=self.lat_var).pack(fill=tk.X, **pad)
        ttk.Label(self.right, text="Longitude:").pack(anchor='w', **pad)
        self.lon_var = tk.StringVar(value="77.0"); ttk.Entry(self.right, textvariable=self.lon_var).pack(fill=tk.X, **pad)

        # Address geocoding row
        ttk.Label(self.right, text="Address (type and click Find):").pack(anchor='w', **pad)
        self.address_var = tk.StringVar()
        entry_frame = ttk.Frame(self.right); entry_frame.pack(fill=tk.X, padx=6)
        ttk.Entry(entry_frame, textvariable=self.address_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(entry_frame, text="Find Address", command=self.on_geocode_address).pack(side=tk.LEFT, padx=(6,0))

        ttk.Label(self.right, text="(Optional) Earthdata token (used for map & POWER):").pack(anchor='w', **pad)
        self.token_var = tk.StringVar(); ttk.Entry(self.right, textvariable=self.token_var, show="*").pack(fill=tk.X, **pad)

        ttk.Button(self.right, text="Get Weather (POWER JSON)", command=self.on_get_power).pack(fill=tk.X, **pad)
        ttk.Button(self.right, text="Load local CSV/JSON", command=self.on_load_local_csvjson).pack(fill=tk.X, **pad)

        ttk.Label(self.right, text="Forecast window ± days (DOY matching):").pack(anchor='w', **pad)
        self.window_var = tk.StringVar(value="7"); ttk.Entry(self.right, textvariable=self.window_var).pack(fill=tk.X, **pad)
        ttk.Label(self.right, text="Start forecast from (YYYY-MM-DD), default tomorrow:").pack(anchor='w', **pad)
        self.start_var = tk.StringVar(value=(datetime.date.today() + datetime.timedelta(days=1)).isoformat()); ttk.Entry(self.right, textvariable=self.start_var).pack(fill=tk.X, **pad)

        ttk.Separator(self.right, orient='horizontal').pack(fill=tk.X, pady=6)
        ttk.Label(self.right, text="Plot / Save Options:", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', padx=6)
        ttk.Button(self.right, text="Plot ALL (hist + 6mo daily forecast)", command=self.plot_all).pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(self.right, text="Plot Temperature (T2M)", command=lambda: self.plot_param('T2M')).pack(fill=tk.X, padx=6, pady=2)
        ttk.Button(self.right, text="Plot Precipitation (PRECTOT)", command=lambda: self.plot_param('PRECTOT')).pack(fill=tk.X, padx=6, pady=2)
        ttk.Button(self.right, text="Plot Wind Speed (WS2M)", command=lambda: self.plot_param('WS2M')).pack(fill=tk.X, padx=6, pady=2)
        ttk.Button(self.right, text="Plot AOD (AOD)", command=lambda: self.plot_param('AOD')).pack(fill=tk.X, padx=6, pady=2)

        ttk.Separator(self.right, orient='horizontal').pack(fill=tk.X, pady=6)
        ttk.Button(self.right, text="Save 6-mo MONTHLY forecast CSVs (per param)", command=self.save_monthly_forecast_csvs).pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(self.right, text="Save 6-mo DAILY forecast CSVs (per param)", command=self.save_daily_forecast_csvs).pack(fill=tk.X, padx=6, pady=2)
        ttk.Button(self.right, text="Save combined 6-mo daily CSV (all params)", command=self.save_combined_forecast).pack(fill=tk.X, padx=6, pady=4)

        ttk.Separator(self.right, orient='horizontal').pack(fill=tk.X, pady=6)
        # New feature: check a single date for conditions
        ttk.Button(self.right, text="Check weather for a DATE (single-day dialog)", command=self.on_check_date_dialog).pack(fill=tk.X, padx=6, pady=6)

        ttk.Button(self.right, text="Open NASA Worldview in browser", command=self.open_worldview).pack(fill=tk.X, padx=6, pady=10)
        self.status = tk.StringVar(value="Status: Ready"); ttk.Label(self.right, textvariable=self.status, foreground='blue').pack(pady=(6,0))

        self.default_map_url = ("https://wvs.earthdata.nasa.gov/api/v1/snapshot?REQUEST=GetSnapshot&TIME=2025-10-05T00:00:00Z&BBOX=-90,-180,90,180&CRS=EPSG:4326&LAYERS=BlueMarble_NextGeneration,Coastlines_15m&WRAP=x,x&FORMAT=image/png&WIDTH=4096&HEIGHT=2048&colormaps=,&ts=1759642600799")

        self.rect_start = None; self.rect_id = None

    # ---------------- Map load / redraw ----------------
    def on_load_map_url(self):
        url = simpledialog.askstring("Map URL", "Enter WVS snapshot URL:", initialvalue=self.default_map_url)
        if not url: return
        token = self.token_var.get().strip() or None
        self.status.set("Status: downloading map..."); self.root_update()
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "NASA-Power-GUI/1.0 (+https://example.org)")
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            self.map.load_from_bytes(data)
            self.status.set("Status: map loaded."); self.redraw_map()
        except Exception as e:
            messagebox.showerror("Map error", f"Failed to download/load map:\n{e}")
            self.status.set("Status: map load failed.")

    def on_load_map_file(self):
        fname = filedialog.askopenfilename(title="Select image", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.tif;*.bmp"),("All","*.*")])
        if not fname: return
        try:
            self.map.load_from_file(fname); self.status.set("Status: map loaded from file."); self.redraw_map()
        except Exception as e:
            messagebox.showerror("Map error", f"Failed to load file:\n{e}")

    def on_canvas_resize(self, event): self.redraw_map()

    def redraw_map(self):
        cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10: return
        self.canvas.delete("all")
        view = self.map.get_view_image(cw, ch)
        if view is None:
            self.canvas.create_text(cw//2, ch//2, text="No map loaded\nLoad WVS snapshot or local image", fill='white'); return
        self.tkimage = ImageTk.PhotoImage(view)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tkimage, tags='map')
        self.draw_ticks()
        if self.last_pick: self._draw_marker(self.last_pick[0], self.last_pick[1])

    def draw_ticks(self):
        self.canvas.delete('ticks'); cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        x0, x1 = self.map.xlim; y0, y1 = self.map.ylim
        for lon in range(-180, 181, 30):
            xfrac = (lon - x0) / (x1 - x0) if x1 != x0 else 0.5
            xpix = int(round(xfrac * cw))
            if 0 <= xpix <= cw: self.canvas.create_text(xpix, 10, text=str(lon), fill='white', tags='ticks', font=('TkDefaultFont', 8))
        for lat in range(-90, 91, 30):
            yfrac = (y1 - lat) / (y1 - y0) if y1 != y0 else 0.5
            ypix = int(round(yfrac * ch))
            if 0 <= ypix <= ch: self.canvas.create_text(10, ypix, text=str(lat), fill='white', tags='ticks', anchor='w', font=('TkDefaultFont', 8))

    # ---------------- Map interactions ----------------
    def on_canvas_click(self, event):
        cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        if cw <= 0 or ch <= 0: return
        lon, lat = self.map.pixel_to_lonlat(event.x, event.y, cw, ch)
        lon = max(-180.0, min(180.0, lon)); lat = max(-90.0, min(90.0, lat))
        self.lat_var.set(f"{lat:.6f}"); self.lon_var.set(f"{lon:.6f}"); self.last_pick = (lon, lat)
        self.draw_marker(lon, lat); self.status.set(f"Status: Picked (lat, lon) = ({lat:.4f}, {lon:.4f})")

    def draw_marker(self, lon, lat):
        self.canvas.delete('marker')
        cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        x0, x1 = self.map.xlim; y0, y1 = self.map.ylim
        xfrac = (lon - x0) / (x1 - x0) if x1 != x0 else 0.5
        yfrac = (y1 - lat) / (y1 - y0) if y1 != y0 else 0.5
        xpix = int(round(xfrac * cw)); ypix = int(round(yfrac * ch))
        r = 6; self.canvas.create_oval(xpix - r, ypix - r, xpix + r, ypix + r, fill='red', tags='marker')

    def _draw_marker(self, lon, lat):
        self.draw_marker(lon, lat)

    # ---------------- Zoom ----------------
    def on_zoom_in(self): cx, cy = self._zoom_center(); self._zoom_at(cx, cy, factor=0.5); self.redraw_map()
    def on_zoom_out(self): cx, cy = self._zoom_center(); self._zoom_at(cx, cy, factor=2.0); self.redraw_map()
    def _zoom_center(self):
        if self.last_pick is not None: return self.last_pick
        x0, x1 = self.map.xlim; y0, y1 = self.map.ylim; return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
    def _zoom_at(self, lonc, latc, factor=0.5):
        x0, x1 = self.map.xlim; y0, y1 = self.map.ylim
        w = (x1 - x0) * factor; h = (y1 - y0) * factor
        newx0 = lonc - w / 2.0; newx1 = lonc + w / 2.0
        newy0 = latc - h / 2.0; newy1 = latc + h / 2.0
        newx0 = max(-180, newx0); newx1 = min(180, newx1)
        newy0 = max(-90, newy0); newy1 = min(90, newy1)
        if newx1 - newx0 < 0.01: newx0, newx1 = -180, 180
        if newy1 - newy0 < 0.01: newy0, newy1 = -90, 90
        self.map.xlim = (newx0, newx1); self.map.ylim = (newy0, newy1)

    def on_reset_zoom(self):
        self.map.xlim = (-180, 180); self.map.ylim = (-90, 90); self.redraw_map()

    def on_rect_zoom(self):
        messagebox.showinfo("Rect Zoom", "Click and drag on the map to select rectangle to zoom.")
        self.canvas.config(cursor="crosshair")
        self.canvas.bind("<ButtonPress-1>", self._rect_start)
        self.canvas.bind("<B1-Motion>", self._rect_drag)
        self.canvas.bind("<ButtonRelease-1>", self._rect_end)

    def _rect_start(self, event):
        self.rect_start = (event.x, event.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id); self.rect_id = None

    def _rect_drag(self, event):
        if not self.rect_start: return
        x0, y0 = self.rect_start; x1, y1 = event.x, event.y
        if self.rect_id:
            self.canvas.coords(self.rect_id, x0, y0, x1, y1)
        else:
            self.rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline='yellow', width=2)

    def _rect_end(self, event):
        if not self.rect_start: return
        x0, y0 = self.rect_start; x1, y1 = event.x, event.y
        self.canvas.config(cursor="")
        self.canvas.unbind("<ButtonPress-1>"); self.canvas.unbind("<B1-Motion>"); self.canvas.unbind("<ButtonRelease-1>")
        if self.rect_id:
            self.canvas.delete(self.rect_id); self.rect_id = None
        self.rect_start = None
        cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        if cw <= 0 or ch <= 0: return
        cx0, cx1 = sorted([x0 / cw, x1 / cw]); cy0, cy1 = sorted([y0 / ch, y1 / ch])
        xlim = self.map.xlim; ylim = self.map.ylim
        lon0 = xlim[0] + cx0 * (xlim[1] - xlim[0]); lon1 = xlim[0] + cx1 * (xlim[1] - xlim[0])
        lat1 = ylim[1] - cy0 * (ylim[1] - ylim[0]); lat0 = ylim[1] - cy1 * (ylim[1] - ylim[0])
        lon0 = max(-180, min(180, lon0)); lon1 = max(-180, min(180, lon1))
        lat0 = max(-90, min(90, lat0)); lat1 = max(-90, min(90, lat1))
        if abs(lon1 - lon0) < 0.01 or abs(lat1 - lat0) < 0.01:
            self.status.set("Status: Rectangle too small; zoom cancelled."); return
        self.map.xlim = (lon0, lon1); self.map.ylim = (lat0, lat1); self.redraw_map()

    # ---------------- POWER fetch / parse / forecasts ----------------
    def on_get_power(self):
        try:
            lat = float(self.lat_var.get()); lon = float(self.lon_var.get())
        except:
            messagebox.showerror("Input", "Enter valid latitude and longitude."); return
        token = self.token_var.get().strip() or None
        start = "20010101"
        end = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
        desired = ['T2M', 'PRECTOT', 'WS2M', 'AOD']
        self.status.set("Status: fetching POWER data..."); self.root.update_idletasks()
        try:
            results = fetch_power_json_with_fallback_and_key_mapping(lat, lon, desired, start, end, token=token)
        except Exception as e:
            messagebox.showerror("POWER error", f"Failed to fetch POWER data:\n{e}"); self.status.set("Status: POWER fetch failed."); return
        self.hist = results
        available = [p for p, (d, v) in results.items() if d is not None]
        if not available:
            messagebox.showinfo("No data", "No parameters returned from POWER."); self.status.set("Status: no POWER data."); return
        self.status.set(f"Status: POWER data loaded for: {', '.join(available)}"); messagebox.showinfo("Done", f"POWER data loaded for: {', '.join(available)}")
        self._build_forecasts_for_all()

    def on_load_local_csvjson(self):
        fname = filedialog.askopenfilename(title="Select CSV or JSON (POWER-like)", filetypes=[("CSV/JSON", "*.csv;*.json;*.txt"), ("All", "*.*")])
        if not fname: return
        try:
            parsed = {}
            params = ['T2M', 'PRECTOT', 'WS2M', 'AOD']
            if fname.lower().endswith('.json'):
                with open(fname, 'r', encoding='utf-8') as f:
                    j = json.load(f)
                for p in params:
                    try:
                        dates, vals = parse_power_json_to_series(j, choose_best_key_for_target(j, p) or p)
                        parsed[p] = (dates, vals)
                    except:
                        parsed[p] = (None, None)
            else:
                # parse CSV: try YYYYMMDD,value or Year DOY value
                dates = []; vals = []
                with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                    rdr = csv.reader(f)
                    for row in rdr:
                        if not row: continue
                        row = [c.strip() for c in row if c.strip() != '']
                        if not row: continue
                        if len(row) >= 2 and len(row[0]) == 8 and row[0].isdigit():
                            try:
                                d = datetime.date(int(row[0][0:4]), int(row[0][4:6]), int(row[0][6:8])); v = float(row[1])
                                dates.append(d); vals.append(np.nan if v == -999 else v); continue
                            except:
                                pass
                        try:
                            y = int(row[0]); doy = int(row[1]); v = float(row[-1])
                            d = datetime.date(y, 1, 1) + datetime.timedelta(days=doy - 1)
                            dates.append(d); vals.append(np.nan if v == -999 else v); continue
                        except:
                            pass
                if len(dates) == 0: raise ValueError("Failed to parse local CSV.")
                parsed = {'PRECTOT': (dates, np.array(vals, dtype=float)), 'T2M': (None, None), 'WS2M': (None, None), 'AOD': (None, None)}
            self.hist = parsed; self.status.set("Status: local data loaded."); self._build_forecasts_for_all()
        except Exception as e:
            messagebox.showerror("Local load error", f"Failed to load local file:\n{e}")

    def _build_forecasts_for_all(self):
        try:
            start_date = datetime.datetime.strptime(self.start_var.get(), "%Y-%m-%d").date()
        except:
            start_date = datetime.date.today() + datetime.timedelta(days=1); self.start_var.set(start_date.isoformat())
        try:
            window = int(self.window_var.get())
        except:
            window = 7
        params = ['T2M', 'PRECTOT', 'WS2M', 'AOD']
        for p in params:
            dates_vals = self.hist.get(p, (None, None))
            if dates_vals[0] is None:
                self.daily_forecast[p] = None; self.monthly_forecast[p] = None; continue
            hist_dates, hist_vals = dates_vals
            forecast = compute_daily_forecast_from_hist(hist_dates, hist_vals, start_date, 183, window=window, threshold=1.0)
            self.daily_forecast[p] = forecast
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
                self.monthly_forecast[p] = {'hist_dn': m_dates, 'hist_vals': m_vals, 'forecast_dates': forecast_dates, 'trend': trend_f, 'clim': clim_f, 'combined': combined}
            except Exception:
                self.monthly_forecast[p] = None
        available = [p for p in params if self.daily_forecast.get(p) is not None]
        self.status.set("Status: forecasts built for: " + (", ".join(available) if available else "none"))

    # ---------------- Plotting ----------------
    def plot_param(self, param):
        df = self.daily_forecast.get(param)
        if df is None:
            messagebox.showinfo("No data", f"No data for {param}."); return
        hist_dates, hist_vals = self.hist.get(param, (None, None))
        plt.figure(figsize=(10, 4))
        if hist_dates is not None:
            plt.plot(hist_dates, hist_vals, '.', alpha=0.4, label='Historical')
        # if daily forecast mean present
        plt.plot(df['dates'], df['mean'], '-r', label='Forecast mean')
        plt.xlabel("Date"); plt.ylabel(param); plt.title(f"{param} historical & 6-month daily forecast")
        plt.legend(); plt.grid(True); plt.gcf().autofmt_xdate(); plt.show()

    def plot_all(self):
        params = ['T2M', 'PRECTOT', 'WS2M', 'AOD']
        available = [p for p in params if self.daily_forecast.get(p) is not None]
        if not available:
            messagebox.showinfo("No data", "No parameters available to plot."); return
        n = len(available); fig, axes = plt.subplots(n, 1, figsize=(10, 3 * n), sharex=True)
        if n == 1: axes = [axes]
        for ax, p in zip(axes, available):
            hist_dates, hist_vals = self.hist.get(p, (None, None))
            if hist_dates is not None:
                ax.plot(hist_dates, hist_vals, '.', alpha=0.4, label='Historical')
            df = self.daily_forecast[p]
            ax.plot(df['dates'], df['mean'], '-r', label='Forecast mean')
            ax.set_ylabel(p); ax.grid(True); ax.legend()
        axes[-1].set_xlabel('Date'); plt.gcf().autofmt_xdate()
        plt.suptitle('Available parameters: historical + 6-month daily forecast'); plt.show()

    # ---------------- CSV save ----------------
    def save_monthly_forecast_csvs(self):
        if not any(self.monthly_forecast.values()): messagebox.showinfo("No data", "No monthly forecast data available."); return
        outdir = filedialog.askdirectory(title="Select folder to save monthly forecast CSVs"); 
        if not outdir: return
        for p, mf in self.monthly_forecast.items():
            if mf is None: continue
            fn = os.path.join(outdir, f"POWER_monthly_forecast_{p}.csv")
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow([f"# 6-month MONTHLY forecast for {p}"]); w.writerow([f'# Generated: {datetime.datetime.now().isoformat()}']); w.writerow([])
                w.writerow(['Year', 'Month', 'Predicted', 'Trend', 'Climatology'])
                for i, d in enumerate(mf['forecast_dates']):
                    pred = mf['combined'][i] if (mf['combined'] is not None and i < len(mf['combined'])) else np.nan
                    tr = mf['trend'][i] if (mf['trend'] is not None and i < len(mf['trend'])) else np.nan
                    cl = mf['clim'][i] if (mf['clim'] is not None and i < len(mf['clim'])) else np.nan
                    w.writerow([d.year, d.month, '' if np.isnan(pred) else f"{pred:.6f}", '' if np.isnan(tr) else f"{tr:.6f}", '' if np.isnan(cl) else f"{cl:.6f}"])
        messagebox.showinfo("Saved", f"Monthly forecast CSVs saved in {outdir}"); self.status.set("Status: Saved monthly forecast CSVs.")

    def save_daily_forecast_csvs(self):
        if not any(self.daily_forecast.values()): messagebox.showinfo("No data", "No daily forecast data available."); return
        outdir = filedialog.askdirectory(title="Select folder to save daily forecast CSVs"); 
        if not outdir: return
        for p, df in self.daily_forecast.items():
            if df is None: continue
            fn = os.path.join(outdir, f"POWER_daily_forecast_{p}.csv")
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow([f"# 6-month DAILY forecast for {p}"]); w.writerow([f'# Generated: {datetime.datetime.now().isoformat()}']); w.writerow([])
                w.writerow(['Date', 'Mean', 'Prob_exceed_fraction', 'Num_samples'])
                for i, d in enumerate(df['dates']):
                    mean = df['mean'][i]; prob = df['prob'][i]; ns = df['nsamples'][i]
                    w.writerow([d.isoformat(), '' if np.isnan(mean) else f"{mean:.6f}", '' if np.isnan(prob) else f"{prob:.6f}", ns])
        messagebox.showinfo("Saved", f"Daily forecast CSVs saved in {outdir}"); self.status.set("Status: Saved daily forecast CSVs.")

    def save_combined_forecast(self):
        if not any(self.daily_forecast.values()): messagebox.showinfo("No data", "No forecast available."); return
        out = filedialog.asksaveasfilename(title="Save combined daily forecast CSV", defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not out: return
        all_dates = sorted({d for df in self.daily_forecast.values() if df for d in df['dates']})
        ps = ['T2M', 'PRECTOT', 'WS2M', 'AOD']
        with open(out, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow([f"# Combined 6-month DAILY forecast"]); w.writerow([f"# Generated: {datetime.datetime.now().isoformat()}"]); w.writerow([])
            w.writerow(['Date'] + ps)
            for d in all_dates:
                row = [d.isoformat()]
                for p in ps:
                    df = self.daily_forecast.get(p)
                    if df is None: row.append(''); continue
                    try:
                        idx = df['dates'].index(d); mean = df['mean'][idx]; row.append('' if np.isnan(mean) else f"{mean:.6f}")
                    except ValueError:
                        diffs = [abs((dd - d).days) for dd in df['dates']]
                        if len(diffs) == 0: row.append('')
                        else:
                            idx = int(np.argmin(diffs)); mean = df['mean'][idx]; row.append('' if np.isnan(mean) else f"{mean:.6f}")
                w.writerow(row)
        messagebox.showinfo("Saved", f"Combined forecast saved:\n{out}"); self.status.set("Status: Saved combined daily forecast CSV.")

    # ---------------- Geocode address ----------------
    def on_geocode_address(self):
        addr = self.address_var.get().strip()
        if not addr:
            messagebox.showinfo("Address", "Type an address or place name, then click Find Address.")
            return
        try:
            q = urllib.parse.quote(addr)
            url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "NASA-Power-GUI/1.0 (+https://example.org)")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            j = json.loads(data.decode('utf-8'))
            if not j:
                messagebox.showinfo("Not found", "Address not found. Try a different query.")
                return
            lat = float(j[0]['lat']); lon = float(j[0]['lon'])
            # update UI and place marker; center map on location with a small zoom
            self.lat_var.set(f"{lat:.6f}"); self.lon_var.set(f"{lon:.6f}"); self.last_pick = (lon, lat)
            self.center_map_on(lon, lat, span_deg=10.0)
            self.redraw_map(); self._draw_marker(lon, lat)
            self.status.set(f"Status: Address resolved to (lat, lon)=({lat:.4f}, {lon:.4f})")
        except Exception as e:
            messagebox.showerror("Geocode error", f"Failed to geocode address:\n{e}")

    def center_map_on(self, lon, lat, span_deg=10.0):
        # set map xlim/ylim to center on lon/lat with given span degrees (clamped)
        hw = max(0.1, min(180, span_deg))
        hh = max(0.1, min(90, span_deg/2.0))
        x0 = max(-180, lon - hw/2.0); x1 = min(180, lon + hw/2.0)
        y0 = max(-90, lat - hh/2.0); y1 = min(90, lat + hh/2.0)
        self.map.xlim = (x0, x1); self.map.ylim = (y0, y1)

    # ---------------- Single-date classification ----------------
    def on_check_date_dialog(self):
        # simple prompt for date
        dstr = simpledialog.askstring("Check date", "Enter date to check (YYYY-MM-DD):", initialvalue=(datetime.date.today()).isoformat())
        if not dstr: return
        try:
            dt = datetime.datetime.strptime(dstr, "%Y-%m-%d").date()
        except:
            messagebox.showerror("Date", "Invalid date format. Use YYYY-MM-DD.")
            return
        # use current lat/lon
        try:
            lat = float(self.lat_var.get()); lon = float(self.lon_var.get())
        except:
            messagebox.showerror("Input", "Enter valid latitude and longitude."); return
        # get window
        try:
            window = int(self.window_var.get())
        except:
            window = 7
        # thresholds (you can customize these defaults)
        thresholds = {'hot_c': 35.0, 'cold_c': 5.0, 'wind_ms': 10.0, 'rain_mm': 5.0, 'aod': 0.3}
        # compute classification
        msg, details = self.classify_conditions_for_date(lon, lat, dt, window=window, thresholds=thresholds)
        # show in a dialog window with details and save option
        win = tk.Toplevel(self.root); win.title(f"Weather check: {dt.isoformat()}")
        win.geometry("480x320")
        ttk.Label(win, text=f"Location: lat={lat:.4f}, lon={lon:.4f}", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', padx=8, pady=(8,4))
        ttk.Label(win, text=f"Date: {dt.isoformat()}", font=('TkDefaultFont', 10)).pack(anchor='w', padx=8, pady=(0,8))
        ttk.Separator(win, orient='horizontal').pack(fill=tk.X, pady=4)
        txt = tk.Text(win, wrap='word', height=12)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        txt.insert('end', msg + "\n\nDetailed probabilities:\n")
        for k, v in details.items():
            txt.insert('end', f" - {k}: {v}\n")
        txt.config(state='disabled')
        btnframe = ttk.Frame(win); btnframe.pack(fill=tk.X, pady=8, padx=8)
        ttk.Button(btnframe, text="Close", command=win.destroy).pack(side=tk.RIGHT)
        ttk.Button(btnframe, text="Save details (CSV)", command=lambda: self._save_details_csv(dt, lat, lon, details)).pack(side=tk.RIGHT, padx=(0,8))

    def classify_conditions_for_date(self, lon, lat, date_obj, window=7, thresholds=None):
        """
        For a given lon/lat and date, compute probability estimates from historical data in self.hist
        If hist not loaded for a parameter, attempt to fetch a short POWER series on-the-fly (last 20 years).
        Returns a user-friendly message and a dict of detailed probability numbers.
        """
        if thresholds is None:
            thresholds = {'hot_c': 35.0, 'cold_c': 5.0, 'wind_ms': 10.0, 'rain_mm': 5.0, 'aod': 0.3}
        res = {}
        problems = []
        # helper to compute prob and mean for a single param series
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
        # ensure hist for required params; if missing, try fetch short period (2000-01-01..yesterday)
        need_params = ['T2M','PRECTOT','WS2M','AOD']
        for p in need_params:
            if self.hist.get(p, (None,None))[0] is None:
                # attempt on-the-fly fetch (shorter range to be quicker)
                try:
                    start = "20010101"; end = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
                    token = self.token_var.get().strip() or None
                    out = fetch_power_json_with_fallback_and_key_mapping(lat, lon, [p], start, end, token=token, timeout=30)
                    self.hist[p] = out.get(p, (None,None))
                except Exception:
                    self.hist[p] = (None, None)
        # Temperature
        td = self.hist.get('T2M', (None, None))
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
        pd = self.hist.get('PRECTOT', (None, None))
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
        wd = self.hist.get('WS2M', (None, None))
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
        ad = self.hist.get('AOD', (None, None))
        ap = compute_prob_for_series(ad[0], ad[1], date_obj, window, thresh=thresholds['aod'], greater=True) if ad[0] is not None else None
        if ap is None:
            res['AOD'] = 'No data'
        else:
            res['AOD_samples'] = f"{ap['n']}"
            res['AOD_mean'] = f"{ap['mean']:.3f}" if ap['mean'] is not None else 'n/a'
            res['Prob_aod_>={:.2f}'.format(thresholds['aod'])] = f"{ap['prob']:.3f}" if ap['prob'] is not None else 'n/a'
            if ap['prob'] is not None and ap['prob'] >= 0.5:
                problems.append(f"High aerosol (AOD ≥ {thresholds['aod']}): {ap['prob']*100:.0f}%")
        # Compose final message
        if not problems:
            summary = "Conditions are not strongly unfavorable based on historical probabilities for that date.\nYou may still want to check short-term forecasts near the date."
        else:
            summary = "Potential issues based on historical probabilities:\n" + "\n".join([" - " + p for p in problems])
            # decide "not favourable to go out" if several flags or severe single flag
            if any("Very likely" in p for p in problems) or len(problems) >= 2:
                summary += "\n\nOverall: NOT FAVOURABLE to go out (based on historical probabilities)."
            else:
                summary += "\n\nOverall: CAUTION recommended."
        return summary, res

    def _save_details_csv(self, date_obj, lat, lon, details):
        out = filedialog.asksaveasfilename(title="Save details CSV", defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not out: return
        with open(out, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow([f"# Weather check details for {date_obj.isoformat()}"])
            w.writerow([f"Latitude", f"Longitude", "Generated"])
            w.writerow([f"{lat}", f"{lon}", datetime.datetime.now().isoformat()])
            w.writerow([])
            w.writerow(["Variable", "Value"])
            for k, v in details.items():
                w.writerow([k, v])
        messagebox.showinfo("Saved", f"Details saved to {out}")

    # ---------------- Misc ----------------
    def root_update(self):
        try: self.root.update_idletasks(); self.root.update()
        except: pass

    def open_worldview(self):
        import webbrowser; webbrowser.open("https://worldview.earthdata.nasa.gov/")

# ---------------- Run ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = NASA_POWER_GUI(root)
    root.geometry("1360x820")
    root.mainloop()
