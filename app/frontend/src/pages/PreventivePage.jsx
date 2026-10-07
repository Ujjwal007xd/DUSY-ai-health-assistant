import React, { useState } from 'react';
import api from '../api/axios';
import './PreventivePage.css';

const presets = {
  highRisk: {
    sleep_hours: 5.5,
    exercise_minutes_per_day: 10,
    daily_steps: 3200,
    water_intake_liters: 1.2,
    diet_type: 'junk-heavy',
    sugary_drinks_per_week: 8,
    smoking: false,
    alcohol_drinks_per_week: 3,
    stress_level: 'high',
    screen_time_hours: 9
  },
  healthy: {
    sleep_hours: 7.5,
    exercise_minutes_per_day: 35,
    daily_steps: 8500,
    water_intake_liters: 2.5,
    diet_type: 'balanced',
    sugary_drinks_per_week: 1,
    smoking: false,
    alcohol_drinks_per_week: 1,
    stress_level: 'low',
    screen_time_hours: 5
  }
};

export default function PreventivePage() {
  const [tab, setTab] = useState(1);
  const [form, setForm] = useState(presets.highRisk);
  const [riskResult, setRiskResult] = useState(null);
  const [changesResult, setChangesResult] = useState(null);
  const [projResult, setProjResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({
      ...f,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseFloat(value) || 0 : value
    }));
  };

  const applyPreset = (presetKey) => {
    setForm(presets[presetKey]);
    setRiskResult(null);
    setChangesResult(null);
    setProjResult(null);
    setError('');
  };

  const analyzeRisk = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/preventive/risk-profile', { lifestyle: form });
      setRiskResult(res);
      return res;
    } catch (e) {
      setError(e.message || 'Failed to analyze risk profile.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  const getChanges = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/preventive/top-changes', { lifestyle: form });
      setChangesResult(res);
    } catch (e) {
      setError(e.message || 'Failed to fetch top changes.');
    } finally {
      setLoading(false);
    }
  };

  const getProjection = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/preventive/projection', { lifestyle: form });
      setProjResult(res);
    } catch (e) {
      setError(e.message || 'Failed to generate projection.');
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (s) => s < 30 ? 'low' : s < 50 ? 'moderate' : s < 70 ? 'high' : 'very-high';
  const barColor = (s) => s < 30 ? '#10B981' : s < 50 ? '#F59E0B' : s < 70 ? '#EF4444' : '#991B1B';

  return (
    <div className="preventive-viewport-page">
      <div className="preventive-max-box">
        
        {/* Page Header */}
        <div className="prev-header-box">
          <span className="prev-badge-tag">EXCLUSIVE UNIQUE ENGINE</span>
          <h1 className="prev-main-title">Preventive Health Risk &amp; Trajectory</h1>
          <p className="prev-subtitle-copy">
            Unlike conventional symptom checkers, our Preventive Engine forecasts long-term risks, identifies your top 3 highest-impact lifestyle adjustments, and simulates your 2-year health trajectory.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="prev-tabs-row">
          <button
            className={`prev-tab-btn ${tab === 1 ? 'active' : ''}`}
            onClick={() => setTab(1)}
          >
            📊 1. Risk Profile
          </button>
          <button
            className={`prev-tab-btn ${tab === 2 ? 'active' : ''}`}
            onClick={() => {
              setTab(2);
              if (!changesResult) getChanges();
            }}
          >
            🎯 2. Highest-Impact Changes
          </button>
          <button
            className={`prev-tab-btn ${tab === 3 ? 'active' : ''}`}
            onClick={() => {
              setTab(3);
              if (!projResult) getProjection();
            }}
          >
            📈 3. Future Health Projection
          </button>
        </div>

        {error && <div className="prev-error-alert">⚠️ {error}</div>}

        {/* ─── TAB 1: Risk Profile ─── */}
        {tab === 1 && (
          <div className="tab-pane-content">
            <div className="lifestyle-input-card">
              <div className="card-top-action-bar">
                <h3 className="card-group-title">Lifestyle Input Parameters</h3>
                <div className="presets-row">
                  <span className="preset-label">Quick Demo:</span>
                  <button type="button" className="preset-chip chip-warn" onClick={() => applyPreset('highRisk')}>
                    ⚡ Load At-Risk Profile
                  </button>
                  <button type="button" className="preset-chip chip-good" onClick={() => applyPreset('healthy')}>
                    🌱 Load Healthy Profile
                  </button>
                </div>
              </div>

              <div className="lifestyle-inputs-grid">
                <div className="form-param-unit">
                  <label>Sleep (hours/night)</label>
                  <input type="number" name="sleep_hours" value={form.sleep_hours} onChange={handleChange} step="0.5" min="0" max="24" />
                </div>
                <div className="form-param-unit">
                  <label>Exercise (minutes/day)</label>
                  <input type="number" name="exercise_minutes_per_day" value={form.exercise_minutes_per_day} onChange={handleChange} />
                </div>
                <div className="form-param-unit">
                  <label>Daily Step Count</label>
                  <input type="number" name="daily_steps" value={form.daily_steps} onChange={handleChange} />
                </div>
                <div className="form-param-unit">
                  <label>Water Intake (liters/day)</label>
                  <input type="number" name="water_intake_liters" value={form.water_intake_liters} onChange={handleChange} step="0.1" />
                </div>
                <div className="form-param-unit">
                  <label>Diet Pattern</label>
                  <select name="diet_type" value={form.diet_type} onChange={handleChange}>
                    <option value="balanced">Balanced Diet</option>
                    <option value="junk-heavy">Junk-Heavy / Processed</option>
                    <option value="high-carb">High Carbohydrate</option>
                    <option value="high-protein">High Protein</option>
                    <option value="vegetarian">Vegetarian</option>
                    <option value="vegan">Vegan</option>
                  </select>
                </div>
                <div className="form-param-unit">
                  <label>Sugary Beverages (per week)</label>
                  <input type="number" name="sugary_drinks_per_week" value={form.sugary_drinks_per_week} onChange={handleChange} />
                </div>
                <div className="form-param-unit">
                  <label>Alcohol Drinks (per week)</label>
                  <input type="number" name="alcohol_drinks_per_week" value={form.alcohol_drinks_per_week} onChange={handleChange} />
                </div>
                <div className="form-param-unit">
                  <label>Reported Stress Level</label>
                  <select name="stress_level" value={form.stress_level} onChange={handleChange}>
                    <option value="low">Low Stress</option>
                    <option value="moderate">Moderate Stress</option>
                    <option value="high">High Stress</option>
                    <option value="very-high">Severe / Chronic Stress</option>
                  </select>
                </div>
                <div className="form-param-unit">
                  <label>Screen Time (hours/day)</label>
                  <input type="number" name="screen_time_hours" value={form.screen_time_hours} onChange={handleChange} />
                </div>
                <div className="form-param-unit param-checkbox-unit">
                  <label className="checkbox-flex-label">
                    <input type="checkbox" name="smoking" checked={form.smoking} onChange={handleChange} />
                    <span>Active Tobacco Smoker</span>
                  </label>
                </div>
              </div>

              <button className="run-analysis-btn" onClick={analyzeRisk} disabled={loading}>
                {loading ? 'Evaluating Health Data...' : '⚡ Generate Preventive Risk Assessment'}
              </button>
            </div>

            {/* Results Section */}
            {riskResult && (
              <div className="results-animated-block">
                
                {/* Overall Score Gauge Box */}
                <div className="overall-risk-banner">
                  <div className={`score-badge-circle badge-color-${scoreColor(riskResult.overall_risk_score)}`}>
                    <span className="score-main-value">{riskResult.overall_risk_score}</span>
                    <span className="score-main-denom">/100</span>
                    <span className="score-main-level">{riskResult.overall_risk_level.toUpperCase()}</span>
                  </div>
                  <div className="risk-summary-text-box">
                    <h3 className="summary-title">Preventive Risk Profile Analysis</h3>
                    <p className="summary-body">{riskResult.summary}</p>
                  </div>
                </div>

                {/* 5 Risk Categories */}
                <div className="categories-breakdown-card">
                  <h4 className="breakdown-title">Multi-Factor Risk Breakdown</h4>
                  
                  {riskResult.risk_categories?.map((cat, idx) => (
                    <div key={idx} className="category-row-item">
                      <div className="cat-row-top">
                        <span className="cat-label-title">{cat.category}</span>
                        <span className="cat-score-text" style={{ color: barColor(cat.risk_score) }}>
                          {cat.risk_score} / 100 &bull; {cat.risk_level.toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="cat-progress-track">
                        <div
                          className="cat-progress-bar"
                          style={{
                            width: `${Math.max(cat.risk_score, 4)}%`,
                            backgroundColor: barColor(cat.risk_score)
                          }}
                        ></div>
                      </div>

                      {cat.contributing_factors?.length > 0 && (
                        <div className="cat-factors-tags">
                          {cat.contributing_factors.map((factor, fIdx) => (
                            <span key={fIdx} className="factor-pill">⚠️ {factor}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Screening Advice */}
                {riskResult.screening_recommendations?.length > 0 && (
                  <div className="screening-recommendations-card">
                    <div className="screening-card-header">
                      <span className="screening-icon">🩺</span>
                      <h4>Proactive Medical Screenings to Consider</h4>
                    </div>
                    <ul className="screening-list">
                      {riskResult.screening_recommendations.map((rec, rIdx) => (
                        <li key={rIdx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="engine-disclaimer-note">
                  ℹ️ {riskResult.disclaimer}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── TAB 2: Top 3 Changes ─── */}
        {tab === 2 && (
          <div className="tab-pane-content">
            <div className="tab-intro-card">
              <h3>🎯 Personalized Highest-Impact Predictor</h3>
              <p>
                Rather than generic advice ("eat better, exercise more"), our AI analyzes your highest-weight risk contributors and identifies the specific 3 lifestyle tweaks that yield the maximum risk reduction.
              </p>
              <button className="run-analysis-btn mt-3" onClick={getChanges} disabled={loading}>
                {loading ? 'Evaluating Model...' : '🔄 Refresh Top 3 Changes'}
              </button>
            </div>

            {changesResult && (
              <div className="changes-results-wrapper">
                <div className="impact-cards-grid">
                  {changesResult.top_changes?.map((item, idx) => (
                    <div key={idx} className="impact-recommendation-card">
                      <div className={`rank-medal rank-medal-${item.rank}`}>#{item.rank}</div>
                      <h4 className="impact-action-title">{item.change}</h4>

                      <div className="current-target-box">
                        <div className="ct-col">
                          <span className="ct-label">Current</span>
                          <span className="ct-val ct-now">{item.current_value}</span>
                        </div>
                        <span className="ct-arrow">&rarr;</span>
                        <div className="ct-col">
                          <span className="ct-label">Target</span>
                          <span className="ct-val ct-goal">{item.target_value}</span>
                        </div>
                      </div>

                      <div className="impact-level-pill-row">
                        <span className={`impact-level-tag tag-${item.impact_level}`}>
                          {item.impact_level.toUpperCase()} IMPACT
                        </span>
                      </div>

                      {item.affected_risks?.length > 0 && (
                        <div className="affected-risks-chips">
                          {item.affected_risks.map((risk, rIdx) => (
                            <span key={rIdx} className="risk-chip">{risk}</span>
                          ))}
                        </div>
                      )}

                      {item.expected_risk_reduction && (
                        <div className="expected-reduction-note">
                          📉 {item.expected_risk_reduction}
                        </div>
                      )}

                      <p className="impact-reasoning">{item.explanation}</p>
                    </div>
                  ))}
                </div>

                {changesResult.personalization_note && (
                  <div className="personalization-callout-box">
                    <strong>💡 Why this prioritization?</strong> {changesResult.personalization_note}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ─── TAB 3: Future Projection ─── */}
        {tab === 3 && (
          <div className="tab-pane-content">
            <div className="tab-intro-card">
              <h3>📈 24-Month Future Health Trajectory</h3>
              <p>
                A visual simulation of your health forecast. Compare your <strong>Current Path</strong> (if habits remain unchanged) versus your <strong>Optimized Path</strong> (if you implement the recommended changes).
              </p>
              <button className="run-analysis-btn mt-3" onClick={getProjection} disabled={loading}>
                {loading ? 'Simulating Trajectory...' : '🔄 Run Trajectory Simulation'}
              </button>
            </div>

            {projResult && (
              <div className="projection-results-wrapper">
                
                {projResult.key_insight && (
                  <div className="key-insight-spotlight-box">
                    <span className="insight-spark">⚡ Key Projection Insight</span>
                    <p className="insight-text">{projResult.key_insight}</p>
                  </div>
                )}

                <div className="trajectory-table-card">
                  <table className="trajectory-data-table">
                    <thead>
                      <tr>
                        <th>Path Scenario</th>
                        <th>Current Baseline</th>
                        <th>3 Months</th>
                        <th>6 Months</th>
                        <th>12 Months</th>
                        <th>24 Months</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="row-current-path">
                        <td className="scenario-label-cell">
                          <span className="scenario-dot dot-red"></span> Current Lifestyle (No Change)
                        </td>
                        {projResult.current_trajectory?.map((point, pIdx) => (
                          <td key={pIdx} className="score-cell cell-worse">
                            {point.overall_risk_score}
                          </td>
                        ))}
                      </tr>
                      <tr className="row-improved-path">
                        <td className="scenario-label-cell">
                          <span className="scenario-dot dot-green"></span> With Top 3 Changes
                        </td>
                        {projResult.improved_trajectory?.map((point, pIdx) => (
                          <td key={pIdx} className="score-cell cell-better">
                            {point.overall_risk_score}
                          </td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>

                {projResult.changes_applied?.length > 0 && (
                  <div className="applied-improvements-box">
                    <h5 className="improvements-title">Modeled Lifestyle Adjustments:</h5>
                    <ul className="improvements-list">
                      {projResult.changes_applied.map((change, cIdx) => (
                        <li key={cIdx}>&check; {change}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="engine-disclaimer-note">
                  ℹ️ {projResult.disclaimer}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
