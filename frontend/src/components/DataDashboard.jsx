import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import { Bar, Line, Pie, Scatter, Doughnut } from 'react-chartjs-2';

const DataDashboard = ({ token, datasets, showNotification, initialDatasetId }) => {
  const [selectedDatasetId, setSelectedDatasetId] = useState(initialDatasetId || '');
  const [loading, setLoading] = useState(false);
  const [dashboard, setDashboard] = useState(null);
  
  // Natural Language Dashboard query state
  const [nlQuestion, setNlQuestion] = useState('');
  const [generating, setGenerating] = useState(false);
  
  // Dashboard history
  const [history, setHistory] = useState([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState(null);
  const [showHistory, setShowHistory] = useState(false);

  // Widget interactivity states
  const [legendVisibleMap, setLegendVisibleMap] = useState({}); // chartId -> bool
  const [fullscreenChartId, setFullscreenChartId] = useState(null); // chartId
  const [zoomRangeMap, setZoomRangeMap] = useState({}); // chartId -> {start: 0, end: 100}

  // Refs for chart elements to enable PNG exports
  const chartRefs = useRef({});

  // Fetch history and default dashboard on mount/selection
  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    if (datasets && datasets.length > 0 && !selectedDatasetId) {
      setSelectedDatasetId(datasets[0].id);
    }
  }, [datasets]);

  useEffect(() => {
    if (selectedDatasetId && !selectedHistoryId) {
      fetchDefaultDashboard(selectedDatasetId);
    }
  }, [selectedDatasetId, selectedHistoryId]);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(response.data);
    } catch (error) {
      console.error("Failed to load dashboard history", error);
    }
  };

  const fetchDefaultDashboard = async (datasetId) => {
    setLoading(true);
    setDashboard(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/${datasetId}/dashboard`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDashboard(response.data);
      // Reset interactive maps
      setLegendVisibleMap({});
      setZoomRangeMap({});
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to fetch default dashboard', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadDashboardFromHistory = async (dashId) => {
    setLoading(true);
    setDashboard(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard/${dashId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const dash = response.data;
      setDashboard(dash.widgets);
      setSelectedHistoryId(dash.id);
      if (dash.widgets?.metadata?.dataset_id) {
        setSelectedDatasetId(dash.widgets.metadata.dataset_id);
      }
      setLegendVisibleMap({});
      setZoomRangeMap({});
    } catch (error) {
      showNotification('Failed to load dashboard from history', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDashboard = async () => {
    if (!nlQuestion.trim()) return;
    setGenerating(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/dashboard/generate`,
        {
          dataset_id: selectedDatasetId,
          question: nlQuestion
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      const newDash = response.data;
      setDashboard(newDash.widgets);
      setSelectedHistoryId(newDash.id);
      showNotification('NL Dashboard generated successfully!', 'success');
      setNlQuestion('');
      fetchHistory(); // Refresh history log list
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to generate dashboard', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleResetToDefault = () => {
    setSelectedHistoryId(null);
    if (selectedDatasetId) {
      fetchDefaultDashboard(selectedDatasetId);
    }
  };

  // Helper: Export Chart as PNG
  const exportChartPng = (chartId, title) => {
    const chartInstance = chartRefs.current[chartId];
    const canvas = chartInstance?.canvas;
    if (canvas) {
      const url = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.download = `${title.toLowerCase().replace(/[^a-z0-9]/g, '_')}.png`;
      link.href = url;
      link.click();
      showNotification('Chart exported as PNG!', 'success');
    } else {
      showNotification('Failed to export chart: reference not found', 'error');
    }
  };

  // Helper: Zoom Controls
  const toggleZoom = (chartId, direction, totalLen) => {
    const currRange = zoomRangeMap[chartId] || { start: 0, end: totalLen };
    let { start, end } = currRange;
    const size = end - start;

    if (direction === 'in') {
      // Focus on the middle 50%
      const offset = Math.max(1, Math.floor(size * 0.25));
      start = Math.min(totalLen - 2, start + offset);
      end = Math.max(start + 2, end - offset);
    } else if (direction === 'out') {
      // Reset zoom
      start = 0;
      end = totalLen;
    } else if (direction === 'left') {
      // Pan left
      const offset = Math.max(1, Math.floor(size * 0.2));
      start = Math.max(0, start - offset);
      end = Math.max(start + 2, end - offset);
    } else if (direction === 'right') {
      // Pan right
      const offset = Math.max(1, Math.floor(size * 0.2));
      end = Math.min(totalLen, end + offset);
      start = Math.min(end - 2, start + offset);
    }

    setZoomRangeMap(prev => ({
      ...prev,
      [chartId]: { start, end }
    }));
  };

  if (!datasets || datasets.length === 0) {
    return (
      <div className="dashboard-empty-state">
        <span className="empty-icon">📊</span>
        <h3>No Datasets Available</h3>
        <p>Please upload a CSV, Excel, or JSON dataset in the sidebar first to enable natural language dashboards.</p>
      </div>
    );
  }

  // Get responsive layout class based on number of charts
  const getLayoutClass = (numCharts) => {
    if (numCharts <= 1) return "layout-single";
    if (numCharts <= 4) return "layout-grid-2";
    return "layout-grid-multi";
  };

  return (
    <div className="dashboard-main-container animation-fade-in">
      
      {/* Upper Controls Panel */}
      <div className="dashboard-controls-card">
        <div className="controls-row">
          <div className="selector-group">
            <label htmlFor="dashboard-dataset-select">Dataset Context:</label>
            <select
              id="dashboard-dataset-select"
              value={selectedDatasetId}
              onChange={(e) => {
                setSelectedDatasetId(e.target.value);
                setSelectedHistoryId(null);
              }}
            >
              {datasets.map(ds => (
                <option key={ds.id} value={ds.id}>
                  {ds.filename}
                </option>
              ))}
            </select>
          </div>
          
          <button className="history-toggle-btn" onClick={() => setShowHistory(!showHistory)}>
            📂 {showHistory ? "Hide History" : "Show Saved Dashboards"} ({history.length})
          </button>
        </div>

        {/* Natural Language dashboard input */}
        <div className="nl-generator-row">
          <input
            type="text"
            placeholder="Ask AI to generate a specific dashboard (e.g. 'average salary by age group' or 'sales count by category')..."
            value={nlQuestion}
            onChange={(e) => setNlQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleGenerateDashboard()}
            disabled={generating}
          />
          <button onClick={handleGenerateDashboard} disabled={generating || !nlQuestion.trim()}>
            {generating ? "Generating..." : "⚡ Generate NL Chart"}
          </button>
          {selectedHistoryId && (
            <button className="reset-default-btn" onClick={handleResetToDefault}>
              Reset to Default Layout
            </button>
          )}
        </div>
      </div>

      <div className="dashboard-content-layout">
        {/* Left Saved History Panel */}
        {showHistory && (
          <aside className="dashboard-history-sidebar">
            <h4>📁 Saved History Log</h4>
            <div className="history-list">
              {history.length === 0 ? (
                <p className="empty-history-text">No saved dashboards found. Generate an NL chart to save them here.</p>
              ) : (
                history.map(dash => (
                  <div
                    key={dash.id}
                    className={`history-item-card ${selectedHistoryId === dash.id ? 'active' : ''}`}
                    onClick={() => loadDashboardFromHistory(dash.id)}
                  >
                    <h5>{dash.name}</h5>
                    <span className="time-lbl">
                      📅 {new Date(dash.created_at).toLocaleString()}
                    </span>
                    <span className="details-lbl">
                      📊 {dash.widgets?.charts?.length || 0} charts • {dash.widgets?.kpi_cards?.length || 0} KPIs
                    </span>
                  </div>
                ))
              )}
            </div>
          </aside>
        )}

        {/* Dashboard Panels Grid */}
        <div className="dashboard-widgets-panel">
          {loading ? (
            <div className="dashboard-skeleton-layout">
              <div className="skeleton-kpis-grid">
                <div className="skeleton-card mini"></div>
                <div className="skeleton-card mini"></div>
                <div className="skeleton-card mini"></div>
                <div className="skeleton-card mini"></div>
              </div>
              <div className="skeleton-chart-card"></div>
              <div className="skeleton-chart-card"></div>
            </div>
          ) : dashboard ? (
            <div className="dashboard-grid-flow">
              
              {/* Dashboard Metadata Row */}
              <div className="dashboard-metadata-card">
                <div className="meta-left">
                  <h3>🎯 {selectedHistoryId ? "Saved Layout" : "Default Auto-Generated Dashboard"}</h3>
                  <span className="ds-lbl">Dataset: <strong>{dashboard.metadata?.dataset_name}</strong></span>
                </div>
                <div className="meta-stats-grid">
                  <div className="stat-pill">Charts: <strong>{dashboard.metadata?.number_of_charts || 0}</strong></div>
                  <div className="stat-pill">KPIs: <strong>{dashboard.metadata?.number_of_kpis || 0}</strong></div>
                  <div className="stat-pill">Records: <strong>{dashboard.metadata?.number_of_records?.toLocaleString() || 0}</strong></div>
                  <div className="stat-pill">Generated: <strong>{new Date(dashboard.metadata?.generated_time).toLocaleTimeString()}</strong></div>
                </div>
              </div>

              {/* FEATURE 3: KPI Cards Grid */}
              {dashboard.kpi_cards && dashboard.kpi_cards.length > 0 && (
                <div className="dashboard-kpis-grid">
                  {dashboard.kpi_cards.map((kpi, idx) => (
                    <div className="kpi-scorecard-card" key={idx}>
                      <div className="kpi-header">
                        <span className="kpi-col-name">{kpi.column}</span>
                        <span className="kpi-badge">{kpi.is_numeric ? "NUMERIC" : "TEXT"}</span>
                      </div>
                      <div className="kpi-values-flow">
                        {kpi.is_numeric ? (
                          <>
                            <div className="val-main">
                              <span className="lbl">Average</span>
                              <span className="val">{kpi.average?.toLocaleString() ?? "N/A"}</span>
                            </div>
                            <div className="val-subs">
                              <div className="sub-item">Max: <span>{kpi.max?.toLocaleString() ?? "N/A"}</span></div>
                              <div className="sub-item">Min: <span>{kpi.min?.toLocaleString() ?? "N/A"}</span></div>
                              <div className="sub-item">Median: <span>{kpi.median?.toLocaleString() ?? "N/A"}</span></div>
                              <div className="sub-item">Sum: <span>{kpi.total?.toLocaleString() ?? "N/A"}</span></div>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="val-main">
                              <span className="lbl">Unique Values</span>
                              <span className="val">{kpi.unique_values ?? "N/A"}</span>
                            </div>
                            <div className="val-subs">
                              <div className="sub-item">Max Value: <span title={kpi.max}>{kpi.max ?? "N/A"}</span></div>
                              <div className="sub-item">Min Value: <span title={kpi.min}>{kpi.min ?? "N/A"}</span></div>
                            </div>
                          </>
                        )}
                      </div>
                      <div className="kpi-footer-stats">
                        <span>Missing Rate: {kpi.missing_pct}%</span>
                        <span>Total Rows: {kpi.count?.toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* FEATURE 5 & 2: Interactive Charts Panels */}
              {dashboard.charts && dashboard.charts.length > 0 ? (
                <div className={`dashboard-charts-layout-container ${getLayoutClass(dashboard.charts.length)}`}>
                  {dashboard.charts.map((chart) => {
                    const isLegendVisible = legendVisibleMap[chart.id] !== false; // Default visible
                    const labels = chart.chart_data?.labels || [];
                    const datasetsArr = chart.chart_data?.datasets || [];
                    const totalLen = labels.length;
                    
                    // Retrieve active Zoom range
                    const zoomRange = zoomRangeMap[chart.id] || { start: 0, end: totalLen };
                    const isZoomed = zoomRange.start > 0 || zoomRange.end < totalLen;

                    // Slice data based on zoom bounds (only for category/line/bar charts, not scatter)
                    let slicedLabels = labels;
                    let slicedDatasets = datasetsArr;

                    if (chart.chart_type !== 'scatter' && totalLen > 0) {
                      slicedLabels = labels.slice(zoomRange.start, zoomRange.end);
                      slicedDatasets = datasetsArr.map(d => ({
                        ...d,
                        data: d.data.slice(zoomRange.start, zoomRange.end)
                      }));
                    }

                    // Format chart data payload
                    const renderData = {
                      labels: slicedLabels,
                      datasets: slicedDatasets
                    };

                    const baseOptions = {
                      responsive: true,
                      maintainAspectRatio: false,
                      indexAxis: chart.chart_type === 'horizontal_bar' ? 'y' : 'x',
                      plugins: {
                        legend: {
                          display: isLegendVisible,
                          position: 'bottom',
                          labels: { color: '#475569', font: { family: 'Outfit, sans-serif', size: 11 } }
                        },
                        title: { display: false }
                      },
                      scales: !['pie', 'donut'].includes(chart.chart_type) ? {
                        y: {
                          ticks: { color: '#64748b', font: { family: 'Outfit, sans-serif' } },
                          grid: { color: '#f1f5f9' }
                        },
                        x: {
                          ticks: { color: '#64748b', font: { family: 'Outfit, sans-serif' } },
                          grid: { display: false }
                        }
                      } : {}
                    };

                    return (
                      <div className="dashboard-chart-card-box" key={chart.id}>
                        <div className="chart-card-header-bar">
                          <h5>{chart.title}</h5>
                          
                          {/* FEATURE 4: Interactivity Toolbar */}
                          <div className="chart-toolbar-actions">
                            
                            {/* Zoom & Pan Controls */}
                            {chart.chart_type !== 'scatter' && totalLen > 5 && (
                              <div className="zoom-pan-controls">
                                <button title="Pan Left" onClick={() => toggleZoom(chart.id, 'left', totalLen)} disabled={!isZoomed}>◀</button>
                                <button title="Zoom In" onClick={() => toggleZoom(chart.id, 'in', totalLen)}>🔍+</button>
                                <button title="Zoom Out" onClick={() => toggleZoom(chart.id, 'out', totalLen)} disabled={!isZoomed}>🔍-</button>
                                <button title="Pan Right" onClick={() => toggleZoom(chart.id, 'right', totalLen)} disabled={!isZoomed}>▶</button>
                              </div>
                            )}

                            <button
                              className="action-btn"
                              title="Toggle Legend"
                              onClick={() => setLegendVisibleMap(prev => ({ ...prev, [chart.id]: !isLegendVisible }))}
                            >
                              💡 Legend
                            </button>
                            <button
                              className="action-btn"
                              title="Fullscreen Overlay"
                              onClick={() => setFullscreenChartId(chart.id)}
                            >
                              🖥️ Max
                            </button>
                            <button
                              className="action-btn secondary"
                              title="Export PNG"
                              onClick={() => exportChartPng(chart.id, chart.title)}
                            >
                              💾 Export
                            </button>
                          </div>
                        </div>

                        {/* Chart Render Area */}
                        <div className="chart-render-wrapper">
                          {chart.chart_type === 'line' && (
                            <Line
                              data={renderData}
                              options={baseOptions}
                              ref={(el) => (chartRefs.current[chart.id] = el)}
                            />
                          )}
                          {(chart.chart_type === 'bar' || chart.chart_type === 'horizontal_bar' || chart.chart_type === 'histogram') && (
                            <Bar
                              data={renderData}
                              options={baseOptions}
                              ref={(el) => (chartRefs.current[chart.id] = el)}
                            />
                          )}
                          {chart.chart_type === 'pie' && (
                            <Pie
                              data={renderData}
                              options={baseOptions}
                              ref={(el) => (chartRefs.current[chart.id] = el)}
                            />
                          )}
                          {chart.chart_type === 'donut' && (
                            <Doughnut
                              data={renderData}
                              options={baseOptions}
                              ref={(el) => (chartRefs.current[chart.id] = el)}
                            />
                          )}
                          {chart.chart_type === 'scatter' && (
                            <Scatter
                              data={renderData}
                              options={baseOptions}
                              ref={(el) => (chartRefs.current[chart.id] = el)}
                            />
                          )}
                        </div>

                        {/* SQL Description & Rationale text if custom NL query generated */}
                        {chart.explanation && (
                          <div className="chart-metadata-desc">
                            <strong>SQL Query Executed:</strong>
                            <pre className="query-sql-code"><code>{chart.sql}</code></pre>
                            <strong>Insight Rationale:</strong>
                            <p>{chart.explanation}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <span className="empty-icon">📊</span>
                  <h3>No Charts Compiled</h3>
                  <p>We could not automatically compile visualization charts for this dataset schema properties. Generate an NL chart above.</p>
                </div>
              )}

            </div>
          ) : (
            <div className="dashboard-empty-state">
              <span className="empty-icon">📈</span>
              <h3>Select Dataset to Generate Dashboard</h3>
              <p>Please select a flat dataset or connected database in the top selector to display automatic widgets.</p>
            </div>
          )}
        </div>
      </div>

      {/* FEATURE 4: Fullscreen Overlay Dialog */}
      {fullscreenChartId && (() => {
        const chart = dashboard?.charts?.find(c => c.id === fullscreenChartId);
        if (!chart) return null;
        
        const isLegendVisible = legendVisibleMap[chart.id] !== false;
        const labels = chart.chart_data?.labels || [];
        const datasetsArr = chart.chart_data?.datasets || [];
        const totalLen = labels.length;
        const zoomRange = zoomRangeMap[chart.id] || { start: 0, end: totalLen };

        let slicedLabels = labels;
        let slicedDatasets = datasetsArr;
        if (chart.chart_type !== 'scatter' && totalLen > 0) {
          slicedLabels = labels.slice(zoomRange.start, zoomRange.end);
          slicedDatasets = datasetsArr.map(d => ({
            ...d,
            data: d.data.slice(zoomRange.start, zoomRange.end)
          }));
        }

        const renderData = { labels: slicedLabels, datasets: slicedDatasets };
        const overlayOptions = {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: chart.chart_type === 'horizontal_bar' ? 'y' : 'x',
          plugins: {
            legend: {
              display: isLegendVisible,
              position: 'bottom',
              labels: { color: '#334155', font: { family: 'Outfit, sans-serif', size: 14 } }
            }
          },
          scales: !['pie', 'donut'].includes(chart.chart_type) ? {
            y: { ticks: { font: { size: 14 } } },
            x: { ticks: { font: { size: 14 } } }
          } : {}
        };

        return (
          <div className="fullscreen-chart-modal-overlay animation-fade-in" onClick={() => setFullscreenChartId(null)}>
            <div className="modal-content-container" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header-bar">
                <h4>{chart.title} (Fullscreen Preview)</h4>
                <button className="close-overlay-btn" onClick={() => setFullscreenChartId(null)}>✖ Close</button>
              </div>
              <div className="modal-chart-render-wrapper">
                {chart.chart_type === 'line' && <Line data={renderData} options={overlayOptions} />}
                {(chart.chart_type === 'bar' || chart.chart_type === 'horizontal_bar' || chart.chart_type === 'histogram') && <Bar data={renderData} options={overlayOptions} />}
                {chart.chart_type === 'pie' && <Pie data={renderData} options={overlayOptions} />}
                {chart.chart_type === 'donut' && <Doughnut data={renderData} options={overlayOptions} />}
                {chart.chart_type === 'scatter' && <Scatter data={renderData} options={overlayOptions} />}
              </div>
            </div>
          </div>
        );
      })()}

    </div>
  );
};

export default DataDashboard;
