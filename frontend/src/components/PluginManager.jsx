import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE_URL } from '../config/api';

const PluginManager = ({ token, showNotification }) => {
  const [plugins, setPlugins] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedPlugin, setSelectedPlugin] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('installed'); // 'installed' or 'marketplace'
  const [searchQuery, setSearchQuery] = useState('');
  const [healthStatus, setHealthStatus] = useState(null);
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);

  const { user } = useAuth();
  const userRole = user?.role || 'Viewer';
  const isAdmin = userRole === 'Admin';

  const getHeaders = () => {
    return {
      headers: { Authorization: `Bearer ${token}` }
    };
  };

  const fetchPlugins = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/plugins`, getHeaders());
      setPlugins(res.data || []);
    } catch (err) {
      console.error(err);
      showNotification('Failed to fetch plugins list.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlugins();
  }, []);

  const handleInstall = async (pluginId) => {
    if (!isAdmin) {
      showNotification('Only Administrators can install plugins.', 'error');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/plugins/install`, { plugin_id: pluginId }, getHeaders());
      showNotification(`Plugin '${pluginId}' installed and activated successfully.`, 'success');
      await fetchPlugins();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      showNotification(`Failed to install plugin: ${msg}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleUninstall = async (pluginId) => {
    if (!isAdmin) {
      showNotification('Only Administrators can uninstall plugins.', 'error');
      return;
    }
    if (!window.confirm(`Are you sure you want to remove the plugin '${pluginId}'?`)) return;
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/plugins/uninstall`, { plugin_id: pluginId }, getHeaders());
      showNotification(`Plugin '${pluginId}' removed successfully.`, 'success');
      if (selectedPlugin?.id === pluginId) setSelectedPlugin(null);
      await fetchPlugins();
    } catch (err) {
      showNotification(`Failed to uninstall plugin: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnable = async (pluginId, isEnabled) => {
    if (!isAdmin) {
      showNotification('Only Administrators can change plugin states.', 'error');
      return;
    }
    setLoading(true);
    const endpoint = isEnabled ? 'disable' : 'enable';
    try {
      await axios.post(`${API_BASE_URL}/plugins/${endpoint}`, { plugin_id: pluginId }, getHeaders());
      showNotification(`Plugin '${pluginId}' is now ${isEnabled ? 'disabled' : 'enabled'}.`, 'success');
      await fetchPlugins();
      // Sync selected plugin
      const updated = plugins.find(p => p.id === pluginId);
      if (updated) {
        setSelectedPlugin({ ...updated, enabled: !isEnabled });
      }
    } catch (err) {
      showNotification(`Failed to change plugin state: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (pluginId) => {
    if (!isAdmin) {
      showNotification('Only Administrators can upgrade plugins.', 'error');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/plugins/upgrade`, { plugin_id: pluginId }, getHeaders());
      showNotification(`Plugin '${pluginId}' upgraded to version 1.0.0.`, 'success');
      await fetchPlugins();
    } catch (err) {
      showNotification(`Upgrade failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (pluginId) => {
    if (!isAdmin) {
      showNotification('Only Administrators can roll back plugins.', 'error');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/plugins/rollback`, { plugin_id: pluginId }, getHeaders());
      showNotification(`Plugin '${pluginId}' version rolled back.`, 'success');
      await fetchPlugins();
    } catch (err) {
      showNotification(`Rollback failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const triggerHealthDiagnostics = async () => {
    setDiagnosticLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/plugins/health`, getHeaders());
      setHealthStatus(res.data);
      showNotification('Plugin health check completed.', 'success');
      await fetchPlugins();
    } catch (err) {
      showNotification('Health checks failed.', 'error');
    } finally {
      setDiagnosticLoading(false);
    }
  };

  // Filters
  const filteredPlugins = plugins.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          p.description.toLowerCase().includes(searchQuery.toLowerCase());
    if (activeSubTab === 'installed') {
      return p.installed && matchesSearch;
    } else {
      return !p.installed && matchesSearch;
    }
  });

  // Calculate summary counts
  const totalLoaded = plugins.filter(p => p.installed).length;
  const activeCount = plugins.filter(p => p.installed && p.enabled).length;
  const unhealthyCount = plugins.filter(p => p.installed && p.health_status === 'unhealthy').length;

  return (
    <div className="plugin-manager-container">
      {/* Top Telemetry Header */}
      <div className="telemetry-row">
        <div className="telemetry-card">
          <span className="card-icon">🔌</span>
          <div className="card-info">
            <h5>Total Installed</h5>
            <h4>{totalLoaded}</h4>
          </div>
        </div>
        <div className="telemetry-card">
          <span className="card-icon">✅</span>
          <div className="card-info">
            <h5>Active/Enabled</h5>
            <h4>{activeCount}</h4>
          </div>
        </div>
        <div className="telemetry-card alert">
          <span className="card-icon">⚠️</span>
          <div className="card-info">
            <h5>Unhealthy Plugins</h5>
            <h4>{unhealthyCount}</h4>
          </div>
        </div>
        <div className="telemetry-card action-card" onClick={triggerHealthDiagnostics}>
          <span className="card-icon">{diagnosticLoading ? '⏳' : '🏥'}</span>
          <div className="card-info">
            <h5>Run health check</h5>
            <p>Diagnose systems</p>
          </div>
        </div>
      </div>

      <div className="plugin-grid-layout">
        {/* Left Side: List and Filters */}
        <div className="plugin-list-panel">
          <div className="panel-controls">
            <div className="tabs-navigation">
              <button 
                className={`tab-link ${activeSubTab === 'installed' ? 'active' : ''}`}
                onClick={() => setActiveSubTab('installed')}
              >
                📥 Installed ({totalLoaded})
              </button>
              <button 
                className={`tab-link ${activeSubTab === 'marketplace' ? 'active' : ''}`}
                onClick={() => setActiveSubTab('marketplace')}
              >
                🛍️ Marketplace Catalog ({plugins.filter(p => !p.installed).length})
              </button>
            </div>
            
            <input 
              type="text" 
              placeholder="Search plugins..." 
              className="search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="plugin-cards-feed">
            {loading ? (
              <div className="loading-state">⏳ Loading plugins registry state...</div>
            ) : filteredPlugins.length === 0 ? (
              <div className="empty-state">No plugins matched this view filter.</div>
            ) : (
              filteredPlugins.map(p => (
                <div 
                  key={p.id} 
                  className={`plugin-item-card ${selectedPlugin?.id === p.id ? 'selected' : ''}`}
                  onClick={() => setSelectedPlugin(p)}
                >
                  <div className="card-header">
                    <h4>{p.name}</h4>
                    <span className={`capability-badge ${p.capability}`}>{p.capability.replace('_', ' ')}</span>
                  </div>
                  <p className="card-description">{p.description}</p>
                  <div className="card-footer">
                    <span className="version">v{p.version}</span>
                    <span className="author">by {p.author}</span>
                    {p.installed ? (
                      <span className={`status-pill ${p.enabled ? 'enabled' : 'disabled'}`}>
                        {p.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    ) : (
                      <span className="status-pill marketplace">Marketplace</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side: Details View Panel */}
        <div className="plugin-details-panel">
          {selectedPlugin ? (
            <div className="details-container">
              <div className="details-header">
                <h2>{selectedPlugin.name}</h2>
                <p><strong>Extension ID:</strong> <code>{selectedPlugin.id}</code></p>
                <div className="metadata-badges">
                  <span className="badge">Capability: {selectedPlugin.capability}</span>
                  <span className="badge">Author: {selectedPlugin.author}</span>
                  <span className="badge">Version: v{selectedPlugin.version}</span>
                </div>
              </div>

              <div className="details-body">
                <div className="section-block">
                  <h4>Description</h4>
                  <p>{selectedPlugin.description}</p>
                </div>

                {selectedPlugin.installed && (
                  <div className="section-block">
                    <h4>Health Status</h4>
                    <div className={`health-status-row ${selectedPlugin.health_status}`}>
                      <span className="health-icon">{selectedPlugin.health_status === 'healthy' ? '💚' : '💔'}</span>
                      <div className="health-info">
                        <strong>{selectedPlugin.health_status.toUpperCase()}</strong>
                        <p>{selectedPlugin.health_message || 'No health report message.'}</p>
                        {selectedPlugin.last_health_check && (
                          <span className="timestamp">Checked: {new Date(selectedPlugin.last_health_check).toLocaleTimeString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {selectedPlugin.dependencies && selectedPlugin.dependencies.length > 0 && (
                  <div className="section-block">
                    <h4>Dependencies</h4>
                    <ul className="dependencies-list">
                      {selectedPlugin.dependencies.map(dep => (
                        <li key={dep}>📦 {dep}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedPlugin.config_schema && (
                  <div className="section-block">
                    <h4>Configuration Schema</h4>
                    <pre className="schema-pre">
                      {JSON.stringify(selectedPlugin.config_schema, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedPlugin.version_history && selectedPlugin.version_history.length > 0 && (
                  <div className="section-block">
                    <h4>Version logs</h4>
                    <table className="logs-table">
                      <thead>
                        <tr>
                          <th>Version</th>
                          <th>Action</th>
                          <th>Timestamp</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedPlugin.version_history.map((hist, idx) => (
                          <tr key={idx}>
                            <td>{hist.version}</td>
                            <td>{hist.action}</td>
                            <td>{new Date(hist.timestamp).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Action Buttons Panel */}
              <div className="details-actions">
                {selectedPlugin.installed ? (
                  <>
                    <button 
                      onClick={() => handleToggleEnable(selectedPlugin.id, selectedPlugin.enabled)}
                      className={`btn ${selectedPlugin.enabled ? 'btn-warn' : 'btn-primary'}`}
                      disabled={!isAdmin}
                    >
                      {selectedPlugin.enabled ? 'Disable Plugin 🔴' : 'Enable Plugin 🟢'}
                    </button>
                    <button 
                      onClick={() => handleUninstall(selectedPlugin.id)}
                      className="btn btn-danger"
                      disabled={!isAdmin}
                    >
                      Uninstall Plugin 🗑️
                    </button>
                    <button 
                      onClick={() => handleUpgrade(selectedPlugin.id)}
                      className="btn btn-secondary"
                      disabled={!isAdmin}
                    >
                      Mock Upgrade ⚡
                    </button>
                    <button 
                      onClick={() => handleRollback(selectedPlugin.id)}
                      className="btn btn-secondary"
                      disabled={!isAdmin}
                    >
                      Rollback ⏪
                    </button>
                  </>
                ) : (
                  <button 
                    onClick={() => handleInstall(selectedPlugin.id)}
                    className="btn btn-primary"
                    disabled={!isAdmin}
                  >
                    Install Plugin 📥
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="select-plugin-placeholder">
              <span className="placeholder-icon">🔌</span>
              <h3>Select a plugin</h3>
              <p>Choose an installed plugin or browse the offline catalog to inspect configurations, schema interfaces, and execution actions.</p>
            </div>
          )}
        </div>
      </div>

      {/* Diagnostic Health Modal Info */}
      {healthStatus && (
        <div className="health-diagnostics-report">
          <div className="report-header">
            <h4>🏥 Plugin Health Diagnostics Log</h4>
            <button className="close-btn" onClick={() => setHealthStatus(null)}>×</button>
          </div>
          <div className="report-body">
            <p><strong>Overall Status:</strong> <span className={healthStatus.overall_status}>{healthStatus.overall_status.toUpperCase()}</span></p>
            <ul>
              {healthStatus.reports && healthStatus.reports.map(r => (
                <li key={r.plugin_id} className={r.status}>
                  <strong>{r.name} ({r.plugin_id}):</strong> {r.status.toUpperCase()}
                  <pre>{JSON.stringify(r.details, null, 2)}</pre>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default PluginManager;
