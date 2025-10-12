import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./navbar.css";

// AstroKites Logo - Enhanced design with dark blue theme
const AstroKitesLogo = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 120 120" fill="none" {...props}>
    <defs>
      {/* Dark blue gradient for kite */}
      <linearGradient id="kiteGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{ stopColor: '#1e40af', stopOpacity: 1 }} />
        <stop offset="50%" style={{ stopColor: '#3b82f6', stopOpacity: 1 }} />
        <stop offset="100%" style={{ stopColor: '#1e3a8a', stopOpacity: 1 }} />
      </linearGradient>
      
      {/* Golden star gradient */}
      <linearGradient id="starGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{ stopColor: '#fbbf24', stopOpacity: 1 }} />
        <stop offset="100%" style={{ stopColor: '#f59e0b', stopOpacity: 1 }} />
      </linearGradient>
      
      {/* Glow effect */}
      <filter id="glow">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      
      {/* Shadow */}
      <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
        <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1e3a8a" floodOpacity="0.5"/>
      </filter>
    </defs>
    
    {/* Outer glow circle */}
    <circle cx="60" cy="60" r="52" fill="none" stroke="#3b82f6" strokeWidth="1" opacity="0.2">
      <animate attributeName="r" values="52;54;52" dur="3s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.2;0.4;0.2" dur="3s" repeatCount="indefinite"/>
    </circle>
    
    {/* Main kite diamond - larger and centered */}
    <path d="M 60 20 L 85 55 L 60 90 L 35 55 Z" 
          fill="url(#kiteGradient)" 
          stroke="#1e40af" 
          strokeWidth="3"
          filter="url(#shadow)"/>
    
    {/* Kite inner details - geometric pattern */}
    <path d="M 60 20 L 60 90" stroke="#93c5fd" strokeWidth="2" opacity="0.6"/>
    <path d="M 35 55 L 85 55" stroke="#93c5fd" strokeWidth="2" opacity="0.6"/>
    
    {/* Decorative triangles inside kite */}
    <path d="M 60 20 L 72 55 L 60 55 Z" fill="#1e3a8a" opacity="0.3"/>
    <path d="M 60 20 L 48 55 L 60 55 Z" fill="#3b82f6" opacity="0.3"/>
    
    {/* Stars with sparkle effect */}
    <g filter="url(#glow)">
      {/* Top left star */}
      <path d="M 25 30 L 27 35 L 32 35 L 28 38 L 30 43 L 25 40 L 20 43 L 22 38 L 18 35 L 23 35 Z" 
            fill="url(#starGradient)">
        <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>
        <animateTransform attributeName="transform" type="rotate" 
                         from="0 25 35" to="360 25 35" dur="4s" repeatCount="indefinite"/>
      </path>
      
      {/* Top right star */}
      <path d="M 95 30 L 97 35 L 102 35 L 98 38 L 100 43 L 95 40 L 90 43 L 92 38 L 88 35 L 93 35 Z" 
            fill="url(#starGradient)">
        <animate attributeName="opacity" values="0.4;1;0.4" dur="2.5s" repeatCount="indefinite"/>
        <animateTransform attributeName="transform" type="rotate" 
                         from="0 95 35" to="360 95 35" dur="5s" repeatCount="indefinite"/>
      </path>
      
      {/* Right star */}
      <path d="M 100 60 L 101.5 63 L 105 63 L 102 65 L 103 68 L 100 66 L 97 68 L 98 65 L 95 63 L 98.5 63 Z" 
            fill="url(#starGradient)">
        <animate attributeName="opacity" values="1;0.5;1" dur="3s" repeatCount="indefinite"/>
        <animateTransform attributeName="transform" type="rotate" 
                         from="0 100 63" to="360 100 63" dur="6s" repeatCount="indefinite"/>
      </path>
    </g>
    
    {/* Kite tail with ribbons */}
    <g opacity="0.9">
      <path d="M 60 90 Q 65 96 60 100" stroke="#3b82f6" strokeWidth="3" fill="none" strokeLinecap="round">
        <animate attributeName="d" 
                 values="M 60 90 Q 65 96 60 100;M 60 90 Q 55 96 60 100;M 60 90 Q 65 96 60 100" 
                 dur="2s" repeatCount="indefinite"/>
      </path>
      <circle cx="60" cy="100" r="3" fill="#fbbf24">
        <animate attributeName="cy" values="100;102;100" dur="2s" repeatCount="indefinite"/>
      </circle>
      <circle cx="60" cy="105" r="2.5" fill="#3b82f6">
        <animate attributeName="cy" values="105;107;105" dur="2s" repeatCount="indefinite"/>
      </circle>
      <circle cx="60" cy="109" r="2" fill="#1e40af">
        <animate attributeName="cy" values="109;111;109" dur="2s" repeatCount="indefinite"/>
      </circle>
    </g>
    
    {/* Wind lines for dynamic effect */}
    <g opacity="0.3">
      <line x1="15" y1="50" x2="25" y2="50" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round">
        <animate attributeName="x1" values="15;10;15" dur="1.5s" repeatCount="indefinite"/>
        <animate attributeName="x2" values="25;20;25" dur="1.5s" repeatCount="indefinite"/>
      </line>
      <line x1="15" y1="60" x2="28" y2="60" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round">
        <animate attributeName="x1" values="15;12;15" dur="2s" repeatCount="indefinite"/>
        <animate attributeName="x2" values="28;25;28" dur="2s" repeatCount="indefinite"/>
      </line>
    </g>
  </svg>
);

// Import icons from a library like react-feather
const CloudRain = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M20 16.2A4.5 4.5 0 0 0 17.5 8h-1.8A7 7 0 1 0 4 14.9"></path>
    <path d="M16 14v6"></path>
    <path d="M8 14v6"></path>
    <path d="M12 16v6"></path>
  </svg>
);

const Home = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
    <polyline points="9 22 9 12 15 12 15 22"></polyline>
  </svg>
);

const Map = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"></polygon>
    <line x1="9" x2="9" y1="3" y2="18"></line>
    <line x1="15" x2="15" y1="6" y2="21"></line>
  </svg>
);

const User = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
    <circle cx="12" cy="7" r="4"></circle>
  </svg>
);

const Search = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const BarChart2 = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>
);

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();
  const [activePage, setActivePage] = useState(() => {
    // Initialize from localStorage or default to home
    return localStorage.getItem('activePage') || '/';
  });

  // Effect to update localStorage when activePage changes
  useEffect(() => {
    localStorage.setItem('activePage', activePage);
  }, [activePage]);

  const go = (path) => {
    setActivePage(path); // Set active page
    navigate(path);
  };

  const submitSearch = (q, closeMenu = false) => {
    const target = q && q.trim() ? `/forecast?q=${encodeURIComponent(q.trim())}` : '/forecast';
    navigate(target);
    if (closeMenu) setIsMenuOpen(false);
  };

  return (
    <nav className="navbar">
      <div className="navbarContainer">
        <div className="navbarInner">
          {/* Logo and brand name with weather icon */}
          <div className="logoSection">
            <div className="logoWrapper" role="button" onClick={() => go('/')}>
              <AstroKitesLogo className="logoIcon" />
              <h1 className="logoText">AstroKites</h1>
            </div>
            
            {/* Desktop Navigation with icons */}
            <div className="desktopNav">
              <button 
                className={`navButton ${activePage === '/' ? 'active' : ''}`} 
                onClick={() => go('/')}
              >
                <Home className="icon" />
                <span>Home</span>
              </button>
              <button 
                className={`navButton ${activePage === '/forecast' ? 'active' : ''}`} 
                onClick={() => go('/forecast')}
              >
                <CloudRain className="icon" />
                <span>Forecast</span>
              </button>
              <button 
                className={`navButton ${activePage === '/maps' ? 'active' : ''}`} 
                onClick={() => go('/maps')}
              >
                <Map className="icon" />
                <span>Maps</span>
              </button>
            </div>
          </div>

          {/* Search and user section */}
          <div className="flex-center">

            {/* User buttons with icon */}
            {/* <div className="userButtons">
              <button className="signInButton">
                <User className="icon" />
                <span>Sign In</span>
              </button>
              <button className="signUpButton">
                <User className="icon" />
                <span onClick={() => go('/signup')}>Sign Up</span>
              </button>
            </div> */}

            {/* Mobile menu button with weather theme */}
            <div className="mobileMenuButton">
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                aria-label="Toggle menu"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  {isMenuOpen ? (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  ) : (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M4 6h16M4 12h16M4 18h16"
                    />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu with enhanced styling */}
        {isMenuOpen && (
          <div className="mobileMenuWrapper">
            <div className="mobileMenuContent">
              <button 
                className={`mobileNavButton ${activePage === '/' ? 'active' : ''}`} 
                onClick={() => { go('/'); setIsMenuOpen(false); }}
              >
                <Home className="icon" />
                <span>Home</span>
              </button>
              <button 
                className={`mobileNavButton ${activePage === '/forecast' ? 'active' : ''}`} 
                onClick={() => { go('/forecast'); setIsMenuOpen(false); }}
              >
                <CloudRain className="icon" />
                <span>Forecast</span>
              </button>
              <button 
                className={`mobileNavButton ${activePage === '/maps' ? 'active' : ''}`} 
                onClick={() => { go('/maps'); setIsMenuOpen(false); }}
              >
                <Map className="icon" />
                <span>Maps</span>
              </button>
              
              {/* Mobile search */}
              <div className="mobileSearchWrapper">
                <Search className="searchIcon" />
                <input
                  type="text"
                  placeholder="Search location..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') submitSearch(searchQuery, true); }}
                  className="mobileSearchInput"
                />
              </div>
              
              {/* Mobile auth buttons */}
              <div className="mobileAuthButtons">
                <button className="mobileSignInButton">
                  <User className="icon" />
                  <span>Sign In</span>
                </button>
                <button className="mobileSignUpButton">
                  <User className="icon" />
                  <span>Sign Up</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;