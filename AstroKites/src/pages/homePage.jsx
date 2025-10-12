import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./home.css";
// import RotatingEarth from "../component/Globe";

const Home = () => {
  const navigate = useNavigate();

  const handleExploreForecast = () => {
    navigate('/forecast');
  };

  return (
    <div className="home">
      {/* Hero Section */}
      <section className="hero">
        <div className="overlay">
          <div className="hero-content hero-large">
            <div className="topbar">
              <h1 className="hero-title">
                Precise <span className="highlight">weather</span>, precisely for you.
              </h1>
              <p className="hero-subtitle">
                Harness the power of probability-based forecasting for smarter decisions
              </p>
            </div>
            <button className="cta-button start" onClick={handleExploreForecast}>Explore Forecast</button>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="about">
        <h2>About Astrokites</h2>
        <p>
          Astrokites delivers hyper-local weather updates and interactive
          forecasts powered by <strong>probability-based analytics</strong> and statistical modeling. 
          Access both <strong>future weather predictions</strong> and <strong>historical weather data</strong> 
          to make smarter decisions with confidence scores and data-driven insights — 
          whether you're planning ahead or analyzing past weather patterns.
        </p>
      </section>

      {/* Features Section */}
      <section className="features">
        <h2>Our Key Features</h2>
        <div className="feature-cards">
          <div className="feature">
            <h3>🌦 Real-Time Forecasts</h3>
            <p>
              Get instant, location-based weather updates with probability-driven
              insights.
            </p>
          </div>
          <div className="feature">
            <h3>🗺 Dynamic Maps</h3>
            <p>
              Visualize temperature, wind flow, and rain movements interactively
              across regions with satellite imagery.
            </p>
          </div>
          <div className="feature">
            <h3>⚡ Smart Alerts</h3>
            <p>
              Receive early warnings for storms, rainfall, and changing weather
              conditions via push notifications.
            </p>
          </div>
          <div className="feature">
            <h3>📊 Advanced Analytics</h3>
            <p>
              Comprehensive weather analytics with probability distributions for future predictions, 
              complete historical weather archives, air quality indices, and trend analysis.
            </p>
          </div>
          <div className="feature">
            <h3>🌍 Global Coverage</h3>
            <p>
              Weather data for over 200,000 cities worldwide with hyper-local
              precision down to street level.
            </p>
          </div>
          <div className="feature">
            <h3>🔮 Probability-Based Forecasts</h3>
            <p>
              Advanced statistical models deliver multi-day future predictions with
              confidence scores and probability metrics, plus access to historical weather patterns.
            </p>
          </div>
        </div>
      </section>


      {/* Why Choose Us Section */}
      <section className="why-choose-us">
        <h2>Why Choose Astrokites</h2>
        <p className="section-subtitle">
          Powered by advanced statistical models and real-world data
        </p>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🌍</div>
            <div className="stat-number">200K+</div>
            <div className="stat-label">Global Locations</div>
            <div className="stat-description">
              Hyper-local weather data for cities worldwide
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📈</div>
            <div className="stat-number">30+ Years</div>
            <div className="stat-label">Historical Data</div>
            <div className="stat-description">
              Comprehensive weather archives for trend analysis
            </div>
          </div>
        </div>
        <div className="data-sources">
          <h3>Trusted Data Sources</h3>
          <div className="sources-list">
            <div className="source-item">🛰️ NASA POWER API</div>
            <div className="source-item">🌐 OpenStreetMap</div>
            <div className="source-item">📡 Satellite Imagery</div>
            <div className="source-item">🔬 Statistical Models</div>
          </div>
        </div>
      </section>

      {/* Newsletter Section */}
      <section className="newsletter">
        <div className="newsletter-content">
          <h2>Stay Weather-Wise</h2>
          <p>Get weekly weather insights and storm alerts delivered to your inbox.</p>
          <form className="newsletter-form">
            <input 
              type="email" 
              placeholder="Enter your email address" 
              className="newsletter-input"
            />
            <button type="submit" className="newsletter-button">
              Subscribe
            </button>
          </form>
          <div className="newsletter-benefits">
            <span>✓ Weekly forecasts</span>
            <span>✓ Storm alerts</span>
            <span>✓ Climate insights</span>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <p>© 2025 Astrokites. All Rights Reserved.</p>
      </footer>
    </div>
  );
};

export default Home;
