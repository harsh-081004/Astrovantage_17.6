import React, { useEffect, useMemo, useState } from "react";
import "./forecast.css";

// --- CONFIG ---
const NASA_API_KEY = "DEMO_KEY";
const NASA_DAILY_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point";
const PARAMETERS = ["T2M", "PRECTOT", "WS2M"]; // Temperature (°C), Precipitation (mm/day), Wind speed (m/s)

// Small list of sample points (you can expand or replace with a search)
const SAMPLE_POINTS = [
  { id: "sf", name: "San Francisco, US", lat: 37.7749, lon: -122.4194 },
  { id: "london", name: "London, GB", lat: 51.5074, lon: -0.1278 },
  { id: "mumbai", name: "Mumbai, IN", lat: 19.0760, lon: 72.8777 },
  { id: "sydney", name: "Sydney, AU", lat: -33.8688, lon: 151.2093 }
];

// --- Utility helpers ---
const formatDate = (d) => d.toISOString().split("T")[0]; // YYYY-MM-DD
const daysBetween = (start, end) => Math.round((end - start) / (1000 * 60 * 60 * 24));

// Aggregate daily into months and compute monthly mean
const aggregateMonthlyMeans = (dailyObj) => {
  // dailyObj: { dateString: value, ... }
  const months = {};
  Object.entries(dailyObj).forEach(([dateStr, val]) => {
    // dateStr often like '2025-09-01' or '20250901' depending on API; try normalizing
    const iso = dateStr.includes("-") ? dateStr : `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
    const d = new Date(iso);
    if (isNaN(d)) return;
    const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`; // YYYY-MM
    if (!months[key]) months[key] = { sum: 0, count: 0 };
    months[key].sum += Number(val) || 0;
    months[key].count += 1;
  });
  // convert to sorted array of { month, mean }
  return Object.entries(months)
    .map(([month, { sum, count }]) => ({ month, mean: count ? sum / count : 0 }))
    .sort((a,b) => a.month.localeCompare(b.month));
};

// Simple SVG line chart component (dependency-free)
const LineChart = ({ data = [], height = 140, stroke = "#2978b5", label }) => {
  // data: array of numbers
  const width = Math.max(300, data.length * 60);
  if (!data || data.length === 0) {
    return <div className="chart-empty">No data</div>;
  }
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = Math.max(1, max - min);
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1 || 1)) * (width - 24) + 12;
      const y = height - ((v - min) / range) * (height - 28) - 12;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} width="100%" height={height}>
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      {data.map((v, i) => {
        const x = (i / (data.length - 1 || 1)) * (width - 24) + 12;
        const y = height - ((v - min) / range) * (height - 28) - 12;
        return <circle key={i} cx={x} cy={y} r="4" fill="#fff" stroke={stroke} />;
      })}
    </svg>
  );
};

// --- Main component ---
const ForecastSimplified = () => {
  const [point, setPoint] = useState(SAMPLE_POINTS[0]);
  const [forecast7, setForecast7] = useState([]); // array of daily objects for next 7 days
  const [last6MonthsMeans, setLast6MonthsMeans] = useState([]); // array of { month, meanTemp, meanPrecip, meanWind }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Build date ranges
  const today = new Date();
  const start7 = formatDate(today);
  const end7Date = new Date();
  end7Date.setDate(end7Date.getDate() + 6);
  const end7 = formatDate(end7Date);

  // last 6 months range: from 6 months ago (approx) to today
  const start6mDate = new Date();
  start6mDate.setMonth(start6mDate.getMonth() - 6);
  const start6m = formatDate(start6mDate);
  const end6m = formatDate(today);

  // Fetch data: daily for next 7 days AND daily for last 6 months (then aggregate)
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError("");
      try {
        const { lat, lon } = point;

        // helper to construct URL
        const buildUrl = (start, end) => {
          const params = [
            `start=${start.replace(/-/g,"")}`,
            `end=${end.replace(/-/g,"")}`,
            `latitude=${lat}`,
            `longitude=${lon}`,
            `parameters=${PARAMETERS.join(",")}`,
            `community=RE`,
            `format=JSON`,
            `user=${NASA_API_KEY}`
          ];
          return `${NASA_DAILY_BASE}?${params.join("&")}`;
        };

        // 1) 7-day forecast (daily)
        const url7 = buildUrl(start7, end7);
        const resp7 = await fetch(url7);
        if (!resp7.ok) throw new Error(`NASA daily (7d) error: ${resp7.status}`);
        const json7 = await resp7.json();

        // POWER daily returns parameters in json: json.properties.parameter.PARAMNAME = { dateStr: value }
        const param7 = json7.properties?.parameter || {};
        // build an array of dates between start7 and end7 in ISO and map to values (T2M, PRECTOT, WS2M)
        const dayCount = daysBetween(new Date(start7), new Date(end7)) + 1;
        const arr7 = [];
        for (let i = 0; i < dayCount; i++) {
          const d = new Date(start7);
          d.setDate(d.getDate() + i);
          const iso = formatDate(d);
          const keyAlt = iso.replace(/-/g,""); // fallback key format
          const t = param7.T2M?.[iso] ?? param7.T2M?.[keyAlt];
          const p = param7.PRECTOT?.[iso] ?? param7.PRECTOT?.[keyAlt];
          const w = param7.WS2M?.[iso] ?? param7.WS2M?.[keyAlt];
          // WS2M is in m/s -> convert to km/h
          const windKmh = w !== undefined && w !== null ? Number(w) * 3.6 : null;
          arr7.push({
            date: iso,
            temp: t !== undefined && t !== null ? Number(t) : null,
            precip: p !== undefined && p !== null ? Number(p) : 0,
            wind: windKmh !== null ? Number(windKmh) : null
          });
        }
        setForecast7(arr7);

        // 2) Last 6 months daily -> aggregate monthly means
        const url6m = buildUrl(start6m, end6m);
        const resp6m = await fetch(url6m);
        if (!resp6m.ok) throw new Error(`NASA daily (6m) error: ${resp6m.status}`);
        const json6m = await resp6m.json();
        const p6 = json6m.properties?.parameter || {};

        // aggregate parameter objects by month
        const tempMonthly = aggregateMonthlyMeans(p6.T2M || {});
        const precipMonthly = aggregateMonthlyMeans(p6.PRECTOT || {});
        const windMonthlyRaw = aggregateMonthlyMeans(p6.WS2M || {});

        // convert wind from m/s means to km/h
        const windMonthly = windMonthlyRaw.map(w => ({ month: w.month, mean: w.mean * 3.6 }));

        // Merge by month keys (some months may be missing in one param)
        const monthsSet = new Set([
          ...tempMonthly.map(m => m.month),
          ...precipMonthly.map(m => m.month),
          ...windMonthly.map(m => m.month)
        ]);
        const merged = Array.from(monthsSet)
          .sort()
          .map(month => {
            const t = tempMonthly.find(m => m.month === month)?.mean ?? null;
            const p = precipMonthly.find(m => m.month === month)?.mean ?? 0;
            const w = windMonthly.find(m => m.month === month)?.mean ?? null;
            return { month, meanTemp: t !== null ? Number(t) : null, meanPrecip: Number(p), meanWind: w !== null ? Number(w) : null };
          });

        setLast6MonthsMeans(merged);
      } catch (err) {
        console.error(err);
        setError("Failed to fetch NASA data — showing sample fallback data.");
        // fallback sample
        setForecast7(getSample7());
        setLast6MonthsMeans(getSample6Months());
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [point]); // re-run when point changes

  // computed arrays for charts
  const temps7 = useMemo(() => forecast7.map(d => d.temp ?? 0), [forecast7]);
  const precip7 = useMemo(() => forecast7.map(d => d.precip ?? 0), [forecast7]);
  const wind7 = useMemo(() => forecast7.map(d => d.wind ?? 0), [forecast7]);

  const meanTemps6 = useMemo(() => last6MonthsMeans.map(m => m.meanTemp ?? 0), [last6MonthsMeans]);
  const meanPrecip6 = useMemo(() => last6MonthsMeans.map(m => m.meanPrecip ?? 0), [last6MonthsMeans]);
  const meanWind6 = useMemo(() => last6MonthsMeans.map(m => m.meanWind ?? 0), [last6MonthsMeans]);
  const monthsLabels6 = useMemo(() => last6MonthsMeans.map(m => m.month), [last6MonthsMeans]);

  return (
    <div className="fs-container">
      <header className="fs-header">
        <h2>Simplified Forecast</h2>
        <p className="muted">7-day forecast + 6-month mean (monthly) — Temperature, Precipitation, Wind</p>
      </header>

      <section className="fs-controls">
        <label>Location</label>
        <select value={point.id} onChange={(e) => setPoint(SAMPLE_POINTS.find(p => p.id === e.target.value))}>
          {SAMPLE_POINTS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <div className="fs-loading">{loading && <span>Loading data...</span>}</div>
        {error && <div className="fs-error">{error}</div>}
      </section>

      <section className="charts-row">
        <div className="chart-block">
          <h4>Temperature (7-day)</h4>
          <LineChart data={temps7} stroke="#ff6b6b" />
          <div className="small-stats">
            <span>Max: {Math.max(...(temps7.length?temps7:[0]))}°C</span>
            <span>Min: {Math.min(...(temps7.length?temps7:[0]))}°C</span>
          </div>
        </div>

        <div className="chart-block">
          <h4>Precipitation (7-day)</h4>
          <LineChart data={precip7} stroke="#48c1a9" />
          <div className="small-stats">
            <span>Total: {precip7.reduce((s,v)=>s+v,0).toFixed(2)} mm</span>
            <span>Avg: {(precip7.reduce((s,v)=>s+v,0)/Math.max(1,precip7.length)).toFixed(2)} mm</span>
          </div>
        </div>

        <div className="chart-block">
          <h4>Wind (7-day)</h4>
          <LineChart data={wind7} stroke="#4d9df6" />
          <div className="small-stats">
            <span>Max: {Math.max(...(wind7.length?wind7:[0])).toFixed(1)} km/h</span>
            <span>Avg: {(wind7.reduce((s,v)=>s+v,0)/Math.max(1,wind7.length)).toFixed(1)} km/h</span>
          </div>
        </div>
      </section>

      <section className="mean-row">
        <h3>Mean of last 6 months (monthly averages)</h3>
        <div className="mean-charts">
          <div className="mean-chart">
            <h5>Mean Temperature (°C)</h5>
            <LineChart data={meanTemps6} stroke="#ff8a65" />
            <div className="axis-labels">{monthsLabels6.map(m => <span key={m}>{m}</span>)}</div>
          </div>

          <div className="mean-chart">
            <h5>Mean Precipitation (mm)</h5>
            <LineChart data={meanPrecip6} stroke="#20c997" />
            <div className="axis-labels">{monthsLabels6.map(m => <span key={m}>{m}</span>)}</div>
          </div>

          <div className="mean-chart">
            <h5>Mean Wind (km/h)</h5>
            <LineChart data={meanWind6} stroke="#5a8dee" />
            <div className="axis-labels">{monthsLabels6.map(m => <span key={m}>{m}</span>)}</div>
          </div>
        </div>
      </section>

      <section className="forecast-list">
        <h3>7-day details</h3>
        <div className="days-grid">
          {forecast7.map((d) => (
            <div key={d.date} className="day-card">
              <div className="day-title">{d.date}</div>
              <div className="day-temp">{d.temp !== null ? `${d.temp}°C` : "N/A"}</div>
              <div className="day-precip">🌧 {d.precip} mm</div>
              <div className="day-wind">🌬 {d.wind !== null ? `${d.wind.toFixed(1)} km/h` : "N/A"}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

// --- Fallback sample data functions ---
function getSample7() {
  // 7 days of sample
  const arr = [];
  const now = new Date();
  for (let i = 0; i < 7; i++) {
    const d = new Date(now);
    d.setDate(now.getDate() + i);
    arr.push({
      date: formatDate(d),
      temp: Math.round(20 + Math.sin(i/7 * Math.PI) * 6),
      precip: Number((Math.random() * 3).toFixed(2)),
      wind: Number((8 + Math.random()*6).toFixed(1))
    });
  }
  return arr;
}

function getSample6Months() {
  const arr = [];
  const now = new Date();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now);
    d.setMonth(d.getMonth() - i);
    const mKey = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    arr.push({
      month: mKey,
      meanTemp: Math.round(15 + Math.random()*10),
      meanPrecip: Number((Math.random()*80).toFixed(1)),
      meanWind: Number((6 + Math.random()*6).toFixed(1))
    });
  }
  return arr;
}

export default ForecastSimplified;
