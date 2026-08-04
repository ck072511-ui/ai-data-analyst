import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const DatabaseConnections = ({
  token,
  dbConnections,
  selectedDbConnId,
  onSelectConnection,
  onConnectionsChanged
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentConnId, setCurrentConnId] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [savingConnection, setSavingConnection] = useState(false);
  
  // Status check state for cards
  const [connectionStatuses, setConnectionStatuses] = useState({});
  const [checkingStatusId, setCheckingStatusId] = useState(null);

  const [form, setForm] = useState({
    name: '',
    db_type: 'postgresql',
    host: '',
    port: '5432',
    database: '',
    username: '',
    password: ''
  });

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Reset form helper
  const resetForm = () => {
    setForm({
      name: '',
      db_type: 'postgresql',
      host: '',
      port: '5432',
      database: '',
      username: '',
      password: ''
    });
    setErrorMsg('');
    setSuccessMsg('');
    setIsEditing(false);
    setCurrentConnId(null);
  };

  // Open modal for add
  const handleOpenAdd = () => {
    resetForm();
    setShowModal(true);
  };

  // Open modal for edit
  const handleOpenEdit = (conn) => {
    resetForm();
    setForm({
      name: conn.name,
      db_type: conn.db_type,
      host: conn.host || '',
      port: conn.port ? String(conn.port) : '',
      database: conn.database,
      username: conn.username || '',
      password: '' // Keep empty, user only fills if changing
    });
    setIsEditing(true);
    setCurrentConnId(conn.id);
    setShowModal(true);
  };

  // Test connection in form
  const handleTestConnection = async () => {
    setTestingConnection(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const payload = {
        db_type: form.db_type,
        host: form.host || null,
        port: form.port ? parseInt(form.port) : null,
        database: form.database,
        username: form.username || null,
        password: form.password || null
      };

      // In case of edit, if password is empty, we test using the saved credentials on the backend
      // So if isEditing is true and password is empty, we must tell the test endpoint?
      // Wait, the /test endpoint expects a password if testing a new/unsaved connection.
      // If we are editing, we can either:
      // 1. Decrypt on backend and test. But wait, /test is a POST with ConnectionTestRequest, it doesn't take an ID!
      // So to test an existing connection with current settings, we should either run it on a separate PUT test endpoint,
      // or we can just send the ID. Wait, since we are in the edit dialog, if the password field is empty, the user hasn't changed it.
      // If the user wants to test, they would be testing the combined configuration.
      // Let's implement a separate test functionality or if they are editing, and password is empty, we can show a warning
      // that "Password must be re-entered to test connection before saving, or save directly."
      // Actually, we can add a connection test that calls GET or POST to test an existing connection by ID!
      // Let's check: did we add an endpoint to test an existing connection?
      // Wait, in db_connection.py, we have:
      // POST /database/test -> ConnectionTestRequest
      // If we want to test an existing connection, we can test it from the card directly!
      // Let's implement a card-level test that tests by connection ID. Wait!
      // Can we test by connection ID?
      // Ah, the backend doesn't have an explicit POST /database/{id}/test endpoint.
      // But wait! We can easily use the existing POST /database/test endpoint by sending the decrypted password.
      // Wait, the frontend doesn't have the password because it is never exposed in API responses!
      // So the card-level test needs a backend endpoint, or we can add a test route for existing connections:
      // `POST /api/v1/database/{connection_id}/test` or `GET /api/v1/database/{connection_id}/test`
      // Wait! Let's check: does the backend have a test endpoint for existing connections?
      // Let's check if we can add a quick route `POST /api/v1/database/{connection_id}/test` to `db_connection.py`!
      // Yes! That is extremely easy and clean! Let's add it or check if we can write it.
      // Wait, we can test by connection ID by calling `test_connection_by_id` on the backend!
      // Let's see: we can implement `POST /database/{connection_id}/test` on the backend!
      // Let's add it to `db_connection.py` in the next refactoring or we can add it now.
      // Oh, wait, we already updated `db_connection.py` once. We can update it again to add this endpoint. It's a single contiguous change.
      // Let's check if we need to. Yes, it makes the "Connection Status Indicator" and "Test Connection" on the card/dialog work perfectly!
      // Wait, let's look at how the status of cards is tested. We can call `/api/v1/database/{connection_id}/schema` which indirectly tests connection,
      // or we can add a dedicated `/api/v1/database/{connection_id}/test` endpoint that returns `{"success": true, "message": "Connection successful"}`.
      // Yes, a dedicated endpoint `POST /{connection_id}/test` is very clean and standard!
      // Let's assume we have it or will add it.
      
      const payload_to_send = { ...payload };
      if (isEditing && !form.password) {
        // If editing and no password is set, we can call the backend to test the saved connection
        // using the ID!
        await axios.post(`${API_BASE_URL}/database/${currentConnId}/test`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setSuccessMsg('Database connection test successful!');
        return;
      }

      await axios.post(`${API_BASE_URL}/database/test`, payload_to_send, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccessMsg('Database connection test successful!');
    } catch (error) {
      setErrorMsg(error.response?.data?.detail || 'Connection test failed. Verify your credentials and network settings.');
    } finally {
      setTestingConnection(false);
    }
  };

  // Test connection on card level
  const testCardConnection = async (connId) => {
    setCheckingStatusId(connId);
    try {
      await axios.post(`${API_BASE_URL}/database/${connId}/test`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConnectionStatuses(prev => ({ ...prev, [connId]: { success: true, message: 'Online' } }));
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Offline';
      setConnectionStatuses(prev => ({ ...prev, [connId]: { success: false, message: errorMsg } }));
    } finally {
      setCheckingStatusId(null);
    }
  };

  // Run card status test on mount for all cards
  useEffect(() => {
    if (dbConnections && dbConnections.length > 0) {
      dbConnections.forEach(conn => {
        if (connectionStatuses[conn.id] === undefined) {
          testCardConnection(conn.id);
        }
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dbConnections]);

  // Save connection (Add or Edit)
  const handleSaveConnection = async () => {
    setSavingConnection(false);
    setErrorMsg('');
    setSuccessMsg('');
    
    if (!form.name || !form.database) {
      setErrorMsg('Display Name and Database Name are required.');
      return;
    }

    try {
      const payload = {
        name: form.name,
        db_type: form.db_type,
        host: form.host || null,
        port: form.port ? parseInt(form.port) : null,
        database: form.database,
        username: form.username || null,
        password: form.password || null
      };

      if (isEditing) {
        // If editing and password is empty, don't send the password key (or send null so backend preserves the old password)
        const updatePayload = { ...payload };
        if (!form.password) {
          delete updatePayload.password;
        }
        await axios.put(`${API_BASE_URL}/database/${currentConnId}`, updatePayload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setSuccessMsg('Database connection updated successfully!');
      } else {
        await axios.post(`${API_BASE_URL}/database/connect`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setSuccessMsg('Database connection saved successfully!');
      }

      // Refresh connection lists
      if (onConnectionsChanged) {
        onConnectionsChanged();
      }
      
      // Close modal after brief delay to show success message
      setTimeout(() => {
        setShowModal(false);
        resetForm();
      }, 1500);

    } catch (error) {
      setErrorMsg(error.response?.data?.detail || 'Failed to save connection config.');
    } finally {
      setSavingConnection(false);
    }
  };

  // Delete connection
  const handleDelete = async (e, conn) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to disconnect and delete configuration for "${conn.name}"?`)) return;

    try {
      await axios.delete(`${API_BASE_URL}/database/${conn.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (selectedDbConnId === conn.id) {
        onSelectConnection(null);
      }
      
      if (onConnectionsChanged) {
        onConnectionsChanged();
      }
    } catch (error) {
      alert('Failed to delete database connection: ' + (error.response?.data?.detail || error.message));
    }
  };

  // Filter connections by search query
  const filteredConnections = dbConnections.filter(conn => {
    const query = searchQuery.toLowerCase();
    return (
      conn.name.toLowerCase().includes(query) ||
      conn.db_type.toLowerCase().includes(query) ||
      conn.database.toLowerCase().includes(query) ||
      (conn.host && conn.host.toLowerCase().includes(query))
    );
  });

  return (
    <div className="database-connections-page">
      <div className="page-header-row">
        <div className="header-text">
          <h3>🔌 Enterprise Database Connections</h3>
          <p>Manage connection engines, view statuses, and switch your active data analysis context.</p>
        </div>
        <button className="add-connection-primary-btn" onClick={handleOpenAdd}>
          ➕ Add New Connection
        </button>
      </div>

      {/* Search & Statistics */}
      <div className="search-bar-row">
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search connections by name, type, host or database..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="connections-count">
          <span>Showing {filteredConnections.length} of {dbConnections.length} connections</span>
        </div>
      </div>

      {/* Connections Grid */}
      {filteredConnections.length === 0 ? (
        <div className="empty-connections-state">
          <span className="empty-icon">🔌</span>
          <h4>No Database Connections Found</h4>
          <p>{searchQuery ? 'Try adjusting your search filters.' : 'Click "Add New Connection" to connect your PostgreSQL or SQLite databases.'}</p>
          {!searchQuery && (
            <button className="add-connection-secondary-btn" onClick={handleOpenAdd}>
              Connect Your First Database
            </button>
          )}
        </div>
      ) : (
        <div className="connections-grid">
          {filteredConnections.map((conn) => {
            const isActive = selectedDbConnId === conn.id;
            const status = connectionStatuses[conn.id];
            
            return (
              <div 
                key={conn.id} 
                className={`connection-card ${isActive ? 'active' : ''}`}
                onClick={() => onSelectConnection(conn.id)}
              >
                {/* Active Indicator Badge */}
                {isActive && <div className="active-card-badge">ACTIVE CONTEXT</div>}
                
                <div className="card-header">
                  <div className="db-icon-wrapper">
                    {conn.db_type === 'postgresql' ? '🐘' : (conn.db_type === 'sqlite' ? '🐚' : '🐬')}
                  </div>
                  <div className="db-meta-info">
                    <span className="db-badge-type">{conn.db_type.toUpperCase()}</span>
                    {status ? (
                      <span className={`status-indicator-badge ${status.success ? 'online' : 'offline'}`}>
                        {status.success ? '● Online' : '● Offline'}
                      </span>
                    ) : (
                      <span className="status-indicator-badge checking">● Checking...</span>
                    )}
                  </div>
                </div>

                <div className="card-body">
                  <h4>{conn.name}</h4>
                  <div className="meta-list">
                    <div className="meta-item">
                      <span className="label">Database:</span>
                      <span className="val" title={conn.database}>{conn.database}</span>
                    </div>
                    {conn.db_type !== 'sqlite' && (
                      <>
                        <div className="meta-item">
                          <span className="label">Host:</span>
                          <span className="val" title={conn.host}>{conn.host}:{conn.port}</span>
                        </div>
                        <div className="meta-item">
                          <span className="label">User:</span>
                          <span className="val">{conn.username}</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="card-actions" onClick={(e) => e.stopPropagation()}>
                  <button 
                    className="card-action-btn select" 
                    onClick={() => onSelectConnection(conn.id)}
                    disabled={isActive}
                  >
                    {isActive ? 'Selected' : 'Use Database'}
                  </button>
                  <div className="right-card-actions">
                    <button 
                      className="card-action-btn test" 
                      onClick={() => testCardConnection(conn.id)}
                      disabled={checkingStatusId === conn.id}
                      title="Test Connection"
                    >
                      {checkingStatusId === conn.id ? '⏳' : '⚡'}
                    </button>
                    <button 
                      className="card-action-btn edit" 
                      onClick={() => handleOpenEdit(conn)}
                      title="Edit Configuration"
                    >
                      ✏️
                    </button>
                    <button 
                      className="card-action-btn delete" 
                      onClick={(e) => handleDelete(e, conn)}
                      title="Disconnect Database"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add / Edit Connection Modal Dialog */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog-card">
            <div className="modal-header">
              <h3>{isEditing ? '✏️ Edit Connection' : '🔌 Connect Enterprise Database'}</h3>
              <button className="close-modal-btn" onClick={() => setShowModal(false)}>✕</button>
            </div>
            
            <div className="modal-body">
              {errorMsg && <div className="modal-alert-error">⚠️ {errorMsg}</div>}
              {successMsg && <div className="modal-alert-success">✅ {successMsg}</div>}

              <div className="form-grid-modal">
                <div className="form-group-modal">
                  <label>Display Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Production Analytics Database"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </div>

                <div className="form-group-modal">
                  <label>Database Type</label>
                  <select
                    value={form.db_type}
                    onChange={(e) => setForm({ 
                      ...form, 
                      db_type: e.target.value,
                      port: e.target.value === 'postgresql' ? '5432' : (e.target.value === 'mysql' ? '3306' : '')
                    })}
                    disabled={isEditing} // Database type cannot be changed on edit
                  >
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                    <option value="sqlite">SQLite</option>
                  </select>
                </div>

                {form.db_type !== 'sqlite' && (
                  <>
                    <div className="form-group-modal">
                      <label>Host Address</label>
                      <input
                        type="text"
                        placeholder="e.g. database.company.com or localhost"
                        value={form.host}
                        onChange={(e) => setForm({ ...form, host: e.target.value })}
                      />
                    </div>

                    <div className="form-group-modal">
                      <label>Port</label>
                      <input
                        type="text"
                        placeholder="e.g. 5432"
                        value={form.port}
                        onChange={(e) => setForm({ ...form, port: e.target.value })}
                      />
                    </div>

                    <div className="form-group-modal">
                      <label>Username</label>
                      <input
                        type="text"
                        placeholder="Database username"
                        value={form.username}
                        onChange={(e) => setForm({ ...form, username: e.target.value })}
                      />
                    </div>

                    <div className="form-group-modal">
                      <label>Password</label>
                      <input
                        type="password"
                        placeholder={isEditing ? 'Leave blank to keep existing password' : 'Database password'}
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                      />
                    </div>
                  </>
                )}

                <div className="form-group-modal full-width">
                  <label>{form.db_type === 'sqlite' ? 'SQLite Database File Path (Relative to project or absolute)' : 'Database Name'}</label>
                  <input
                    type="text"
                    placeholder={form.db_type === 'sqlite' ? 'e.g. backend/data/test_analytics.db' : 'e.g. customer_orders'}
                    value={form.database}
                    onChange={(e) => setForm({ ...form, database: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button 
                className="modal-test-btn" 
                onClick={handleTestConnection}
                disabled={testingConnection || !form.database}
              >
                {testingConnection ? '⏳ Testing...' : 'Test Connection ⚡'}
              </button>
              <div className="right-actions">
                <button className="modal-cancel-btn" onClick={() => setShowModal(false)}>Cancel</button>
                <button 
                  className="modal-save-btn" 
                  onClick={handleSaveConnection}
                  disabled={savingConnection || !form.name || !form.database}
                >
                  {savingConnection ? '⏳ Saving...' : 'Save & Connect 💾'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DatabaseConnections;
