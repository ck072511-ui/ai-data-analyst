import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const DataCleaningVersions = ({ token, datasetId, showNotification, onRollbackComplete }) => {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState(false);
  const [targetRollbackVersion, setTargetRollbackVersion] = useState(null);

  useEffect(() => {
    if (datasetId) {
      fetchVersions();
    }
  }, [datasetId]);

  const fetchVersions = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/${datasetId}/versions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setVersions(response.data);
    } catch (error) {
      showNotification('Failed to fetch dataset versions history', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRollbackClick = (v) => {
    setTargetRollbackVersion(v);
  };

  const executeRollback = async () => {
    if (!targetRollbackVersion) return;
    setRollbackLoading(true);
    try {
      await axios.post(
        `${API_BASE_URL}/datasets/${datasetId}/rollback`,
        { version_number: targetRollbackVersion.version_number },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      showNotification(`Successfully restored dataset pointer back to Version ${targetRollbackVersion.version_number}!`, 'success');
      setTargetRollbackVersion(null);
      fetchVersions();
      if (onRollbackComplete) {
        onRollbackComplete();
      }
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to execute rollback restore', 'error');
    } finally {
      setRollbackLoading(false);
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

  if (versions.length === 0) {
    return (
      <div className="preview-empty-report">
        <span className="radar-icon">🐚</span>
        <h5>No Snapshots Found</h5>
        <p>Run a cleaning strategy configuration checklist to write your first snapshot database version.</p>
      </div>
    );
  }

  return (
    <div className="versions-container animation-fade-in">
      <div className="versions-header">
        <h4>📦 Dataset Version History & Snapshots</h4>
        <p>Every clean action automatically registers a new version on disk. Restore any previous version instantly.</p>
      </div>

      <div className="versions-list">
        {versions.map((v) => (
          <div key={v.id} className="version-card">
            <div className="version-meta">
              <span className="version-num-badge">V{v.version_number}</span>
              <div className="meta-info">
                <h5>{new Date(v.timestamp).toLocaleString()}</h5>
                <p>{v.row_count.toLocaleString()} rows • {v.col_count.toLocaleString()} columns</p>
              </div>
            </div>

            <div className="version-operations">
              <h6>Applied Operations:</h6>
              <div className="ops-list">
                {v.operations_applied?.map((op, idx) => (
                  <span key={idx} className="op-tag">{op}</span>
                ))}
              </div>
            </div>

            <div className="version-actions">
              <button 
                className="rollback-btn"
                onClick={() => handleRollbackClick(v)}
                disabled={v.version_number === versions[0].version_number}
                title={v.version_number === versions[0].version_number ? 'This is the active version' : 'Rollback pointer to this snapshot'}
              >
                {v.version_number === versions[0].version_number ? '✓ Active Version' : '↩ Restore Snapshot'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Confirmation Modal */}
      {targetRollbackVersion && (
        <div className="custom-modal-backdrop animation-fade-in">
          <div className="custom-modal-card">
            <h4>↩ Confirm Version Rollback</h4>
            <p>You are restoring dataset pointers to **Version {targetRollbackVersion.version_number}**. This will update the active database schema catalog. Operations applied after this version will be bypassed in queries.</p>
            
            <div className="modal-actions">
              <button 
                className="modal-cancel-btn"
                onClick={() => setTargetRollbackVersion(null)}
                disabled={rollbackLoading}
              >
                Cancel
              </button>
              <button 
                className="modal-confirm-btn"
                style={{ background: '#3b82f6' }}
                onClick={executeRollback}
                disabled={rollbackLoading}
              >
                {rollbackLoading ? 'Restoring...' : 'Yes, Restore Version'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataCleaningVersions;
