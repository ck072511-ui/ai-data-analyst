import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const ReportCenter = ({ token, showNotification }) => {
  const [history, setHistory] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [reportType, setReportType] = useState('executive');
  const [fileFormat, setFileFormat] = useState('pdf');
  const [companyName, setCompanyName] = useState('Enterprise Systems Corp');
  const [version, setVersion] = useState('1.0.0');
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    fetchReports();
    fetchRuns();
  }, []);

  const fetchReports = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/reports`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchRuns = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/agents/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRuns(res.data || []);
      if (res.data.length > 0) {
        setSelectedRunId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerate = async () => {
    if (!selectedRunId) {
      showNotification('Please run an analytical query or select an audit run first.', 'error');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/reports/generate`, {
        execution_id: selectedRunId,
        report_type: reportType,
        file_format: fileFormat,
        branding: {
          company_name: companyName,
          version: version
        }
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      showNotification('Report compilation job queued in background!', 'success');
      setTimeout(fetchReports, 1500);
    } catch (err) {
      showNotification('Failed to trigger report generation job', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (id) => {
    window.open(`${API_BASE_URL}/reports/${id}/download?token=${token}`, '_blank');
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API_BASE_URL}/reports/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Report logs cleared.', 'success');
      fetchReports();
    } catch (err) {
      showNotification('Failed to clear report logs', 'error');
    }
  };

  const theme = {
    bg: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    cardBg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    sidebarBg: darkMode ? '#020617' : '#cbd5e1',
    subText: darkMode ? '#94a3b8' : '#64748b',
    activeBlue: '#2563eb',
    shadow: '0 4px 20px rgba(0,0,0,0.1)',
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1.3fr',
      gap: '24px',
      padding: '24px',
      backgroundColor: theme.bg,
      color: theme.color,
      fontFamily: "'Outfit', sans-serif",
      borderRadius: '16px',
      minHeight: '100%',
      transition: 'all 0.3s ease'
    }}>
      
      {/* Left panel: Trigger compiler parameters */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>📄 Document Generator</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: theme.subText }}>Compile professional document layouts offline.</p>
        </div>

        {/* Configurations Card */}
        <div style={{
          padding: '20px',
          borderRadius: '12px',
          backgroundColor: theme.cardBg,
          border: theme.border,
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: theme.shadow
        }}>
          
          {/* Select execution source */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Select Source Analytics Run:</label>
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              style={{
                padding: '10px',
                borderRadius: '6px',
                border: theme.border,
                backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                color: theme.color,
                fontSize: '0.85rem'
              }}
            >
              {runs.map(r => (
                <option key={r.id} value={r.id}>{r.prompt} ({Math.round(r.confidence_score * 100)}% Conf)</option>
              ))}
            </select>
          </div>

          {/* Template Selectors */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Report Template:</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              style={{
                padding: '10px',
                borderRadius: '6px',
                border: theme.border,
                backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                color: theme.color,
                fontSize: '0.85rem'
              }}
            >
              <option value="executive">Executive Report</option>
              <option value="technical">Technical Report</option>
              <option value="audit">Audit Report</option>
              <option value="data_quality">Data Quality Report</option>
              <option value="ai_insights">AI Insights Report</option>
            </select>
          </div>

          {/* Formats Tabs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Export Format:</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              {['pdf', 'docx', 'pptx'].map(fmt => (
                <button
                  key={fmt}
                  onClick={() => setFileFormat(fmt)}
                  style={{
                    flexGrow: 1,
                    padding: '8px',
                    borderRadius: '6px',
                    border: fileFormat === fmt ? 'none' : theme.border,
                    backgroundColor: fileFormat === fmt ? '#2563eb' : 'transparent',
                    color: fileFormat === fmt ? '#ffffff' : theme.color,
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '0.8rem'
                  }}
                >
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Branding Settings */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', borderTop: theme.border, paddingTop: '14px' }}>
            <h4 style={{ margin: 0, fontSize: '0.85rem' }}>🎨 Corporate Branding Option</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '0.72rem' }}>Company Name</label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  style={{
                    padding: '8px',
                    borderRadius: '6px',
                    border: theme.border,
                    backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                    color: theme.color,
                    fontSize: '0.8rem'
                  }}
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '0.72rem' }}>Version</label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  style={{
                    padding: '8px',
                    borderRadius: '6px',
                    border: theme.border,
                    backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                    color: theme.color,
                    fontSize: '0.8rem'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Compile Button */}
          <button
            onClick={handleGenerate}
            disabled={loading || !selectedRunId}
            style={{
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              padding: '12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.88rem',
              marginTop: '10px',
              opacity: (loading || !selectedRunId) ? 0.6 : 1
            }}
          >
            {loading ? 'Queuing Compilation...' : 'Compile Document ⚙️'}
          </button>

        </div>

      </div>

      {/* Right panel: Downloads history list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>📂 Generated Archives</h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: theme.subText }}>Track background compiling states.</p>
          </div>
          <button
            onClick={fetchReports}
            style={{
              background: 'none',
              border: theme.border,
              color: theme.color,
              padding: '6px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.78rem'
            }}
          >
            🔄 Refresh
          </button>
        </div>

        {/* History records */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '480px', overflowY: 'auto' }}>
          {history.length > 0 ? (
            history.map(r => (
              <div
                key={r.id}
                style={{
                  padding: '14px',
                  borderRadius: '12px',
                  backgroundColor: theme.cardBg,
                  border: theme.border,
                  boxShadow: theme.shadow,
                  display: 'grid',
                  gridTemplateColumns: '1fr auto',
                  alignItems: 'center',
                  gap: '12px'
                }}
              >
                <div>
                  <h4 style={{ margin: '0 0 4px 0', fontSize: '0.88rem' }}>{r.title}</h4>
                  <div style={{ display: 'flex', gap: '10px', fontSize: '0.72rem', color: theme.subText }}>
                    <span style={{ fontWeight: 600, color: '#2563eb' }}>{r.file_format.toUpperCase()}</span>
                    <span>•</span>
                    <span>Status: <b style={{
                      color: r.status === 'completed' ? '#10b981' : r.status === 'failed' ? '#ef4444' : '#f59e0b'
                    }}>{r.status.toUpperCase()}</b></span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  {r.status === 'completed' && (
                    <button
                      onClick={() => handleDownload(r.id)}
                      style={{
                        backgroundColor: '#10b981',
                        color: '#ffffff',
                        border: 'none',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: 600
                      }}
                    >
                      Download 💾
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(r.id)}
                    style={{
                      backgroundColor: 'transparent',
                      border: theme.border,
                      color: '#ef4444',
                      padding: '6px 10px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.75rem'
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div style={{
              padding: '40px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.border,
              textAlign: 'center',
              color: theme.subText
            }}>
              <span>📂 No records compiled. Choose parameters to trigger compilation.</span>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};

export default ReportCenter;
