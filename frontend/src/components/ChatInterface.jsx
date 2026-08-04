import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE_URL } from '../config/api';
import DatabaseConnections from './DatabaseConnections';
import DataProfiling from './DataProfiling';
import DataCleaning from './DataCleaning';
import DataInsights from './DataInsights';
import DataDashboard from './DataDashboard';
import UnauthorizedPage from './UnauthorizedPage';
import UserRolesConsole from './UserRolesConsole';
import SecuritySettings from './SecuritySettings';
import SystemHealth from './SystemHealth';
import TaskCenter from './TaskCenter';
import PerformanceDashboard from './PerformanceDashboard';
import ModelManagement from './ModelManagement';
import NaturalLanguageSQL from './NaturalLanguageSQL';
import AICleaningAssistant from './AICleaningAssistant';
import DocumentChat from './DocumentChat';
import MultiAgentAnalytics from './MultiAgentAnalytics';
import ExplainabilityDashboard from './ExplainabilityDashboard';
import ReportCenter from './ReportCenter';
import PromptManager from './PromptManager';
import EvaluationDashboard from './EvaluationDashboard';
import ModelRegistry from './ModelRegistry';
import SystemStatus from './SystemStatus';
import KnowledgeGraph from './KnowledgeGraph';
import FederatedQuery from './FederatedQuery';
import WorkflowBuilder from './WorkflowBuilder';
import WorkflowExecution from './WorkflowExecution';
import WorkflowTemplates from './WorkflowTemplates';
import StreamingDashboard from './StreamingDashboard';
import AICopilot from './AICopilot';
import PredictiveAnalytics from './PredictiveAnalytics';
import PluginManager from './PluginManager';
import ClusterDashboard from './ClusterDashboard';




// Chart.js imports
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip as ChartTooltip,
  Legend
} from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  ChartTooltip,
  Legend
);

const ChatInterface = () => {
  const { token, logout, user } = useAuth();
  
  const userRole = user?.role || 'Viewer';
  const rolePermissions = {
    'Admin': ['user_management', 'rollback', 'versioning', 'ai_recommendations', 'clean', 'upload', 'analyze', 'profile', 'dashboard_write', 'view'],
    'Data Scientist': ['rollback', 'versioning', 'ai_recommendations', 'clean', 'upload', 'analyze', 'profile', 'dashboard_write', 'view'],
    'Data Analyst': ['clean', 'upload', 'analyze', 'profile', 'dashboard_write', 'view'],
    'Viewer': ['view']
  };

  const hasPermission = (perm) => {
    const allowed = rolePermissions[userRole] || ['view'];
    return allowed.includes(perm);
  };
  
  // Datasets state
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null); // null = default DB
  const [selectedDataset, setSelectedDataset] = useState(null);
  
  // Database Connections state
  const [dbConnections, setDbConnections] = useState([]);
  const [selectedDbConnId, setSelectedDbConnId] = useState(null);
  const [selectedDbConnSchema, setSelectedDbConnSchema] = useState(null);
  const [activeSchemaTable, setActiveSchemaTable] = useState(null);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Chat state
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  
  // UI Navigation
  const [activeTab, setActiveTab] = useState('chat'); // 'chat', 'eda', 'schema', 'connections'
  const [workflowSubTab, setWorkflowSubTab] = useState('builder');
  const [templateToLoad, setTemplateToLoad] = useState(null);
  
  // Notification state
  const [notification, setNotification] = useState(null);

  // Fetch datasets and database connections on mount
  useEffect(() => {
    fetchDatasets();
    fetchDbConnections();
  }, []);

  // Poll for background task notifications
  useEffect(() => {
    if (!token) return;
    
    const pollNotifications = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/tasks/notifications`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (response.data && response.data.notifications && response.data.notifications.length > 0) {
          response.data.notifications.forEach(n => {
            showNotification(`${n.title}: ${n.message}`, n.severity || 'info');
          });
        }
      } catch (error) {
        console.error('Error polling notifications:', error);
      }
    };
    
    const interval = setInterval(pollNotifications, 5000);
    return () => clearInterval(interval);
  }, [token]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Fetch details when selected dataset changes
  useEffect(() => {
    setMessages([]); // Clear active chat history on context change to keep clean states
    if (selectedDatasetId) {
      setSelectedDbConnId(null);
      setSelectedDbConnSchema(null);
      fetchDatasetDetails(selectedDatasetId);
    } else {
      setSelectedDataset(null);
      setActiveTab('chat');
    }
  }, [selectedDatasetId]);

  // Fetch schema when selected database connection changes
  useEffect(() => {
    setMessages([]); // Clear active chat history on context change to keep clean states
    if (selectedDbConnId) {
      setSelectedDatasetId(null);
      setSelectedDataset(null);
      fetchDbSchema(selectedDbConnId);
      setActiveTab('chat');
    } else {
      setSelectedDbConnSchema(null);
      setActiveTab('chat');
    }
  }, [selectedDbConnId]);

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };

  const fetchDatasets = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDatasets(response.data);
    } catch (error) {
      showNotification('Failed to fetch datasets list', 'error');
    }
  };

  const fetchDatasetDetails = async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedDataset(response.data);
    } catch (error) {
      showNotification('Failed to load dataset details', 'error');
      setSelectedDatasetId(null);
    }
  };

  // Fetch DB connections list
  const fetchDbConnections = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/database/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDbConnections(response.data);
    } catch (error) {
      showNotification('Failed to fetch database connections list', 'error');
    }
  };

  // Fetch dynamic DB connection schema
  const fetchDbSchema = async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/database/${id}/schema`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedDbConnSchema(response.data.schema);
      const tables = Object.keys(response.data.schema);
      if (tables.length > 0) {
        setActiveSchemaTable(tables[0]);
      } else {
        setActiveSchemaTable(null);
      }
    } catch (error) {
      showNotification('Failed to load database schema details', 'error');
      setSelectedDbConnId(null);
    }
  };

  // Drag and Drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      validateAndUploadFile(files[0]);
    }
  };

  const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      validateAndUploadFile(files[0]);
    }
  };

  const validateAndUploadFile = (file) => {
    const allowedExtensions = ['csv', 'xlsx', 'xls', 'json'];
    const ext = file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(ext)) {
      showNotification('Unsupported file type. Please upload CSV, Excel, or JSON.', 'error');
      return;
    }

    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      showNotification('File exceeds the 50 MB limit.', 'error');
      return;
    }

    uploadFile(file);
  };

  const uploadFile = async (file) => {
    setUploading(true);
    setUploadProgress(0);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/datasets/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          }
        }
      );

      showNotification(`File "${file.name}" uploaded successfully!`, 'success');
      await fetchDatasets();
      setSelectedDatasetId(response.data.id);
      setActiveTab('profiling');
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Upload failed', 'error');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteDataset = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this dataset? This will drop the table and delete the file.')) return;
    
    try {
      await axios.delete(`${API_BASE_URL}/datasets/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Dataset deleted', 'success');
      if (selectedDatasetId === id) {
        setSelectedDatasetId(null);
      }
      fetchDatasets();
    } catch (error) {
      showNotification('Failed to delete dataset', 'error');
    }
  };

  const handleDeleteConnectionSidebar = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this database connection configuration?')) return;
    try {
      await axios.delete(`${API_BASE_URL}/database/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Database connection configuration deleted', 'success');
      if (selectedDbConnId === id) {
        setSelectedDbConnId(null);
      }
      fetchDbConnections();
    } catch (error) {
      showNotification('Failed to delete database connection', 'error');
    }
  };

  const handleChatSubmit = async () => {
    if (!question.trim() || loading) return;

    const userMsgText = question;
    setQuestion('');
    setLoading(true);
    
    setMessages(prev => [...prev, { role: 'user', content: userMsgText }]);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/query/`,
        {
          question: userMsgText,
          dataset_id: selectedDatasetId,
          db_connection_id: selectedDbConnId
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const data = response.data;
      if (data.success) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.explanation || 'Query executed successfully',
          sql: data.sql,
          data: data.data,
          chart_type: data.chart_type,
          chart_data: data.chart_data
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${data.error || 'Failed to process query'}`
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error: ' + (error.response?.data?.detail || error.message)
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleChatSubmit();
    }
  };

  const handleCopySQL = (sqlText) => {
    navigator.clipboard.writeText(sqlText);
    showNotification('SQL copied to clipboard!', 'success');
  };

  const renderChart = (msg, idx) => {
    if (!msg.chart_data || !msg.chart_data.datasets || msg.chart_data.datasets.length === 0) return null;
    
    const chartData = msg.chart_data;
    
    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#374151', font: { family: 'Outfit, sans-serif', size: 12 } }
        },
        title: {
          display: true,
          text: `Visualization (${msg.chart_type.toUpperCase()})`,
          color: '#111827',
          font: { family: 'Outfit, sans-serif', size: 14, weight: 'bold' }
        }
      },
      scales: msg.chart_type !== 'pie' ? {
        y: {
          ticks: { color: '#4b5563', font: { family: 'Outfit, sans-serif' } },
          grid: { color: 'rgba(243, 244, 246, 1)' }
        },
        x: {
          ticks: { color: '#4b5563', font: { family: 'Outfit, sans-serif' } },
          grid: { display: false }
        }
      } : {}
    };

    return (
      <div className="chart-wrapper" key={`chart-${idx}`}>
        {msg.chart_type === 'bar' && <Bar data={chartData} options={options} height={280} />}
        {msg.chart_type === 'line' && <Line data={chartData} options={options} height={280} />}
        {msg.chart_type === 'pie' && <Pie data={chartData} options={options} height={280} />}
        {msg.chart_type === 'scatter' && <Scatter data={chartData} options={options} height={280} />}
      </div>
    );
  };

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {notification && (
        <div className={`notification-toast ${notification.type}`}>
          {notification.type === 'success' ? '✅' : '⚠️'} {notification.message}
        </div>
      )}

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <span className="brand-icon">🤖</span>
            <div className="brand-text">
              <h2>AI Data Analyst</h2>
              <span className="version">v2.0 Enterprise</span>
            </div>
          </div>
        </div>

        {/* Drag and Drop Upload */}
        <div 
          className={`upload-zone ${dragOver ? 'dragover' : ''} ${uploading ? 'uploading' : ''} ${!hasPermission('upload') ? 'disabled' : ''}`}
          onDragOver={hasPermission('upload') ? handleDragOver : (e) => e.preventDefault()}
          onDragLeave={hasPermission('upload') ? handleDragLeave : undefined}
          onDrop={hasPermission('upload') ? handleDrop : (e) => e.preventDefault()}
          onClick={() => hasPermission('upload') && !uploading && fileInputRef.current.click()}
          style={!hasPermission('upload') ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileSelect} 
            style={{ display: 'none' }} 
            accept=".csv, .xlsx, .xls, .json"
            disabled={uploading}
          />
          {uploading ? (
            <div className="upload-progress-container">
              <span className="upload-icon-spinner">⏳</span>
              <p>Uploading dataset...</p>
              <div className="progress-bar-bg">
                <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }}></div>
              </div>
              <span className="progress-percent">{uploadProgress}%</span>
            </div>
          ) : (
            <div className="upload-idle">
              <span className="upload-icon">📤</span>
              {hasPermission('upload') ? (
                <>
                  <h4>Upload Dataset</h4>
                  <p>Drag & drop or click</p>
                  <span className="file-formats">CSV, Excel, JSON (Max 50MB)</span>
                </>
              ) : (
                <>
                  <h4>Upload Restricted</h4>
                  <p>Contact Admin to upload datasets</p>
                </>
              )}
            </div>
          )}
        </div>

        {/* Datasets Menu */}
        <div className="datasets-menu">
          <h3>📂 Flat Datasets</h3>
          <div className="datasets-list">
            <div 
              className={`dataset-item ${selectedDatasetId === null && selectedDbConnId === null ? 'active' : ''}`}
              onClick={() => {
                setSelectedDatasetId(null);
                setSelectedDbConnId(null);
              }}
            >
              <span className="ds-icon">💾</span>
              <div className="ds-info">
                <span className="ds-name">Default Database</span>
                <span className="ds-meta">System (sales, products)</span>
              </div>
            </div>
            
            {datasets.map(ds => (
              <div 
                key={ds.id} 
                className={`dataset-item ${selectedDatasetId === ds.id ? 'active' : ''}`}
                onClick={() => {
                  setSelectedDatasetId(ds.id);
                }}
              >
                <span className="ds-icon">📊</span>
                <div className="ds-info">
                  <span className="ds-name" title={ds.filename}>{ds.filename}</span>
                  <span className="ds-meta">{ds.row_count} rows • {ds.col_count} columns</span>
                </div>
                {hasPermission('clean') && (
                  <button 
                    className="ds-delete-btn" 
                    onClick={(e) => handleDeleteDataset(e, ds.id)}
                    title="Remove Dataset"
                  >
                    🗑️
                  </button>
                )}
              </div>
            ))}
          </div>
          
          <div className="db-sidebar-header">
            <h3>🔌 Enterprise Databases</h3>
            {hasPermission('upload') && (
              <button className="add-db-btn" onClick={() => setActiveTab('connections')} title="Manage Connections">⚙️ Manage</button>
            )}
          </div>
          
          <div className="datasets-list">
            {dbConnections.map(conn => (
              <div 
                key={conn.id} 
                className={`dataset-item ${selectedDbConnId === conn.id ? 'active' : ''}`}
                onClick={() => {
                  setSelectedDbConnId(conn.id);
                }}
              >
                <span className="ds-icon">
                  {conn.db_type === 'postgresql' ? '🐘' : (conn.db_type === 'sqlite' ? '🐚' : '🐬')}
                </span>
                <div className="ds-info">
                  <span className="ds-name" title={conn.name}>{conn.name}</span>
                  <span className="ds-meta">{conn.db_type.toUpperCase()} • {conn.database}</span>
                </div>
                <button 
                  className="ds-delete-btn" 
                  onClick={(e) => handleDeleteConnectionSidebar(e, conn.id)}
                  title="Disconnect Database"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* User profile / Logout */}
        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="avatar">{user?.full_name ? user.full_name[0].toUpperCase() : 'U'}</div>
            <div className="user-details">
              <span className="name">{user?.full_name || 'User'}</span>
              <span className="email">{user?.email}</span>
              {user?.role && <span className="user-role-badge">{user.role}</span>}
            </div>
          </div>
          <button className="logout-btn" onClick={logout}>Sign Out 🚪</button>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="main-panel">
        {/* Navigation Bar */}
        <header className="main-header">
          <div className="active-dataset">
            <span className="indicator"></span>
            <h4>
              Active Context: {
                selectedDataset ? selectedDataset.filename : 
                (selectedDbConnId ? dbConnections.find(c => c.id === selectedDbConnId)?.name || 'Remote Database' : 'Default Database')
              }
            </h4>
          </div>
          
          <div className="tab-navigation">
            <button 
              className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              💬 Ask Assistant
            </button>
            <button 
              className={`tab-btn ${activeTab === 'copilot' ? 'active' : ''}`}
              onClick={() => setActiveTab('copilot')}
            >
              🤖 AI Copilot
            </button>
            <button 
              className={`tab-btn ${activeTab === 'predictive' ? 'active' : ''}`}
              onClick={() => setActiveTab('predictive')}
            >
              🧠 Predictive Analytics
            </button>
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'nl2sql' ? 'active' : ''}`}
                onClick={() => setActiveTab('nl2sql')}
              >
                🧠 NL2SQL Chat
              </button>
            )}
            {selectedDataset && (
              <button 
                className={`tab-btn ${activeTab === 'eda' ? 'active' : ''}`}
                onClick={() => setActiveTab('eda')}
              >
                📊 Dashboard & EDA
              </button>
            )}
            {datasets && datasets.length > 0 && hasPermission('profile') && (
              <button 
                className={`tab-btn ${activeTab === 'profiling' ? 'active' : ''}`}
                onClick={() => setActiveTab('profiling')}
              >
                📊 Data Profiling
              </button>
            )}
            {datasets && datasets.length > 0 && hasPermission('clean') && (
              <button 
                className={`tab-btn ${activeTab === 'cleaning' ? 'active' : ''}`}
                onClick={() => setActiveTab('cleaning')}
              >
                🧹 Data Cleaning
              </button>
            )}
            {datasets && datasets.length > 0 && hasPermission('clean') && (
              <button 
                className={`tab-btn ${activeTab === 'ai_cleaning' ? 'active' : ''}`}
                onClick={() => setActiveTab('ai_cleaning')}
              >
                🪄 AI Cleaning
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'document_chat' ? 'active' : ''}`}
                onClick={() => setActiveTab('document_chat')}
              >
                📁 Document Chat
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'multi_agent' ? 'active' : ''}`}
                onClick={() => setActiveTab('multi_agent')}
              >
                🤖 Multi-Agent QA
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'xai' ? 'active' : ''}`}
                onClick={() => setActiveTab('xai')}
              >
                🔍 XAI Explanations
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
                onClick={() => setActiveTab('reports')}
              >
                📄 Report Center
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'prompts' ? 'active' : ''}`}
                onClick={() => setActiveTab('prompts')}
              >
                📖 Prompts
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'evaluation' ? 'active' : ''}`}
                onClick={() => setActiveTab('evaluation')}
              >
                🔬 Evaluation
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'models' ? 'active' : ''}`}
                onClick={() => setActiveTab('models')}
              >
                🖥️ Models
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'workflows' ? 'active' : ''}`}
                onClick={() => setActiveTab('workflows')}
              >
                ⛓️ Workflows
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'streaming' ? 'active' : ''}`}
                onClick={() => setActiveTab('streaming')}
              >
                📡 Streaming
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
                onClick={() => setActiveTab('knowledge')}
              >
                🧠 Knowledge Graph
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'federation' ? 'active' : ''}`}
                onClick={() => setActiveTab('federation')}
              >
                🌐 Federated Query
              </button>
            )}
            {hasPermission('admin') && (
              <button 
                className={`tab-btn ${activeTab === 'status' ? 'active' : ''}`}
                onClick={() => setActiveTab('status')}
              >
                🖥️ System Status
              </button>
            )}
            {datasets && datasets.length > 0 && hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'insights' ? 'active' : ''}`}
                onClick={() => setActiveTab('insights')}
              >
                🧠 AI Insights
              </button>
            )}
            {datasets && datasets.length > 0 && hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('dashboard')}
              >
                🖥️ Dashboard
              </button>
            )}
            {hasPermission('user_management') && (
              <button 
                className={`tab-btn ${activeTab === 'roles' ? 'active' : ''}`}
                onClick={() => setActiveTab('roles')}
              >
                🔑 Access Control
              </button>
            )}
            {selectedDbConnSchema && (
              <button 
                className={`tab-btn ${activeTab === 'schema' ? 'active' : ''}`}
                onClick={() => setActiveTab('schema')}
              >
                📂 Schema Catalog
              </button>
            )}
            {hasPermission('upload') && (
              <button 
                className={`tab-btn ${activeTab === 'connections' ? 'active' : ''}`}
                onClick={() => setActiveTab('connections')}
              >
                🔌 Databases
              </button>
            )}
            <button 
              className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`}
              onClick={() => setActiveTab('security')}
            >
              🛡️ Security
            </button>
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'health' ? 'active' : ''}`}
                onClick={() => setActiveTab('health')}
              >
                🏥 System Health
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'tasks' ? 'active' : ''}`}
                onClick={() => setActiveTab('tasks')}
              >
                ⚙️ Task Center
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'performance' ? 'active' : ''}`}
                onClick={() => setActiveTab('performance')}
              >
                ⚡ Performance
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'llm' ? 'active' : ''}`}
                onClick={() => setActiveTab('llm')}
              >
                🤖 LLM Settings
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'plugins' ? 'active' : ''}`}
                onClick={() => setActiveTab('plugins')}
              >
                🔌 Plugins
              </button>
            )}
            {hasPermission('view') && (
              <button 
                className={`tab-btn ${activeTab === 'cluster' ? 'active' : ''}`}
                onClick={() => setActiveTab('cluster')}
              >
                ⛓️ Cluster Nodes
              </button>
            )}
          </div>
        </header>

        {/* Active Tab Contents */}
        <div className="content-container">
          {activeTab === 'cluster' ? (
            <ClusterDashboard
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'plugins' ? (
            <PluginManager
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'copilot' ? (
            <AICopilot
              token={token}
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              selectedDbConnId={selectedDbConnId}
              showNotification={showNotification}
            />
          ) : activeTab === 'predictive' ? (
            <PredictiveAnalytics
              token={token}
              datasets={datasets}
              showNotification={showNotification}
            />
          ) : activeTab === 'cleaning' && !hasPermission('clean') ? (
            <UnauthorizedPage requiredPermission="clean" onBack={() => setActiveTab('chat')} />
          ) : activeTab === 'cleaning' ? (
            <DataCleaning
              token={token}
              datasets={datasets}
              showNotification={showNotification}
              initialDatasetId={selectedDatasetId}
              onCleanComplete={() => {
                fetchDatasets();
              }}
            />
          ) : activeTab === 'insights' && !hasPermission('view') ? (
            <UnauthorizedPage requiredPermission="view" onBack={() => setActiveTab('chat')} />
          ) : activeTab === 'insights' ? (
            <DataInsights
              token={token}
              datasets={datasets}
              showNotification={showNotification}
              initialDatasetId={selectedDatasetId}
            />
          ) : activeTab === 'dashboard' && !hasPermission('view') ? (
            <UnauthorizedPage requiredPermission="view" onBack={() => setActiveTab('chat')} />
          ) : activeTab === 'dashboard' ? (
            <DataDashboard
              token={token}
              datasets={datasets}
              showNotification={showNotification}
              initialDatasetId={selectedDatasetId}
            />
          ) : activeTab === 'profiling' && !hasPermission('profile') ? (
            <UnauthorizedPage requiredPermission="profile" onBack={() => setActiveTab('chat')} />
          ) : activeTab === 'profiling' ? (
            <DataProfiling
              token={token}
              datasets={datasets}
              showNotification={showNotification}
              initialDatasetId={selectedDatasetId}
            />
          ) : activeTab === 'connections' && !hasPermission('upload') ? (
            <UnauthorizedPage requiredPermission="upload" onBack={() => setActiveTab('chat')} />
          ) : activeTab === 'connections' ? (
            <DatabaseConnections
              token={token}
              dbConnections={dbConnections}
              selectedDbConnId={selectedDbConnId}
              onSelectConnection={(id) => {
                setSelectedDbConnId(id);
                if (id) {
                  setActiveTab('schema');
                } else {
                  setActiveTab('chat');
                }
              }}
              onConnectionsChanged={fetchDbConnections}
            />
          ) : activeTab === 'roles' && !hasPermission('user_management') ? (
            <UnauthorizedPage requiredPermission="user_management" onBack={() => setActiveTab('chat')} />
          ) : activeTab === 'roles' ? (
            <UserRolesConsole
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'security' ? (
            <SecuritySettings
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'health' ? (
            <SystemHealth
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'tasks' ? (
            <TaskCenter
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'performance' ? (
            <PerformanceDashboard
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'llm' ? (
            <ModelManagement
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'nl2sql' ? (
            <NaturalLanguageSQL
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'ai_cleaning' ? (
            <AICleaningAssistant
              token={token}
              datasets={datasets}
              showNotification={showNotification}
              initialDatasetId={selectedDatasetId}
            />
          ) : activeTab === 'document_chat' ? (
            <DocumentChat
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'multi_agent' ? (
            <MultiAgentAnalytics
              token={token}
              datasets={datasets}
              showNotification={showNotification}
            />
          ) : activeTab === 'xai' ? (
            <ExplainabilityDashboard
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'reports' ? (
            <ReportCenter
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'prompts' ? (
            <PromptManager
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'evaluation' ? (
            <EvaluationDashboard
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'models' ? (
            <ModelRegistry
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'streaming' ? (
            <StreamingDashboard
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'workflows' ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '15px' }}>
              <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid #334155', paddingBottom: '10px' }}>
                <button 
                  className={`tab-btn ${workflowSubTab === 'builder' ? 'active' : ''}`}
                  onClick={() => setWorkflowSubTab('builder')}
                  style={{ padding: '6px 15px', fontSize: '13px' }}
                >
                  🛠️ Builder Canvas
                </button>
                <button 
                  className={`tab-btn ${workflowSubTab === 'executions' ? 'active' : ''}`}
                  onClick={() => setWorkflowSubTab('executions')}
                  style={{ padding: '6px 15px', fontSize: '13px' }}
                >
                  ⏱️ Live Executions & Logs
                </button>
                <button 
                  className={`tab-btn ${workflowSubTab === 'templates' ? 'active' : ''}`}
                  onClick={() => setWorkflowSubTab('templates')}
                  style={{ padding: '6px 15px', fontSize: '13px' }}
                >
                  📚 Pipeline Templates
                </button>
              </div>
              <div style={{ flex: 1, minHeight: 0 }}>
                {workflowSubTab === 'builder' && (
                  <WorkflowBuilder 
                    token={token} 
                    datasets={datasets} 
                    showNotification={showNotification} 
                  />
                )}
                {workflowSubTab === 'executions' && (
                  <WorkflowExecution 
                    token={token} 
                    showNotification={showNotification} 
                  />
                )}
                {workflowSubTab === 'templates' && (
                  <WorkflowTemplates 
                    onLoadTemplate={(tmpl) => {
                      setWorkflowSubTab('builder');
                      sessionStorage.setItem('loaded_workflow_template', JSON.stringify(tmpl));
                      window.dispatchEvent(new Event('storage'));
                    }}
                  />
                )}
              </div>
            </div>
          ) : activeTab === 'knowledge' ? (
            <KnowledgeGraph
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'federation' ? (
            <FederatedQuery
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'status' ? (
            <SystemStatus
              token={token}
              showNotification={showNotification}
            />
          ) : activeTab === 'chat' ? (
            /* Chat Tab */
            <div className="chat-interface">
              <div className="messages-feed">
                {messages.length === 0 ? (
                  <div className="chat-placeholder">
                    <span className="welcome-icon">💬</span>
                    <h3>Chat with your Data Analyst</h3>
                    <p>Ask questions in natural language. The AI will translate them into secure SQL, fetch the rows, and design visual charts for you.</p>
                    <div className="suggested-questions">
                      <h4>Suggested queries:</h4>
                      <ul>
                        <li onClick={() => setQuestion("Show total sales by region")}>&quot;Show total sales by region&quot;</li>
                        {selectedDataset ? (
                          <li onClick={() => setQuestion(`Summarize table ${selectedDataset.table_name}`)}>&quot;Summarize this dataset&quot;</li>
                        ) : (
                          selectedDbConnSchema && Object.keys(selectedDbConnSchema).length > 0 ? (
                            <li onClick={() => setQuestion(`Show rows from table ${Object.keys(selectedDbConnSchema)[0]} limit 10`)}>{`"Show records from table ${Object.keys(selectedDbConnSchema)[0]}"`}</li>
                          ) : (
                            <li onClick={() => setQuestion("List top products category-wise")}>&quot;List top products category-wise&quot;</li>
                          )
                        )}
                      </ul>
                    </div>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <div key={idx} className={`chat-bubble-row ${msg.role}`}>
                      <div className="chat-avatar">{msg.role === 'user' ? '👤' : '🤖'}</div>
                      <div className="chat-bubble-card">
                        <div className="chat-bubble-header">
                          <strong>{msg.role === 'user' ? 'You' : 'Analyst AI'}</strong>
                          <span className="timestamp">{new Date().toLocaleTimeString()}</span>
                        </div>
                        <div className="chat-bubble-body">
                          <p>{msg.content}</p>
                          
                          {/* Render generated SQL */}
                          {msg.sql && (
                            <div className="sql-card">
                              <div className="sql-card-header">
                                <span>Generated SQL</span>
                                <button className="copy-btn" onClick={() => handleCopySQL(msg.sql)}>Copy SQL 📋</button>
                              </div>
                              <pre className="code-block">{msg.sql}</pre>
                            </div>
                          )}

                          {/* Render visual chart */}
                          {msg.chart_type && msg.chart_type !== 'table' && renderChart(msg, idx)}

                          {/* Render execution data table */}
                          {msg.data && msg.data.length > 0 && (
                            <div className="result-table-wrapper">
                              <h5>Execution Output ({msg.data.length} rows returned)</h5>
                              <div className="table-responsive">
                                <table className="result-table">
                                  <thead>
                                    <tr>
                                      {Object.keys(msg.data[0]).map(k => <th key={k}>{k}</th>)}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {msg.data.slice(0, 10).map((row, rIdx) => (
                                      <tr key={rIdx}>
                                        {Object.values(row).map((val, cIdx) => (
                                          <td key={cIdx}>{val === null ? 'NULL' : String(val)}</td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                              {msg.data.length > 10 && (
                                <span className="table-truncation-note">Showing first 10 rows. Export or execute custom queries to retrieve all rows.</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
                {loading && (
                  <div className="chat-bubble-row assistant">
                    <div className="chat-avatar">🤖</div>
                    <div className="chat-bubble-card loading">
                      <span className="pulse-loader">⏳ Running query and translating results...</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              <div className="chat-input-bar">
                <input
                  type="text"
                  placeholder={hasPermission('analyze') ? "Ask a question about the active context..." : "Chat queries restricted for Viewers..."}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyPress={hasPermission('analyze') ? handleKeyPress : undefined}
                  disabled={loading || !hasPermission('analyze')}
                />
                <button 
                  onClick={handleChatSubmit} 
                  disabled={loading || !question.trim() || !hasPermission('analyze')}
                  className="send-btn"
                >
                  Send 🚀
                </button>
              </div>
            </div>
          ) : activeTab === 'eda' && selectedDataset ? (
            /* EDA Tab */
            <div className="eda-dashboard">
              <div className="eda-summary-cards">
                <div className="summary-card">
                  <span className="card-icon">📁</span>
                  <div className="card-details">
                    <h5>Filename</h5>
                    <h4>{selectedDataset.filename}</h4>
                  </div>
                </div>
                <div className="summary-card">
                  <span className="card-icon">🔢</span>
                  <div className="card-details">
                    <h5>Row Count</h5>
                    <h4>{selectedDataset.row_count}</h4>
                  </div>
                </div>
                <div className="summary-card">
                  <span className="card-icon">📊</span>
                  <div className="card-details">
                    <h5>Column Count</h5>
                    <h4>{selectedDataset.col_count}</h4>
                  </div>
                </div>
                <div className="summary-card">
                  <span className="card-icon">⚙️</span>
                  <div className="card-details">
                    <h5>DB Table</h5>
                    <h4><code>{selectedDataset.table_name}</code></h4>
                  </div>
                </div>
              </div>

              <div className="eda-panels-grid">
                <div className="eda-panel">
                  <div className="panel-header">
                    <h3>📊 Column Properties & Statistics (EDA)</h3>
                  </div>
                  <div className="panel-body table-responsive">
                    <table className="eda-table">
                      <thead>
                        <tr>
                          <th>Column Name</th>
                          <th>Data Type</th>
                          <th>Unique Values</th>
                          <th>Missing Values</th>
                          <th>Mean</th>
                          <th>Min / Max</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(selectedDataset.schema_info || {}).map(([colName, colInfo]) => (
                          <tr key={colName}>
                            <td><strong>{colName}</strong></td>
                            <td><span className="badge-dtype">{colInfo.dtype}</span></td>
                            <td>{colInfo.unique_count}</td>
                            <td>
                              <span className={`badge-missing ${colInfo.missing_count > 0 ? 'alert' : 'clean'}`}>
                                {colInfo.missing_count} ({selectedDataset.row_count > 0 ? Math.round((colInfo.missing_count / selectedDataset.row_count) * 100) : 0}%)
                              </span>
                            </td>
                            <td>{colInfo.mean !== null ? colInfo.mean : '-'}</td>
                            <td>
                              {colInfo.min !== null && colInfo.max !== null ? (
                                <span className="min-max-range">
                                  {colInfo.min} to {colInfo.max}
                                </span>
                              ) : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="eda-panel">
                  <div className="panel-header">
                    <h3>📄 Data Preview (First 20 rows)</h3>
                  </div>
                  <div className="panel-body table-responsive">
                    {selectedDataset.preview && selectedDataset.preview.length > 0 ? (
                      <table className="eda-preview-table">
                        <thead>
                          <tr>
                            {selectedDataset.columns.map(col => <th key={col}>{col}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {selectedDataset.preview.map((row, rIdx) => (
                            <tr key={rIdx}>
                              {selectedDataset.columns.map(col => (
                                <td key={col}>{row[col] === null ? 'NULL' : String(row[col])}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p className="no-data-msg">No preview rows found in this dataset.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Database Schema Browser Tab */
            selectedDbConnSchema && (
              <div className="schema-browser">
                <div className="schema-grid">
                  <div className="tables-list-card">
                    <h4>📁 Database Catalog</h4>
                    <ul>
                      {Object.keys(selectedDbConnSchema).map(tbl => (
                        <li 
                          key={tbl} 
                          className={activeSchemaTable === tbl ? 'active' : ''}
                          onClick={() => setActiveSchemaTable(tbl)}
                        >
                          <span className="tbl-bullet">📋</span> {tbl}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="table-details-card">
                    {activeSchemaTable && selectedDbConnSchema[activeSchemaTable] ? (
                      <div className="table-schema-details">
                        <h4>📊 Column Specifications: <code>{activeSchemaTable}</code></h4>
                        <div className="table-responsive">
                          <table className="eda-table">
                            <thead>
                              <tr>
                                <th>Column Name</th>
                                <th>Data Type</th>
                                <th>Nullable</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedDbConnSchema[activeSchemaTable].map(col => (
                                <tr key={col.name}>
                                  <td><strong>{col.name}</strong></td>
                                  <td><span className="badge-dtype">{col.type}</span></td>
                                  <td>{col.nullable ? '✅ Yes' : '❌ No'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ) : (
                      <div className="select-table-placeholder">
                        <span className="placeholder-icon">👉</span>
                        <p>Select a table from the catalog list to inspect its columns schema properties.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      </main>
    </div>
  );
};

export default ChatInterface;
