import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import DataCleaningRecommendations from './DataCleaningRecommendations';
import DataCleaningVersions from './DataCleaningVersions';
import DataCleaningAudit from './DataCleaningAudit';

const DataCleaning = ({ token, datasets, showNotification, initialDatasetId, onCleanComplete }) => {
  const [selectedDatasetId, setSelectedDatasetId] = useState(initialDatasetId || '');
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [subTab, setSubTab] = useState('checklist'); // 'checklist' | 'recommendations' | 'versions' | 'audit'
  
  // Cleaning configurations
  const [cleanMode, setCleanMode] = useState('auto'); // 'auto' | 'manual'
  const [config, setConfig] = useState({
    whitespace: { apply: true },
    duplicate_rows: { apply: true },
    duplicate_columns: { apply: true },
    constant_columns: { apply: true },
    empty_columns: { apply: true },
    mixed_types: { apply: true, normalization_value: '' },
    invalid_dates: { apply: false, columns: [], format: 'YYYY-MM-DD' },
    invalid_emails: { apply: false, columns: [], strategy: 'remove' },
    invalid_phones: { apply: false, columns: [], strategy: 'normalize' },
    outliers: { apply: false, columns: [], strategy: 'cap' },
    missing_values: { apply: false, strategies: {}, constant_values: {} },
    text_normalization: { apply: false, strategies: {} }
  });

  // UI state
  const [previewReport, setPreviewReport] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [cleaningStatus, setCleaningStatus] = useState('idle'); // 'idle' | 'cleaning' | 'completed' | 'failed'
  const [cleaningResult, setCleaningResult] = useState(null);

  // Auto-select first dataset on load if available
  useEffect(() => {
    if (datasets && datasets.length > 0 && !selectedDatasetId) {
      setSelectedDatasetId(datasets[0].id);
    }
  }, [datasets, selectedDatasetId]);

  // Set selected dataset object
  useEffect(() => {
    if (selectedDatasetId && datasets) {
      const found = datasets.find(d => d.id === selectedDatasetId);
      setSelectedDataset(found);
      
      // Reset config state & preview when dataset changes
      setPreviewReport(null);
      setCleaningResult(null);
      setCleaningStatus('idle');
      
      // Initialize default column strategies based on selected dataset columns
      if (found) {
        const initialStrategies = {};
        const initialTextStrategies = {};
        found.columns.forEach(col => {
          initialStrategies[col] = 'mode';
          initialTextStrategies[col] = 'lower';
        });
        setConfig(prev => ({
          ...prev,
          missing_values: { ...prev.missing_values, strategies: initialStrategies },
          text_normalization: { ...prev.text_normalization, strategies: initialTextStrategies }
        }));
      }
    } else {
      setSelectedDataset(null);
    }
  }, [selectedDatasetId, datasets]);

  // Sync mode choices to config structure
  useEffect(() => {
    if (cleanMode === 'auto') {
      // Setup aggressive auto-cleaning parameters
      if (selectedDataset) {
        const allCols = selectedDataset.columns || [];
        // Guess columns
        const emailCols = allCols.filter(c => c.toLowerCase().includes('email') || c.toLowerCase().includes('mail'));
        const phoneCols = allCols.filter(c => c.toLowerCase().includes('phone') || c.toLowerCase().includes('tel') || c.toLowerCase().includes('mobile'));
        const dateCols = allCols.filter(c => c.toLowerCase().includes('date') || c.toLowerCase().includes('time') || c.toLowerCase().includes('created') || c.toLowerCase().includes('updated'));
        const numCols = selectedDataset.schema_info?.numerical_columns || [];

        setConfig({
          whitespace: { apply: true },
          duplicate_rows: { apply: true },
          duplicate_columns: { apply: true },
          constant_columns: { apply: true },
          empty_columns: { apply: true },
          mixed_types: { apply: true, normalization_value: '' },
          invalid_dates: { apply: dateCols.length > 0, columns: dateCols, format: 'YYYY-MM-DD' },
          invalid_emails: { apply: emailCols.length > 0, columns: emailCols, strategy: 'remove' },
          invalid_phones: { apply: phoneCols.length > 0, columns: phoneCols, strategy: 'normalize' },
          outliers: { apply: numCols.length > 0, columns: numCols, strategy: 'cap' },
          missing_values: { apply: false, strategies: {}, constant_values: {} }, // auto handles simple drop/imputes or skips
          text_normalization: { apply: false, strategies: {} }
        });
      }
    }
  }, [cleanMode, selectedDataset]);

  const handleConfigChange = (section, field, value) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }));
  };

  const handleApplyRecommendation = (rec) => {
    setCleanMode('manual');
    const rText = rec.recommendation || '';
    const issue = rec.issue || '';
    const colMatch = rText.match(/'([^']+)'/) || issue.match(/'([^']+)'/);
    const colName = colMatch ? colMatch[1] : null;

    setConfig(prev => {
      const updated = { ...prev };
      
      if (rText.includes("Remove Duplicate Rows")) {
        updated.duplicate_rows.apply = true;
      }
      else if (rText.includes("Remove Duplicate Columns")) {
        updated.duplicate_columns.apply = true;
      }
      else if (rText.includes("Remove Constant Columns")) {
        updated.constant_columns.apply = true;
      }
      else if (rText.includes("Remove Empty Columns")) {
        updated.empty_columns.apply = true;
      }
      else if (rText.includes("Normalize Mixed Types")) {
        updated.mixed_types.apply = true;
      }
      else if (colName) {
        if (rText.includes("Drop Column")) {
          updated.missing_values = {
            ...updated.missing_values,
            apply: true,
            strategies: { ...updated.missing_values.strategies, [colName]: 'drop_columns' }
          };
        }
        else if (rText.includes("Median Imputation")) {
          updated.missing_values = {
            ...updated.missing_values,
            apply: true,
            strategies: { ...updated.missing_values.strategies, [colName]: 'median' }
          };
        }
        else if (rText.includes("Mode Imputation")) {
          updated.missing_values = {
            ...updated.missing_values,
            apply: true,
            strategies: { ...updated.missing_values.strategies, [colName]: 'mode' }
          };
        }
        else if (rText.includes("Standardize Date Format")) {
          updated.invalid_dates = {
            ...updated.invalid_dates,
            apply: true,
            columns: updated.invalid_dates.columns.includes(colName) 
              ? updated.invalid_dates.columns 
              : [...updated.invalid_dates.columns, colName]
          };
        }
        else if (rText.includes("Handle Invalid Emails")) {
          updated.invalid_emails = {
            ...updated.invalid_emails,
            apply: true,
            columns: updated.invalid_emails.columns.includes(colName) 
              ? updated.invalid_emails.columns 
              : [...updated.invalid_emails.columns, colName]
          };
        }
        else if (rText.includes("Normalize Phone Formatting")) {
          updated.invalid_phones = {
            ...updated.invalid_phones,
            apply: true,
            columns: updated.invalid_phones.columns.includes(colName) 
              ? updated.invalid_phones.columns 
              : [...updated.invalid_phones.columns, colName]
          };
        }
      }
      return updated;
    });

    setSubTab('checklist');
    showNotification(`Auto-configured checklist operation: "${rText}"`, 'info');
  };

  const handleListToggle = (section, columnName) => {
    const currentList = config[section].columns || [];
    const newList = currentList.includes(columnName)
      ? currentList.filter(c => c !== columnName)
      : [...currentList, columnName];
    
    handleConfigChange(section, 'columns', newList);
  };

  const handleMissingStrategyChange = (column, strategy) => {
    setConfig(prev => ({
      ...prev,
      missing_values: {
        ...prev.missing_values,
        strategies: {
          ...prev.missing_values.strategies,
          [column]: strategy
        }
      }
    }));
  };

  const handleMissingConstantChange = (column, value) => {
    setConfig(prev => ({
      ...prev,
      missing_values: {
        ...prev.missing_values,
        constant_values: {
          ...prev.missing_values.constant_values,
          [column]: value
        }
      }
    }));
  };

  const handleTextNormalizationChange = (column, strategy) => {
    setConfig(prev => ({
      ...prev,
      text_normalization: {
        ...prev.text_normalization,
        strategies: {
          ...prev.text_normalization.strategies,
          [column]: strategy
        }
      }
    }));
  };

  // Generate cleaning preview report
  const handleGeneratePreview = async () => {
    if (!selectedDatasetId) return;
    setPreviewLoading(true);
    setPreviewReport(null);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/datasets/${selectedDatasetId}/clean/preview`,
        config,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setPreviewReport(response.data);
      showNotification('Cleaning preview report generated successfully.', 'success');
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to generate cleaning preview', 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Execute cleaning operation
  const handleApplyClean = async () => {
    if (!selectedDatasetId) return;
    setShowConfirmModal(false);
    setCleaningStatus('cleaning');
    setLoading(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/datasets/${selectedDatasetId}/clean`,
        config,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setCleaningResult(response.data);
      setCleaningStatus('completed');
      showNotification('Dataset auto-cleaned successfully.', 'success');
      
      // Trigger update of parent datasets listing context
      if (onCleanComplete) {
        onCleanComplete();
      }
    } catch (error) {
      setCleaningStatus('failed');
      showNotification(error.response?.data?.detail || 'Failed to apply cleaning operations', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (!datasets || datasets.length === 0) {
    return (
      <div className="profiling-empty-state">
        <span className="empty-icon">🧹</span>
        <h3>No Datasets Available for Cleaning</h3>
        <p>Upload a CSV, Excel, or JSON dataset in the sidebar first to access cleaning operations.</p>
      </div>
    );
  }

  const columns = selectedDataset?.columns || [];
  const numericalCols = selectedDataset?.schema_info?.numerical_columns || [];

  return (
    <div className="profiling-container">
      {/* Selector row */}
      <div className="profiling-selector-row">
        <div className="selector-text">
          <h3>🧹 Enterprise Auto Cleaning Engine</h3>
          <p>Deduplicate, normalize datatypes, standardize inconsistent date formats, and resolve outliers safely.</p>
        </div>
        <div className="selector-wrapper">
          <label>Select Target Dataset:</label>
          <select 
            value={selectedDatasetId} 
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            disabled={loading || previewLoading}
          >
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>
                {ds.filename} ({ds.row_count} rows)
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedDatasetId && cleaningStatus === 'idle' && (
        <div className="cleaning-subtabs-row">
          <button 
            className={`subtab-btn ${subTab === 'checklist' ? 'active' : ''}`}
            onClick={() => setSubTab('checklist')}
          >
            🛠️ Checklist & Manual Imputation
          </button>
          <button 
            className={`subtab-btn ${subTab === 'recommendations' ? 'active' : ''}`}
            onClick={() => setSubTab('recommendations')}
          >
            💡 AI Recommendations
          </button>
          <button 
            className={`subtab-btn ${subTab === 'versions' ? 'active' : ''}`}
            onClick={() => setSubTab('versions')}
          >
            📦 Version Snapshots
          </button>
          <button 
            className={`subtab-btn ${subTab === 'audit' ? 'active' : ''}`}
            onClick={() => setSubTab('audit')}
          >
            📋 Cleaning Audits
          </button>
        </div>
      )}

      {cleaningStatus === 'cleaning' && (
        <div className="profiling-loading-state">
          <span className="profiling-spinner">🧹</span>
          <h4>Running cleaning engine...</h4>
          <p>Rewriting database tables, running format standardizations, and recalculating data profiling scorecard stats...</p>
        </div>
      )}

      {cleaningStatus === 'completed' && cleaningResult && (
        <div className="dashboard-card cleaning-success-card animation-fade-in">
          <span className="success-badge-icon">🎉</span>
          <h4>Cleaning Completed Successfully!</h4>
          <p>The dataset <strong>{selectedDataset?.filename}</strong> has been auto-cleaned, matching your customized parameters. Disk records and dynamic relational tables have been updated.</p>
          
          <div className="preview-metrics-split mt-15">
            <div className="split-metric">
              <h5>Rows Before</h5>
              <p>{cleaningResult.preview_report?.rows_before?.toLocaleString()}</p>
            </div>
            <div className="split-metric clean">
              <h5>Rows After</h5>
              <p>{cleaningResult.preview_report?.rows_after?.toLocaleString()}</p>
            </div>
            <div className="split-metric">
              <h5>Columns Before</h5>
              <p>{cleaningResult.preview_report?.columns_before?.toLocaleString()}</p>
            </div>
            <div className="split-metric clean">
              <h5>Columns After</h5>
              <p>{cleaningResult.preview_report?.columns_after?.toLocaleString()}</p>
            </div>
          </div>

          <div className="applied-ops-summary mt-15">
            <h5>Operations Applied:</h5>
            <ul>
              {cleaningResult.preview_report?.operations_to_apply?.map((op, idx) => (
                <li key={idx}>✅ {op}</li>
              ))}
            </ul>
          </div>

          <div className="success-action-row">
            <button className="primary-btn" onClick={() => {
              setCleaningStatus('idle');
              setPreviewReport(null);
              // Direct user to view updated profile
              const profTab = document.querySelector('button[data-tab="profiling"]');
              if (profTab) profTab.click();
            }}>
              👁️ View Updated Data Profile
            </button>
            <button className="secondary-btn" onClick={() => setCleaningStatus('idle')}>
              Clean Another Dataset
            </button>
          </div>
        </div>
      )}

      {cleaningStatus === 'idle' && subTab === 'checklist' && (
        <div className="cleaning-engine-layout grid-2-col">
          
          {/* LEFT: Config Panel */}
          <div className="cleaning-config-section">
            <div className="dashboard-card">
              <div className="cleaning-mode-selector">
                <h4>1. Choose Imputation Strategy</h4>
                <div className="mode-toggle-buttons">
                  <button 
                    className={`mode-btn ${cleanMode === 'auto' ? 'active' : ''}`}
                    onClick={() => setCleanMode('auto')}
                  >
                    🚀 Auto Clean Mode
                  </button>
                  <button 
                    className={`mode-btn ${cleanMode === 'manual' ? 'active' : ''}`}
                    onClick={() => setCleanMode('manual')}
                  >
                    🛠️ Manual Clean Mode
                  </button>
                </div>
                <p className="mode-desc">
                  {cleanMode === 'auto' 
                    ? 'Auto Clean maps default rules: trims spaces, clears duplicates, drops empty/constant columns, caps outliers, and standardizes date/email/phone formats.'
                    : 'Manual Clean allows granular controls, customizing missing value imputations and casing normalizations per column.'
                  }
                </p>
              </div>

              {cleanMode === 'manual' && (
                <div className="manual-options-list animation-slide-down">
                  
                  {/* Basic Clean Toggles */}
                  <div className="options-group">
                    <h5>General Operations</h5>
                    <div className="checkbox-row-grid">
                      <label className="checkbox-container">
                        <input 
                          type="checkbox" 
                          checked={config.whitespace.apply}
                          onChange={(e) => handleConfigChange('whitespace', 'apply', e.target.checked)}
                        />
                        Trim Whitespaces
                      </label>
                      <label className="checkbox-container">
                        <input 
                          type="checkbox" 
                          checked={config.duplicate_rows.apply}
                          onChange={(e) => handleConfigChange('duplicate_rows', 'apply', e.target.checked)}
                        />
                        Remove Duplicate Rows
                      </label>
                      <label className="checkbox-container">
                        <input 
                          type="checkbox" 
                          checked={config.duplicate_columns.apply}
                          onChange={(e) => handleConfigChange('duplicate_columns', 'apply', e.target.checked)}
                        />
                        Remove Duplicate Columns
                      </label>
                      <label className="checkbox-container">
                        <input 
                          type="checkbox" 
                          checked={config.constant_columns.apply}
                          onChange={(e) => handleConfigChange('constant_columns', 'apply', e.target.checked)}
                        />
                        Drop Constant Columns
                      </label>
                      <label className="checkbox-container">
                        <input 
                          type="checkbox" 
                          checked={config.empty_columns.apply}
                          onChange={(e) => handleConfigChange('empty_columns', 'apply', e.target.checked)}
                        />
                        Drop 100% Empty Columns
                      </label>
                      <label className="checkbox-container">
                        <input 
                          type="checkbox" 
                          checked={config.mixed_types.apply}
                          onChange={(e) => handleConfigChange('mixed_types', 'apply', e.target.checked)}
                        />
                        Normalize Mixed Data Placeholders
                      </label>
                    </div>
                  </div>

                  {/* Standardize Dates */}
                  <div className="options-group">
                    <label className="checkbox-container group-header">
                      <input 
                        type="checkbox" 
                        checked={config.invalid_dates.apply}
                        onChange={(e) => handleConfigChange('invalid_dates', 'apply', e.target.checked)}
                      />
                      📅 Standardize Inconsistent Dates
                    </label>
                    {config.invalid_dates.apply && (
                      <div className="group-body">
                        <div className="form-item">
                          <label>Target Format:</label>
                          <select 
                            value={config.invalid_dates.format}
                            onChange={(e) => handleConfigChange('invalid_dates', 'format', e.target.value)}
                          >
                            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                          </select>
                        </div>
                        <div className="column-select-box">
                          <label>Select Date Columns:</label>
                          <div className="checkbox-scroll-list">
                            {columns.map(col => (
                              <label key={col} className="column-checkbox">
                                <input 
                                  type="checkbox"
                                  checked={config.invalid_dates.columns?.includes(col)}
                                  onChange={() => handleListToggle('invalid_dates', col)}
                                />
                                {col}
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Emails handling */}
                  <div className="options-group">
                    <label className="checkbox-container group-header">
                      <input 
                        type="checkbox" 
                        checked={config.invalid_emails.apply}
                        onChange={(e) => handleConfigChange('invalid_emails', 'apply', e.target.checked)}
                      />
                      ✉️ Handle Malformed Emails
                    </label>
                    {config.invalid_emails.apply && (
                      <div className="group-body">
                        <div className="form-item">
                          <label>Strategy:</label>
                          <select 
                            value={config.invalid_emails.strategy}
                            onChange={(e) => handleConfigChange('invalid_emails', 'strategy', e.target.value)}
                          >
                            <option value="remove">Remove (Set to Null)</option>
                            <option value="mark">Mark as &apos;INVALID_EMAIL&apos;</option>
                          </select>
                        </div>
                        <div className="column-select-box">
                          <label>Select Email Columns:</label>
                          <div className="checkbox-scroll-list">
                            {columns.map(col => (
                              <label key={col} className="column-checkbox">
                                <input 
                                  type="checkbox"
                                  checked={config.invalid_emails.columns?.includes(col)}
                                  onChange={() => handleListToggle('invalid_emails', col)}
                                />
                                {col}
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Phone handling */}
                  <div className="options-group">
                    <label className="checkbox-container group-header">
                      <input 
                        type="checkbox" 
                        checked={config.invalid_phones.apply}
                        onChange={(e) => handleConfigChange('invalid_phones', 'apply', e.target.checked)}
                      />
                      📞 Normalize Phone Formats
                    </label>
                    {config.invalid_phones.apply && (
                      <div className="group-body">
                        <div className="column-select-box">
                          <label>Select Phone Columns:</label>
                          <div className="checkbox-scroll-list">
                            {columns.map(col => (
                              <label key={col} className="column-checkbox">
                                <input 
                                  type="checkbox"
                                  checked={config.invalid_phones.columns?.includes(col)}
                                  onChange={() => handleListToggle('invalid_phones', col)}
                                />
                                {col}
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Outliers */}
                  <div className="options-group">
                    <label className="checkbox-container group-header">
                      <input 
                        type="checkbox" 
                        checked={config.outliers.apply}
                        onChange={(e) => handleConfigChange('outliers', 'apply', e.target.checked)}
                      />
                      📊 Outlier Handling
                    </label>
                    {config.outliers.apply && (
                      <div className="group-body">
                        <div className="form-item">
                          <label>Strategy:</label>
                          <select 
                            value={config.outliers.strategy}
                            onChange={(e) => handleConfigChange('outliers', 'strategy', e.target.value)}
                          >
                            <option value="cap">Cap Outliers (Winsorize)</option>
                            <option value="remove">Remove Rows</option>
                          </select>
                        </div>
                        <div className="column-select-box">
                          <label>Select Numeric Columns:</label>
                          <div className="checkbox-scroll-list">
                            {numericalCols.map(col => (
                              <label key={col} className="column-checkbox">
                                <input 
                                  type="checkbox"
                                  checked={config.outliers.columns?.includes(col)}
                                  onChange={() => handleListToggle('outliers', col)}
                                />
                                {col}
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Missing Values details */}
                  <div className="options-group">
                    <label className="checkbox-container group-header">
                      <input 
                        type="checkbox" 
                        checked={config.missing_values.apply}
                        onChange={(e) => handleConfigChange('missing_values', 'apply', e.target.checked)}
                      />
                      📍 Missing Value Imputation
                    </label>
                    {config.missing_values.apply && (
                      <div className="group-body flex-list">
                        <label className="sub-instruction">Set strategies per column:</label>
                        <div className="missing-strategies-grid">
                          {columns.map(col => (
                            <div key={col} className="strategy-grid-item">
                              <span className="col-lbl">{col}:</span>
                              <select 
                                value={config.missing_values.strategies[col] || 'mode'}
                                onChange={(e) => handleMissingStrategyChange(col, e.target.value)}
                              >
                                <option value="mode">Mode</option>
                                <option value="mean">Mean (numeric)</option>
                                <option value="median">Median (numeric)</option>
                                <option value="constant">Constant</option>
                                <option value="ffill">Forward Fill</option>
                                <option value="bfill">Backward Fill</option>
                                <option value="drop_rows">Drop Rows</option>
                                <option value="drop_columns">Drop Column</option>
                              </select>
                              {config.missing_values.strategies[col] === 'constant' && (
                                <input 
                                  type="text"
                                  placeholder="Constant value..."
                                  value={config.missing_values.constant_values[col] || ''}
                                  onChange={(e) => handleMissingConstantChange(col, e.target.value)}
                                  className="compact-input"
                                />
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Text Case Normalization */}
                  <div className="options-group">
                    <label className="checkbox-container group-header">
                      <input 
                        type="checkbox" 
                        checked={config.text_normalization.apply}
                        onChange={(e) => handleConfigChange('text_normalization', 'apply', e.target.checked)}
                      />
                      🔤 Text Case Normalization
                    </label>
                    {config.text_normalization.apply && (
                      <div className="group-body flex-list">
                        <div className="missing-strategies-grid">
                          {columns.map(col => (
                            <div key={col} className="strategy-grid-item">
                              <span className="col-lbl">{col}:</span>
                              <select 
                                value={config.text_normalization.strategies[col] || 'lower'}
                                onChange={(e) => handleTextNormalizationChange(col, e.target.value)}
                              >
                                <option value="lower">lower case</option>
                                <option value="upper">UPPER CASE</option>
                                <option value="title">Title Case</option>
                              </select>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                </div>
              )}

              <div className="preview-action-row">
                <button 
                  className="primary-btn wide-btn"
                  onClick={handleGeneratePreview}
                  disabled={previewLoading || loading}
                >
                  {previewLoading ? '⏳ Generating Preview...' : '🔬 Generate Cleaning Preview'}
                </button>
              </div>
            </div>
          </div>

          {/* RIGHT: Preview Report Dashboard */}
          <div className="cleaning-preview-section">
            <div className="dashboard-card preview-card-outer">
              <h4>2. Preview Report Summary</h4>
              
              {previewLoading && (
                <div className="preview-skeleton-loader">
                  <div className="skeleton-row short"></div>
                  <div className="skeleton-row mt-15"></div>
                  <div className="skeleton-row"></div>
                  <div className="skeleton-row medium"></div>
                </div>
              )}

              {!previewLoading && !previewReport && (
                <div className="preview-empty-report">
                  <span className="radar-icon">🔬</span>
                  <h5>No Preview Generated</h5>
                  <p>Choose your cleaning strategy configuration on the left, then click <strong>Generate Cleaning Preview</strong> to calculate estimates before writing any changes.</p>
                </div>
              )}

              {!previewLoading && previewReport && (
                <div className="preview-results-content animation-slide-down">
                  <div className="preview-metrics-split">
                    <div className="split-metric">
                      <h5>Rows Before</h5>
                      <p>{previewReport.rows_before?.toLocaleString()}</p>
                    </div>
                    <div className="split-metric highlight">
                      <h5>Rows After</h5>
                      <p>{previewReport.rows_after?.toLocaleString()}</p>
                    </div>
                    <div className="split-metric">
                      <h5>Columns Before</h5>
                      <p>{previewReport.columns_before?.toLocaleString()}</p>
                    </div>
                    <div className="split-metric highlight">
                      <h5>Columns After</h5>
                      <p>{previewReport.columns_after?.toLocaleString()}</p>
                    </div>
                  </div>

                  <div className="change-details-list mt-15">
                    <div className="detail-stat-item">
                      <span className="lbl">Estimated Cells Modified:</span>
                      <span className="val highlight">{previewReport.estimated_changes?.toLocaleString()}</span>
                    </div>
                    <div className="detail-stat-item">
                      <span className="lbl">Potential Data Loss:</span>
                      <span className={`val badge ${previewReport.potential_data_loss.includes('High') ? 'danger' : previewReport.potential_data_loss.includes('Medium') ? 'warning' : 'success'}`}>
                        {previewReport.potential_data_loss}
                      </span>
                    </div>
                  </div>

                  <div className="preview-ops-applied mt-15">
                    <h5>Cleaning Operations to Apply:</h5>
                    <ul>
                      {previewReport.operations_to_apply?.map((op, idx) => (
                        <li key={idx}>⚡ {op}</li>
                      ))}
                    </ul>
                  </div>

                  <button 
                    className="apply-clean-btn mt-15"
                    onClick={() => setShowConfirmModal(true)}
                  >
                    🚀 Apply Cleaning Operations
                  </button>
                </div>
              )}
            </div>
          </div>

        </div>
      )}

      {selectedDatasetId && cleaningStatus === 'idle' && subTab === 'recommendations' && (
        <DataCleaningRecommendations 
          token={token} 
          datasetId={selectedDatasetId} 
          showNotification={showNotification} 
          onApplyRecommendation={handleApplyRecommendation} 
        />
      )}

      {selectedDatasetId && cleaningStatus === 'idle' && subTab === 'versions' && (
        <DataCleaningVersions 
          token={token} 
          datasetId={selectedDatasetId} 
          showNotification={showNotification} 
          onRollbackComplete={() => {
            if (onCleanComplete) onCleanComplete();
          }} 
        />
      )}

      {selectedDatasetId && cleaningStatus === 'idle' && subTab === 'audit' && (
        <DataCleaningAudit 
          token={token} 
          datasetId={selectedDatasetId} 
          showNotification={showNotification} 
        />
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="custom-modal-backdrop animation-fade-in">
          <div className="custom-modal-card">
            <h4>⚠️ Confirm Auto Cleaning Execution</h4>
            <p>You are about to execute the cleaning operations. This will overwrite the uploaded dataset file on server disk and re-map the dynamic SQL database table. This action cannot be undone.</p>
            
            <div className="modal-actions">
              <button 
                className="modal-cancel-btn"
                onClick={() => setShowConfirmModal(false)}
                disabled={loading}
              >
                Cancel
              </button>
              <button 
                className="modal-confirm-btn"
                onClick={handleApplyClean}
                disabled={loading}
              >
                Yes, Apply and Overwrite
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataCleaning;
