import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import { Bar, Doughnut } from 'react-chartjs-2';

const DataInsights = ({ token, datasets, showNotification, initialDatasetId }) => {
  const [selectedDatasetId, setSelectedDatasetId] = useState(initialDatasetId || '');
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState(null);
  const [health, setHealth] = useState(null);

  // Auto-select first dataset on load if available
  useEffect(() => {
    if (datasets && datasets.length > 0 && !selectedDatasetId) {
      setSelectedDatasetId(datasets[0].id);
    }
  }, [datasets, selectedDatasetId]);

  // Fetch insights and health when dataset selection changes
  useEffect(() => {
    if (selectedDatasetId) {
      fetchInsightsAndHealth(selectedDatasetId);
    } else {
      setInsights(null);
      setHealth(null);
    }
  }, [selectedDatasetId]);

  const fetchInsightsAndHealth = async (id) => {
    setLoading(true);
    try {
      const [insightsRes, healthRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/datasets/${id}/insights`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE_URL}/datasets/${id}/health`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setInsights(insightsRes.data);
      setHealth(healthRes.data);
    } catch (error) {
      const errMsg = error.response?.data?.detail || 'Failed to load dataset insights';
      if (showNotification) {
        showNotification(errMsg, 'error');
      } else {
        alert(errMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  if (!datasets || datasets.length === 0) {
    return (
      <div className="insights-empty-state">
        <span className="empty-icon">🧠</span>
        <h3>No Datasets Available for AI Insights</h3>
        <p>Please upload a CSV, Excel, or JSON dataset in the sidebar to generate comprehensive insights and health diagnostics.</p>
      </div>
    );
  }

  // Count recommendation severities for the chart
  const getSeverityCounts = () => {
    const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
    if (insights?.business_recommendations) {
      insights.business_recommendations.forEach(rec => {
        if (counts[rec.severity] !== undefined) {
          counts[rec.severity]++;
        }
      });
    }
    return counts;
  };

  const severityCounts = getSeverityCounts();

  const barChartData = {
    labels: ['Critical', 'High', 'Medium', 'Low'],
    datasets: [
      {
        label: 'Recommendations Count',
        data: [
          severityCounts.Critical,
          severityCounts.High,
          severityCounts.Medium,
          severityCounts.Low
        ],
        backgroundColor: [
          'rgba(239, 68, 68, 0.75)',  // Red
          'rgba(249, 115, 22, 0.75)', // Orange
          'rgba(234, 179, 8, 0.75)',  // Yellow
          'rgba(59, 130, 246, 0.75)'  // Blue
        ],
        borderColor: [
          'rgb(239, 68, 68)',
          'rgb(249, 115, 22)',
          'rgb(234, 179, 8)',
          'rgb(59, 130, 246)'
        ],
        borderWidth: 1.5,
        borderRadius: 6
      }
    ]
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: 'Recommendations by Severity Level',
        color: '#1e293b',
        font: { family: 'Outfit, sans-serif', size: 14, weight: '600' }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { stepSize: 1, color: '#64748b', font: { family: 'Outfit, sans-serif' } },
        grid: { color: '#f1f5f9' }
      },
      x: {
        ticks: { color: '#64748b', font: { family: 'Outfit, sans-serif', weight: '600' } },
        grid: { display: false }
      }
    }
  };

  // Health Doughnut/Gauge Data
  const healthScore = health?.overall_health ?? 0;
  const healthGaugeData = {
    labels: ['Health Score', 'Deductions'],
    datasets: [
      {
        data: [healthScore, 100 - healthScore],
        backgroundColor: [
          healthScore >= 85 ? 'rgba(16, 185, 129, 0.85)' : // Green
          healthScore >= 70 ? 'rgba(59, 130, 246, 0.85)' : // Blue
          healthScore >= 50 ? 'rgba(234, 179, 8, 0.85)' :  // Yellow
          'rgba(239, 68, 68, 0.85)',                        // Red
          'rgba(241, 245, 249, 1)'                         // Slate Light
        ],
        borderWidth: 0,
        hoverOffset: 0
      }
    ]
  };

  const healthGaugeOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '80%',
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false }
    }
  };

  const getScoreColorClass = (score) => {
    if (score >= 85) return 'excellent';
    if (score >= 70) return 'good';
    if (score >= 50) return 'average';
    return 'poor';
  };

  const getScoreRatingText = (score) => {
    if (score >= 85) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Average';
    return 'Poor';
  };

  return (
    <div className="insights-container animation-fade-in">
      {/* Top Selector Card */}
      <div className="insights-selector-card">
        <div className="selector-left">
          <label htmlFor="insight-dataset-select">Active Dataset for AI Insights:</label>
          <select
            id="insight-dataset-select"
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
          >
            {datasets.map(ds => (
              <option key={ds.id} value={ds.id}>
                {ds.filename} ({ds.row_count} rows × {ds.col_count} columns)
              </option>
            ))}
          </select>
        </div>
        {loading && <span className="loader-inline">⚡ Scanning dataset properties...</span>}
      </div>

      {loading && !insights ? (
        <div className="insights-loading-layout">
          <div className="skeleton-loader-card large"></div>
          <div className="skeleton-loader-card"></div>
          <div className="skeleton-loader-card"></div>
        </div>
      ) : insights && health ? (
        <div className="insights-layout-grid">
          
          {/* FEATURE 3: Dataset Health Summary Block */}
          <section className="insight-section health-hero-card">
            <div className="health-dial-container">
              <div className="health-chart-wrapper">
                <Doughnut data={healthGaugeData} options={healthGaugeOptions} />
                <div className="health-center-value">
                  <span className={`health-score-val ${getScoreColorClass(healthScore)}`}>{healthScore}</span>
                  <span className="health-score-label">/100</span>
                </div>
              </div>
              <div className="health-score-summary">
                <h3>Dataset Health Index</h3>
                <div className={`health-status-badge ${getScoreColorClass(healthScore)}`}>
                  Rating: {getScoreRatingText(healthScore)}
                </div>
                <p className="health-narrative-text">
                  {insights.quality_summary}
                </p>
              </div>
            </div>

            {/* Strengths & Weaknesses */}
            <div className="health-diagnostics-grid">
              <div className="diagnostics-column strengths-box">
                <h4>🟢 Dataset Strengths</h4>
                {health.strengths && health.strengths.length > 0 ? (
                  <ul>
                    {health.strengths.map((str, idx) => (
                      <li key={idx}>✨ {str}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty-diagnostic-text">No significant strengths observed.</p>
                )}
              </div>
              <div className="diagnostics-column weaknesses-box">
                <h4>🔴 Dataset Weaknesses</h4>
                {health.weaknesses && health.weaknesses.length > 0 ? (
                  <ul>
                    {health.weaknesses.map((weak, idx) => (
                      <li key={idx}>⚠️ {weak}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty-diagnostic-text">No major weaknesses detected. Outstanding!</p>
                )}
              </div>
            </div>

            {/* Recommended Next Steps */}
            <div className="recommended-steps-box">
              <h4>🛠️ Recommended Actions Sequence</h4>
              <ol>
                {health.recommended_next_steps && health.recommended_next_steps.map((step, idx) => (
                  <li key={idx}>{step}</li>
                ))}
              </ol>
            </div>
          </section>

          {/* FEATURE 5: Summary Cards & Trend Indicators */}
          <section className="insights-metrics-dashboard">
            <div className="metrics-summary-grid">
              {/* Health Score Card */}
              <div className="metric-card-box">
                <div className="card-top">
                  <span className="metric-title">Quality Score</span>
                  <span className="metric-icon">🛡️</span>
                </div>
                <div className="card-value-row">
                  <h3 className={`metric-value ${getScoreColorClass(healthScore)}`}>{healthScore}%</h3>
                  {insights.quality_improvement && insights.quality_improvement.improvement > 0 ? (
                    <span className="trend-indicator up">
                      ▲ +{insights.quality_improvement.improvement}% improvement
                    </span>
                  ) : (
                    <span className="trend-indicator neutral">Stable</span>
                  )}
                </div>
                <p className="metric-desc">Overall data quality index before/after corrections.</p>
              </div>

              {/* Duplicate Rows Card */}
              <div className="metric-card-box">
                <div className="card-top">
                  <span className="metric-title">Duplicate Density</span>
                  <span className="metric-icon">👥</span>
                </div>
                <div className="card-value-row">
                  <h3>{datasets.find(d => d.id === selectedDatasetId)?.row_count ? (
                    health.top_risks.some(r => r.risk === "Row Duplication Bias") ? 'Detected' : '0%'
                  ) : '0%'}</h3>
                </div>
                <p className="metric-desc">Duplicate rows skew statistical aggregates.</p>
              </div>

              {/* Severe Risks Card */}
              <div className="metric-card-box">
                <div className="card-top">
                  <span className="metric-title">Active Risks</span>
                  <span className="metric-icon">⚠️</span>
                </div>
                <div className="card-value-row">
                  <h3 className={health.top_risks?.length > 0 ? 'poor' : 'excellent'}>
                    {health.top_risks?.length || 0} Issues
                  </h3>
                </div>
                <p className="metric-desc">Data quality anomalies requiring cleaning actions.</p>
              </div>
            </div>
            
            {/* Top Risks Section */}
            {health.top_risks && health.top_risks.length > 0 && (
              <div className="insights-risks-container">
                <h4>⚡ Risk Summary & Exposure</h4>
                <div className="risks-grid">
                  {health.top_risks.map((risk, idx) => (
                    <div className={`risk-card-item severity-${risk.severity.toLowerCase()}`} key={idx}>
                      <div className="risk-header">
                        <span className={`severity-badge severity-${risk.severity.toLowerCase()}`}>
                          {risk.severity} Risk
                        </span>
                        <h5>{risk.risk}</h5>
                      </div>
                      <p className="risk-desc">{risk.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quality improvement compare */}
            {insights.quality_improvement && (
              <div className="quality-improvements-panel">
                <h4>📈 Cleaning Quality Progress</h4>
                <div className="compare-bar-layout">
                  <div className="compare-column">
                    <span className="lbl">Initial Quality</span>
                    <div className="bar-bg">
                      <div className="bar-fill initial" style={{ width: `${insights.quality_improvement.score_before}%` }}>
                        {insights.quality_improvement.score_before}%
                      </div>
                    </div>
                  </div>
                  <div className="compare-column mt-10">
                    <span className="lbl">Current Quality</span>
                    <div className="bar-bg">
                      <div className="bar-fill current" style={{ width: `${insights.quality_improvement.score_after}%` }}>
                        {insights.quality_improvement.score_after}%
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Interactive Chart & Quality details */}
          <section className="insight-chart-section card-box-panel">
            <div className="chart-card-header">
              <h4>📊 Insights & Severities Matrix</h4>
              <p>Severity distribution of data validation recommendations.</p>
            </div>
            <div className="insights-bar-chart-wrapper">
              <Bar data={barChartData} options={barChartOptions} height={250} />
            </div>
          </section>

          {/* FEATURE 1: Heuristic Quality Summary & Detailed Observations */}
          <section className="insight-section quality-observations-card">
            <h4>💡 Dataset Quality Summary & Impacts</h4>
            <div className="observations-list-layout">
              <div className="observation-item">
                <h5>👥 Duplicate Density Impact</h5>
                <p>{insights.duplicate_impact}</p>
              </div>
              <div className="observation-item">
                <h5>❓ Missing Values Integrity</h5>
                <p>{insights.missing_value_impact}</p>
              </div>
              <div className="observation-item">
                <h5>📈 Outliers Variance Impact</h5>
                <p>{insights.outlier_impact}</p>
              </div>
              <div className="observation-item">
                <h5>⛓️ Feature Correlations</h5>
                <p>{insights.correlation_observations}</p>
              </div>
              <div className="observation-item">
                <h5>📇 High-Cardinality Variables</h5>
                <p>{insights.high_cardinality_observations}</p>
              </div>
            </div>

            {insights.most_problematic_columns && insights.most_problematic_columns.length > 0 && (
              <div className="problematic-columns-table">
                <h5>⚠️ Most Problematic Columns</h5>
                <table className="insights-table">
                  <thead>
                    <tr>
                      <th>Column Name</th>
                      <th>Observed issue</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.most_problematic_columns.map((item, idx) => (
                      <tr key={idx}>
                        <td className="col-name-cell"><code>{item.column}</code></td>
                        <td>{item.issue}</td>
                        <td>
                          <span className={`severity-text severity-${item.severity.toLowerCase()}`}>
                            {item.severity}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* FEATURE 2: Business Recommendations */}
          <section className="insight-section recommendations-card">
            <div className="recommendations-section-header">
              <h4>🎯 Business Recommendations</h4>
              <p>Automated action items designed to improve model predictions and business logic operations.</p>
            </div>
            <div className="rich-recommendations-grid">
              {insights.business_recommendations && insights.business_recommendations.length > 0 ? (
                insights.business_recommendations.map((rec, idx) => (
                  <div className={`rich-rec-card severity-${rec.severity.toLowerCase()}`} key={idx}>
                    <div className="rec-card-header">
                      <span className={`severity-badge severity-${rec.severity.toLowerCase()}`}>
                        {rec.severity}
                      </span>
                      <span className="rec-confidence">
                        {rec.confidence_score}% Confidence
                      </span>
                    </div>
                    <h5>{rec.title}</h5>
                    <p className="rec-desc">{rec.description}</p>
                    <div className="rec-impact-section">
                      <strong>💼 Business Impact:</strong>
                      <p>{rec.business_impact}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-recommendations">
                  <span>🎉</span>
                  <h5>All Clear!</h5>
                  <p>No business recommendations found. The dataset features are clean, non-redundant, and ready for deployment.</p>
                </div>
              )}
            </div>
          </section>

          {/* FEATURE 4: Explain Every Cleaning Action */}
          <section className="insight-section cleaning-explanations-card">
            <h4>🧹 Applied Cleaning Operations & Rationale</h4>
            <p className="cleaning-section-subtitle">
              Audit log analysis detailing transformations applied to date, and why they matter for your business.
            </p>
            <div className="cleaning-explanations-timeline">
              {insights.cleaning_explanations && insights.cleaning_explanations.length > 0 ? (
                insights.cleaning_explanations.map((expl, idx) => (
                  <div className="timeline-item" key={idx}>
                    <div className="timeline-marker"></div>
                    <div className="timeline-content">
                      <div className="timeline-header">
                        <h5>{expl.operation}</h5>
                      </div>
                      <div className="timeline-body-grid">
                        <div className="body-cell">
                          <strong>🔄 What changed:</strong>
                          <p>{expl.what_changed}</p>
                        </div>
                        <div className="body-cell">
                          <strong>❓ Why it changed:</strong>
                          <p>{expl.why_it_changed}</p>
                        </div>
                        <div className="body-cell">
                          <strong>💼 Business Impact:</strong>
                          <p>{expl.business_impact}</p>
                        </div>
                        <div className="body-cell">
                          <strong>📈 Expected Improvement:</strong>
                          <p>{expl.expected_improvement}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-timeline-state">
                  <span>🧹</span>
                  <h5>No Cleaning Steps Logged Yet</h5>
                  <p>
                    This dataset has not had any data cleaning operations applied to it yet.
                    Go to the <strong>Data Cleaning</strong> tab to configure and run cleaning pipelines.
                  </p>
                </div>
              )}
            </div>
          </section>

        </div>
      ) : (
        <div className="insights-empty-state">
          <span className="empty-icon">📊</span>
          <h3>Insights Diagnostics Unavailable</h3>
          <p>Please ensure that the active dataset has been profiled to generate the required quality statistics.</p>
        </div>
      )}
    </div>
  );
};

export default DataInsights;
