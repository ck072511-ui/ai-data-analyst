import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const FederatedQuery = ({ token, showNotification }) => {
  const [catalog, setCatalog] = useState([]);
  const [queryInput, setQueryInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Query execution outputs
  const [results, setResults] = useState(null);
  const [executionPlan, setExecutionPlan] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [latencyMs, setLatencyMs] = useState(0);

  // History & Statistics state
  const [history, setHistory] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [selectedDatabases, setSelectedDatabases] = useState([]);

  useEffect(() => {
    fetchCatalog();
    fetchHistoryAndStats();
  }, []);

  const fetchCatalog = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/federation/catalog`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCatalog(res.data || []);
      
      // Auto-select unique databases list
      const dbs = [...new Set(res.data.map(item => item.database_name))];
      setSelectedDatabases(dbs);
    } catch (err) {
      console.error(err);
      showNotification('Failed to retrieve unified catalog metadata.', 'error');
    }
  };

  const fetchHistoryAndStats = async () => {
    try {
      const [histRes, statsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/federation/history`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE_URL}/federation/statistics`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setHistory(histRes.data || []);
      setStatistics(statsRes.data || null);
    } catch (err) {
      console.error(err);
    }
  };

  const handleExecuteQuery = async (e) => {
    e.preventDefault();
    if (!queryInput.trim()) return;
    setIsLoading(true);
    setResults(null);
    setExecutionPlan(null);
    setWarnings([]);

    try {
      const res = await axios.post(`${API_BASE_URL}/federation/query`, {
        query: queryInput
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.data.success) {
        setResults({
          columns: res.data.columns,
          rows: res.data.rows
        });
        setExecutionPlan(res.data.execution_plan);
        setWarnings(res.data.warning || []);
        setLatencyMs(res.data.latency_ms);
        showNotification('Federated query executed successfully.', 'success');
      } else {
        showNotification(res.data.error || 'Failed to execute query.', 'error');
        setWarnings(res.data.warning || []);
      }
      fetchHistoryAndStats();
    } catch (err) {
      console.error(err);
      showNotification(err.response?.data?.detail || 'Query execution failed.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleDbSelection = (dbName) => {
    if (selectedDatabases.includes(dbName)) {
      setSelectedDatabases(selectedDatabases.filter(d => d !== dbName));
    } else {
      setSelectedDatabases([...selectedDatabases, dbName]);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '15px' }}>
      
      {/* Header Description */}
      <div className="section-header">
        <h2 style={{ margin: 0 }}>Federated Multi-Database Query Engine</h2>
        <p style={{ margin: '5px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
          Query multiple heterogeneous database engines (PostgreSQL, MySQL, SQLite) using unified natural language prompts completely offline.
        </p>
      </div>

      {/* Main Workspace Layout */}
      <div style={{ display: 'flex', flex: 1, gap: '20px', minHeight: '500px' }}>
        
        {/* Left column: Schema Explorer & Databases Checkbox catalog */}
        <div className="card" style={{ width: '320px', padding: '15px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
          
          <div>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>Target Databases</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {[...new Set(catalog.map(c => c.database_name))].map(db => (
                <label key={db} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedDatabases.includes(db)}
                    onChange={() => toggleDbSelection(db)}
                  />
                  🔹 {db}
                </label>
              ))}
            </div>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <h3 style={{ margin: 0, fontSize: '14px' }}>Unified Schema Catalog</h3>
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {catalog
                .filter(item => selectedDatabases.includes(item.database_name))
                .map((item, idx) => (
                  <div key={idx} style={{ padding: '8px', backgroundColor: '#0f172a', borderRadius: '6px', border: '1px solid #334155' }}>
                    <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8' }}>Table: {item.table_name}</div>
                    <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>Source: {item.database_name} ({item.dialect})</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', paddingLeft: '5px' }}>
                      {item.columns.map(col => (
                        <div key={col.name} style={{ fontSize: '11px', display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#cbd5e1' }}>• {col.name}</span>
                          <span style={{ color: '#64748b' }}>{col.type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          </div>

        </div>

        {/* Right column: NL query input, subqueries cards, results table */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '15px' }}>
          
          {/* Query input card */}
          <div className="card" style={{ padding: '15px' }}>
            <form onSubmit={handleExecuteQuery} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label style={{ fontSize: '13px', fontWeight: '600' }}>Ask a question across database engines:</label>
              <div style={{ display: 'flex', gap: '10px' }}>
                <input
                  type="text"
                  placeholder="e.g. Join orders from order_db SQLite with customer records from user_db Postgres..."
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  className="form-control"
                  style={{ flex: 1 }}
                />
                <button type="submit" className="btn-primary" disabled={isLoading || !queryInput.trim()}>
                  {isLoading ? 'Executing plan...' : 'Run Query'}
                </button>
              </div>
            </form>
          </div>

          {/* Warnings Panel */}
          {warnings.length > 0 && (
            <div className="card" style={{ borderLeft: '4px solid #f59e0b', backgroundColor: '#3b2f0f', padding: '12px', color: '#fcd34d', fontSize: '13px' }}>
              <strong>⚠️ Warnings / Partial Failures recorded:</strong>
              <ul style={{ margin: '5px 0 0 0', paddingLeft: '15px' }}>
                {warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}

          {/* Execution Details & Plan card */}
          {executionPlan && (
            <div className="card" style={{ padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                <h4 style={{ margin: 0, fontSize: '13px', color: '#38bdf8' }}>Distributed Execution Plan</h4>
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>Total Latency: {latencyMs.toFixed(1)} ms</span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '5px' }}>Target SQL Subqueries:</div>
                  {executionPlan.subqueries?.map((sub, i) => (
                    <div key={i} style={{ backgroundColor: '#0f172a', padding: '8px', borderRadius: '4px', border: '1px solid #334155', marginBottom: '5px' }}>
                      <div style={{ fontSize: '10px', color: '#a855f7', fontWeight: 'bold' }}>Alias: {sub.alias} (Conn: {sub.db_connection_id})</div>
                      <pre style={{ margin: '4px 0 0 0', fontSize: '11px', overflowX: 'auto', fontFamily: 'monospace', color: '#cbd5e1' }}>{sub.sql}</pre>
                    </div>
                  ))}
                </div>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '5px' }}>In-memory Pandas Merge operation:</div>
                  <pre style={{ backgroundColor: '#0f172a', padding: '8px', borderRadius: '4px', border: '1px solid #334155', fontSize: '11px', fontFamily: 'monospace', color: '#cbd5e1' }}>
                    {JSON.stringify(executionPlan.merge_operations, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Results table */}
          {results && (
            <div className="card" style={{ flex: 1, padding: '15px', overflowY: 'auto' }}>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px' }}>Merged results query table ({results.rows.length} rows)</h4>
              {results.rows.length === 0 ? (
                <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>Empty dataset results.</div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #334155' }}>
                        {results.columns.map(col => (
                          <th key={col} style={{ padding: '8px', color: '#38bdf8' }}>
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {results.rows.map((row, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                          {row.map((val, cellIdx) => (
                            <td key={cellIdx} style={{ padding: '8px', color: '#e2e8f0' }}>
                              {val === null ? <em style={{ color: '#64748b' }}>null</em> : String(val)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Statistics Summary Panel */}
          {statistics && !results && (
            <div className="card" style={{ padding: '15px' }}>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px' }}>Engine Telemetry Metrics Stats</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', textAlign: 'center' }}>
                <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: '#94a3b8' }}>Total Queries</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{statistics.query_count}</div>
                </div>
                <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: '#94a3b8' }}>Success Rate</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#10b981' }}>
                    {statistics.query_count > 0 ? ((statistics.success_count / statistics.query_count) * 100).toFixed(0) : 0}%
                  </div>
                </div>
                <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: '#94a3b8' }}>Partial Failures</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#f59e0b' }}>{statistics.partial_failure_count}</div>
                </div>
                <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: '#94a3b8' }}>Avg Latency</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                    {statistics.query_count > 0 ? (statistics.total_latency_ms / statistics.query_count).toFixed(0) : 0} ms
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>

      </div>

    </div>
  );
};

export default FederatedQuery;
export { ENTITY_TYPES } from './KnowledgeGraph';
