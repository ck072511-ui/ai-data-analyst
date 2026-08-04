import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import { Doughnut, Bar } from 'react-chartjs-2';

const DataProfiling = ({ token, datasets, showNotification, initialDatasetId }) => {
  const [selectedDatasetId, setSelectedDatasetId] = useState(initialDatasetId || '');
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState(null);
  
  // Accordion active sections state
  const [expandedSections, setExpandedSections] = useState({
    missing: true,
    duplicates: false,
    outliers: false,
    formats: false,
    cardinality: false
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Auto-select first dataset on load if available
  useEffect(() => {
    if (datasets && datasets.length > 0 && !selectedDatasetId) {
      setSelectedDatasetId(datasets[0].id);
    }
  }, [datasets, selectedDatasetId]);

  // Fetch profile when dataset selection changes
  useEffect(() => {
    if (selectedDatasetId) {
      fetchProfile(selectedDatasetId);
    } else {
      setProfile(null);
    }
  }, [selectedDatasetId]);

  const fetchProfile = async (id) => {
    setLoading(true);
    setProfile(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/${id}/profile`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProfile(response.data);
    } catch (error) {
      if (showNotification) {
        showNotification(error.response?.data?.detail || 'Failed to load dataset profile', 'error');
      } else {
        alert(error.response?.data?.detail || 'Failed to load dataset profile');
      }
    } finally {
      setLoading(false);
    }
  };

  if (!datasets || datasets.length === 0) {
    return (
      <div className="profiling-empty-state">
        <span className="empty-icon">📊</span>
        <h3>No Datasets Available for Profiling</h3>
        <p>Upload a CSV, Excel, or JSON dataset in the sidebar first to automatically generate a data profile report.</p>
      </div>
    );
  }

  // Helper to get score color
  const getScoreColorClass = (score) => {
    if (score >= 85) return 'excellent';
    if (score >= 70) return 'good';
    if (score >= 50) return 'average';
    return 'poor';
  };

  const colTypeCounts = profile ? {
    numerical: profile.column_types?.numerical?.length || 0,
    categorical: profile.column_types?.categorical?.length || 0,
    date: profile.column_types?.date?.length || 0,
    boolean: profile.column_types?.boolean?.length || 0,
    text: profile.column_types?.text?.length || 0
  } : {};

  // Doughnut Chart Data
  const doughnutData = {
    labels: ['Numerical', 'Categorical', 'Date', 'Boolean', 'Text'],
    datasets: [
      {
        data: profile ? [
          colTypeCounts.numerical,
          colTypeCounts.categorical,
          colTypeCounts.date,
          colTypeCounts.boolean,
          colTypeCounts.text
        ] : [0, 0, 0, 0, 0],
        backgroundColor: [
          'rgba(37, 99, 235, 0.75)',   // blue
          'rgba(124, 58, 237, 0.75)',  // purple
          'rgba(249, 115, 22, 0.75)',  // orange
          'rgba(16, 185, 129, 0.75)',  // green
          'rgba(236, 72, 153, 0.75)'   // pink
        ],
        borderColor: [
          'rgb(37, 99, 235)',
          'rgb(124, 58, 237)',
          'rgb(249, 115, 22)',
          'rgb(16, 185, 129)',
          'rgb(236, 72, 153)'
        ],
        borderWidth: 1.5,
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: '#475569',
          font: { family: 'Outfit, sans-serif', size: 12, weight: '500' }
        }
      }
    }
  };

  // Bar Chart Data (Missing Values)
  const missingByCol = profile?.quality_report?.missing_values?.by_column || {};
  const missingCols = Object.keys(missingByCol);
  const missingCounts = Object.values(missingByCol);

  const barData = {
    labels: missingCols.length > 0 ? missingCols : ['No Missing Values'],
    datasets: [
      {
        label: 'Missing Count',
        data: missingCols.length > 0 ? missingCounts : [0],
        backgroundColor: 'rgba(239, 68, 68, 0.65)',
        borderColor: 'rgb(239, 68, 68)',
        borderWidth: 1.5,
      },
    ],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { color: '#64748b', font: { family: 'Outfit, sans-serif' } }
      },
      x: {
        ticks: { color: '#64748b', font: { family: 'Outfit, sans-serif' } }
      }
    }
  };

  // Correlation cell coloring helper
  const getCorrelationColor = (val) => {
    if (val === 1) return { background: 'rgba(37, 99, 235, 0.2)', color: '#1e3a8a', fontWeight: 'bold' };
    if (Math.abs(val) > 0.85) {
      return val > 0 
        ? { background: 'rgba(37, 99, 235, 0.85)', color: '#ffffff', fontWeight: '700' }
        : { background: 'rgba(239, 68, 68, 0.85)', color: '#ffffff', fontWeight: '700' };
    }
    if (Math.abs(val) > 0.5) {
      return val > 0 
        ? { background: 'rgba(37, 99, 235, 0.4)', color: '#1e3a8a' }
        : { background: 'rgba(239, 68, 68, 0.4)', color: '#7f1d1d' };
    }
    if (Math.abs(val) > 0.1) {
      return val > 0 
        ? { background: 'rgba(37, 99, 235, 0.1)', color: '#2563eb' }
        : { background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' };
    }
    return { background: '#f8fafc', color: '#64748b' };
  };

  return (
    <div className="profiling-container">
      {/* Selection Row */}
      <div className="profiling-selector-row">
        <div className="selector-text">
          <h3>📊 Enterprise Data Quality Engine</h3>
          <p>Examine statistical diagnostics, format inconsistencies, duplicate samples, outliers, and highly correlated columns.</p>
        </div>
        <div className="selector-wrapper">
          <label>Select Dataset:</label>
          <select 
            value={selectedDatasetId} 
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            disabled={loading}
          >
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>
                {ds.filename} ({ds.row_count} rows)
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div className="profiling-loading-state">
          <span className="profiling-spinner">⏳</span>
          <h4>Analyzing dataset quality metrics...</h4>
          <p>Running duplicate row checking, outlier IQR/Z-score calculations, date consistency pattern analysis, email/phone format verifications, and numeric stats...</p>
        </div>
      )}

      {!loading && profile && (
        <div className="profiling-report-layout animation-fade-in">
          
          {/* Top Score Cards */}
          <div className="profiling-dashboard-grid">
            
            {/* Score Ring Card */}
            <div className="dashboard-card score-card-wrapper">
              <h4>Data Quality Scorecard</h4>
              <div className="scorecard-body">
                <div className={`circular-score-ring ${getScoreColorClass(profile.quality_score)}`}>
                  <div className="score-value">{profile.quality_score}<span>/100</span></div>
                </div>
                <div className="score-rating-text">
                  <span className={`rating-badge ${getScoreColorClass(profile.quality_score)}`}>
                    {profile.quality_rating}
                  </span>
                  <p>Quality score calculated based on null indexes, duplicates, date formats, outliers, invalid emails, and phone counts.</p>
                </div>
              </div>
            </div>

            {/* General Profile Card */}
            <div className="dashboard-card metadata-card-wrapper">
              <h4>Dataset Profile Summary</h4>
              <div className="meta-stats-grid">
                <div className="meta-stat-item">
                  <span className="icon">📁</span>
                  <div className="info">
                    <h5>Dataset Name</h5>
                    <p title={profile.dataset_name}>{profile.dataset_name}</p>
                  </div>
                </div>
                <div className="meta-stat-item">
                  <span className="icon">🔢</span>
                  <div className="info">
                    <h5>Rows Count</h5>
                    <p>{profile.row_count.toLocaleString()}</p>
                  </div>
                </div>
                <div className="meta-stat-item">
                  <span className="icon">📊</span>
                  <div className="info">
                    <h5>Columns Count</h5>
                    <p>{profile.col_count}</p>
                  </div>
                </div>
                <div className="meta-stat-item">
                  <span className="icon">💾</span>
                  <div className="info">
                    <h5>Memory Footprint</h5>
                    <p>{profile.memory_usage}</p>
                  </div>
                </div>
                <div className="meta-stat-item">
                  <span className="icon">📂</span>
                  <div className="info">
                    <h5>Disk File Size</h5>
                    <p>{profile.file_size}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Visualizations Grid */}
          <div className="profiling-charts-grid">
            <div className="chart-card">
              <h4>Column Types Distribution</h4>
              <div className="chart-container-profiling">
                <Doughnut data={doughnutData} options={doughnutOptions} />
              </div>
              <div className="chart-types-summary">
                {Object.entries(profile.column_types).map(([type, list]) => (
                  list && list.length > 0 && (
                    <div key={type} className="type-summary-item">
                      <span className={`type-dot ${type}`}></span>
                      <span className="type-name">{type.toUpperCase()} ({list.length})</span>
                    </div>
                  )
                ))}
              </div>
            </div>

            <div className="chart-card">
              <h4>Missing Values rate per Column</h4>
              <div className="chart-container-profiling">
                <Bar data={barData} options={barOptions} />
              </div>
              <p className="chart-sub-note">
                {missingCols.length > 0 
                  ? `Detected missing values in ${missingCols.length} column(s).` 
                  : 'Great! No missing values detected in this dataset.'}
              </p>
            </div>
          </div>

          {/* SPRINT 2.2 Numerical Statistics Table */}
          {profile.numerical_statistics && Object.keys(profile.numerical_statistics).length > 0 && (
            <div className="dashboard-card numeric-stats-card">
              <h4>🔢 Detailed Numerical Statistics</h4>
              <div className="responsive-table-wrapper">
                <table className="stats-table">
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Mean</th>
                      <th>Median</th>
                      <th>Mode</th>
                      <th>Min</th>
                      <th>Max</th>
                      <th>Std Dev</th>
                      <th>Variance</th>
                      <th>Q1 (25%)</th>
                      <th>Q3 (75%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(profile.numerical_statistics).map(([colName, stats]) => (
                      <tr key={colName}>
                        <td className="stat-column-name"><strong>{colName}</strong></td>
                        <td>{stats.mean !== null ? stats.mean.toLocaleString() : 'N/A'}</td>
                        <td>{stats.median !== null ? stats.median.toLocaleString() : 'N/A'}</td>
                        <td>{stats.mode !== null ? stats.mode.toLocaleString() : 'N/A'}</td>
                        <td className="min-stat">{stats.min !== null ? stats.min.toLocaleString() : 'N/A'}</td>
                        <td className="max-stat">{stats.max !== null ? stats.max.toLocaleString() : 'N/A'}</td>
                        <td>{stats.std_dev !== null ? stats.std_dev.toLocaleString() : 'N/A'}</td>
                        <td>{stats.variance !== null ? stats.variance.toLocaleString() : 'N/A'}</td>
                        <td>{stats.quartiles?.q1 !== null ? stats.quartiles.q1.toLocaleString() : 'N/A'}</td>
                        <td>{stats.quartiles?.q3 !== null ? stats.quartiles.q3.toLocaleString() : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* SPRINT 2.2 Correlation Analysis Card */}
          {profile.correlation_analysis && profile.correlation_analysis.correlation_matrix?.columns?.length >= 2 && (
            <div className="dashboard-card correlation-card">
              <h4>🔗 Pearson Correlation Matrix</h4>
              <p className="card-sub-info">Values close to +1 represent strong positive correlation; values near -1 represent strong negative correlation.</p>
              
              <div className="correlation-matrix-grid-wrapper">
                <div className="responsive-table-wrapper">
                  <table className="correlation-table">
                    <thead>
                      <tr>
                        <th></th>
                        {profile.correlation_analysis.correlation_matrix.columns.map((colName) => (
                          <th key={colName} className="matrix-header-cell" title={colName}>{colName}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {profile.correlation_analysis.correlation_matrix.columns.map((rowName, rIdx) => (
                        <tr key={rowName}>
                          <td className="matrix-row-header-cell"><strong>{rowName}</strong></td>
                          {profile.correlation_analysis.correlation_matrix.columns.map((colName, cIdx) => {
                            const val = profile.correlation_analysis.correlation_matrix.matrix[rIdx][cIdx];
                            return (
                              <td 
                                key={colName} 
                                style={getCorrelationColor(val)}
                                className="correlation-cell"
                                title={`Correlation between ${rowName} and ${colName}: ${val.toFixed(4)}`}
                              >
                                {val.toFixed(2)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {profile.correlation_analysis.high_correlations?.length > 0 && (
                <div className="high-correlations-alerts">
                  <h5>Highly Correlated Column Pairs ( &gt; 0.85 )</h5>
                  <ul>
                    {profile.correlation_analysis.high_correlations.map((pair, idx) => (
                      <li key={idx} className="high-corr-item">
                        ⚠️ Columns <strong>{pair.col1}</strong> and <strong>{pair.col2}</strong> are highly correlated (<strong>{pair.coefficient.toFixed(3)}</strong>). This redundancy might impact machine learning models.
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* SPRINT 2.2 Expandable Diagnostics Accordions */}
          <div className="profiling-alerts-section">
            <h4>🚨 Advanced Quality Diagnostics Report</h4>
            
            <div className="diagnostics-accordion">
              
              {/* Accordion Item: Missing Values Analysis */}
              <div className="accordion-item-card">
                <div className="accordion-header" onClick={() => toggleSection('missing')}>
                  <div className="title-row">
                    <span className="bullet">📍</span>
                    <h5>1. Missing Value Analysis & Null Rate</h5>
                  </div>
                  <span className="accordion-toggle-icon">{expandedSections.missing ? '▼' : '▶'}</span>
                </div>
                {expandedSections.missing && (
                  <div className="accordion-content animation-slide-down">
                    <p className="section-desc">Analyzes empty fields and null values. A high missing percentage indicates incomplete observations.</p>
                    
                    {profile.quality_report.missing_values.total_missing > 0 ? (
                      <div className="diagnostics-detail-wrapper">
                        <div className="metric-callout warning">
                          <strong>{profile.quality_report.missing_values.total_missing}</strong> cells are missing, representing <strong>{profile.quality_report.missing_values.missing_pct}%</strong> of the entire dataset.
                        </div>
                        
                        {profile.quality_report.missing_values.top_affected_columns?.length > 0 && (
                          <div className="details-sub-table">
                            <h6>Top Incomplete Columns:</h6>
                            <table className="compact-table">
                              <thead>
                                <tr>
                                  <th>Column Name</th>
                                  <th>Missing Count</th>
                                  <th>Percentage</th>
                                </tr>
                              </thead>
                              <tbody>
                                {profile.quality_report.missing_values.top_affected_columns.map(row => (
                                  <tr key={row.column}>
                                    <td><strong>{row.column}</strong></td>
                                    <td>{row.count.toLocaleString()}</td>
                                    <td className="warning-text">{row.pct}%</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="metric-callout clean">
                        🎉 Perfect! Zero missing values detected. Every row contains fully populated metadata.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Accordion Item: Duplicate Detection */}
              <div className="accordion-item-card">
                <div className="accordion-header" onClick={() => toggleSection('duplicates')}>
                  <div className="title-row">
                    <span className="bullet">👥</span>
                    <h5>2. Duplicate Record Inspection</h5>
                  </div>
                  <span className="accordion-toggle-icon">{expandedSections.duplicates ? '▼' : '▶'}</span>
                </div>
                {expandedSections.duplicates && (
                  <div className="accordion-content animation-slide-down">
                    <p className="section-desc">Checks for exact matching rows and redundant identical column variables.</p>
                    
                    <div className="diagnostics-detail-wrapper">
                      {profile.quality_report.duplicate_rows.count > 0 ? (
                        <div className="metric-callout warning">
                          Detected <strong>{profile.quality_report.duplicate_rows.count}</strong> duplicate rows, representing <strong>{profile.quality_report.duplicate_rows.pct}%</strong> of records.
                        </div>
                      ) : (
                        <div className="metric-callout clean">
                          🎉 Distinct Records! All rows contain unique identifiers. Zero duplicate rows found.
                        </div>
                      )}

                      {/* Sample Duplicate Rows Rendering */}
                      {profile.quality_report.duplicate_rows.sample_records?.length > 0 && (
                        <div className="details-sub-table mt-15">
                          <h6>Sample Duplicate Records (First 5):</h6>
                          <div className="horizontal-scroll-table">
                            <table className="compact-table scroll-table">
                              <thead>
                                <tr>
                                  {Object.keys(profile.quality_report.duplicate_rows.sample_records[0]).map(col => (
                                    <th key={col}>{col}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {profile.quality_report.duplicate_rows.sample_records.slice(0, 5).map((row, rIdx) => (
                                  <tr key={rIdx}>
                                    {Object.values(row).map((val, cIdx) => (
                                      <td key={cIdx}>{val === null ? <em className="null-text">null</em> : String(val)}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Duplicate Columns */}
                      {profile.quality_report.duplicate_columns?.length > 0 && (
                        <div className="details-sub-table mt-15">
                          <h6>Identical Columns Detected:</h6>
                          <table className="compact-table">
                            <thead>
                              <tr>
                                <th>First Column</th>
                                <th>Identical Match</th>
                              </tr>
                            </thead>
                            <tbody>
                              {profile.quality_report.duplicate_columns.map((pair, idx) => (
                                <tr key={idx}>
                                  <td><strong>{pair[0]}</strong></td>
                                  <td>{pair[1]}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Accordion Item: Outlier Detection */}
              <div className="accordion-item-card">
                <div className="accordion-header" onClick={() => toggleSection('outliers')}>
                  <div className="title-row">
                    <span className="bullet">📊</span>
                    <h5>3. Outlier Analysis (IQR & Z-Score)</h5>
                  </div>
                  <span className="accordion-toggle-icon">{expandedSections.outliers ? '▼' : '▶'}</span>
                </div>
                {expandedSections.outliers && (
                  <div className="accordion-content animation-slide-down">
                    <p className="section-desc">Identifies values deviating significantly from other observations. Tested using Interquartile Range (IQR) and standard deviation Z-Scores.</p>
                    
                    <div className="diagnostics-detail-wrapper">
                      {profile.quality_report.outliers && Object.keys(profile.quality_report.outliers.by_column).length > 0 ? (
                        <>
                          <div className="metrics-split-row">
                            <div className="split-metric warning">
                              <h5>IQR Method Outliers</h5>
                              <p><strong>{profile.quality_report.outliers.total_outliers_iqr}</strong> cells ({profile.quality_report.outliers.pct_outliers_iqr}%)</p>
                            </div>
                            <div className="split-metric warning">
                              <h5>Z-Score Method Outliers</h5>
                              <p><strong>{profile.quality_report.outliers.total_outliers_zscore}</strong> cells ({profile.quality_report.outliers.pct_outliers_zscore}%)</p>
                            </div>
                          </div>

                          <div className="details-sub-table mt-15">
                            <h6>Outliers by Column:</h6>
                            <table className="compact-table">
                              <thead>
                                <tr>
                                  <th>Column</th>
                                  <th>IQR Count</th>
                                  <th>Z-Score Count</th>
                                  <th>Sample Values</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(profile.quality_report.outliers.by_column).map(([col, stats]) => (
                                  <tr key={col}>
                                    <td><strong>{col}</strong></td>
                                    <td>{stats.iqr_count.toLocaleString()} ({stats.iqr_pct}%)</td>
                                    <td>{stats.zscore_count.toLocaleString()} ({stats.zscore_pct}%)</td>
                                    <td className="sample-list-cell">
                                      <code>
                                        {stats.iqr_outliers && stats.iqr_outliers.length > 0 
                                          ? stats.iqr_outliers.slice(0, 5).join(', ') 
                                          : (stats.zscore_outliers ? stats.zscore_outliers.slice(0, 5).join(', ') : 'None')}
                                      </code>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      ) : (
                        <div className="metric-callout clean">
                          🎉 Uniform Data! No significant outliers detected in the numeric columns.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Accordion Item: Format Violations (Dates, Emails, Phones) */}
              <div className="accordion-item-card">
                <div className="accordion-header" onClick={() => toggleSection('formats')}>
                  <div className="title-row">
                    <span className="bullet">✉️</span>
                    <h5>4. Format Inconsistency Diagnostics</h5>
                  </div>
                  <span className="accordion-toggle-icon">{expandedSections.formats ? '▼' : '▶'}</span>
                </div>
                {expandedSections.formats && (
                  <div className="accordion-content animation-slide-down">
                    <p className="section-desc">Validates phone numbers, emails, and date formatting against standard patterns and schemas.</p>
                    
                    <div className="diagnostics-detail-wrapper">
                      
                      {/* Invalid Dates */}
                      {profile.quality_report.invalid_dates?.length > 0 && (
                        <div className="format-alert-item danger">
                          <h6>⚠️ Inconsistent Date Formats:</h6>
                          {profile.quality_report.invalid_dates.map((row, idx) => (
                            <div key={idx} className="format-col-info">
                              <p>Column <strong>{row.column}</strong> contains multiple date formats: <code>{row.inconsistent_formats.join(', ')}</code>.</p>
                              {row.sample_invalid_values && row.sample_invalid_values.length > 0 && (
                                <p className="sample-vals">Samples: <code>{row.sample_invalid_values.slice(0, 5).join(', ')}</code></p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Invalid Emails */}
                      {profile.quality_report.invalid_emails && profile.quality_report.invalid_emails.total_invalid_count > 0 ? (
                        <div className="format-alert-item warning">
                          <h6>⚠️ Malformed Email Formats:</h6>
                          <div className="metric-callout warning">
                            Total <strong>{profile.quality_report.invalid_emails.total_invalid_count}</strong> malformed email strings found.
                          </div>
                          {Object.entries(profile.quality_report.invalid_emails.affected_columns).map(([col, data]) => (
                            <div key={col} className="format-col-info">
                              <p>Column <strong>{col}</strong>: <strong>{data.invalid_count}</strong> values violate standard email pattern.</p>
                              <p className="sample-vals">Malformed: <code>{data.sample_invalid_values.slice(0, 5).join(', ')}</code></p>
                            </div>
                          ))}
                        </div>
                      ) : null}

                      {/* Invalid Phone Numbers */}
                      {profile.quality_report.invalid_phones && profile.quality_report.invalid_phones.total_invalid_count > 0 ? (
                        <div className="format-alert-item warning">
                          <h6>⚠️ Malformed Phone Formats:</h6>
                          <div className="metric-callout warning">
                            Total <strong>{profile.quality_report.invalid_phones.total_invalid_count}</strong> malformed phone strings found.
                          </div>
                          {Object.entries(profile.quality_report.invalid_phones.affected_columns).map(([col, data]) => (
                            <div key={col} className="format-col-info">
                              <p>Column <strong>{col}</strong>: <strong>{data.invalid_count}</strong> values violate phone formats.</p>
                              <p className="sample-vals">Malformed: <code>{data.sample_invalid_values.slice(0, 5).join(', ')}</code></p>
                            </div>
                          ))}
                        </div>
                      ) : null}

                      {!(profile.quality_report.invalid_dates?.length > 0) && 
                        !(profile.quality_report.invalid_emails?.total_invalid_count > 0) &&
                        !(profile.quality_report.invalid_phones?.total_invalid_count > 0) && (
                          <div className="metric-callout clean">
                            🎉 Clean Formats! Emails, dates, and phone numbers are correctly structured and formatted.
                          </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Accordion Item: Cardinality, Constants, Empty & Mixed Types */}
              <div className="accordion-item-card">
                <div className="accordion-header" onClick={() => toggleSection('cardinality')}>
                  <div className="title-row">
                    <span className="bullet">⚙️</span>
                    <h5>5. Column Cardinality & Schema Properties</h5>
                  </div>
                  <span className="accordion-toggle-icon">{expandedSections.cardinality ? '▼' : '▶'}</span>
                </div>
                {expandedSections.cardinality && (
                  <div className="accordion-content animation-slide-down">
                    <p className="section-desc">Identifies columns with structural issues: high cardinality, empty columns, constant values, or mixed datatypes.</p>
                    
                    <div className="diagnostics-detail-wrapper">
                      
                      {/* High Cardinality */}
                      {profile.quality_report.high_cardinality?.length > 0 && (
                        <div className="format-alert-item warning">
                          <h6>⚠️ High Cardinality in Categories:</h6>
                          <ul>
                            {profile.quality_report.high_cardinality.map((row, idx) => (
                              <li key={idx}>
                                Column <strong>{row.column}</strong> has <strong>{row.unique_count}</strong> unique values (<strong>{row.unique_pct}%</strong> unique rate). {row.severity} severity redundancy.
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Mixed Data Types */}
                      {profile.quality_report.mixed_data_types && Object.keys(profile.quality_report.mixed_data_types).length > 0 && (
                        <div className="format-alert-item danger">
                          <h6>⚠️ Mixed Value Types:</h6>
                          <p>Columns containing multiple datatypes (e.g. text mixed with numbers):</p>
                          <ul>
                            {Object.entries(profile.quality_report.mixed_data_types).map(([col, list]) => (
                              <li key={col}>Column <strong>{col}</strong> contains types: <code>{list.join(', ')}</code></li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Empty Columns */}
                      {profile.quality_report.empty_columns?.length > 0 && (
                        <div className="format-alert-item danger">
                          <h6>⚠️ Fully Empty Columns (All Null/Blank):</h6>
                          <p>Columns containing only null values or empty whitespace strings: <code>{profile.quality_report.empty_columns.join(', ')}</code></p>
                        </div>
                      )}

                      {/* Constant Columns */}
                      {profile.quality_report.constant_columns?.length > 0 && (
                        <div className="format-alert-item info">
                          <h6>ℹ️ Constant Value Columns:</h6>
                          <p>Columns containing only a single unique value: <code>{profile.quality_report.constant_columns.join(', ')}</code></p>
                        </div>
                      )}

                      {!(profile.quality_report.high_cardinality?.length > 0) &&
                        !(Object.keys(profile.quality_report.mixed_data_types).length > 0) &&
                        !(profile.quality_report.empty_columns?.length > 0) &&
                        !(profile.quality_report.constant_columns?.length > 0) && (
                          <div className="metric-callout clean">
                            🎉 Clean Schemas! No empty columns, mixed datatypes, or cardinality issues found.
                          </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

            </div>
          </div>

        </div>
      )}
    </div>
  );
};

export default DataProfiling;
