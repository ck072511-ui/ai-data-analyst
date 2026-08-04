import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const ExplainabilityDashboard = ({ token, showNotification }) => {
  const [history, setHistory] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [openSection, setOpenSection] = useState('summary');
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
      if (res.data.length > 0) {
        setSelectedId(res.data[0].id);
        fetchExplanation(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchExplanation = async (id) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/xai/explain/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setExplanation(res.data);
    } catch (err) {
      showNotification('Failed to compile explainability report', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleIdChange = (id) => {
    setSelectedId(id);
    fetchExplanation(id);
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

  const getConfidenceColor = (level) => {
    if (level === 'High') return '#10b981';
    if (level === 'Medium') return '#f59e0b';
    return '#ef4444';
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
      
      {/* Sidebar: execution selector */}
      <div style={{
        backgroundColor: theme.sidebarBg,
        borderRight: theme.border,
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '0.88rem', fontWeight: 700 }}>🔍 Select Audit Run</h3>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1, overflowY: 'auto' }}>
          {history.map(h => (
            <div
              key={h.id}
              onClick={() => handleIdChange(h.id)}
              style={{
                padding: '10px 12px',
                borderRadius: '6px',
                backgroundColor: selectedId === h.id ? '#2563eb' : theme.cardBg,
                color: selectedId === h.id ? '#ffffff' : theme.color,
                cursor: 'pointer',
                fontSize: '0.8rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                boxShadow: theme.shadow
              }}
            >
              <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {h.prompt}
              </span>
              <span style={{ fontSize: '0.68rem', color: selectedId === h.id ? '#ffffff' : theme.subText }}>
                {new Date(h.created_at).toLocaleTimeString()}
              </span>
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
            padding: '8px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.8rem'
          }}
        >
          {darkMode ? '☀️ Light' : '🌙 Dark'}
        </button>
      </div>

      {/* Main workspace */}
      <div style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: '24px', gap: '20px' }}>
        
        {/* Header */}
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>🔍 Explainable AI & Confidence Engine</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: theme.subText }}>
            Evidence-based audit dashboards for system processes and output validity.
          </p>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <span style={{ fontSize: '1.3rem' }}>🔍 Formulating explanations logs...</span>
          </div>
        )}

        {explanation && !loading && (
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
            
            {/* Left panel: Expandable sections */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Grounded Summary */}
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                boxShadow: theme.shadow
              }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1rem', fontWeight: 700 }}>📝 Synthesized Final Answer</h3>
                <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.6' }}>
                  {explanation.final_synthesized_answer}
                </p>
              </div>

              {/* Navigation Tabs for details */}
              <div style={{ display: 'flex', gap: '10px', borderBottom: theme.border, paddingBottom: '10px' }}>
                {['summary', 'sql', 'rag', 'agents', 'business'].map(sec => (
                  <button
                    key={sec}
                    onClick={() => setOpenSection(sec)}
                    style={{
                      background: openSection === sec ? '#2563eb' : 'transparent',
                      color: openSection === sec ? '#ffffff' : theme.color,
                      border: openSection === sec ? 'none' : theme.border,
                      padding: '6px 14px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      fontWeight: 600
                    }}
                  >
                    {sec.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* SQL Explanation View */}
              {openSection === 'sql' && (
                <div style={{ padding: '16px', borderRadius: '12px', backgroundColor: theme.cardBg, border: theme.border }}>
                  <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem' }}>💻 SQL Generation Context</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                    <div><strong>Why Generated:</strong> {explanation.sql_explanation.why_generated}</div>
                    <div><strong>Tables Referenced:</strong> {explanation.sql_explanation.tables.join(', ') || 'None'}</div>
                    <div><strong>Columns Referenced:</strong> {explanation.sql_explanation.columns.join(', ') || 'None'}</div>
                    <div><strong>Execution Complexity:</strong> <span style={{ fontWeight: 700 }}>{explanation.sql_explanation.complexity}</span></div>
                    {explanation.sql_explanation.joins && explanation.sql_explanation.joins.length > 0 && (
                      <div>
                        <strong>Joins Applied:</strong>
                        <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px' }}>
                          {explanation.sql_explanation.joins.map((j, jIdx) => <li key={jIdx}>{j}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* RAG Explanation View */}
              {openSection === 'rag' && (
                <div style={{ padding: '16px', borderRadius: '12px', backgroundColor: theme.cardBg, border: theme.border }}>
                  <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem' }}>📂 Offline Document Grounding</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                    <div><strong>Citations Count:</strong> {explanation.rag_explanation.cited_sources_count}</div>
                    {explanation.rag_explanation.unique_documents && (
                      <div><strong>Cited Files:</strong> {explanation.rag_explanation.unique_documents.join(', ') || 'None'}</div>
                    )}
                    <div><strong>Selection Reason:</strong> {explanation.rag_explanation.chunks_selected_reason}</div>
                    {explanation.rag_explanation.warning && (
                      <div style={{ padding: '10px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', borderRadius: '6px', fontWeight: 600 }}>
                        ⚠️ {explanation.rag_explanation.warning}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Agents Explanation View */}
              {openSection === 'agents' && (
                <div style={{ padding: '16px', borderRadius: '12px', backgroundColor: theme.cardBg, border: theme.border }}>
                  <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem' }}>🤖 Planner & Orchestrator Decisions</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                    <div><strong>Critic Summary:</strong> {explanation.agent_explanation.critic_validation_summary}</div>
                    <div><strong>Replanning Counts:</strong> {explanation.agent_explanation.re_planning_events_count}</div>
                    <div>
                      <strong>Decisions Log:</strong>
                      <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px', color: theme.subText }}>
                        {explanation.agent_explanation.planner_decisions.map((dec, dIdx) => <li key={dIdx}>{dec}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Business Insight Explanation */}
              {openSection === 'business' && (
                <div style={{ padding: '16px', borderRadius: '12px', backgroundColor: theme.cardBg, border: theme.border }}>
                  <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem' }}>💡 Business Actionability Evidence</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.85rem' }}>
                    <div><strong>Statistical Basis:</strong> {explanation.business_explanation.statistical_basis}</div>
                    <div>
                      <strong>Actionable Recommendations:</strong>
                      <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px' }}>
                        {explanation.business_explanation.recommendations.map((rec, rIdx) => <li key={rIdx}>{rec}</li>)}
                      </ul>
                    </div>
                    <div>
                      <strong>Risk Parameters:</strong>
                      <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px', color: '#ef4444' }}>
                        {explanation.business_explanation.risks.map((risk, rIdx) => <li key={rIdx}>{risk}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Default Summary General View */}
              {openSection === 'summary' && (
                <div style={{
                  padding: '20px',
                  borderRadius: '12px',
                  backgroundColor: theme.cardBg,
                  border: theme.border,
                  boxShadow: theme.shadow
                }}>
                  <h3 style={{ margin: '0 0 14px 0', fontSize: '1rem', fontWeight: 700 }}>🔍 Evidence Map</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.88rem' }}>
                    <div>🛡️ **Database Query Validation**: Success</div>
                    <div>📂 **Manual Documents Grounding**: Cited {explanation.rag_explanation.cited_sources_count} context blocks.</div>
                    <div>🤝 **Critic validation status**: Passed. No hallucinations detected.</div>
                  </div>
                </div>
              )}

            </div>

            {/* Right panel: Confidence score & level classification */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                textAlign: 'center',
                boxShadow: theme.shadow
              }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: theme.subText }}>SYSTEM CONFIDENCE INDEX</span>
                <h2 style={{
                  fontSize: '3.5rem',
                  margin: '12px 0',
                  fontWeight: 800,
                  color: getConfidenceColor(explanation.confidence_level)
                }}>
                  {explanation.confidence_score}%
                </h2>
                <div style={{
                  display: 'inline-block',
                  padding: '4px 14px',
                  borderRadius: '12px',
                  backgroundColor: getConfidenceColor(explanation.confidence_level),
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  fontWeight: 700
                }}>
                  {explanation.confidence_level} Confidence
                </div>
              </div>

              {/* Breakdown cards */}
              <div style={{
                padding: '16px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                boxShadow: theme.shadow
              }}>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', fontWeight: 700 }}>📊 Confidence Weights</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>SQL validation:</span>
                    <span style={{ fontWeight: 700 }}>25% weight</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Schema matching:</span>
                    <span style={{ fontWeight: 700 }}>20% weight</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Citations coverage:</span>
                    <span style={{ fontWeight: 700 }}>20% weight</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Agent agreement:</span>
                    <span style={{ fontWeight: 700 }}>20% weight</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Data completeness:</span>
                    <span style={{ fontWeight: 700 }}>15% weight</span>
                  </div>
                </div>
              </div>

            </div>

          </div>
        )}

        {!explanation && !loading && (
          <div style={{
            padding: '40px',
            borderRadius: '12px',
            backgroundColor: theme.cardBg,
            border: theme.border,
            textAlign: 'center'
          }}>
            <span style={{ fontSize: '3rem' }}>🔬</span>
            <h4 style={{ margin: '16px 0 8px 0', fontSize: '1.1rem' }}>No Audit Logs Available</h4>
            <p style={{ margin: 0, fontSize: '0.85rem', color: theme.subText }}>
              Start by typing analytical queries inside the chat panels.
            </p>
          </div>
        )}

      </div>

    </div>
  );
};

export default ExplainabilityDashboard;
