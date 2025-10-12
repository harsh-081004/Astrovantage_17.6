import React, { useState, useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "./maps.css";
import { postCheckDate } from "../api/axios";


// ✅ Fix marker icon in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

const EnglishCountryMap = () => {
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [checkResult, setCheckResult] = useState(null);
  const markerRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [loadingLocation, setLoadingLocation] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [numDays, setNumDays] = useState(30);
  

  const reverseGeocode = async (lat, lng) => {
    try {
      setLoadingLocation(true);
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=10&addressdetails=1`
      );
      const data = await response.json();
      
      const address = data.address || {};
      const name = address.city || address.town || address.village || 
                   address.county || address.state || address.country || 
                   data.display_name || "Unknown Location";
      
      return name;
    } catch (error) {
      console.error("Reverse geocoding error:", error);
      return "Unknown Location";
    } finally {
      setLoadingLocation(false);
    }
  };

  const MapClickHandler = () => {
    useMapEvents({
      click: async (e) => {
        const lat = e.latlng.lat.toFixed(5);
        const lng = e.latlng.lng.toFixed(5);
        
        const locationName = await reverseGeocode(lat, lng);
        
        setSelectedFeature({
          name: locationName,
          lat,
          lng,
        });
        setCheckResult(null);
      },
    });
    return null;
  };

  // ✅ Submit data
  const handleSubmit = async () => {
    if (!selectedFeature || !startDate || !numDays) {
      alert("Please fill all fields");
      return;
    }

    const selectedDate = new Date(startDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (selectedDate < today) {
      alert("Start date cannot be in the past");
      return;
    }

    const days = parseInt(numDays);
    if (days < 1 || days > 30) {
      alert("Days must be between 1 and 30");
      return;
    }

    const formData = {
      location: {
        name: selectedFeature.name,
        latitude: parseFloat(selectedFeature.lat),
        longitude: parseFloat(selectedFeature.lng),
      },
      startDate,
      numDays: days,
    };

    console.log("Form Data:", formData);

    try {
      setLoading(true);
      const resp = await postCheckDate({
        lat: formData.location.latitude,
        lon: formData.location.longitude,
        date: startDate,
        window: 7,
      });
      if (resp.ok) {
        setCheckResult(resp.data || null);
        // ensure popup is visible after data arrives
        try {
          if (markerRef.current && markerRef.current.openPopup) {
            markerRef.current.openPopup();
          }
        } catch (_) {}
      } else {
        const msg = typeof resp.error === 'string' ? resp.error : JSON.stringify(resp.error);
        alert(`❌ Backend error (${resp.status}): ${msg}`);
      }
    } catch (e) {
      alert(`❌ Request failed: ${e?.message || e}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="maps-container">
      <div className="map-wrapper">
        <MapContainer
          style={{ height: "100%", width: "100%" }}
          zoom={selectedFeature ? 8 : 3}
          center={selectedFeature ? [selectedFeature.lat, selectedFeature.lng] : [20, 0]}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <TileLayer
            attribution='Tiles &copy; Esri'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            opacity={0.6}
          />

          <MapClickHandler />

          {selectedFeature && (
            <Marker ref={markerRef} position={[selectedFeature.lat, selectedFeature.lng]}>
              <Popup maxWidth={380}>
                <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
                  <div style={{ 
                    fontSize: '18px', 
                    fontWeight: '700', 
                    color: '#667eea',
                    marginBottom: '12px',
                    paddingBottom: '10px',
                    borderBottom: '2px solid rgba(102, 126, 234, 0.2)'
                  }}>
                    📍 {selectedFeature.name}
                  </div>
                  
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: '1fr 1fr', 
                    gap: '8px', 
                    marginBottom: '12px',
                    fontSize: '13px',
                    color: '#4a5568'
                  }}>
                    <div><strong>Lat:</strong> {parseFloat(selectedFeature.lat).toFixed(4)}°</div>
                    <div><strong>Lng:</strong> {parseFloat(selectedFeature.lng).toFixed(4)}°</div>
                  </div>

                  <div style={{
                    background: 'rgba(102, 126, 234, 0.1)',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    marginBottom: '12px',
                    fontSize: '12px',
                    color: '#2d3748'
                  }}>
                    <strong>📅 Start:</strong> {startDate} &nbsp;|&nbsp; <strong>📊 Days:</strong> {numDays}
                  </div>

                  {loading && (
                    <div style={{ 
                      marginTop: '12px', 
                      padding: '12px',
                      textAlign: 'center',
                      background: 'rgba(102, 126, 234, 0.1)',
                      borderRadius: '8px',
                      color: '#667eea',
                      fontWeight: '600'
                    }}>
                      ⏳ Fetching prediction...
                    </div>
                  )}

                  {!loading && checkResult && (
                    <div style={{ marginTop: '12px' }}>
                      <div style={{ 
                        fontWeight: '700', 
                        fontSize: '15px',
                        marginBottom: '12px',
                        color: '#2d3748',
                        paddingBottom: '8px',
                        borderBottom: '2px solid rgba(102, 126, 234, 0.2)'
                      }}>
                        🌦️ Prediction for {startDate}
                      </div>
                      
                      {checkResult.details && (() => {
                        const d = checkResult.details;
                        const toNum = (x) => (x === undefined || x === null ? null : Number(x));
                        const pct = (p) => (p === null || isNaN(p) ? 'n/a' : `${Math.round(p * 100)}%`);
                        const risk = (p) => {
                          if (p === null || isNaN(p)) return { label: 'Unknown', color: '#999' };
                          if (p >= 0.6) return { label: 'High', color: '#d9534f' };
                          if (p >= 0.3) return { label: 'Medium', color: '#f0ad4e' };
                          return { label: 'Low', color: '#5cb85c' };
                        };
                        const hot = toNum(d['Prob_hot_>35.0C']);
                        const cold = toNum(d['Prob_cold_<5.0C']);
                        const rain = toNum(d['Prob_rain_>=5.0mm']);
                        const wind = toNum(d['Prob_wind_>=10.0m/s']);
                        const tmean = toNum(d['Temp_mean_degC']);
                        const pmean = toNum(d['Precip_mean_mm']);
                        const wmean = toNum(d['Wind_mean_mps']);
                        const kmh = (ms) => (ms == null || isNaN(ms) ? null : (ms * 3.6));
                        
                        const tag = (text, color) => (
                          <span style={{ 
                            background: color, 
                            color: '#fff', 
                            borderRadius: '12px', 
                            padding: '3px 10px', 
                            fontSize: '11px', 
                            fontWeight: '600',
                            marginLeft: '8px',
                            display: 'inline-block'
                          }}>
                            {text}
                          </span>
                        );
                        
                        const section = (icon, title, children) => (
                          <div style={{ 
                            marginBottom: '16px',
                            background: 'rgba(102, 126, 234, 0.04)',
                            padding: '12px',
                            borderRadius: '10px',
                            border: '1px solid rgba(102, 126, 234, 0.1)'
                          }}>
                            <div style={{ 
                              fontSize: '13px', 
                              fontWeight: '700', 
                              color: '#667eea',
                              marginBottom: '8px'
                            }}>
                              {icon} {title}
                            </div>
                            {children}
                          </div>
                        );
                        
                        const row = (label, value, badge) => (
                          <div style={{ 
                            marginBottom: '8px',
                            fontSize: '13px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                          }}>
                            <span style={{ color: '#4a5568' }}>{label}:</span>
                            <span style={{ fontWeight: '600', color: '#2d3748' }}>
                              {value} {badge}
                            </span>
                          </div>
                        );

                        return (
                          <div>
                            {section('🌡️', 'Temperature', <>
                              {row('Mean', tmean == null || isNaN(tmean) ? 'n/a' : `${tmean.toFixed(1)}°C`, null)}
                              {row('Hot chance (>35°C)', pct(hot), tag(risk(hot).label, risk(hot).color))}
                              {row('Cold chance (<5°C)', pct(cold), tag(risk(cold).label, risk(cold).color))}
                            </>)}
                            
                            {section('💧', 'Rain', <>
                              {row('Mean', pmean == null || isNaN(pmean) ? 'n/a' : `${pmean.toFixed(2)} mm`, null)}
                              {row('Rainy chance (≥5mm)', pct(rain), tag(risk(rain).label, risk(rain).color))}
                            </>)}
                            
                            {section('💨', 'Wind', <>
                              {row('Mean', wmean == null || isNaN(wmean) ? 'n/a' : `${wmean.toFixed(2)} m/s (${kmh(wmean)?.toFixed(1)} km/h)`, null)}
                              {row('Windy chance (≥10m/s)', pct(wind), tag(risk(wind).label, risk(wind).color))}
                            </>)}
                            
                            <div style={{ 
                              marginTop: '12px', 
                              padding: '10px',
                              background: 'rgba(102, 126, 234, 0.08)',
                              borderRadius: '8px',
                              fontSize: '11px',
                              color: '#666',
                              lineHeight: '1.5'
                            }}>
                              <strong>Units:</strong> Temp in °C (Celsius), Wind in m/s with km/h in brackets, Rain in mm/day.
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          )}
        </MapContainer>

        <div className="map-overlay">

          <div className="form-overlay">
            <h3 className="form-title">🌍 Weather Prediction</h3>
            <p className="form-subtitle">Click anywhere on the map to select a location</p>
            <div className="form-group">
              <label>📅 Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                min={new Date().toISOString().split("T")[0]}
              />
            </div>
            <div className="form-group">
              <label>📊 Number of Days</label>
              <input
                type="number"
                value={numDays}
                onChange={(e) => setNumDays(e.target.value)}
                min="1"
                max="30"
                placeholder="Enter days (1-30)"
              />
            </div>
            <button
              className="submit-btn"
              onClick={handleSubmit}
              disabled={!selectedFeature || !startDate || !numDays || loading}
            >
              {loading ? '⏳ Loading Prediction...' : '🚀 Get Weather Forecast'}
            </button>
          </div>

          {selectedFeature && (
            <div className="info-card">
              <div className="info-header">
                <h4>📍 Selected Location</h4>
                {loadingLocation && <span className="loading-badge">Loading...</span>}
              </div>
              
              {checkResult && checkResult.details && (
                <div className="summary-line">
                  {(() => {
                    const d = checkResult.details;
                    const temp = Number(d['Temp_mean_degC']);
                    const rain = Number(d['Prob_rain_>=5.0mm']) || 0;
                    const hot = Number(d['Prob_hot_>35.0C']) || 0;
                    const cold = Number(d['Prob_cold_<5.0C']) || 0;
                    const getRisk = (p) => {
                      if (p >= 0.6) return 'High';
                      if (p >= 0.3) return 'Medium';
                      return 'Low';
                    };
                    const tempStr = (!isNaN(temp) && temp !== null) ? temp.toFixed(1) + '°C' : 'N/A';
                    const condition = hot >= 0.3 ? 'Hot' : cold >= 0.3 ? 'Cold' : 'Moderate';
                    return `${tempStr} | Rain: ${getRisk(rain)} | ${condition}`;
                  })()}
                </div>
              )}
              
              <div className="info-content">
                <div className="info-row">
                  <span className="info-label">Location:</span>
                  <span className="info-value">{selectedFeature.name}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Latitude:</span>
                  <span className="info-value">{parseFloat(selectedFeature.lat).toFixed(5)}°</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Longitude:</span>
                  <span className="info-value">{parseFloat(selectedFeature.lng).toFixed(5)}°</span>
                </div>
                {startDate && (
                  <div className="info-row">
                    <span className="info-label">Start Date:</span>
                    <span className="info-value">{startDate}</span>
                  </div>
                )}
                {numDays && (
                  <div className="info-row">
                    <span className="info-label">Duration:</span>
                    <span className="info-value">{numDays} days</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnglishCountryMap;
