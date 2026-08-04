import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const ModelRegistry = ({ token, showNotification }) => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/models`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setModels(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleActivate = async (id) => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/models/activate`, {
        model_id: id
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Active default local model toggled successfully!', 'success');
      fetchModels();
    } catch (err) {
      showNotification('Failed to toggle active model', 'error');
    } finally {
      setLoading(false);
    }
  };

  const theme = {
    bg: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    cardBg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    subText: darkMode ? '#94a3b8' : '#64748b',
    activeGreen: '#10b981',
    shadow: '0 4px 20px rgba(0,0,0,0.1)',
  };

  return (
    <div style={{
      padding: '24px',
      backgroundColor: theme.bg,
      color: theme.color,
      fontFamily: "'Outfit', sans-serif",
      borderRadius: '16px',
      minHeight: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
      transition: 'all 0.3s ease'
    }}>
      
      <div>
        <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>🖥️ Offline Model Registry</h2>
        <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: theme.subText }}>Track local parameters, quantization weights, and select the system active inference engine.</p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '20px',
        marginTop: '10px'
      }}>
        {models.map(m => (
          <div
            key={m.id}
            style={{
              padding: '20px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.border,
              boxShadow: theme.shadow,
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              position: 'relative',
              opacity: loading ? 0.7 : 1
            }}
          >
            {m.status === 'active' && (
              <span style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                backgroundColor: theme.activeGreen,
                color: '#fff',
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '10px'
              }}>
                ACTIVE DEFAULT
              </span>
            )}

            <div>
              <h3 style={{ margin: '0 0 4px 0', fontSize: '1.1rem', fontWeight: 700 }}>{m.name}</h3>
              <span style={{ fontSize: '0.72rem', color: theme.subText }}>Provider: {m.provider}</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.78rem' }}>
              <div>
                <span style={{ color: theme.subText, display: 'block' }}>Context Length</span>
                <strong>{m.context_length} tokens</strong>
              </div>
              <div>
                <span style={{ color: theme.subText, display: 'block' }}>Quantization</span>
                <strong>{m.quantization}</strong>
              </div>
            </div>

            {m.status !== 'active' ? (
              <button
                onClick={() => handleActivate(m.id)}
                disabled={loading}
                style={{
                  marginTop: '10px',
                  backgroundColor: '#2563eb',
                  color: '#ffffff',
                  border: 'none',
                  padding: '8px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.8rem'
                }}
              >
                Set System Default ⚙️
              </button>
            ) : (
              <div style={{
                marginTop: '10px',
                padding: '8px',
                textAlign: 'center',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                color: theme.activeGreen,
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 700
              }}>
                System Active
              </div>
            )}

          </div>
        ))}
      </div>

      <button
        onClick={() => setDarkMode(!darkMode)}
        style={{
          marginTop: '20px',
          background: 'none',
          border: theme.border,
          color: theme.color,
          padding: '8px 16px',
          borderRadius: '6px',
          cursor: 'pointer',
          fontSize: '0.8rem',
          width: 'fit-content'
        }}
      >
        {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
      </button>

    </div>
  );
};

export default ModelRegistry;
