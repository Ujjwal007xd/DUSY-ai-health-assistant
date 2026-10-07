import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import './ProfilePage.css';

export default function ProfilePage() {
  const { token, user } = useAuth();
  const [formData, setFormData] = useState({
    height_cm: '',
    weight_kg: '',
    blood_group: '',
    medical_conditions: '',
    allergies: '',
    current_medications: '',
    family_history: '',
    contact_name: '',
    contact_phone: ''
  });
  const [serverBmi, setServerBmi] = useState(null);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    const fetchProfile = async () => {
      try {
        const profile = await api.get('/api/health/profile');
        if (profile) {
          setFormData({
            height_cm: profile.height_cm || '',
            weight_kg: profile.weight_kg || '',
            blood_group: profile.blood_group || '',
            medical_conditions: profile.medical_conditions?.join(', ') || '',
            allergies: profile.allergies?.join(', ') || '',
            current_medications: profile.current_medications?.join(', ') || '',
            family_history: profile.family_history?.join(', ') || '',
            contact_name: profile.emergency_contacts?.[0]?.name || '',
            contact_phone: profile.emergency_contacts?.[0]?.phone || ''
          });
          if (profile.bmi) {
            setServerBmi({ bmi: profile.bmi, category: profile.bmi_category });
          }
        }
      } catch (error) {
        console.log('Profile not created yet, starting fresh.');
      }
    };
    fetchProfile();
  }, [token]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  // Instant client-side BMI calculation
  const getBmiInfo = () => {
    const h = parseFloat(formData.height_cm);
    const w = parseFloat(formData.weight_kg);
    if (!h || !w || h <= 0 || w <= 0) return serverBmi || null;
    
    const bmi = parseFloat((w / Math.pow(h / 100, 2)).toFixed(1));
    let category = '';
    let color = '';
    
    if (bmi < 18.5) { category = 'Underweight'; color = '#EAB308'; }
    else if (bmi <= 24.9) { category = 'Normal weight'; color = '#10B981'; }
    else if (bmi <= 29.9) { category = 'Overweight'; color = '#F59E0B'; }
    else { category = 'Obese'; color = '#EF4444'; }
    
    return { bmi, category, color };
  };

  const bmiInfo = getBmiInfo();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token) {
      setMessage({ type: 'error', text: 'Please sign in to save your profile.' });
      return;
    }

    setLoading(true);
    setMessage({ type: '', text: '' });

    const payload = {
      height_cm: parseFloat(formData.height_cm) || null,
      weight_kg: parseFloat(formData.weight_kg) || null,
      blood_group: formData.blood_group || null,
      medical_conditions: formData.medical_conditions.split(',').map(s => s.trim()).filter(Boolean),
      allergies: formData.allergies.split(',').map(s => s.trim()).filter(Boolean),
      current_medications: formData.current_medications.split(',').map(s => s.trim()).filter(Boolean),
      family_history: formData.family_history.split(',').map(s => s.trim()).filter(Boolean),
      emergency_contacts: formData.contact_name ? [{
        name: formData.contact_name,
        relationship: 'Emergency Contact',
        phone: formData.contact_phone || ''
      }] : []
    };

    try {
      const saved = await api.post('/api/health/profile', payload);
      setMessage({ type: 'success', text: 'Health profile updated successfully!' });
      if (saved?.bmi) {
        setServerBmi({ bmi: saved.bmi, category: saved.bmi_category });
      }
    } catch (error) {
      console.error('Error saving profile:', error);
      setMessage({ type: 'error', text: error.message || 'Failed to save health profile.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="profile-viewport-page">
      <div className="profile-card-container">
        
        <div className="profile-top-header">
          <div className="profile-badge-icon">📋</div>
          <div>
            <h1 className="profile-heading-title">Health Profile &amp; Vitals</h1>
            <p className="profile-subheading">
              Personalize your health assistant by keeping your health metrics and history up to date.
            </p>
          </div>
        </div>

        {!token && (
          <div className="profile-login-reminder">
            <span>🔒 You are viewing the demo form. </span>
            <a href="#/login">Sign in to save your personal medical profile</a>
          </div>
        )}

        {message.text && (
          <div className={`profile-status-alert alert-${message.type}`}>
            {message.type === 'success' ? '✅' : '⚠️'} {message.text}
          </div>
        )}

        <form className="profile-data-form" onSubmit={handleSubmit}>
          
          {/* Biometrics */}
          <div className="form-section-card">
            <h3 className="section-header-title">Physical Metrics</h3>
            <div className="form-two-col-grid">
              <div className="form-field-unit">
                <label>Height (cm)</label>
                <input
                  type="number"
                  name="height_cm"
                  placeholder="e.g. 175"
                  value={formData.height_cm}
                  onChange={handleChange}
                />
              </div>

              <div className="form-field-unit">
                <label>Weight (kg)</label>
                <input
                  type="number"
                  name="weight_kg"
                  placeholder="e.g. 70"
                  value={formData.weight_kg}
                  onChange={handleChange}
                />
              </div>
            </div>

            {/* Live BMI Indicator */}
            {bmiInfo && (
              <div className="bmi-gauge-banner">
                <div className="bmi-info-left">
                  <span className="bmi-title">Calculated BMI</span>
                  <span className="bmi-num">{bmiInfo.bmi}</span>
                </div>
                <span className="bmi-pill-tag" style={{ backgroundColor: bmiInfo.color || '#10B981' }}>
                  {bmiInfo.category}
                </span>
              </div>
            )}

            <div className="form-field-unit mt-3">
              <label>Blood Group</label>
              <select name="blood_group" value={formData.blood_group} onChange={handleChange}>
                <option value="">Select Blood Group...</option>
                <option value="A+">A+</option>
                <option value="A-">A-</option>
                <option value="B+">B+</option>
                <option value="B-">B-</option>
                <option value="AB+">AB+</option>
                <option value="AB-">AB-</option>
                <option value="O+">O+</option>
                <option value="O-">O-</option>
              </select>
            </div>
          </div>

          {/* Medical Context */}
          <div className="form-section-card">
            <h3 className="section-header-title">Medical History &amp; Allergies</h3>
            <div className="form-field-unit">
              <label>Existing Medical Conditions (comma-separated)</label>
              <input
                type="text"
                name="medical_conditions"
                placeholder="e.g. Hypertension, Mild Asthma"
                value={formData.medical_conditions}
                onChange={handleChange}
              />
            </div>

            <div className="form-field-unit mt-3">
              <label>Allergies (comma-separated)</label>
              <input
                type="text"
                name="allergies"
                placeholder="e.g. Penicillin, Peanuts, Pollen"
                value={formData.allergies}
                onChange={handleChange}
              />
            </div>

            <div className="form-field-unit mt-3">
              <label>Current Medications</label>
              <input
                type="text"
                name="current_medications"
                placeholder="e.g. Metformin 500mg, Multivitamin"
                value={formData.current_medications}
                onChange={handleChange}
              />
            </div>

            <div className="form-field-unit mt-3">
              <label>Family Medical History</label>
              <input
                type="text"
                name="family_history"
                placeholder="e.g. Type 2 Diabetes, Heart disease"
                value={formData.family_history}
                onChange={handleChange}
              />
            </div>
          </div>

          {/* Emergency Contact */}
          <div className="form-section-card">
            <h3 className="section-header-title">Emergency Contact</h3>
            <div className="form-two-col-grid">
              <div className="form-field-unit">
                <label>Contact Person Name</label>
                <input
                  type="text"
                  name="contact_name"
                  placeholder="e.g. Jane Doe"
                  value={formData.contact_name}
                  onChange={handleChange}
                />
              </div>
              <div className="form-field-unit">
                <label>Contact Phone Number</label>
                <input
                  type="text"
                  name="contact_phone"
                  placeholder="e.g. +1 555-0199"
                  value={formData.contact_phone}
                  onChange={handleChange}
                />
              </div>
            </div>
          </div>

          <button type="submit" className="save-profile-btn" disabled={loading}>
            {loading ? 'Updating Profile...' : 'Save Profile & Update Vitals'}
          </button>
        </form>
      </div>
    </div>
  );
}
