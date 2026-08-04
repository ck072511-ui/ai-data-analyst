import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const MultiAgentAnalytics = ({ token, datasets, showNotification }) => {
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState([]);
  const [activeResult, setActiveResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [timelineVisible, setTimelineVisible] = useState(true);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/agents/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleQuery = async () => {
    if (!query.trim() || !selectedDatasetId) {
      showNotification('Please select a dataset and type your query.', 'error');
      return;
    }

    setLoading(true);
    setActiveResult(null);

    try {
      const res = await axios.post(`${API_BASE_URL}/agents/query`, {
        question: query,
        dataset_id: selectedDatasetId
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setActiveResult(res.data);
      showNotification('Multi-Agent collaboration query completed!', 'success');
      fetchHistory();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Agent execution failed';
      showNotification(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReplay = async (executionId) => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/agents/replay`, {
        execution_id: executionId
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setActiveResult(res.data);
      showNotification('Replayed prior agent execution metrics.', 'success');
    } catch (err) {
      showNotification('Failed to replay execution log', 'error');
    } finally {
      setLoading(false);
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
    shadow: '0 8px 30px rgba(0,0,0,0.1)',
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '260px 1fr',
      height: '100%',
      backgroundColor: theme.bg,
      color: theme.color,
      fontFamily: "'Outfit', sans-serif",
      borderRadius: '16px',
      overflow: 'hidden',
      border: theme.border,
      transition: 'all 0.3s ease'
    }}>
      
      {/* Sidebar: Query logs */}
      <div style={{
        backgroundColor: theme.sidebarBg,
        borderRight: theme.border,
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700 }}>🔍 Agent Audit Logs</h3>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1, overflowY: 'auto' }}>
          {history.length > 0 ? (
            history.map(h => (
              <div
                key={h.id}
                onClick={() => handleReplay(h.id)}
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  backgroundColor: activeResult?.execution_id === h.id ? '#2563eb' : theme.cardBg,
                  color: activeResult?.execution_id === h.id ? '#ffffff' : theme.color,
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  boxShadow: theme.shadow
                }}
              >
                <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {h.prompt}
                </span>
                <span style={{ fontSize: '0.7rem', color: activeResult?.execution_id === h.id ? '#ffffff' : theme.subText }}>
                  Score: {Math.round(h.confidence_score * 100)}% • {h.status.toUpperCase()}
                </span>
              </div>
            ))
          ) : (
            <p style={{ fontSize: '0.78rem', color: theme.subText, textAlign: 'center' }}>No historical agent runs.</p>
          )}
        </div>

        <button
          onClick={() => setDarkMode(!darkMode)}
          style={{
            marginTop: '20px',
            background: 'none',
            border: theme.border,
            color: theme.color,
            padding: '8px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.8rem'
          }}
        >
          {darkMode ? '☀️ Light' : '🌙 Dark'}
        </button>
      </div>

      {/* Main Panel */}
      <div style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: '24px', gap: '20px' }}>
        
        {/* Header */}
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>🤖 Offline Multi-Agent Analytics</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: theme.subText }}>Decompose prompts, fetch schemas, generate SQL, extract RAG citations, build chart designs, and review outputs.</p>
        </div>

        {/* Input Card */}
        <div style={{
          padding: '16px',
          borderRadius: '12px',
          backgroundColor: theme.cardBg,
          border: theme.border,
          display: 'grid',
          gridTemplateColumns: '260px 1fr 120px',
          gap: '16px',
          alignItems: 'center'
        }}>
          <select
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            style={{
              padding: '10px',
              borderRadius: '6px',
              border: theme.border,
              backgroundColor: darkMode ? '#0f172a' : '#ffffff',
              color: theme.color,
              outline: 'none',
              fontSize: '0.85rem'
            }}
          >
            <option value="">-- Active Dataset --</option>
            {datasets.map(d => (
              <option key={d.id} value={d.id}>{d.filename}</option>
            ))}
          </select>

          <input
            type="text"
            placeholder="Type your complex analytical request..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              border: theme.border,
              backgroundColor: darkMode ? '#0f172a' : '#ffffff',
              color: theme.color,
              outline: 'none',
              fontSize: '0.85rem'
            }}
          />

          <button
            onClick={handleQuery}
            disabled={loading || !query.trim()}
            style={{
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              padding: '10px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              opacity: (loading || !query.trim()) ? 0.6 : 1
            }}
          >
            {loading ? 'Synthesizing...' : 'Run Agents 🚀'}
          </button>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <span style={{ fontSize: '1.4rem' }}>🤝 Coordinating Agent execution steps...</span>
          </div>
        )}

        {/* Results Panels */}
        {activeResult && !loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Top row: Answer summary and confidence score */}
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px' }}>
              
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border
              }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1rem', fontWeight: 700 }}>📝 Final Grounded Answer</h3>
                <p style={{ margin: 0, fontSize: '0.92rem', lineHeight: '1.6' }}>
                  {activeResult.final_answer}
                </p>
              </div>

              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center'
              }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 600, color: theme.subText }}>Critic Score</span>
                <h2 style={{ fontSize: '2.5rem', margin: '8px 0 0 0', fontWeight: 800, color: '#10b981' }}>
                  {Math.round(activeResult.confidence_score * 100)}%
                </h2>
                <span style={{ fontSize: '0.7rem', color: theme.subText, marginTop: '6px' }}>
                  Execution: {activeResult.duration_ms} ms
                </span>
              </div>

            </div>

            {/* Timeline Accordion */}
            <div style={{
              padding: '16px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.border
            }}>
              <div 
                onClick={() => setTimelineVisible(!timelineVisible)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  alignItems: 'center'
                }}
              >
                <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>⚙️ Execution Timeline Logs</h3>
                <span>{timelineVisible ? '▲ Hide' : '▼ Show'}</span>
              </div>

              {timelineVisible && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '16px' }}>
                  {(activeResult.timeline || []).map(step => (
                    <div
                      key={step.step_id}
                      style={{
                        padding: '10px 14px',
                        borderRadius: '6px',
                        border: theme.border,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.8rem'
                      }}
                    >
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <span style={{ fontWeight: 700, color: '#2563eb' }}>{step.agent}</span>
                        <span style={{ color: theme.subText }}>{step.description}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: step.status === 'completed' ? '#10b981' : '#ef4444',
                          color: '#fff',
                          fontSize: '0.68rem',
                          fontWeight: 600
                        }}>{step.status.toUpperCase()}</span>
                        <span style={{ fontSize: '0.72rem', color: theme.subText }}>{step.duration_ms} ms</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Detailed data row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              
              {/* SQL Panel */}
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border
              }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', fontWeight: 700 }}>💻 Generated SQL</h3>
                <pre style={{
                  padding: '12px',
                  borderRadius: '6px',
                  backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
                  overflowX: 'auto',
                  fontSize: '0.8rem',
                  margin: 0
                }}>
                  <code>{activeResult.sql || 'No SQL generated.'}</code>
                </pre>
              </div>

              {/* RAG Citations */}
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border
              }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', fontWeight: 700 }}>📂 Citations & Glossary</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto' }}>
                  {activeResult.citations && activeResult.citations.length > 0 ? (
                    activeResult.citations.map((c, cIdx) => (
                      <div
                        key={cIdx}
                        style={{
                          padding: '8px 10px',
                          borderRadius: '6px',
                          border: theme.border,
                          fontSize: '0.78rem'
                        }}
                      >
                        <span style={{ fontWeight: 700, color: '#2563eb' }}>{c.filename} (Pg {c.page_number})</span>
                        <p style={{ margin: '4px 0 0 0', color: theme.subText }}>{c.text_content}</p>
                      </div>
                    ))
                  ) : (
                    <span style={{ fontSize: '0.78rem', color: theme.subText }}>No document context cited.</span>
                  )}
                </div>
              </div>

            </div>

            {/* Visualization & Insights panel */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              
              {/* Visualization Recommendations */}
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border
              }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', fontWeight: 700 }}>📊 Recommended Layout</h3>
                {activeResult.chart_recommended ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ fontSize: '0.82rem' }}>
                      <strong>Chart Type:</strong> {activeResult.chart_type.toUpperCase()}
                    </div>
                    {activeResult.kpis && activeResult.kpis.length > 0 && (
                      <div>
                        <strong style={{ display: 'block', fontSize: '0.8rem', marginBottom: '4px' }}>Suggested KPIs:</strong>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                          {activeResult.kpis.map((k, kIdx) => (
                            <div key={kIdx} style={{ padding: '6px', borderRadius: '4px', border: theme.border, fontSize: '0.72rem' }}>
                              <div>{k.title}</div>
                              <div style={{ fontWeight: 700, color: '#2563eb', marginTop: '2px' }}>{k.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <span style={{ fontSize: '0.78rem', color: theme.subText }}>No chart selection recommended.</span>
                )}
              </div>

              {/* Insights List */}
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border
              }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', fontWeight: 700 }}>💡 Extracted Insights</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
                  {activeResult.insights && activeResult.insights.map((ins, iIdx) => (
                    <div key={iIdx} style={{ display: 'flex', gap: '8px' }}>
                      <span>•</span>
                      <span>{ins}</span>
                    </div>
                  ))}
                  {activeResult.trends && activeResult.trends.length > 0 && (
                    <div style={{ marginTop: '6px', borderTop: theme.border, paddingTop: '6px' }}>
                      <strong>Detected Trends:</strong>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px', fontSize: '0.78rem', color: theme.subText }}>
                        {activeResult.trends.map((tr, tIdx) => (
                          <div key={tIdx}>- {tr}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

            </div>

          </div>
        )}

      </div>

    </div>
  );
};

export default MultiAgentAnalytics;
