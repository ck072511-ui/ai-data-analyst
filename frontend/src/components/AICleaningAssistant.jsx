import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const AICleaningAssistant = ({ token, datasets, showNotification, initialDatasetId }) => {
  const [selectedDatasetId, setSelectedDatasetId] = useState(initialDatasetId || '');
  const [recommendation, setRecommendation] = useState(null);
  const [approvedStepIds, setApprovedStepIds] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  const [history, setHistory] = useState([]);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    if (selectedDatasetId) {
      fetchRecommendations(selectedDatasetId);
      fetchHistory(selectedDatasetId);
    } else {
      setRecommendation(null);
      setHistory([]);
    }
  }, [selectedDatasetId]);

  const fetchRecommendations = async (datasetId) => {
    setIsLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/ai-cleaning/recommendations/${datasetId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRecommendation(res.data);
      // Automatically check/approve all steps initially
      const stepIds = (res.data.execution_plan || []).map(s => s.step_id);
      setApprovedStepIds(stepIds);
    } catch (err) {
      console.error(err);
      showNotification('Failed to generate AI data cleaning recommendations', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHistory = async (datasetId) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/ai-cleaning/history/${datasetId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCheckboxToggle = (stepId) => {
    setApprovedStepIds(prev =>
      prev.includes(stepId) ? prev.filter(id => id !== stepId) : [...prev, stepId]
    );
  };

  const handleApproveAndExecute = async () => {
    if (!recommendation) return;
    setIsExecuting(true);
    setProgress(5);
    setStatusText('Approving cleaning checklist...');

    try {
      // 1. Approve selected steps
      await axios.post(`${API_BASE_URL}/ai-cleaning/approve`, {
        recommendation_id: recommendation.recommendation_id,
        approved_step_ids: approvedStepIds
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setProgress(30);
      setStatusText('Queueing cleaning task...');

      // 2. Execute plan
      const res = await axios.post(`${API_BASE_URL}/ai-cleaning/execute`, {
        recommendation_id: recommendation.recommendation_id
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const taskId = res.data.task_id;
      pollTaskProgress(taskId);

    } catch (err) {
      console.error(err);
      showNotification('Failed to execute AI data cleaning pipeline', 'error');
      setIsExecuting(false);
      setProgress(0);
      setStatusText('');
    }
  };

  const pollTaskProgress = (taskId) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/tasks/${taskId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const task = res.data;
        setProgress(task.progress || 35);
        setStatusText(`Running transformations: ${task.progress}%`);

        if (task.status === 'completed') {
          clearInterval(interval);
          setIsExecuting(false);
          setProgress(100);
          setStatusText('');
          showNotification('Dataset cleaned successfully!', 'success');
          // Reload dataset profiling lists
          fetchRecommendations(selectedDatasetId);
          fetchHistory(selectedDatasetId);
        } else if (task.status === 'failed') {
          clearInterval(interval);
          setIsExecuting(false);
          setProgress(0);
          setStatusText('');
          showNotification(`Task failed: ${task.error_message}`, 'error');
        }
      } catch (err) {
        clearInterval(interval);
        setIsExecuting(false);
        setProgress(0);
        setStatusText('');
      }
    }, 2000);
  };

  const handleRollback = async (versionNum) => {
    if (!window.confirm(`Are you sure you want to rollback to Version ${versionNum}? This will restore dataset values.`)) return;
    try {
      await axios.post(`${API_BASE_URL}/datasets/${selectedDatasetId}/rollback/${versionNum}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification(`Rolled back successfully to Version ${versionNum}`, 'success');
      fetchRecommendations(selectedDatasetId);
      fetchHistory(selectedDatasetId);
    } catch (err) {
      showNotification('Rollback execution failed', 'error');
    }
  };

  const theme = {
    bg: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    cardBg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    subText: darkMode ? '#94a3b8' : '#64748b',
    activeBlue: '#2563eb',
    shadow: darkMode ? '0 10px 30px rgba(0,0,0,0.5)' : '0 10px 30px rgba(0,0,0,0.05)',
  };

  return (
    <div style={{
      padding: '24px',
      backgroundColor: theme.bg,
      color: theme.color,
      fontFamily: "'Outfit', sans-serif",
      minHeight: '100%',
      borderRadius: '16px',
      transition: 'all 0.3s ease'
    }}>
      
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
        borderBottom: theme.border,
        paddingBottom: '16px'
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>🧹 AI Data Cleaning & Transformation Assistant</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: theme.subText }}>
            Inspect dataset columns, identify anomaly patterns, and trigger dynamic local LLM pipelines.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            style={{
              background: 'none',
              border: theme.border,
              padding: '8px 16px',
              borderRadius: '8px',
              cursor: 'pointer',
              color: theme.color,
              fontSize: '0.85rem'
            }}
          >
            {darkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
        </div>
      </div>

      {/* Dataset selector */}
      <div style={{
        padding: '16px',
        borderRadius: '12px',
        backgroundColor: theme.cardBg,
        border: theme.border,
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px'
      }}>
        <label style={{ fontWeight: 600, fontSize: '0.9rem' }}>📂 Active Dataset:</label>
        <select
          value={selectedDatasetId}
          onChange={(e) => setSelectedDatasetId(e.target.value)}
          style={{
            padding: '8px 16px',
            borderRadius: '8px',
            border: theme.border,
            backgroundColor: darkMode ? '#0f172a' : '#ffffff',
            color: theme.color,
            outline: 'none',
            fontSize: '0.9rem',
            width: '280px'
          }}
        >
          <option value="">-- Select flat dataset --</option>
          {datasets.map(d => (
            <option key={d.id} value={d.id}>{d.filename} ({d.row_count} rows)</option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <span style={{ fontSize: '1.5rem' }}>🤖 Generating local suggestions...</span>
        </div>
      )}

      {recommendation && !isLoading && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
          
          {/* Left panel: suggestions list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Overview Explanation */}
            <div style={{
              padding: '20px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.border,
              boxShadow: theme.shadow
            }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem', fontWeight: 700 }}>🔍 Anomaly Summary</h3>
              <p style={{ margin: 0, fontSize: '0.92rem', lineHeight: '1.6', color: theme.color }}>
                {recommendation.dataset_explanation}
              </p>
            </div>

            {/* Checklist items */}
            <div style={{
              padding: '20px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.border,
              boxShadow: theme.shadow
            }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', fontWeight: 700 }}>📋 Recommended Pipeline Checklist</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {(recommendation.execution_plan || []).map(step => {
                  const isChecked = approvedStepIds.includes(step.step_id);
                  return (
                    <div 
                      key={step.step_id}
                      style={{
                        padding: '16px',
                        borderRadius: '8px',
                        border: theme.border,
                        backgroundColor: isChecked ? 'rgba(37, 99, 235, 0.05)' : 'transparent',
                        display: 'flex',
                        gap: '16px',
                        alignItems: 'flex-start'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleCheckboxToggle(step.step_id)}
                        disabled={isExecuting}
                        style={{ width: '18px', height: '18px', marginTop: '4px', cursor: 'pointer' }}
                      />
                      <div style={{ flexGrow: 1 }}>
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '0.9rem', fontWeight: 700 }}>Column: {step.column}</span>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: '#2563eb',
                            color: '#fff',
                            fontSize: '0.7rem',
                            fontWeight: 600
                          }}>{step.category.toUpperCase()}</span>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: step.confidence > 0.8 ? '#10b981' : '#f59e0b',
                            color: '#fff',
                            fontSize: '0.7rem',
                            fontWeight: 600
                          }}>Confidence: {Math.round(step.confidence * 100)}%</span>
                        </div>
                        <p style={{ margin: '8px 0 4px 0', fontSize: '0.88rem', fontWeight: 600 }}>{step.description}</p>
                        <p style={{ margin: '0 0 4px 0', fontSize: '0.82rem', color: theme.subText }}><strong>Reason:</strong> {step.reason}</p>
                        <p style={{ margin: 0, fontSize: '0.82rem', color: theme.subText }}><strong>Estimated Impact:</strong> {step.estimated_impact}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Execution panel */}
              <div style={{ marginTop: '24px', borderTop: theme.border, paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <button
                  onClick={handleApproveAndExecute}
                  disabled={isExecuting || approvedStepIds.length === 0}
                  style={{
                    alignSelf: 'flex-end',
                    background: '#2563eb',
                    color: '#fff',
                    border: 'none',
                    padding: '12px 28px',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '0.95rem',
                    opacity: (isExecuting || approvedStepIds.length === 0) ? 0.6 : 1
                  }}
                >
                  {isExecuting ? 'Running Cleaning Pipeline...' : 'Approve & Execute Selected Steps 🚀'}
                </button>

                {isExecuting && (
                  <div style={{ width: '100%', marginTop: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: theme.subText, marginBottom: '6px' }}>
                      <span>{statusText}</span>
                      <span>{progress}%</span>
                    </div>
                    <div style={{ height: '8px', backgroundColor: darkMode ? '#334155' : '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ width: `${progress}%`, height: '100%', backgroundColor: '#2563eb', transition: 'width 0.3s ease' }}></div>
                    </div>
                  </div>
                )}
              </div>

            </div>

          </div>

          {/* Right panel: Quality score and rollback history */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Score improvement meter */}
            <div style={{
              padding: '20px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.border,
              boxShadow: theme.shadow,
              textAlign: 'center'
            }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: theme.subText }}>ESTIMATED QUALITY SCORE IMPROVEMENT</span>
              <h2 style={{ fontSize: '3rem', margin: '12px 0', fontWeight: 800, color: '#10b981' }}>
                +{recommendation.quality_improvement_est}%
              </h2>
              <p style={{ margin: 0, fontSize: '0.8rem', color: theme.subText }}>
                Estimated improvement on dataset health index.
              </p>
            </div>

            {/* Rollback history list */}
            <div style={{
              padding: '20px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.border,
              boxShadow: theme.shadow
            }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', fontWeight: 700 }}>🛡️ Rollback History</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {history.length > 0 ? (
                  history.map((h, hIdx) => (
                    <div 
                      key={h.id}
                      style={{
                        padding: '10px',
                        borderRadius: '6px',
                        border: theme.border,
                        fontSize: '0.82rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontWeight: 600 }}>Plan {history.length - hIdx} ({h.status.toUpperCase()})</span>
                        <span style={{ color: theme.subText, fontSize: '0.75rem', marginTop: '2px' }}>
                          {new Date(h.created_at).toLocaleString()}
                        </span>
                      </div>
                      {h.status === 'executed' && (
                        <button 
                          onClick={() => handleRollback(hIdx + 1)}
                          style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            border: '1px solid #ef4444',
                            color: '#ef4444',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            cursor: 'pointer',
                            fontSize: '0.75rem'
                          }}
                        >
                          Rollback ↩️
                        </button>
                      )}
                    </div>
                  ))
                ) : (
                  <p style={{ fontSize: '0.8rem', color: theme.subText, textAlign: 'center' }}>No historical cleaning logs.</p>
                )}
              </div>
            </div>

          </div>

        </div>
      )}

      {!recommendation && !isLoading && (
        <div style={{
          padding: '40px',
          borderRadius: '12px',
          backgroundColor: theme.cardBg,
          border: theme.border,
          textAlign: 'center'
        }}>
          <span style={{ fontSize: '3rem' }}>🧙‍♂️</span>
          <h4 style={{ margin: '16px 0 8px 0', fontSize: '1.1rem' }}>No Dataset Selected</h4>
          <p style={{ margin: 0, fontSize: '0.85rem', color: theme.subText }}>
            Choose a dataset in the selector above to analyze cleaning opportunities.
          </p>
        </div>
      )}

    </div>
  );
};

export default AICleaningAssistant;
