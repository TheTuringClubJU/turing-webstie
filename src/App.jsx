import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import Navbar from './components/Navbar';
import NotificationBar from './components/NotificationBar';
import Footer from './components/Footer';
import Home from './pages/Home';
import OurWork from './pages/OurWork';
import EventDetail from './pages/EventDetail';
import Results from './pages/Results';

function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (hash) return;
    window.scrollTo(0, 0);
  }, [pathname, hash]);

  return null;
}

function App() {
  return (
    <BrowserRouter>
      <div className="bg-bg min-h-screen">
        <Navbar />
        <NotificationBar />
        <ScrollToTop />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/our-work" element={<OurWork />} />
          <Route path="/our-work/:slug" element={<EventDetail />} />
          <Route path="/our-work/:slug/results" element={<Results />} />
        </Routes>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App;