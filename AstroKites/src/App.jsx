import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './component/navbar';
import Home from './pages/homePage';
import Forecast from './pages/forecast';
import Maps from './pages/maps';
import './App.css';

function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/forecast" element={<Forecast />} />
        <Route path="/maps" element={<Maps />} />
      </Routes>
    </Router>
  );
}

export default App
