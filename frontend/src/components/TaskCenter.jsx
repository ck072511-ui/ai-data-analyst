import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const TaskCenter = ({ token, showNotification }) => {
  const [tasks, setTasks] = useState([]);
  const [workerHealth, setWorkerHealth] = useState(null);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  // Configure axios auth headers
  const getHeaders = () => ({
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchTasksAndHealth = async () => {
    try {
      // Fetch tasks
      const tasksRes = await axios.get(`${API_BASE_URL}/tasks`, getHeaders());
      setTasks(tasksRes.data);

      // Fetch worker health
      const healthRes = await axios.get(`${API_BASE_URL}/workers/health`, getHeaders());
      setWorkerHealth(healthRes.data);
    } catch (error) {
      console.error('Error fetching tasks or health:', error);
    }
  };

  useEffect(() => {
    fetchTasksAndHealth();
    const interval = setInterval(fetchTasksAndHealth, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const handleRetry = async (taskId) => {
    try {
      await axios.post(`${API_BASE_URL}/tasks/${taskId}/retry`, {}, getHeaders());
      showNotification('Task retry initiated successfully.', 'success');
      fetchTasksAndHealth();
    } catch (error) {
      const msg = error.response?.data?.detail || 'Failed to retry task';
      showNotification(msg, 'error');
    }
  };

  const handleCancel = async (taskId) => {
    try {
      await axios.delete(`${API_BASE_URL}/tasks/${taskId}`, getHeaders());
      showNotification('Task cancelled successfully.', 'info');
      fetchTasksAndHealth();
    } catch (error) {
      const msg = error.response?.data?.detail || 'Failed to cancel task';
      showNotification(msg, 'error');
    }
  };

  const calculateDuration = (startedAt, finishedAt) => {
    if (!startedAt) return '0s';
    const start = new Date(startedAt);
    const end = finishedAt ? new Date(finishedAt) : new Date();
    const diffMs = Math.max(0, end - start);
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return `${diffSec}s`;
    const diffMin = Math.floor(diffSec / 60);
    return `${diffMin}m ${diffSec % 60}s`;
  };

  // Color mapping
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'running': return '#3b82f6';
      case 'failed': return '#ef4444';
      case 'cancelled': return '#6b7280';
      case 'pending': return '#f59e0b';
      default: return '#9ca3af';
    }
  };

  const filteredTasks = tasks.filter(t => {
    if (filter === 'all') return true;
    return t.status === filter;
  });

  // UI Styles
  const containerStyle = {
    padding: '24px',
    borderRadius: '16px',
    fontFamily: "'Inter', sans-serif",
    transition: 'all 0.3s ease',
    backgroundColor: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    minHeight: '600px',
    boxShadow: darkMode ? '0 10px 30px rgba(0,0,0,0.5)' : '0 10px 30px rgba(0,0,0,0.05)',
    border: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0',
  };

  const cardStyle = {
    padding: '20px',
    borderRadius: '12px',
    backgroundColor: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    marginBottom: '16px',
  };

  const navTabStyle = (active) => ({
    padding: '8px 16px',
    borderRadius: '8px',
    fontWeight: '600',
    fontSize: '0.9rem',
    cursor: 'pointer',
    border: 'none',
    backgroundColor: active ? (darkMode ? '#3b82f6' : '#2563eb') : 'transparent',
    color: active ? '#ffffff' : (darkMode ? '#94a3b8' : '#64748b'),
    transition: 'all 0.2s',
  });

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0', paddingBottom: '16px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700 }}>⚙️ Task Queue & Background Processing</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>
            Monitor and control running analytics, cleaning, and profiling tasks.
          </p>
        </div>
        <button 
          onClick={() => setDarkMode(!darkMode)}
          style={{ padding: '8px 16px', borderRadius: '8px', border: 'none', cursor: 'pointer', backgroundColor: darkMode ? '#334155' : '#e2e8f0', color: darkMode ? '#f8fafc' : '#0f172a', fontWeight: '600' }}
        >
          {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
        </button>
      </div>

      {/* Worker Health Banner */}
      {workerHealth && (
        <div style={{ ...cardStyle, display: 'flex', flexWrap: 'wrap', gap: '24px', alignItems: 'center', backgroundColor: darkMode ? '#0f172a' : '#f1f5f9', borderColor: darkMode ? '#1e293b' : '#cbd5e1', padding: '16px 20px', borderRadius: '12px' }}>
          <div>
            <span style={{ fontSize: '0.85rem', color: darkMode ? '#64748b' : '#94a3b8', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Engine Status</span>
            <span style={{ fontWeight: 700, color: workerHealth.status === 'healthy' ? '#10b981' : '#ef4444', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: workerHealth.status === 'healthy' ? '#10b981' : '#ef4444' }}></span>
              {workerHealth.status === 'healthy' ? 'ACTIVE' : 'DEGRADED'}
            </span>
          </div>
          <div>
            <span style={{ fontSize: '0.85rem', color: darkMode ? '#64748b' : '#94a3b8', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Queue Broker (Redis)</span>
            <span style={{ fontWeight: 600 }}>{workerHealth.redis_connected ? '🟢 Connected' : '🔴 Offline'}</span>
          </div>
          <div>
            <span style={{ fontSize: '0.85rem', color: darkMode ? '#64748b' : '#94a3b8', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Celery Worker Node</span>
            <span style={{ fontWeight: 600 }}>{workerHealth.celery_workers_active ? '🟢 Online' : '🟡 Offline (Fallback Enabled)'}</span>
          </div>
          <div>
            <span style={{ fontSize: '0.85rem', color: darkMode ? '#64748b' : '#94a3b8', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Queue Backlog</span>
            <span style={{ fontWeight: 600, padding: '2px 8px', borderRadius: '4px', backgroundColor: workerHealth.queue_backlog > 0 ? '#ef4444' : (darkMode ? '#334155' : '#cbd5e1'), color: workerHealth.queue_backlog > 0 ? '#ffffff' : 'inherit' }}>
              {workerHealth.queue_backlog} tasks pending
            </span>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', overflowX: 'auto', paddingBottom: '4px' }}>
        <button onClick={() => setFilter('all')} style={navTabStyle(filter === 'all')}>All ({tasks.length})</button>
        <button onClick={() => setFilter('running')} style={navTabStyle(filter === 'running')}>Running ({tasks.filter(t => t.status === 'running').length})</button>
        <button onClick={() => setFilter('pending')} style={navTabStyle(filter === 'pending')}>Pending ({tasks.filter(t => t.status === 'pending').length})</button>
        <button onClick={() => setFilter('completed')} style={navTabStyle(filter === 'completed')}>Completed ({tasks.filter(t => t.status === 'completed').length})</button>
        <button onClick={() => setFilter('failed')} style={navTabStyle(filter === 'failed')}>Failed ({tasks.filter(t => t.status === 'failed').length})</button>
      </div>

      {/* Task List */}
      <div>
        {filteredTasks.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: darkMode ? '#64748b' : '#94a3b8' }}>
            <span style={{ fontSize: '3rem', display: 'block', marginBottom: '12px' }}>📭</span>
            No tasks found in this category.
          </div>
        ) : (
          filteredTasks.map(task => (
            <div key={task.id} style={cardStyle}>
              {/* Task Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, textTransform: 'capitalize' }}>
                    {task.task_type.replace(/_/g, ' ')}
                  </h4>
                  <span style={{ fontSize: '0.8rem', color: darkMode ? '#64748b' : '#94a3b8', fontFamily: 'monospace' }}>
                    ID: {task.id}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '0.85rem', color: darkMode ? '#94a3b8' : '#64748b' }}>
                    ⏱️ {calculateDuration(task.started_at, task.finished_at)}
                  </span>
                  <span style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    color: '#ffffff',
                    backgroundColor: getStatusColor(task.status),
                    textTransform: 'uppercase'
                  }}>
                    {task.status}
                  </span>
                </div>
              </div>

              {/* Progress Bar (Visible for incomplete states) */}
              {(task.status === 'running' || task.status === 'pending') && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 600 }}>
                    <span>Processing progress</span>
                    <span>{task.progress}%</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', backgroundColor: darkMode ? '#334155' : '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${task.progress}%`, height: '100%', backgroundColor: '#3b82f6', borderRadius: '4px', transition: 'width 0.4s ease' }} />
                  </div>
                </div>
              )}

              {/* Error Box (Visible for Failed state) */}
              {task.status === 'failed' && task.error_message && (
                <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#f87171', fontSize: '0.9rem', marginBottom: '16px', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  <strong>Error details:</strong> {task.error_message}
                </div>
              )}

              {/* Footer Timestamps and Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', borderTop: darkMode ? '1px solid #2d3748' : '1px solid #f1f5f9', paddingTop: '12px' }}>
                <span style={{ fontSize: '0.8rem', color: darkMode ? '#64748b' : '#94a3b8' }}>
                  Started: {task.started_at ? new Date(task.started_at).toLocaleString() : '-'}
                  {task.finished_at && ` | Finished: ${new Date(task.finished_at).toLocaleString()}`}
                </span>
                
                <div style={{ display: 'flex', gap: '8px' }}>
                  {task.status === 'failed' && (
                    <button
                      onClick={() => handleRetry(task.id)}
                      style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', cursor: 'pointer', backgroundColor: '#10b981', color: '#ffffff', fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      🔄 Rerun Task
                    </button>
                  )}
                  {(task.status === 'running' || task.status === 'pending') && (
                    <button
                      onClick={() => handleCancel(task.id)}
                      style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', cursor: 'pointer', backgroundColor: '#ef4444', color: '#ffffff', fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      🛑 Cancel Execution
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TaskCenter;
