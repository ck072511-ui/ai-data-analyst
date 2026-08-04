import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const ClusterDashboard = ({ token, showNotification }) => {
  const [workers, setWorkers] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [topology, setTopology] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [dispatchLoading, setDispatchLoading] = useState(false);
  
  // Job dispatcher form state
  const [taskType, setTaskType] = useState('predictive');
  const [priority, setPriority] = useState('medium');
  const [preferredCap, setPreferredCap] = useState('');
  const [payloadStr, setPayloadStr] = useState('{"mock": true, "dataset_id": "test_dataset"}');

  const getHeaders = () => {
    return {
      headers: { Authorization: `Bearer ${token}` }
    };
  };

  const fetchClusterData = async () => {
    setLoading(true);
    try {
      const [workersRes, jobsRes, topoRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/cluster/workers`, getHeaders()),
        axios.get(`${API_BASE_URL}/cluster/jobs`, getHeaders()),
        axios.get(`${API_BASE_URL}/cluster/topology`, getHeaders())
      ]);
      setWorkers(workersRes.data || []);
      setJobs(jobsRes.data || []);
      setTopology(topoRes.data || { nodes: [], links: [] });
    } catch (err) {
      console.error('Failed to fetch cluster state:', err);
      showNotification('Failed to fetch cluster platform metrics.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClusterData();
    const interval = setInterval(fetchClusterData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleManualDispatch = async (e) => {
    e.preventDefault();
    setDispatchLoading(true);
    try {
      let parsedPayload = {};
      try {
        parsedPayload = JSON.parse(payloadStr);
      } catch (err) {
        showNotification('Invalid JSON syntax in payload.', 'error');
        setDispatchLoading(false);
        return;
      }

      const res = await axios.post(
        `${API_BASE_URL}/cluster/dispatch`,
        {
          task_type: taskType,
          payload: parsedPayload,
          priority: priority,
          preferred_capability: preferredCap || null
        },
        getHeaders()
      );
      showNotification(`Job successfully enqueued: ${res.data.job_id}`, 'success');
      fetchClusterData();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      showNotification(`Dispatch failed: ${msg}`, 'error');
    } finally {
      setDispatchLoading(false);
    }
  };

  // Summary computations
  const activeWorkersCount = workers.filter(w => w.status !== 'offline').length;
  const totalJobsCount = jobs.length;
  const runningJobsCount = jobs.filter(j => j.status === 'running').length;
  const queueDepth = jobs.filter(j => j.status === 'pending').length;

  return (
    <div className="cluster-dashboard-container">
      {/* Top Telemetry Row */}
      <div className="telemetry-row">
        <div className="telemetry-card">
          <span className="card-icon">🖥️</span>
          <div className="card-info">
            <h5>Active Cluster Nodes</h5>
            <h4>{activeWorkersCount} / {workers.length}</h4>
          </div>
        </div>
        <div className="telemetry-card">
          <span className="card-icon">⚡</span>
          <div className="card-info">
            <h5>Running Jobs</h5>
            <h4>{runningJobsCount}</h4>
          </div>
        </div>
        <div className="telemetry-card alert">
          <span className="card-icon">⏳</span>
          <div className="card-info">
            <h5>Queue Depth</h5>
            <h4>{queueDepth}</h4>
          </div>
        </div>
        <div className="telemetry-card action-card" onClick={fetchClusterData}>
          <span className="card-icon">{loading ? '⏳' : '🔄'}</span>
          <div className="card-info">
            <h5>Cluster State</h5>
            <p>{loading ? 'Refreshing...' : 'Click to refresh'}</p>
          </div>
        </div>
      </div>

      <div className="cluster-grid-layout">
        {/* Left Side: Topology & Nodes List */}
        <div className="cluster-left-panel">
          {/* Topology Diagram */}
          <div className="dashboard-card">
            <h4>Live Cluster Topology</h4>
            <div className="topology-canvas">
              {topology.nodes.map(node => (
                <div 
                  key={node.id} 
                  className={`topology-node ${node.type} ${node.status}`}
                >
                  <span className="node-icon">
                    {node.type === 'coordinator' ? '👑' : '💻'}
                  </span>
                  <div className="node-popover">
                    <strong>{node.label}</strong>
                    {node.type === 'worker' && (
                      <p>CPU: {node.cpu}% | RAM: {node.memory}% | Jobs: {node.jobs}</p>
                    )}
                  </div>
                </div>
              ))}
              <div className="topology-legend">
                <span><span className="dot coordinator"></span> Hub</span>
                <span><span className="dot healthy"></span> Worker (Healthy)</span>
                <span><span className="dot warning"></span> Warning</span>
                <span><span className="dot offline"></span> Offline</span>
              </div>
            </div>
          </div>

          {/* Workers Details List */}
          <div className="dashboard-card">
            <h4>Worker Nodes Utilization</h4>
            <div className="workers-table-container">
              <table className="cluster-table">
                <thead>
                  <tr>
                    <th>Worker Name</th>
                    <th>Status</th>
                    <th>Capabilities</th>
                    <th>CPU</th>
                    <th>Memory</th>
                    <th>Jobs</th>
                  </tr>
                </thead>
                <tbody>
                  {workers.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="empty-cell">No workers registered.</td>
                    </tr>
                  ) : (
                    workers.map(w => (
                      <tr key={w.worker_id} className={w.status}>
                        <td>
                          <strong>{w.name}</strong>
                          <div className="subtext">ID: {w.worker_id}</div>
                        </td>
                        <td>
                          <span className={`status-pill ${w.status}`}>{w.status}</span>
                        </td>
                        <td>
                          <div className="caps-row">
                            {w.capabilities.map(cap => (
                              <span key={cap} className="cap-tag">{cap}</span>
                            ))}
                          </div>
                        </td>
                        <td>
                          <div className="resource-bar-wrapper">
                            <span>{w.cpu_util}%</span>
                            <div className="bar-bg">
                              <div className="bar-fill" style={{ width: `${w.cpu_util}%`, backgroundColor: w.cpu_util > 80 ? '#ef4444' : '#10b981' }}></div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="resource-bar-wrapper">
                            <span>{w.mem_util}%</span>
                            <div className="bar-bg">
                              <div className="bar-fill" style={{ width: `${w.mem_util}%`, backgroundColor: w.mem_util > 80 ? '#ef4444' : '#10b981' }}></div>
                            </div>
                          </div>
                        </td>
                        <td>{w.active_jobs}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Side: Jobs Queue & Dispatcher Form */}
        <div className="cluster-right-panel">
          {/* Manual Job Dispatcher */}
          <div className="dashboard-card">
            <h4>Manual Task Dispatcher</h4>
            <form onSubmit={handleManualDispatch} className="dispatch-form">
              <div className="form-group">
                <label>Workload Action Type</label>
                <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
                  <option value="predictive">Predictive Analytics (AutoML)</option>
                  <option value="rag_indexing">RAG Ingestion indexing</option>
                  <option value="multi_agent">Multi-Agent query planner</option>
                  <option value="report">Report PDF flow compilation</option>
                  <option value="ai_cleaning">AI dataset cleaning</option>
                  <option value="federated_query">Federated cross-db join</option>
                  <option value="streaming">Streaming aggregation run</option>
                </select>
              </div>

              <div className="form-row-group">
                <div className="form-group">
                  <label>Priority</label>
                  <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                    <option value="low">Low Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="high">High Priority</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Preferred Node Cap</label>
                  <select value={preferredCap} onChange={(e) => setPreferredCap(e.target.value)}>
                    <option value="">Any Worker</option>
                    <option value="predictive">Predictive</option>
                    <option value="rag">RAG</option>
                    <option value="report">Report</option>
                    <option value="streaming">Streaming</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Job Payload parameters (JSON)</label>
                <textarea 
                  rows={2} 
                  value={payloadStr} 
                  onChange={(e) => setPayloadStr(e.target.value)}
                />
              </div>

              <button 
                type="submit" 
                className="btn btn-primary btn-block"
                disabled={dispatchLoading}
              >
                {dispatchLoading ? 'Dispatched...' : 'Submit Job to Cluster 🚀'}
              </button>
            </form>
          </div>

          {/* Cluster Jobs Queue */}
          <div className="dashboard-card">
            <h4>Jobs Execution History & Queue</h4>
            <div className="jobs-table-container">
              <table className="cluster-table">
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>Type</th>
                    <th>Worker</th>
                    <th>Progress</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="empty-cell">No jobs submitted.</td>
                    </tr>
                  ) : (
                    jobs.map(j => (
                      <tr key={j.job_id} className={j.status}>
                        <td>
                          <strong>{j.job_id}</strong>
                          <div className="subtext">Priority: {j.priority}</div>
                        </td>
                        <td>
                          <span className="task-type-badge">{j.task_type}</span>
                        </td>
                        <td>{j.worker_id || 'Pending Scheduler'}</td>
                        <td>
                          <div className="progress-cell">
                            <span>{j.progress}%</span>
                            <div className="progress-bar-bg">
                              <div className="progress-bar-fill" style={{ width: `${j.progress}%` }}></div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className={`status-pill ${j.status}`}>{j.status}</span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClusterDashboard;
