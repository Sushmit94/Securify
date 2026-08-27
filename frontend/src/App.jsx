import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage.jsx';
import Dashboard from './pages/Dashboard.jsx';

function LandingRoute() {
  const navigate = useNavigate();
  return <LandingPage onLaunch={() => navigate('/dashboard')} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingRoute />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}