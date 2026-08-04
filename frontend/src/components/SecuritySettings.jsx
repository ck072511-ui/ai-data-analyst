import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';

const SecuritySettings = ({ token, showNotification }) => {
  const { logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  // Evaluate password strength in real-time
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: 'None', color: '#e2e8f0', checks: {} };
    
    const checks = {
      length: pwd.length >= 8,
      upper: /[A-Z]/.test(pwd),
      lower: /[a-z]/.test(pwd),
      number: /\d/.test(pwd),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(pwd)
    };

    let score = Object.values(checks).filter(Boolean).length * 20;
    
    let label = 'Weak';
    let color = '#ef4444'; // Red
    if (score >= 80) {
      label = 'Strong';
      color = '#22c55e'; // Green
    } else if (score >= 40) {
      label = 'Moderate';
      color = '#eab308'; // Yellow
    }

    return { score, label, color, checks };
  };

  const strength = getPasswordStrength(newPassword);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSessions(response.data || []);
    } catch (error) {
      showNotification('Failed to retrieve active sessions', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeSession = async (sessionId) => {
    try {
      await axios.delete(`${API_BASE_URL}/auth/sessions/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Session terminated successfully', 'success');
      // Update state
      setSessions(prev => prev.filter(s => s.id !== sessionId));
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to terminate session', 'error');
    }
  };

  const handleRevokeAllSessions = async () => {
    if (!window.confirm("Are you sure you want to terminate all of your active sessions? You will be signed out.")) {
      return;
    }
    try {
      await axios.delete(`${API_BASE_URL}/auth/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('All sessions revoked successfully', 'success');
      logout(); // Force log out on complete revocation
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to revoke all sessions', 'error');
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      showNotification('New passwords do not match', 'error');
      return;
    }
    if (strength.score < 80) {
      showNotification('Please choose a stronger password', 'error');
      return;
    }

    setChangingPassword(true);
    try {
      await axios.post(
        `${API_BASE_URL}/auth/change-password`,
        {
          current_password: currentPassword,
          new_password: newPassword
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      showNotification('Password updated successfully. Other sessions logged out.', 'success');
      // Reset form
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to change password', 'error');
    } finally {
      setChangingPassword(false);
    }
  };

  // Helper to format user-agent into a readable browser/device
  const formatUserAgent = (ua) => {
    if (!ua) return "Unknown Browser";
    if (ua.includes("Chrome")) return "Google Chrome 🌐";
    if (ua.includes("Firefox")) return "Mozilla Firefox 🦊";
    if (ua.includes("Safari") && !ua.includes("Chrome")) return "Apple Safari 🧭";
    if (ua.includes("Edge")) return "Microsoft Edge 🌀";
    return ua.split(" ")[0] || "Web Browser";
  };

  return (
    <div className="security-settings-container animation-fade-in">
      <div className="security-grid">
        
        {/* Sessions Panel */}
        <div className="security-card">
          <div className="card-header-bar">
            <h3>🛡️ Active Login Sessions</h3>
            <button className="refresh-btn mini" onClick={fetchSessions} disabled={loading}>
              🔄 Refresh List
            </button>
          </div>
          <p className="card-desc">
            Monitor and revoke active device contexts currently authenticated to your account.
          </p>

          {loading && sessions.length === 0 ? (
            <div className="dashboard-skeleton-layout">
              <div className="skeleton-chart-card mini"></div>
            </div>
          ) : (
            <div className="sessions-list">
              {sessions.map(s => (
                <div key={s.id} className="session-item">
                  <div className="session-icon">📱</div>
                  <div className="session-meta">
                    <strong>{formatUserAgent(s.user_agent)}</strong>
                    <span className="ip-addr">IP: <code>{s.client_ip}</code></span>
                    <span className="timestamp">Active: {new Date(s.last_activity).toLocaleString()}</span>
                  </div>
                  <button 
                    className="revoke-btn" 
                    onClick={() => handleRevokeSession(s.id)}
                  >
                    Revoke ❌
                  </button>
                </div>
              ))}
            </div>
          )}

          {sessions.length > 0 && (
            <button className="revoke-all-btn" onClick={handleRevokeAllSessions}>
              🚨 Revoke All & Sign Out
            </button>
          )}
        </div>

        {/* Change Password Panel */}
        <div className="security-card">
          <h3>🔑 Change Secure Password</h3>
          <p className="card-desc">
            Update your authentication password credentials to secure your account.
          </p>

          <form onSubmit={handleChangePassword} className="security-form">
            <div className="form-group">
              <label>Current Password</label>
              <input 
                type="password" 
                value={currentPassword} 
                onChange={e => setCurrentPassword(e.target.value)} 
                required 
                className="rbac-role-select w-full"
                placeholder="••••••••"
              />
            </div>

            <div className="form-group">
              <label>New Password</label>
              <input 
                type="password" 
                value={newPassword} 
                onChange={e => setNewPassword(e.target.value)} 
                required 
                className="rbac-role-select w-full"
                placeholder="••••••••"
              />
              
              {/* Password Strength Indicator */}
              {newPassword && (
                <div className="password-strength-panel">
                  <div className="strength-progress-bg">
                    <div 
                      className="strength-progress-fill" 
                      style={{ 
                        width: `${strength.score}%`, 
                        backgroundColor: strength.color 
                      }}
                    ></div>
                  </div>
                  <span className="strength-label" style={{ color: strength.color }}>
                    Strength: <strong>{strength.label}</strong>
                  </span>
                  
                  <ul className="strength-criteria-checklist">
                    <li className={strength.checks.length ? 'met' : 'unmet'}>
                      {strength.checks.length ? '✓' : '✗'} Minimum 8 characters
                    </li>
                    <li className={strength.checks.upper ? 'met' : 'unmet'}>
                      {strength.checks.upper ? '✓' : '✗'} At least one uppercase letter
                    </li>
                    <li className={strength.checks.lower ? 'met' : 'unmet'}>
                      {strength.checks.lower ? '✓' : '✗'} At least one lowercase letter
                    </li>
                    <li className={strength.checks.number ? 'met' : 'unmet'}>
                      {strength.checks.number ? '✓' : '✗'} At least one number
                    </li>
                    <li className={strength.checks.special ? 'met' : 'unmet'}>
                      {strength.checks.special ? '✓' : '✗'} At least one special symbol (!@#...)
                    </li>
                  </ul>
                </div>
              )}
            </div>

            <div className="form-group">
              <label>Confirm New Password</label>
              <input 
                type="password" 
                value={confirmPassword} 
                onChange={e => setConfirmPassword(e.target.value)} 
                required 
                className="rbac-role-select w-full"
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              className="back-safety-btn mt-2" 
              disabled={changingPassword || strength.score < 80}
            >
              {changingPassword ? 'Updating Password...' : 'Save Password Update'}
            </button>
          </form>
        </div>

      </div>
    </div>
  );
};

export default SecuritySettings;
