import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const WorkflowExecution = ({ token, showNotification }) => {
  const [history, setHistory] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  useEffect(() => {
    fetchHistory();
    // Start automated polling refresh loop
    const interval = setInterval(fetchHistory, 10000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/workflows/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(res.data || []);
      
      // If we have an active detail panel, refresh its status parameters
      if (selectedRun) {
        const refreshed = (res.data || []).find(r => r.id === selectedRun.id);
        if (refreshed) {
          setSelectedRun(refreshed);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'completed': return { bg: '#059669', color: '#ecfdf5' };
      case 'failed': return { bg: '#dc2626', color: '#fef2f2' };
      case 'running': return { bg: '#d97706', color: '#fffbeb' };
      default: return { bg: '#475569', color: '#f8fafc' };
    }
  };

  return (
    <div style={{ display: 'flex', gap: '20px', height: '100%' }}>
      
      {/* History List Panel */}
      <div className="card" style={{ flex: 1, padding: '15px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '16px' }}>Execution History Runs</h3>
          <button className="btn-secondary" onClick={fetchHistory} style={{ padding: '4px 10px', fontSize: '12px' }}>⟳ Refresh</button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {history.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>
              No historical execution runs found.
            </div>
          ) : (
            history.map(run => {
              const badge = getStatusBadgeColor(run.status);
              const isSelected = selectedRun && selectedRun.id === run.id;
              return (
                <div 
                  key={run.id}
                  onClick={() => setSelectedRun(run)}
                  style={{
                    padding: '12px',
                    backgroundColor: isSelected ? '#1e293b' : '#0f172a',
                    border: isSelected ? '1px solid #38bdf8' : '1px solid #334155',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h4 style={{ margin: 0, fontSize: '14px', color: '#f8fafc' }}>{run.workflow_name}</h4>
                    <span style={{ 
                      fontSize: '11px', 
                      padding: '2px 8px', 
                      borderRadius: '12px', 
                      backgroundColor: badge.bg, 
                      color: badge.color, 
                      fontWeight: 'bold',
                      textTransform: 'uppercase'
                    }}>{run.status}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8' }}>
                    <span>Run ID: {run.id.substring(0, 8)}...</span>
                    <span>Started: {run.started_at ? new Date(run.started_at).toLocaleString() : 'N/A'}</span>
                  </div>
                  {run.duration > 0 && (
                    <div style={{ fontSize: '11px', color: '#38bdf8', alignSelf: 'flex-end' }}>
                      ⏱ Duration: {run.duration}s
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Details Timeline Panel */}
      <div className="card" style={{ width: '450px', padding: '15px', display: 'flex', flexDirection: 'column', gap: '15px', overflowY: 'auto' }}>
        <h3 style={{ margin: 0, fontSize: '16px', borderBottom: '1px solid #334155', paddingBottom: '10px' }}>
          Details & Timeline Monitor
        </h3>

        {!selectedRun ? (
          <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#94a3b8' }}>
            Select an execution run to inspect logs and step pipelines timeline metrics.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>Workflow Reference</div>
              <div style={{ fontSize: '15px', fontWeight: 'bold', color: '#f8fafc' }}>{selectedRun.workflow_name}</div>
            </div>

            {selectedRun.error_message && (
              <div style={{ padding: '10px', backgroundColor: '#7f1d1d', border: '1px solid #b91c1c', borderRadius: '6px', color: '#fef2f2', fontSize: '12px' }}>
                <strong>Execution Error:</strong> {selectedRun.error_message}
              </div>
            )}

            {/* Steps Timeline Grid */}
            <div>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#38bdf8' }}>Node Timelines</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {Object.entries(selectedRun.node_states || {}).length === 0 ? (
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>No nodes executed.</div>
                ) : (
                  Object.entries(selectedRun.node_states).map(([nodeId, state]) => {
                    const stepBadge = getStatusBadgeColor(state.status);
                    return (
                      <div 
                        key={nodeId}
                        style={{ 
                          padding: '10px', 
                          backgroundColor: '#0f172a', 
                          borderRadius: '6px', 
                          border: '1px solid #334155',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '13px', fontWeight: 'bold' }}>{nodeId.replace('_', ' ')}</span>
                          <span style={{ 
                            fontSize: '9px', 
                            padding: '1px 6px', 
                            borderRadius: '8px', 
                            backgroundColor: stepBadge.bg, 
                            color: stepBadge.color,
                            fontWeight: 'bold',
                            textTransform: 'uppercase'
                          }}>{state.status}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8' }}>
                          <span>⏱ {state.duration ? `${state.duration}s` : '0s'}</span>
                          {state.retries > 0 && <span style={{ color: '#f59e0b' }}>🔁 Retries: {state.retries}</span>}
                        </div>
                        {state.logs && state.logs.length > 0 && (
                          <div style={{ 
                            marginTop: '5px', 
                            maxHeight: '100px', 
                            overflowY: 'auto', 
                            backgroundColor: '#000000', 
                            padding: '6px', 
                            borderRadius: '4px',
                            fontFamily: 'monospace',
                            fontSize: '10px',
                            color: '#22c55e',
                            whiteSpace: 'pre-wrap'
                          }}>
                            {state.logs.join('\n')}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

          </div>
        )}
      </div>

    </div>
  );
};

export default WorkflowExecution;
