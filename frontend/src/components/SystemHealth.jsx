import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const SystemHealth = ({ token, showNotification }) => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastCheck, setLastCheck] = useState(null);
  const [darkMode, setDarkMode] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setHealthData(response.data);
      setLastCheck(new Date().toLocaleTimeString());
    } catch (error) {
      if (error.response && error.response.data) {
        setHealthData(error.response.data);
      } else {
        showNotification('Failed to fetch system health diagnostics', 'error');
      }
      setLastCheck(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    if (status === 'healthy') return '#10b981';
    if (status === 'degraded') return '#f59e0b';
    return '#ef4444';
  };

  const containerStyle = {
    padding: '24px',
    borderRadius: '16px',
    fontFamily: "'Inter', sans-serif",
    transition: 'all 0.3s ease',
    backgroundColor: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    minHeight: '400px',
    boxShadow: darkMode ? '0 10px 30px rgba(0,0,0,0.5)' : '0 10px 30px rgba(0,0,0,0.05)',
    border: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0',
  };

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
    borderBottom: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0',
    paddingBottom: '16px',
  };

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '20px',
    marginBottom: '24px',
  };

  const cardStyle = {
    padding: '20px',
    borderRadius: '12px',
    backgroundColor: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
  };

  const badgeStyle = (status) => ({
    display: 'inline-block',
    padding: '4px 12px',
    borderRadius: '20px',
    fontSize: '0.85rem',
    fontWeight: '600',
    color: '#ffffff',
    backgroundColor: getStatusColor(status),
    textTransform: 'uppercase',
  });

  return (
    <div style={containerStyle} className="animation-fade-in">
      <div style={headerStyle}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            🏥 System Health Monitoring
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>
            Real-time status updates and telemetry metrics.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              backgroundColor: darkMode ? '#334155' : '#e2e8f0',
              color: darkMode ? '#ffffff' : '#0f172a',
            }}
          >
            {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
          <button 
            onClick={fetchHealth} 
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Refreshing...' : '🔄 Refresh Now'}
          </button>
        </div>
      </div>

      {healthData ? (
        <>
          <div style={{
            ...cardStyle,
            marginBottom: '24px',
            background: darkMode ? 'linear-gradient(135deg, #1e293b, #0f172a)' : 'linear-gradient(135deg, #ffffff, #f1f5f9)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '16px',
          }}>
            <div>
              <span style={{ fontSize: '0.9rem', textTransform: 'uppercase', tracking: '0.1em', color: darkMode ? '#94a3b8' : '#64748b' }}>
                Overall System Status
              </span>
              <h3 style={{ margin: '8px 0', fontSize: '2rem', fontWeight: 800 }}>
                {healthData.status === 'healthy' ? 'ALL SYSTEMS OPERATIONAL' : 'SYSTEM ISSUES DETECTED'}
              </h3>
              <span style={badgeStyle(healthData.status)}>{healthData.status}</span>
            </div>
            <div style={{ textAlign: 'right' }}>
              <p style={{ margin: 0, fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>
                Uptime: <strong>{healthData.uptime}</strong>
              </p>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>
                Last Health Check: <strong>{lastCheck || healthData.timestamp}</strong>
              </p>
            </div>
          </div>

          <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', fontWeight: 600 }}>Components Status</h3>
          <div style={gridStyle}>
            <div style={cardStyle}>
              <h4 style={{ margin: '0 0 8px 0', color: darkMode ? '#cbd5e1' : '#475569' }}>🗄️ Database Service</h4>
              <span style={badgeStyle(healthData.checks?.database)}>{healthData.checks?.database || 'unknown'}</span>
              <p style={{ fontSize: '0.85rem', marginTop: '12px', color: darkMode ? '#94a3b8' : '#64748b' }}>
                PostgreSQL pool availability.
              </p>
            </div>
            <div style={cardStyle}>
              <h4 style={{ margin: '0 0 8px 0', color: darkMode ? '#cbd5e1' : '#475569' }}>⚡ API Service</h4>
              <span style={badgeStyle(healthData.status)}>{healthData.status === 'healthy' ? 'healthy' : 'degraded'}</span>
              <p style={{ fontSize: '0.85rem', marginTop: '12px', color: darkMode ? '#94a3b8' : '#64748b' }}>
                FastAPI framework liveness and routes.
              </p>
            </div>
            <div style={cardStyle}>
              <h4 style={{ margin: '0 0 8px 0', color: darkMode ? '#cbd5e1' : '#475569' }}>🔑 Authentication Service</h4>
              <span style={badgeStyle(healthData.checks?.authentication)}>{healthData.checks?.authentication || 'unknown'}</span>
              <p style={{ fontSize: '0.85rem', marginTop: '12px', color: darkMode ? '#94a3b8' : '#64748b' }}>
                User table lookup validation.
              </p>
            </div>
            <div style={cardStyle}>
              <h4 style={{ margin: '0 0 8px 0', color: darkMode ? '#cbd5e1' : '#475569' }}>💾 Storage System</h4>
              <span style={badgeStyle(healthData.checks?.storage)}>{healthData.checks?.storage || 'unknown'}</span>
              <p style={{ fontSize: '0.85rem', marginTop: '12px', color: darkMode ? '#94a3b8' : '#64748b' }}>
                Upload directory read/write check.
              </p>
            </div>
            <div style={cardStyle}>
              <h4 style={{ margin: '0 0 8px 0', color: darkMode ? '#cbd5e1' : '#475569' }}>🤖 Local LLM Service</h4>
              <span style={badgeStyle(healthData.checks?.llm)}>{healthData.checks?.llm || 'unknown'}</span>
              <p style={{ fontSize: '0.85rem', marginTop: '12px', color: darkMode ? '#94a3b8' : '#64748b' }}>
                Ollama model connection status.
              </p>
            </div>
          </div>

          <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', fontWeight: 600 }}>Active Telemetry Stats</h3>
          <div style={gridStyle}>
            <div style={cardStyle}>
              <span style={{ fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>Active HTTP Requests</span>
              <h2 style={{ fontSize: '2.5rem', margin: '12px 0 0 0', fontWeight: 700, color: '#3b82f6' }}>
                {healthData.metrics?.active_requests ?? 0}
              </h2>
            </div>
            <div style={cardStyle}>
              <span style={{ fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>Average Response Time</span>
              <h2 style={{ fontSize: '2.5rem', margin: '12px 0 0 0', fontWeight: 700, color: '#8b5cf6' }}>
                {healthData.metrics?.average_response_time_ms ?? 0} <span style={{ fontSize: '1.2rem' }}>ms</span>
              </h2>
            </div>
            <div style={cardStyle}>
              <span style={{ fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>Total Requests Processed</span>
              <h2 style={{ fontSize: '2.5rem', margin: '12px 0 0 0', fontWeight: 700, color: '#10b981' }}>
                {healthData.metrics?.total_requests ?? 0}
              </h2>
            </div>
          </div>
        </>
      ) : (
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <p>No health report available. Click Refresh to attempt polling.</p>
        </div>
      )}
    </div>
  );
};

export default SystemHealth;
