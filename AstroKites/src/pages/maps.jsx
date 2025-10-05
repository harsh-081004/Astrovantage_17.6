import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, GeoJSON, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "./maps.css";

const CONTINENT_COLORS = {
  Africa: "#FFA500",
  Americas: "#90EE90",
  Asia: "#DDA0DD",
  Europe: "#FFFF99",
  Oceania: "#F0E68C",
  Antarctica: "#D3D3D3",
  Default: "#A9A9A9",
};

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
  const [countriesData, setCountriesData] = useState(null);
  const [statesData, setStatesData] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);

  // 🔍 Search + form state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [startDate, setStartDate] = useState("");
  const [numDays, setNumDays] = useState(1);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  // 🌍 Load GeoJSON data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const countriesRes = await fetch(
          "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
        );
        const countries = await countriesRes.json();
        setCountriesData(countries);

        const statesRes = await fetch(
          "https://raw.githubusercontent.com/deldersveld/topojson/master/world-countries.json"
        );
        const states = await statesRes.json();
        const geojson = window.topojson
          ? window.topojson.feature(states, states.objects.countries)
          : null;
        setStatesData(geojson);
      } catch (error) {
        console.error("Error fetching GeoJSON:", error);
      }
    };

    fetchData();
  }, []);

  // 🏷️ Extract readable name
  const getFeatureName = (feature) => {
    const props = feature.properties || {};
    return (
      props.ADMIN ||
      props.ADMIN_EN ||
      props.NAME_EN ||
      props.name_en ||
      props.NAME ||
      props.name ||
      props.formal_en ||
      props.geounit ||
      props.sovereignt ||
      "Unnamed Region"
    );
  };

  // 🎨 Country style
  const styleCountry = (feature) => {
    const continent = feature.properties.CONTINENT || "Default";
    return {
      fillColor: CONTINENT_COLORS[continent] || CONTINENT_COLORS.Default,
      weight: 1,
      color: "black",
      fillOpacity: 0.6,
    };
  };

  const styleState = {
    fillColor: "#87CEFA",
    weight: 0.5,
    color: "#000",
    fillOpacity: 0.4,
  };

  const onEachFeature = (feature, layer) => {
    const name = getFeatureName(feature);
    layer.bindTooltip(name, { sticky: true });
    layer.on({
      click: (e) => {
        setSelectedFeature({
          name,
          lat: e.latlng.lat.toFixed(5),
          lng: e.latlng.lng.toFixed(5),
        });
      },
    });
  };

  // 🔍 Search location via OpenStreetMap
  const searchLocation = async () => {
    if (!searchQuery.trim()) {
      setSearchError("Please enter a location to search");
      return;
    }

    setIsSearching(true);
    setSearchResults([]);
    setSearchError("");

    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          searchQuery
        )}&limit=10&addressdetails=1`
      );

      if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

      const results = await response.json();

      if (results.length === 0) {
        setSearchError("No locations found. Try another name.");
      } else {
        setSearchResults(results);
      }
    } catch (error) {
      console.error("Error searching location:", error);
      setSearchError("Search failed. Please check your connection.");
    } finally {
      setIsSearching(false);
    }
  };

  // 📍 Select a location from results
  const handleLocationSelect = (location) => {
    setSelectedLocation({
      name: location.display_name,
      lat: parseFloat(location.lat),
      lng: parseFloat(location.lon),
    });
    setSearchQuery(location.display_name);
    setSearchResults([]);
    setSearchError("");
  };

  // ❌ Clear search
  const clearSearch = () => {
    setSearchQuery("");
    setSearchResults([]);
    setSelectedLocation(null);
    setSearchError("");
  };

  // ✅ Submit data
  const handleSubmit = () => {
    if (!selectedLocation || !startDate || !numDays) {
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
        name: selectedLocation.name,
        latitude: selectedLocation.lat,
        longitude: selectedLocation.lng,
      },
      startDate,
      numDays: days,
    };

    console.log("Form Data:", formData);
    alert(
      `✅ Ready for backend:\n📍 ${selectedLocation.name}\n🌍 (${selectedLocation.lat}, ${selectedLocation.lng})\n📅 ${startDate}\n📊 ${numDays} day${numDays > 1 ? "s" : ""}`
    );
  };

  return (
    <div className="maps-container">
      <div className="map-wrapper">
        <MapContainer
          style={{ height: "80vh", width: "100%" }}
          zoom={selectedLocation ? 10 : 2}
          center={
            selectedLocation
              ? [selectedLocation.lat, selectedLocation.lng]
              : [20, 0]
          }
        >
          <TileLayer
            attribution="© OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {countriesData && (
            <GeoJSON
              data={countriesData}
              style={styleCountry}
              onEachFeature={onEachFeature}
            />
          )}

          {statesData && (
            <GeoJSON
              data={statesData}
              style={() => styleState}
              onEachFeature={onEachFeature}
            />
          )}

          {selectedFeature && (
            <Marker position={[selectedFeature.lat, selectedFeature.lng]}>
              <Popup>
                <strong>{selectedFeature.name}</strong>
                <br />
                Lat: {selectedFeature.lat}
                <br />
                Lng: {selectedFeature.lng}
              </Popup>
            </Marker>
          )}

          {selectedLocation && (
            <Marker position={[selectedLocation.lat, selectedLocation.lng]}>
              <Popup>
                <strong>📍 {selectedLocation.name}</strong>
                <br />
                Lat: {selectedLocation.lat.toFixed(5)}
                <br />
                Lng: {selectedLocation.lng.toFixed(5)}
                <br />
                <small>
                  Start: {startDate} | Days: {numDays}
                </small>
              </Popup>
            </Marker>
          )}
        </MapContainer>

        {/* 🔍 Floating Search + Form */}
        <div className="map-overlay">
          <div className="search-box">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="🔍 Search location..."
              onKeyPress={(e) => e.key === "Enter" && searchLocation()}
            />
            <button
              onClick={searchLocation}
              disabled={isSearching || !searchQuery.trim()}
            >
              {isSearching ? "⏳" : "🔍"}
            </button>
            {searchQuery && <button onClick={clearSearch}>✕</button>}
          </div>

          {searchError && <div className="error">{searchError}</div>}

          {searchResults.length > 0 && (
            <div className="search-results">
              {searchResults.map((res, i) => (
                <div
                  key={i}
                  className="result-item"
                  onClick={() => handleLocationSelect(res)}
                >
                  <strong>{res.display_name}</strong>
                  <br />
                  <small>
                    📍 {parseFloat(res.lat).toFixed(4)},{" "}
                    {parseFloat(res.lon).toFixed(4)}
                  </small>
                </div>
              ))}
            </div>
          )}

          <div className="form-overlay">
            <label>📅 Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
            />
            <label>📊 Days</label>
            <input
              type="number"
              value={numDays}
              onChange={(e) => setNumDays(e.target.value)}
              min="1"
              max="30"
            />
            <button
              onClick={handleSubmit}
              disabled={!selectedLocation || !startDate || !numDays}
            >
              🚀 Get Forecast
            </button>
          </div>

          {selectedLocation && (
            <div className="info-card">
              <h4>📍 {selectedLocation.name}</h4>
              <p>
                <strong>Coords:</strong> {selectedLocation.lat.toFixed(4)},{" "}
                {selectedLocation.lng.toFixed(4)}
              </p>
              <p>
                <strong>Date:</strong> {startDate}
              </p>
              <p>
                <strong>Days:</strong> {numDays}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnglishCountryMap;
