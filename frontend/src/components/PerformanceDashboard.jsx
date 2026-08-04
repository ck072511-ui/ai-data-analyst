import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import PerformanceBenchmarks from './PerformanceBenchmarks';

const PerformanceDashboard = ({ token, showNotification }) => {
  const [perfData, setPerfData] = useState(null);
  const [cacheData, setCacheData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastCheck, setLastCheck] = useState(null);
  const [darkMode, setDarkMode] = useState(true);
  const [patternInput, setPatternInput] = useState('');
  const [invalidating, setInvalidating] = useState(false);
  const [subTab, setSubTab] = useState('telemetry');

  const getHeaders = () => {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return { headers };
  };

  const fetchPerformanceStats = async () => {
    setLoading(true);
    try {
      // Poll both endpoints concurrently
      const [perfRes, cacheRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/performance`, getHeaders()),
        axios.get(`${API_BASE_URL}/cache/stats`, getHeaders())
      ]);
      setPerfData(perfRes.data);
      setCacheData(cacheRes.data);
      setLastCheck(new Date().toLocaleTimeString());
    } catch (error) {
      console.error('Error retrieving performance statistics:', error);
      showNotification('Failed to retrieve performance stats, unauthorized or service down.', 'error');
      setLastCheck(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    if (!window.confirm('Are you sure you want to clear the entire cache database?')) return;
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/cache/clear`, {}, getHeaders());
      showNotification('Cache cleared successfully.', 'success');
      fetchPerformanceStats();
    } catch (error) {
      showNotification('Only administrators can clear cache.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleInvalidatePattern = async (e) => {
    e.preventDefault();
    if (!patternInput.trim()) return;
    setInvalidating(true);
    try {
      await axios.post(`${API_BASE_URL}/cache/invalidate`, { pattern: patternInput }, getHeaders());
      showNotification(`Keys matching pattern "${patternInput}" invalidated.`, 'success');
      setPatternInput('');
      fetchPerformanceStats();
    } catch (error) {
      showNotification('Failed to invalidate pattern. Permission denied.', 'error');
    } finally {
      setInvalidating(false);
    }
  };

  useEffect(() => {
    fetchPerformanceStats();
    const interval = setInterval(fetchPerformanceStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (sec) => {
    return (sec * 1000).toFixed(1) + ' ms';
  };

  const containerStyle = {
    padding: '24px',
    borderRadius: '16px',
    fontFamily: "'Inter', sans-serif",
    transition: 'all 0.3s ease',
    backgroundColor: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    minHeight: '400px',
    boxShadow: darkMode ? '0 10px 30px rgba(0,0,0,0.5)' : '0 10px 30px rgba(0,0,0,0.05)',
    border: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0',
  };

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
    borderBottom: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0',
    paddingBottom: '16px',
  };

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '20px',
    marginBottom: '24px',
  };

  const cardStyle = {
    padding: '20px',
    borderRadius: '12px',
    backgroundColor: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    transition: 'all 0.2s ease',
  };

  return (
    <div style={containerStyle} className="animation-fade-in">
      <div style={headerStyle}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            ⚡ Enterprise Performance Console
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', color: darkMode ? '#94a3b8' : '#64748b' }}>
            Real-time telemetry, cache databases, response compression, and slow database query logs.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              backgroundColor: darkMode ? '#334155' : '#e2e8f0',
              color: darkMode ? '#ffffff' : '#0f172a',
            }}
          >
            {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
          <button 
            onClick={fetchPerformanceStats} 
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Refreshing...' : '🔄 Refresh Stats'}
          </button>
        </div>
      </div>

      {/* Sub-tab selection bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', borderBottom: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0', paddingBottom: '12px' }}>
        <button
          onClick={() => setSubTab('telemetry')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            fontWeight: '600',
            backgroundColor: subTab === 'telemetry' ? '#8b5cf6' : 'transparent',
            color: darkMode ? '#ffffff' : '#0f172a',
          }}
        >
          ⚡ Real-time Telemetry
        </button>
        <button
          onClick={() => setSubTab('benchmarks')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            fontWeight: '600',
            backgroundColor: subTab === 'benchmarks' ? '#8b5cf6' : 'transparent',
            color: darkMode ? '#ffffff' : '#0f172a',
          }}
        >
          📈 Load Benchmarks
        </button>
      </div>

      {subTab === 'benchmarks' ? (
        <PerformanceBenchmarks token={token} showNotification={showNotification} />
      ) : perfData && cacheData ? (
        <>
          {/* General Stats overview */}
          <div style={gridStyle}>
            <div style={cardStyle}>
              <span style={{ fontSize: '0.85rem', color: darkMode ? '#94a3b8' : '#64748b' }}>⚡ Response Latency</span>
              <h2 style={{ fontSize: '2.2rem', margin: '10px 0 0 0', fontWeight: 700, color: '#8b5cf6' }}>
                {perfData.avg_response_time_ms} <span style={{ fontSize: '1.1rem', fontWeight: 500 }}>ms</span>
              </h2>
              <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: darkMode ? '#64748b' : '#94a3b8' }}>
                Rolling average API response time.
              </p>
            </div>
            
            <div style={cardStyle}>
              <span style={{ fontSize: '0.85rem', color: darkMode ? '#94a3b8' : '#64748b' }}>📈 Cache Hit Rate</span>
              <h2 style={{ fontSize: '2.2rem', margin: '10px 0 0 0', fontWeight: 700, color: '#10b981' }}>
                {cacheData.hit_rate}%
              </h2>
              <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: darkMode ? '#64748b' : '#94a3b8' }}>
                Hits: {cacheData.hits} | Misses: {cacheData.misses}
              </p>
            </div>

            <div style={cardStyle}>
              <span style={{ fontSize: '0.85rem', color: darkMode ? '#94a3b8' : '#64748b' }}>💾 Cache Memory Size</span>
              <h2 style={{ fontSize: '2.2rem', margin: '10px 0 0 0', fontWeight: 700, color: '#3b82f6' }}>
                {formatBytes(cacheData.memory_usage_bytes)}
              </h2>
              <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: darkMode ? '#64748b' : '#94a3b8' }}>
                Cached Keys: {cacheData.keys_count}
              </p>
            </div>

            <div style={cardStyle}>
              <span style={{ fontSize: '0.85rem', color: darkMode ? '#94a3b8' : '#64748b' }}>📦 Compression Ratio</span>
              <h2 style={{ fontSize: '2.2rem', margin: '10px 0 0 0', fontWeight: 700, color: '#f59e0b' }}>
                {perfData.compression_ratio}x
              </h2>
              <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: darkMode ? '#64748b' : '#94a3b8' }}>
                Saved: {formatBytes(perfData.total_uncompressed_bytes - perfData.total_compressed_bytes)}
              </p>
            </div>

            <div style={cardStyle}>
              <span style={{ fontSize: '0.85rem', color: darkMode ? '#94a3b8' : '#64748b' }}>🧠 Knowledge Layer</span>
              <h2 style={{ fontSize: '2.2rem', margin: '10px 0 0 0', fontWeight: 700, color: '#ec4899' }}>
                {perfData.kg_entities_count || 0} <span style={{ fontSize: '1.1rem', fontWeight: 500 }}>nodes</span>
              </h2>
              <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: darkMode ? '#64748b' : '#94a3b8' }}>
                Relationships: {perfData.kg_relationships_count || 0} edges
              </p>
            </div>
          </div>

          <div style={gridStyle}>
            {/* Cache settings and status details */}
            <div style={{ ...cardStyle, gridColumn: 'span 2' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>🛠️ Cache Invalidation & Controls</h3>
                <span style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  backgroundColor: cacheData.redis_available ? '#10b981' : '#f59e0b',
                  color: '#ffffff'
                }}>
                  {cacheData.redis_available ? 'REDIS DISTRIBUTED' : 'IN-MEMORY FALLBACK'}
                </span>
              </div>
              <p style={{ fontSize: '0.85rem', color: darkMode ? '#cbd5e1' : '#475569', marginBottom: '16px' }}>
                Clear the entire cache storage or invalidate specific groupings matching glob keys (e.g. <code>dataset:details:*</code>).
              </p>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <button 
                  onClick={handleClearCache}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '8px',
                    backgroundColor: '#ef4444',
                    color: '#ffffff',
                    border: 'none',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                  }}
                >
                  🧹 Clear Entire Cache
                </button>
                <form onSubmit={handleInvalidatePattern} style={{ display: 'flex', flexGrow: 1, gap: '8px' }}>
                  <input 
                    type="text" 
                    placeholder="Key Pattern (e.g. dataset:details:*)" 
                    value={patternInput}
                    onChange={(e) => setPatternInput(e.target.value)}
                    style={{
                      padding: '10px',
                      borderRadius: '8px',
                      border: darkMode ? '1px solid #475569' : '1px solid #cbd5e1',
                      backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                      color: darkMode ? '#ffffff' : '#0f172a',
                      flexGrow: 1,
                    }}
                  />
                  <button 
                    type="submit" 
                    disabled={invalidating}
                    style={{
                      padding: '10px 16px',
                      borderRadius: '8px',
                      backgroundColor: '#3b82f6',
                      color: '#ffffff',
                      border: 'none',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                    }}
                  >
                    {invalidating ? 'Invalidating...' : 'Invalidate Pattern'}
                  </button>
                </form>
              </div>
            </div>
            
            {/* Compression Telemetry Details */}
            <div style={cardStyle}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem', fontWeight: 600 }}>📦 Compression Status</h3>
              <div style={{ fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: darkMode ? '#94a3b8' : '#64748b' }}>Algorithm:</span>
                  <strong style={{ color: '#10b981' }}>GZip (Active)</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: darkMode ? '#94a3b8' : '#64748b' }}>Uncompressed:</span>
                  <strong>{formatBytes(perfData.total_uncompressed_bytes)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: darkMode ? '#94a3b8' : '#64748b' }}>Compressed:</span>
                  <strong>{formatBytes(perfData.total_compressed_bytes)}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Copilot Telemetry details */}
          {perfData.copilot_stats && (
            <div style={{ ...cardStyle, marginTop: '20px' }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.25rem', fontWeight: 600 }}>🤖 Unified Copilot Telemetry</h3>
              <p style={{ fontSize: '0.85rem', color: darkMode ? '#cbd5e1' : '#475569', marginBottom: '16px' }}>
                Request latency, orchestration count, failed pipelines, and module invocation distribution.
              </p>
              
              <div style={gridStyle}>
                <div style={{ ...cardStyle, backgroundColor: darkMode ? '#0f172a' : '#f8fafc' }}>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Total Orchestrations</span>
                  <h3 style={{ fontSize: '1.8rem', margin: '8px 0 0 0', color: '#38bdf8', fontWeight: 700 }}>{perfData.copilot_stats.request_count}</h3>
                </div>
                <div style={{ ...cardStyle, backgroundColor: darkMode ? '#0f172a' : '#f8fafc' }}>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Avg Latency</span>
                  <h3 style={{ fontSize: '1.8rem', margin: '8px 0 0 0', color: '#a855f7', fontWeight: 700 }}>{perfData.copilot_stats.avg_response_time_ms} ms</h3>
                </div>
                <div style={{ ...cardStyle, backgroundColor: darkMode ? '#0f172a' : '#f8fafc' }}>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Failed Orchestrations</span>
                  <h3 style={{ fontSize: '1.8rem', margin: '8px 0 0 0', color: '#f43f5e', fontWeight: 700 }}>{perfData.copilot_stats.failed_orchestrations}</h3>
                </div>
              </div>

              {/* Intents & Tools usage distribution list */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginTop: '15px' }}>
                <div>
                  <h4 style={{ fontSize: '0.95rem', marginBottom: '10px', color: '#38bdf8' }}>🎯 User Intent Distribution</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem' }}>
                    {Object.entries(perfData.copilot_stats.intent_distribution || {}).map(([intent, count]) => (
                      <div key={intent} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: darkMode ? '1px solid #334155' : '1px solid #e2e8f0', paddingBottom: '3px' }}>
                        <span>{intent}</span>
                        <strong>{count} hits</strong>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 style={{ fontSize: '0.95rem', marginBottom: '10px', color: '#a855f7' }}>🛠️ Module Invocation Frequencies</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem' }}>
                    {Object.entries(perfData.copilot_stats.tool_usage_frequency || {}).map(([tool, count]) => (
                      <div key={tool} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: darkMode ? '1px solid #334155' : '1px solid #e2e8f0', paddingBottom: '3px' }}>
                        <span>{tool.replace('_', ' ')}</span>
                        <strong>{count} runs</strong>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Database Slow Queries Tracker */}
          <div style={{ ...cardStyle, marginTop: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.25rem', fontWeight: 600 }}>🐌 Slow Database Query Analyzer (&gt;100ms)</h3>
            <p style={{ fontSize: '0.85rem', color: darkMode ? '#cbd5e1' : '#475569', marginBottom: '16px' }}>
              Database statements captured by cursor execute listeners exceeding threshold duration. Useful for index optimizations.
            </p>
            {perfData.slow_queries && perfData.slow_queries.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: darkMode ? '2px solid #334155' : '2px solid #e2e8f0' }}>
                      <th style={{ padding: '10px' }}>Timestamp</th>
                      <th style={{ padding: '10px' }}>Execution Time</th>
                      <th style={{ padding: '10px' }}>SQL Statement</th>
                    </tr>
                  </thead>
                  <tbody>
                    {perfData.slow_queries.map((q, idx) => (
                      <tr key={idx} style={{ borderBottom: darkMode ? '1px solid #1e293b' : '1px solid #f1f5f9' }}>
                        <td style={{ padding: '10px', color: darkMode ? '#94a3b8' : '#64748b', whiteSpace: 'nowrap' }}>
                          {new Date(q.timestamp * 1000).toLocaleTimeString()}
                        </td>
                        <td style={{ padding: '10px', color: '#ef4444', fontWeight: 'bold' }}>
                          {formatDuration(q.duration_sec)}
                        </td>
                        <td style={{ padding: '10px', fontFamily: 'monospace', color: darkMode ? '#cbd5e1' : '#1e293b' }}>
                          {q.sql}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '24px', textAlign: 'center', backgroundColor: darkMode ? '#0f172a' : '#f8fafc', borderRadius: '8px' }}>
                <p style={{ margin: 0, color: darkMode ? '#94a3b8' : '#64748b' }}>
                  ✅ No slow queries recorded yet. All SQL statements executed within sub-100ms constraints.
                </p>
              </div>
            )}
          </div>
        </>
      ) : (
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <p>Retrieving performance indicators, please wait...</p>
        </div>
      )}
    </div>
  );
};

export default PerformanceDashboard;
