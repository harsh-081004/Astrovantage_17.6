import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import Navbar from './component/navbar.jsx';
import Home from './pages/homePage.jsx';
import ForecastPage from './pages/forecast.jsx';
import Signup from './pages/signup.jsx';
import EnglishCountryMap from './pages/maps.jsx';

const NotFound = () => (
  <div style={{ padding: 40, color: "#fff", textAlign: "center" }}>
    <h2>Page not found</h2>
    <p>Return to <a href="/">home</a>.</p>
  </div>
);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/home" element={<Home />} />
          <Route path="/forecast" element={<ForecastPage />} />
          <Route path="/maps" element={<EnglishCountryMap />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </BrowserRouter>
  </StrictMode>
);
