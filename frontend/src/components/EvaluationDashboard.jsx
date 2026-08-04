import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const EvaluationDashboard = ({ token, showNotification }) => {
  const [prompts, setPrompts] = useState([]);
  const [selectedPromptId, setSelectedPromptId] = useState('');
  const [models, setModels] = useState([]);
  const [modelA, setModelA] = useState('');
  const [modelB, setModelB] = useState('');
  const [enableAB, setEnableAB] = useState(false);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [evalResult, setEvalResult] = useState(null);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    fetchPrompts();
    fetchModels();
    fetchHistory();
  }, []);

  const fetchPrompts = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/prompts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPrompts(res.data || []);
      if (res.data.length > 0) {
        setSelectedPromptId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/models`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setModels(res.data || []);
      if (res.data.length > 0) {
        setModelA(res.data[0].name);
        if (res.data.length > 1) {
          setModelB(res.data[1].name);
        } else {
          setModelB(res.data[0].name);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/evaluation/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunEval = async () => {
    if (!selectedPromptId || !modelA) {
      showNotification('Please select a prompt template and models.', 'error');
      return;
    }

    setLoading(true);
    setEvalResult(null);

    try {
      const res = await axios.post(`${API_BASE_URL}/evaluation/run`, {
        prompt_id: selectedPromptId,
        model_name: modelA,
        compare_model_name: enableAB ? modelB : null
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setEvalResult(res.data);
      showNotification('Offline evaluation complete!', 'success');
      fetchHistory();
    } catch (err) {
      showNotification('Evaluation runner task failed', 'error');
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
      
      {/* Left panel: Trigger Evaluations configs */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>🔬 Offline AI Evaluations</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: theme.subText }}>Rate local models outputs accuracy and response completeness.</p>
        </div>

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
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Select Prompt Template:</label>
            <select
              value={selectedPromptId}
              onChange={(e) => setSelectedPromptId(e.target.value)}
              style={{
                padding: '10px',
                borderRadius: '6px',
                border: theme.border,
                backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                color: theme.color,
                fontSize: '0.85rem'
              }}
            >
              {prompts.map(p => <option key={p.id} value={p.id}>{p.name} (V{p.version})</option>)}
            </select>
          </div>

          <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
            <input
              type="checkbox"
              id="enableAB"
              checked={enableAB}
              onChange={(e) => setEnableAB(e.target.checked)}
              style={{ width: '16px', height: '16px', cursor: 'pointer' }}
            />
            <label htmlFor="enableAB" style={{ fontSize: '0.82rem', fontWeight: 700, cursor: 'pointer' }}>
              ⚖️ Enable A/B Model Comparison
            </label>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: enableAB ? '1fr 1fr' : '1fr', gap: '14px' }}>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.8rem' }}>Model A (Evaluated)</label>
              <select
                value={modelA}
                onChange={(e) => setModelA(e.target.value)}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  border: theme.border,
                  backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                  color: theme.color,
                  fontSize: '0.85rem'
                }}
              >
                {models.map(m => <option key={m.id} value={m.name}>{m.name}</option>)}
              </select>
            </div>

            {enableAB && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.8rem' }}>Model B (Comparison)</label>
                <select
                  value={modelB}
                  onChange={(e) => setModelB(e.target.value)}
                  style={{
                    padding: '10px',
                    borderRadius: '6px',
                    border: theme.border,
                    backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                    color: theme.color,
                    fontSize: '0.85rem'
                  }}
                >
                  {models.map(m => <option key={m.id} value={m.name}>{m.name}</option>)}
                </select>
              </div>
            )}

          </div>

          <button
            onClick={handleRunEval}
            disabled={loading || !selectedPromptId}
            style={{
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              padding: '12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.88rem',
              opacity: (loading || !selectedPromptId) ? 0.6 : 1
            }}
          >
            {loading ? 'Evaluating...' : 'Run Evaluator 🚀'}
          </button>

        </div>

        {/* Results Panels */}
        {evalResult && !loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {!enableAB ? (
              /* Single Model Results */
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                boxShadow: theme.shadow
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, fontSize: '0.98rem' }}>📊 Single Model Score</h3>
                  <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#10b981' }}>
                    {evalResult.scores?.overall_score}%
                  </span>
                </div>
                <p style={{ fontSize: '0.8rem', color: theme.subText, marginTop: '8px' }}>
                  <strong>Latency:</strong> {evalResult.latency_ms} ms | <strong>Model:</strong> {evalResult.model_name}
                </p>
                <div style={{
                  padding: '10px',
                  borderRadius: '6px',
                  backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
                  fontFamily: 'monospace',
                  fontSize: '0.78rem',
                  marginTop: '10px',
                  whiteSpace: 'pre-wrap'
                }}>{evalResult.answer}</div>
              </div>
            ) : (
              /* A/B Compare Results */
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                
                {/* Model A */}
                <div style={{ padding: '16px', borderRadius: '12px', backgroundColor: theme.cardBg, border: theme.border }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                    <span>{evalResult.model_a?.model_name}</span>
                    <span style={{ color: '#10b981' }}>{evalResult.model_a?.scores?.overall_score}%</span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: theme.subText, margin: '4px 0' }}>
                    Latency: {evalResult.model_a?.latency_ms} ms
                  </div>
                  <pre style={{
                    padding: '8px',
                    borderRadius: '4px',
                    backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
                    fontSize: '0.72rem',
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap'
                  }}>{evalResult.model_a?.answer}</pre>
                </div>

                {/* Model B */}
                <div style={{ padding: '16px', borderRadius: '12px', backgroundColor: theme.cardBg, border: theme.border }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                    <span>{evalResult.model_b?.model_name}</span>
                    <span style={{ color: '#10b981' }}>{evalResult.model_b?.scores?.overall_score}%</span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: theme.subText, margin: '4px 0' }}>
                    Latency: {evalResult.model_b?.latency_ms} ms
                  </div>
                  <pre style={{
                    padding: '8px',
                    borderRadius: '4px',
                    backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
                    fontSize: '0.72rem',
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap'
                  }}>{evalResult.model_b?.answer}</pre>
                </div>

              </div>
            )}

          </div>
        )}

      </div>

      {/* Right panel: Benchmarks logs history */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>📊 Benchmark Progression</h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: theme.subText }}>Historical evaluations audits trail.</p>
          </div>
          <button
            onClick={fetchHistory}
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
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <h4 style={{ margin: '0 0 4px 0', fontSize: '0.85rem' }}>Model: {r.model_name}</h4>
                  <div style={{ display: 'flex', gap: '10px', fontSize: '0.72rem', color: theme.subText }}>
                    <span>Latency: {r.execution_latency_ms} ms</span>
                    <span>•</span>
                    <span>Relevance: {r.answer_relevance}%</span>
                  </div>
                </div>

                <div style={{
                  fontSize: '1.2rem',
                  fontWeight: 800,
                  color: r.overall_score >= 80 ? '#10b981' : r.overall_score >= 50 ? '#f59e0b' : '#ef4444'
                }}>
                  {r.overall_score}%
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
              <span>📊 No benchmarks stored. Conduct model runs to compile history logs.</span>
            </div>
          )}
        </div>

      </div>

      <button
        onClick={() => setDarkMode(!darkMode)}
        style={{
          gridColumn: 'span 2',
          marginTop: '20px',
          background: 'none',
          border: theme.border,
          color: theme.color,
          padding: '8px',
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

export default EvaluationDashboard;
