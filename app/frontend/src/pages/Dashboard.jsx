import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { DusyLogoIcon } from '../components/DusyLogo';
import './Dashboard.css';

export default function Dashboard() {
  const { user, token } = useAuth();
  const [context, setContext] = useState(null);
  const [loadingContext, setLoadingContext] = useState(true);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const displayName = user?.name ? user.name.toUpperCase() : 'GUEST';

  useEffect(() => {
    if (!token) {
      setLoadingContext(false);
      return;
    }

    api.get('/api/agent/context')
      .then(res => setContext(res))
      .catch(err => console.log('Error loading dashboard health context:', err))
      .finally(() => setLoadingContext(false));
  }, [token]);

  const profile = context?.profile_summary || {};
  const lifestyle = context?.lifestyle_summary || {};
  const completion = context?.completion_percentage ?? (user ? 35 : 0);

  // Dynamic DUSY advice based on real data
  const getDynamicAdvice = () => {
    if (!token) {
      return "Sign in to connect your personal vitals, health records, and autonomous DUSY clinical agent.";
    }
    if (!profile.height_cm && !lifestyle.sleep_hours) {
      return "No health profile recorded yet. Visit your Dashboard or Diet & Fitness to log your metrics for personalized insights.";
    }
    const highlights = [];
    if (profile.bmi) highlights.push(`BMI ${profile.bmi} (${profile.bmi_category || 'Normal'})`);
    if (lifestyle.sleep_hours) highlights.push(`${lifestyle.sleep_hours}h average sleep`);
    if (lifestyle.water_intake_liters) highlights.push(`${lifestyle.water_intake_liters}L daily hydration`);
    if (profile.allergies && profile.allergies.length > 0 && profile.allergies[0] !== 'none') {
      highlights.push(`noting ${profile.allergies.join(', ')} allergy precautions`);
    }
    return `Active metrics loaded: ${highlights.join(', ')}. All parameters are integrated into your DUSY consultations.`;
  };

  return (
    <div className="home-dashboard">
      {/* ─── HERO SECTION ─── */}
      <section className="hero-viewport">
        <div className="hero-inner-container">
          
          {/* Left Column */}
          <div className="hero-text-col">
            <div className="hero-pill-badge">
              <span className="pill-dot"></span>
              <span className="pill-text">Autonomous Clinical Intelligence</span>
            </div>

            <h1 className="hero-headline">
              Your Personal <span className="teal-highlight">DUSY</span><br />
              Health Companion
            </h1>

            <p className="hero-subtext">
              Intelligent, personalized health guidance powered by clinical AI. Analyze your
              symptoms, plan your diet, track vitals, and get proactive wellness
              insights — all in one place.
            </p>

            <div className="hero-cta-group">
              <a href="#/agent" className="cta-btn-primary">
                <span className="cta-agent-icon">🩺</span> Consult DUSY Agent <span className="cta-arrow">&rarr;</span>
              </a>
              <a href="#/preventive" className="cta-btn-outline">
                Diet &amp; Fitness
              </a>
              <a href="#/chat" className="cta-btn-outline">
                <span className="cta-chat-icon">💬</span> General AI Chat
              </a>
            </div>

            <div className="hero-trust-row">
              <div className="trust-cell">
                <span className="trust-emoji">🛡️</span>
                <span>HIPAA-Aware</span>
              </div>
              <div className="trust-cell">
                <span className="trust-emoji">⚡</span>
                <span>AI-Powered</span>
              </div>
              <div className="trust-cell">
                <span className="trust-emoji">⏱️</span>
                <span>24/7 Available</span>
              </div>
            </div>
          </div>

          {/* Right Column: Live User Health Profile Card */}
          <div className="hero-card-col">
            <div className="vitals-floating-card">
              
              {/* Card Header: Greeting & Health Score Circle */}
              <div className="vitals-card-top">
                <div className="greeting-block">
                  <span className="greeting-label">{getGreeting()}</span>
                  <h3 className="greeting-name">{displayName}</h3>
                </div>

                <div className="circular-score-wrapper">
                  <svg className="score-svg" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="42" fill="none" stroke="#E2E8F0" strokeWidth="6" />
                    <circle
                      cx="50" cy="50" r="42"
                      fill="none"
                      stroke="#0D9488"
                      strokeWidth="6"
                      strokeDasharray="264"
                      strokeDashoffset={264 * (1 - (completion / 100))}
                      strokeLinecap="round"
                      transform="rotate(-90 50 50)"
                    />
                  </svg>
                  <div className="score-center-content">
                    <span className="score-big-num">{completion}%</span>
                    <span className="score-micro-label">Health Score</span>
                  </div>
                </div>
              </div>

              {/* Real User Vitals & Habits Tiles (3 columns) */}
              <div className="vitals-tiles-grid">
                <div className="vital-tile vital-tile-bp">
                  <span className="vital-digit">{profile.bmi || '--'}</span>
                  <span className="vital-measurement">{profile.bmi_category ? profile.bmi_category.split(' ')[0] : 'BMI Score'}</span>
                </div>
                <div className="vital-tile vital-tile-sleep">
                  <span className="vital-digit">{lifestyle.sleep_hours ? `${lifestyle.sleep_hours}h` : '--'}</span>
                  <span className="vital-measurement">Daily Sleep</span>
                </div>
                <div className="vital-tile vital-tile-spo2">
                  <span className="vital-digit">{lifestyle.water_intake_liters ? `${lifestyle.water_intake_liters}L` : '--'}</span>
                  <span className="vital-measurement">Hydration</span>
                </div>
              </div>

              {/* User-Provided Medical Baseline Panel */}
              <div className="user-telemetry-panel">
                <div className="telemetry-panel-title">Your Logged Health Baseline</div>
                <div className="telemetry-badges-grid">
                  <div className="telemetry-badge-item">
                    <span className="telemetry-kicker">Height &amp; Weight</span>
                    <span className="telemetry-val">
                      {profile.height_cm && profile.weight_kg ? `${profile.height_cm} cm • ${profile.weight_kg} kg` : 'Not recorded'}
                    </span>
                  </div>
                  <div className="telemetry-badge-item">
                    <span className="telemetry-kicker">Blood Group</span>
                    <span className="telemetry-val">{profile.blood_group || 'Not recorded'}</span>
                  </div>
                  <div className="telemetry-badge-item">
                    <span className="telemetry-kicker">Allergies</span>
                    <span className="telemetry-val">
                      {profile.allergies && profile.allergies.length > 0 && profile.allergies[0] !== 'none'
                        ? profile.allergies.join(', ')
                        : 'None logged'}
                    </span>
                  </div>
                  <div className="telemetry-badge-item">
                    <span className="telemetry-kicker">Daily Exercise</span>
                    <span className="telemetry-val">
                      {lifestyle.exercise_minutes_per_day
                        ? `${lifestyle.exercise_minutes_per_day}m • ${lifestyle.daily_steps || 0} steps`
                        : 'Not logged'}
                    </span>
                  </div>
                </div>
              </div>

              {/* DUSY Clinical Advisor Banner */}
              <div className="ai-advisor-banner">
                <div className="ai-advisor-avatar">
                  <DusyLogoIcon size={20} />
                </div>
                <div className="ai-advisor-copy">
                  <span className="ai-advisor-title">DUSY Assistant</span>
                  <p className="ai-advisor-detail">
                    {getDynamicAdvice()}
                  </p>
                </div>
              </div>

            </div>
          </div>

        </div>
      </section>

      {/* ─── FEATURES SHOWCASE SECTION ─── */}
      <section className="features-showcase-section">
        <div className="features-inner-container">
          
          <div className="features-intro">
            <h2 className="features-main-heading">What can DUSY do for you?</h2>
            <p className="features-lead">
              From instant personalized triage to longitudinal habit optimization,
              DUSY gives you tools to understand and improve your well-being.
            </p>
          </div>

          <div className="features-card-grid">
            <a href="#/agent" className="feature-interactive-card highlight-card">
              <span className="card-badge-unique">AI AGENT</span>
              <div className="card-icon-bubble">🩺</div>
              <h3 className="card-feature-title">DUSY Health Agent</h3>
              <p className="card-feature-desc">
                Your 24/7 autonomous DUSY clinical partner. Correlates symptoms with your actual medical profile and creates tailored habit goals.
              </p>
              <span className="card-action-link">Open Agent &rarr;</span>
            </a>

            <a href="#/chat" className="feature-interactive-card">
              <div className="card-icon-bubble">💬</div>
              <h3 className="card-feature-title">AI Chat</h3>
              <p className="card-feature-desc">
                Ask any health question and receive clear, evidence-based answers backed by clinical medical knowledge.
              </p>
              <span className="card-action-link">Start Chat &rarr;</span>
            </a>

            <a href="#/preventive" className="feature-interactive-card">
              <div className="card-icon-bubble">🥗</div>
              <h3 className="card-feature-title">Diet &amp; Fitness</h3>
              <p className="card-feature-desc">
                Log your sleep, daily steps, water intake, and diet to compute personalized preventive lifestyle scores.
              </p>
              <span className="card-action-link">Analyze Habits &rarr;</span>
            </a>

            <a href="#/profile" className="feature-interactive-card">
              <div className="card-icon-bubble">📋</div>
              <h3 className="card-feature-title">Medical Records</h3>
              <p className="card-feature-desc">
                Keep your height, weight, chronic conditions, and emergency contacts securely saved in your profile.
              </p>
              <span className="card-action-link">Update Records &rarr;</span>
            </a>
          </div>

        </div>
      </section>
    </div>
  );
}
