import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import { Line } from 'react-chartjs-2';

const PerformanceBenchmarks = ({ token, showNotification }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const getHeaders = () => {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return { headers };
  };

  const fetchBenchmarks = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/performance/benchmarks`, getHeaders());
      setData(response.data);
    } catch (error) {
      console.error('Error fetching benchmarks report:', error);
      showNotification('Failed to load performance benchmarks.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBenchmarks();
  }, []);

  if (loading && !data) {
    return <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>Loading benchmarks telemetry...</div>;
  }

  if (!data) {
    return <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>No benchmark data available.</div>;
  }

  const { targets, actuals, history } = data;

  // Prepare chart data for benchmark history
  const chartData = {
    labels: history ? history.map(h => h.date) : [],
    datasets: [
      {
        label: 'P95 Latency (ms)',
        data: history ? history.map(h => h.p95) : [],
        borderColor: '#8b5cf6',
        backgroundColor: 'rgba(139, 92, 246, 0.1)',
        tension: 0.3,
        fill: true,
      },
      {
        label: 'P99 Latency (ms)',
        data: history ? history.map(h => h.p99) : [],
        borderColor: '#f43f5e',
        backgroundColor: 'rgba(244, 63, 94, 0.1)',
        tension: 0.3,
        fill: true,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#94a3b8' }
      }
    },
    scales: {
      x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
      y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }
    }
  };

  const targetVsActual = [
    { name: 'API P95 Latency', target: `<= ${targets.api_p95_latency_ms} ms`, actual: actuals.api_p95_latency_ms ? `${actuals.api_p95_latency_ms} ms` : 'N/A', pass: actuals.api_p95_latency_ms ? actuals.api_p95_latency_ms <= targets.api_p95_latency_ms : true },
    { name: 'API P99 Latency', target: `<= ${targets.api_p99_latency_ms} ms`, actual: actuals.api_p99_latency_ms ? `${actuals.api_p99_latency_ms} ms` : 'N/A', pass: actuals.api_p99_latency_ms ? actuals.api_p99_latency_ms <= targets.api_p99_latency_ms : true },
    { name: 'Dashboard Gen Time', target: `<= ${targets.dashboard_gen_time_s} s`, actual: actuals.dashboard_gen_time_s ? `${actuals.dashboard_gen_time_s} s` : 'N/A', pass: actuals.dashboard_gen_time_s ? actuals.dashboard_gen_time_s <= targets.dashboard_gen_time_s : true },
    { name: 'Dataset Upload Time', target: `<= ${targets.dataset_upload_time_s} s`, actual: actuals.dataset_upload_time_s ? `${actuals.dataset_upload_time_s} s` : 'N/A', pass: actuals.dataset_upload_time_s ? actuals.dataset_upload_time_s <= targets.dataset_upload_time_s : true },
    { name: 'Background Task Time', target: `<= ${targets.task_completion_time_s} s`, actual: actuals.task_completion_time_s ? `${actuals.task_completion_time_s} s` : 'N/A', pass: actuals.task_completion_time_s ? actuals.task_completion_time_s <= targets.task_completion_time_s : true },
    { name: 'Cache Hit Rate', target: `>= ${targets.cache_hit_percentage}%`, actual: actuals.cache_hit_percentage ? `${actuals.cache_hit_percentage}%` : 'N/A', pass: actuals.cache_hit_percentage ? actuals.cache_hit_percentage >= targets.cache_hit_percentage : true },
    { name: 'Request Error Rate', target: `<= ${targets.error_rate_threshold_pct}%`, actual: actuals.error_rate_pct !== undefined ? `${actuals.error_rate_pct}%` : 'N/A', pass: actuals.error_rate_pct !== undefined ? actuals.error_rate_pct <= targets.error_rate_threshold_pct : true }
  ];

  return (
    <div style={{ padding: '8px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#8b5cf6' }}>📈 Load Testing Targets & Actual Run Benchmarks</h3>
        <button 
          onClick={fetchBenchmarks} 
          disabled={loading}
          style={{
            padding: '6px 12px',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: '#2563eb',
            color: '#fff',
            fontWeight: '600',
            fontSize: '0.85rem'
          }}
        >
          {loading ? 'Refreshing...' : '🔄 Sync Run Results'}
        </button>
      </div>

      {/* Grid of basic parameters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#1e293b', border: '1px solid #334155' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Throughput (RPS)</span>
          <h3 style={{ margin: '8px 0 0 0', fontSize: '1.8rem', color: '#3b82f6' }}>{actuals.rps || '0.0'} req/s</h3>
        </div>
        <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#1e293b', border: '1px solid #334155' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>CPU Usage</span>
          <h3 style={{ margin: '8px 0 0 0', fontSize: '1.8rem', color: '#eab308' }}>{data.cpu_usage_pct || '0.0'}%</h3>
        </div>
        <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#1e293b', border: '1px solid #334155' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Memory Usage</span>
          <h3 style={{ margin: '8px 0 0 0', fontSize: '1.8rem', color: '#10b981' }}>{data.memory_usage_pct || '0.0'}%</h3>
        </div>
      </div>

      {/* Comparison table */}
      <div style={{ marginBottom: '24px', backgroundColor: '#1e293b', borderRadius: '8px', border: '1px solid #334155', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #334155' }}>
              <th style={{ padding: '12px 16px', color: '#94a3b8' }}>Metric Indicator</th>
              <th style={{ padding: '12px 16px', color: '#94a3b8' }}>SLA Target</th>
              <th style={{ padding: '12px 16px', color: '#94a3b8' }}>Actual Benchmark</th>
              <th style={{ padding: '12px 16px', color: '#94a3b8' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {targetVsActual.map((item, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '12px 16px', fontWeight: '500' }}>{item.name}</td>
                <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{item.target}</td>
                <td style={{ padding: '12px 16px', fontWeight: '600', color: item.pass ? '#10b981' : '#f43f5e' }}>{item.actual}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: '700',
                    backgroundColor: item.pass ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 148, 0.1)',
                    color: item.pass ? '#10b981' : '#f43f5e'
                  }}>
                    {item.pass ? 'PASS' : 'FAIL'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Latency History Chart */}
      <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#1e293b', border: '1px solid #334155', height: '280px' }}>
        <h4 style={{ margin: '0 0 16px 0', fontSize: '0.95rem', color: '#94a3b8' }}>Historical Latency Trend (ms)</h4>
        {history && history.length > 0 ? (
          <div style={{ height: '220px' }}>
            <Line data={chartData} options={chartOptions} />
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px', color: '#64748b' }}>No run history logs found.</div>
        )}
      </div>
    </div>
  );
};

export default PerformanceBenchmarks;
