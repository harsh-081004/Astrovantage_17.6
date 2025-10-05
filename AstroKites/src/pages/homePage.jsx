import React, { useState, useEffect } from "react";
import "./home.css";

const Home = () => {
  const [countries, setCountries] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState("US");
  const [selectedState, setSelectedState] = useState("CA");
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [countriesLoading, setCountriesLoading] = useState(true);
  const [earthRotation, setEarthRotation] = useState(0);
  const [earthXRotation, setEarthXRotation] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

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
            </div>


            <button className="cta-button start">Explore forecast</button>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="about">
        <h2>About Astrokites</h2>
        <p>
          Astrokites delivers hyper-local weather updates and interactive
          forecasts powered by advanced data analytics. We help you make smarter
          decisions — whether you’re planning a trip, farming, or just curious
          about the skies.
        </p>
      </section>

      {/* Features Section */}
      <section className="features">
        <h2>Our Key Features</h2>
        <div className="feature-cards">
          <div className="feature">
            <h3>🌦 Real-Time Forecasts</h3>
            <p>
              Get instant, location-based weather updates with AI-enhanced
              predictions updated every 15 minutes.
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
              Detailed weather analytics including air quality, UV index, and
              historical data comparisons.
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
            <h3>🔮 AI Predictions</h3>
            <p>
              Machine learning algorithms provide 10-day forecasts with
              unprecedented accuracy and reliability.
            </p>
          </div>
        </div>
      </section>


      {/* Testimonials Section */}
      <section className="testimonials">
        <h2>What Our Users Say</h2>
        <div className="testimonial-cards">
          <div className="testimonial">
            <div className="testimonial-content">
              "Astrokites has revolutionized how I plan my outdoor activities. The accuracy is incredible!"
            </div>
            <div className="testimonial-author">
              <div className="author-name">Sarah Johnson</div>
              <div className="author-title">Outdoor Enthusiast</div>
            </div>
            <div className="testimonial-rating">⭐⭐⭐⭐⭐</div>
          </div>
          <div className="testimonial">
            <div className="testimonial-content">
              "As a farmer, I rely on precise weather data. Astrokites gives me the edge I need."
            </div>
            <div className="testimonial-author">
              <div className="author-name">Mike Chen</div>
              <div className="author-title">Agricultural Professional</div>
            </div>
            <div className="testimonial-rating">⭐⭐⭐⭐⭐</div>
          </div>
          <div className="testimonial">
            <div className="testimonial-content">
              "The interface is beautiful and the data is always up-to-date. Highly recommended!"
            </div>
            <div className="testimonial-author">
              <div className="author-name">Emily Rodriguez</div>
              <div className="author-title">Weather Enthusiast</div>
            </div>
            <div className="testimonial-rating">⭐⭐⭐⭐⭐</div>
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
