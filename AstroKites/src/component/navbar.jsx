import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User, Home, CloudRain, Map } from "lucide-react";
import './navbar.css'; // Import the pure CSS file

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const go = (path) => {
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
              <CloudRain className="logoIcon" />
              <h1 className="logoText">Astrokites</h1>
            </div>
            
            {/* Desktop Navigation with icons */}
            <div className="desktopNav">
              <button className="navButton" onClick={() => go('/')}>
                <Home className="icon" />
                <span>Home</span>
              </button>
              <button className="navButton" onClick={() => go('/forecast')}>
                <CloudRain className="icon" />
                <span>Forecast</span>
              </button>
              <button className="navButton" onClick={() => go('/maps')}>
                <Map className="icon" />
                <span>Maps</span>
              </button>
            </div>
          </div>

          {/* Search and user section */}
          <div className="flex-center">

            {/* User buttons with icon */}
            <div className="userButtons">
              <button className="signInButton">
                <User className="icon" />
                <span>Sign In</span>
              </button>
              <button className="signUpButton">
                <User className="icon" />
                <span onClick={() => go('/signup')}>Sign Up</span>
              </button>
            </div>

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
              <button className="mobileNavButton" onClick={() => { go('/'); setIsMenuOpen(false); }}>
                <Home className="icon" />
                <span>Home</span>
              </button>
              <button className="mobileNavButton" onClick={() => { go('/forecast'); setIsMenuOpen(false); }}>
                <CloudRain className="icon" />
                <span>Forecast</span>
              </button>
              <button className="mobileNavButton" onClick={() => { go('/maps'); setIsMenuOpen(false); }}>
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