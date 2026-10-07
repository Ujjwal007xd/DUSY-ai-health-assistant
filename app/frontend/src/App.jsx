import DusyLogo from './components/DusyLogo';
import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import Dashboard from './pages/Dashboard';
import ChatPage from './pages/ChatPage';
import ProfilePage from './pages/ProfilePage';
import PreventivePage from './pages/PreventivePage';
import AgentPage from './pages/AgentPage';
import './App.css';

const Navbar = () => {
  const { user, token, logout } = useAuth();
  const [hash, setHash] = useState(window.location.hash || '#/');

  useEffect(() => {
    const handleHashChange = () => setHash(window.location.hash || '#/');
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const isHomeActive = !hash || hash === '#/' || hash === '#/home' || hash === '#/dashboard';
  const isAgentActive = hash === '#/agent';
  const isChatActive = hash === '#/chat';
  const isDietActive = hash === '#/diet' || hash === '#/preventive';
  const isProfileActive = hash === '#/profile';

  return (
    <nav className="site-navbar">
      <div className="nav-container">
        {/* Brand Logo matching screenshot */}
        <a href="#/dashboard" className="brand-logo">
          <DusyLogo />
        </a>

        {/* Center navigation links */}
        <div className="nav-menu">
          <a href="#/dashboard" className={`nav-item ${isHomeActive ? 'active' : ''}`}>Home</a>
          <a href="#/agent" className={`nav-item ${isAgentActive ? 'active' : ''}`}>DUSY Agent</a>
          <a href="#/chat" className={`nav-item ${isChatActive ? 'active' : ''}`}>AI Chat</a>
          <a href="#/preventive" className={`nav-item ${isDietActive ? 'active' : ''}`}>Diet &amp; Fitness</a>
          <a href="#/profile" className={`nav-item ${isProfileActive ? 'active' : ''}`}>Dashboard</a>
        </div>

        {/* Right auth buttons matching screenshot */}
        <div className="nav-actions">
          {token ? (
            <div className="user-logged-box">
              <span className="user-pill">👤 {user?.name || 'User'}</span>
              <button onClick={logout} className="btn-signout">Sign Out</button>
            </div>
          ) : (
            <div className="auth-buttons-row">
              <a href="#/login" className="btn-signin-link">Sign In</a>
              <a href="#/register" className="btn-get-started">Get Started</a>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

const Router = () => {
  const [hash, setHash] = useState(window.location.hash || '#/');
  const { token, loading } = useAuth();

  useEffect(() => {
    const handleHashChange = () => setHash(window.location.hash || '#/');
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  if (loading) {
    return (
      <div className="global-loader-screen">
        <div className="loader-ring"></div>
        <p className="loader-text">Loading DUSY...</p>
      </div>
    );
  }

  // Route resolver: home is always visible!
  let CurrentPage = Dashboard;

  if (hash === '#/login') {
    CurrentPage = LoginPage;
  } else if (hash === '#/register') {
    CurrentPage = RegisterPage;
  } else if (hash === '#/agent') {
    CurrentPage = AgentPage;
  } else if (hash === '#/chat') {
    CurrentPage = ChatPage;
  } else if (hash === '#/profile') {
    CurrentPage = ProfilePage;
  } else if (hash === '#/preventive' || hash === '#/diet') {
    CurrentPage = PreventivePage;
  } else {
    CurrentPage = Dashboard;
  }

  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-viewport">
        <CurrentPage />
      </main>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <Router />
    </AuthProvider>
  );
}
