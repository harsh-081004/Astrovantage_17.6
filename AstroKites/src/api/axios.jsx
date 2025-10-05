import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
    baseURL: 'http://127.0.0.1:8000',
    headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        access_control_allow_origin: '*',
    },
});

// Generic helper to unwrap response
const unwrap = (resp) => (resp && resp.data ? resp.data : resp);

export const getForecastData = async (lat, lon) => {
    const res = await api.post(`/forecast?lat=${lat}&lon=${lon}`);
    return unwrap(res);
};

export const postPowerData = async ({ lat, lon, start = null, end = null, parameters = ['T2M', 'PRECTOT', 'WS2M', 'AOD'], token = null, timeout = 60 }) => {
    const payload = { lat, lon, start, end, parameters, token, timeout };
    const res = await api.post('/power-data', payload);
    return unwrap(res);
};

export const postForecast = async (payload) => {
    // payload should include lat, lon, start/end or similar per server API
    const res = await api.post('/forecast', payload);
    return unwrap(res);
};

export const postForecastSimple = async (lat, lon, date, ndays = 7, parameters = ['T2M', 'PRECTOT', 'ALLSKY_SFC_SW_DWN'], window = 7, token = null, timeout = 60, headers = {}) => {
    const payload = { lat, lon, date, ndays, parameters, window, token, timeout };
    const res = await api.post('/forecast-simple', payload, { headers });
    return unwrap(res);
};

export const postCheckDate = async (lat, lon, date, window = 7, thresholds = null, token = null, timeout = 30) => {
    const payload = { lat, lon, date, window, thresholds, token, timeout };
    const res = await api.post('/check-date', payload);
    return unwrap(res);
};

export const geocode = async (q) => {
    const res = await api.get(`/geocode?q=${encodeURIComponent(q)}`);
    return unwrap(res);
};

export const getProbabilityData = async (geometry, variable, day_of_year, threshold, years = null, window_days = null) => {
    const requestData = { geometry, variable, day_of_year, threshold };
    if (years) requestData.years = years;
    if (window_days) requestData.window_days = window_days;
    const res = await api.post('/api/query/probability', requestData);
    return unwrap(res);
};
