import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const DataCleaningAudit = ({ token, datasetId, showNotification }) => {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (datasetId) {
      fetchAudits();
    }
  }, [datasetId]);

  const fetchAudits = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/${datasetId}/audit`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAudits(response.data);
    } catch (error) {
      showNotification('Failed to fetch cleaning audit history', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="preview-skeleton-loader">
        <div className="skeleton-row short"></div>
        <div className="skeleton-row mt-15"></div>
      </div>
    );
  }

  if (audits.length === 0) {
    return (
      <div className="preview-empty-report">
        <span className="radar-icon">📑</span>
        <h5>No Audits Logged</h5>
        <p>Run a cleaning configuration session to log audit metrics.</p>
      </div>
    );
  }

  // Calculate quality improvement metrics if available
  const firstAudit = audits[audits.length - 1]; // oldest
  const latestAudit = audits[0]; // newest
  const totalScoreGain = latestAudit.quality_score_after - firstAudit.quality_score_before;

  return (
    <div className="audit-timeline-container animation-fade-in">
      <div className="audit-header">
        <h4>📋 Data Cleaning Audit Trail</h4>
        <p>A secure ledger tracking all data sanitizations, metrics differences, cell changes, and quality score deltas.</p>
      </div>

      {/* Quality Improvement summary card */}
      <div className="quality-gains-banner">
        <div className="banner-details">
          <span>Overall Quality Score Progression:</span>
          <h4>
            {firstAudit.quality_score_before} ➔ {latestAudit.quality_score_after}
            <span className={`gain-badge ${totalScoreGain >= 0 ? 'positive' : 'negative'}`}>
              {totalScoreGain >= 0 ? `+${totalScoreGain}` : totalScoreGain} score gain
            </span>
          </h4>
        </div>
      </div>

      <div className="audit-timeline">
        {audits.map((a, index) => (
          <div key={a.id} className="timeline-node">
            <div className="node-marker">
              <span className="bullet-indicator"></span>
              {index < audits.length - 1 && <span className="connecting-line"></span>}
            </div>
            
            <div className="node-card">
              <div className="node-header">
                <span className="timestamp">{new Date(a.timestamp).toLocaleString()}</span>
                <span className="user-lbl">{a.user_email}</span>
              </div>
              
              <div className="node-body">
                <h5>Version Created: **V{a.version_created}**</h5>
                
                <div className="ops-applied-row">
                  <strong>Operations:</strong>
                  <div className="ops-tags">
                    {a.operations_applied?.map((op, idx) => (
                      <span key={idx} className="op-tag">{op}</span>
                    ))}
                  </div>
                </div>

                <div className="audit-metrics-row">
                  <div className="metric-tag">
                    <strong>Rows Changed:</strong> <span>{a.rows_changed > 0 ? `-${a.rows_changed}` : a.rows_changed}</span>
                  </div>
                  <div className="metric-tag">
                    <strong>Columns Changed:</strong> <span>{a.columns_changed > 0 ? `-${a.columns_changed}` : a.columns_changed}</span>
                  </div>
                  <div className="metric-tag score-delta">
                    <strong>Quality Score:</strong> 
                    <span className="delta-badge">
                      {a.quality_score_before} ➔ {a.quality_score_after}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DataCleaningAudit;
