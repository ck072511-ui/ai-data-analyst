import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const ModelManagement = ({ token, showNotification }) => {
  const [models, setModels] = useState([]);
  const [activeModel, setActiveModel] = useState('');
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  // Playground/Testing State
  const [promptInput, setPromptInput] = useState('');
  const [testResult, setTestResult] = useState('');
  const [testLoading, setTestLoading] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);
  const [streamText, setStreamText] = useState('');
  const [latency, setLatency] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch models
      const modelsRes = await axios.get(`${API_BASE_URL}/llm/models`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setModels(modelsRes.data.models || []);
      setActiveModel(modelsRes.data.active_model || '');

      // Fetch status
      const statusRes = await axios.get(`${API_BASE_URL}/llm/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStatusData(statusRes.data);
    } catch (error) {
      console.error('Error fetching LLM data:', error);
      showNotification('Failed to fetch LLM manager diagnostics', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchData();
    }
  }, [token]);

  const handleSelectModel = async (modelName) => {
    setSwitching(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/llm/select`, 
        { model: modelName },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setActiveModel(modelName);
      showNotification(response.data.message || `Switched to model ${modelName}`, 'success');
      
      // Refresh status telemetry
      const statusRes = await axios.get(`${API_BASE_URL}/llm/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStatusData(statusRes.data);
    } catch (error) {
      console.error('Error switching model:', error);
      showNotification(error.response?.data?.detail || 'Failed to switch active model', 'error');
    } finally {
      setSwitching(false);
    }
  };

  const handleTestPrompt = async () => {
    if (!promptInput.trim()) return;
    setTestLoading(true);
    setTestResult('');
    setStreamText('');
    setLatency(null);

    if (useStreaming) {
      try {
        const response = await fetch(`${API_BASE_URL}/llm/test`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ prompt: promptInput, stream: true })
        });

        if (!response.ok) {
          throw new Error('Streaming connection failed');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let done = false;

        while (!done) {
          const { value, done: readerDone } = await reader.read();
          done = readerDone;
          if (value) {
            const chunk = decoder.decode(value, { stream: !done });
            const lines = chunk.split('\n\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6).trim();
                if (dataStr === '[DONE]') {
                  done = true;
                  break;
                }
                try {
                  const parsed = JSON.parse(dataStr);
                  if (parsed.chunk) {
                    setStreamText(prev => prev + parsed.chunk);
                  } else if (parsed.error) {
                    setStreamText(prev => prev + `\n[Error: ${parsed.error}]`);
                  }
                } catch (e) {
                  // Ignore parse issues of incomplete chunks
                }
              }
            }
          }
        }
      } catch (err) {
        console.error('Streaming test failed:', err);
        showNotification('Streaming testing request failed', 'error');
      } finally {
        setTestLoading(false);
      }
    } else {
      const startTime = Date.now();
      try {
        const response = await axios.post(`${API_BASE_URL}/llm/test`, 
          { prompt: promptInput, stream: false },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setTestResult(response.data.response);
        setLatency(Date.now() - startTime);
      } catch (error) {
        console.error('Test prompt failed:', error);
        showNotification(error.response?.data?.detail || 'Inference test request failed', 'error');
      } finally {
        setTestLoading(false);
      }
    }
  };

  // Styles matching the premium design system
  const theme = {
    bg: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    cardBg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #1e293b' : '1px solid #e2e8f0',
    cardBorder: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    subText: darkMode ? '#94a3b8' : '#64748b',
    shadow: darkMode ? '0 10px 30px rgba(0,0,0,0.5)' : '0 10px 30px rgba(0,0,0,0.05)',
  };

  const getStatusBadgeColor = (status) => {
    if (status === 'healthy') return '#10b981';
    if (status === 'unhealthy') return '#ef4444';
    return '#64748b';
  };

  return (
    <div style={{
      padding: '24px',
      borderRadius: '16px',
      fontFamily: "'Outfit', sans-serif",
      backgroundColor: theme.bg,
      color: theme.color,
      transition: 'all 0.3s ease',
      boxShadow: theme.shadow,
      border: theme.border,
      minHeight: '600px'
    }} className="animation-fade-in">
      
      {/* Header section */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
        borderBottom: theme.border,
        paddingBottom: '16px'
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
            🤖 Offline LLM Orchestrator
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', color: theme.subText }}>
            Orchestrate local offline language models via Ollama dynamic configurations.
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
            {darkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
          <button 
            onClick={fetchData} 
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
            {loading ? 'Refreshing...' : '🔄 Refresh'}
          </button>
        </div>
      </div>

      {/* Main Status & Configuration Row */}
      {statusData && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px',
          marginBottom: '24px'
        }}>
          {/* Card: Active Engine Details */}
          <div style={{
            padding: '20px',
            borderRadius: '12px',
            backgroundColor: theme.cardBg,
            border: theme.cardBorder,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}>
            <div>
              <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: theme.subText, fontWeight: 600 }}>Active Provider Engine</span>
              <h3 style={{ margin: '8px 0', fontSize: '1.5rem', fontWeight: 700, textTransform: 'capitalize' }}>
                {statusData.provider}
              </h3>
              <p style={{ fontSize: '0.85rem', color: theme.subText, margin: 0 }}>
                {statusData.provider === 'ollama' ? 'Local offline offline-inference network.' : `${statusData.provider} offline-inference provider.`}
              </p>
            </div>
            <div style={{ marginTop: '16px' }}>
              <span style={{
                display: 'inline-block',
                padding: '4px 12px',
                borderRadius: '12px',
                color: '#ffffff',
                fontSize: '0.8rem',
                fontWeight: '600',
                textTransform: 'uppercase',
                backgroundColor: getStatusBadgeColor(statusData.status)
              }}>{statusData.status}</span>
            </div>
          </div>

          {/* Card: Latency & Telemetry */}
          <div style={{
            padding: '20px',
            borderRadius: '12px',
            backgroundColor: theme.cardBg,
            border: theme.cardBorder
          }}>
            <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: theme.subText, fontWeight: 600 }}>Inference Telemetry</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '12px' }}>
              <div>
                <p style={{ fontSize: '0.85rem', color: theme.subText, margin: 0 }}>Avg Latency</p>
                <h4 style={{ fontSize: '1.5rem', margin: '4px 0 0 0', fontWeight: 700, color: '#8b5cf6' }}>
                  {statusData.avg_latency_ms} <span style={{ fontSize: '0.9rem' }}>ms</span>
                </h4>
              </div>
              <div>
                <p style={{ fontSize: '0.85rem', color: theme.subText, margin: 0 }}>Failed Requests</p>
                <h4 style={{ fontSize: '1.5rem', margin: '4px 0 0 0', fontWeight: 700, color: '#ef4444' }}>
                  {statusData.failed_requests}
                </h4>
              </div>
              <div>
                <p style={{ fontSize: '0.85rem', color: theme.subText, margin: 0 }}>Total Requests</p>
                <h4 style={{ fontSize: '1.2rem', margin: '4px 0 0 0', fontWeight: 600 }}>
                  {statusData.total_requests}
                </h4>
              </div>
              <div>
                <p style={{ fontSize: '0.85rem', color: theme.subText, margin: 0 }}>Stream Requests</p>
                <h4 style={{ fontSize: '1.2rem', margin: '4px 0 0 0', fontWeight: 600 }}>
                  {statusData.streaming_statistics?.streaming_requests_total || 0}
                </h4>
              </div>
            </div>
          </div>

          {/* Card: Connection Endpoint */}
          <div style={{
            padding: '20px',
            borderRadius: '12px',
            backgroundColor: theme.cardBg,
            border: theme.cardBorder,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}>
            <div>
              <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: theme.subText, fontWeight: 600 }}>Local Host Health</span>
              <h4 style={{ margin: '8px 0', fontSize: '1.2rem', fontWeight: 600 }}>
                Ollama Connection
              </h4>
              <p style={{ fontSize: '0.85rem', color: theme.subText, margin: 0 }}>
                Status: <strong>{statusData.ollama_connected ? 'Connected ✅' : 'Offline / Unreachable ❌'}</strong>
              </p>
            </div>
            <div style={{ marginTop: '16px', fontSize: '0.8rem', color: theme.subText }}>
              Verify Ollama daemon is running at <code>http://localhost:11434</code>.
            </div>
          </div>
        </div>
      )}

      {/* Model Selection Panel */}
      <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', fontWeight: 600 }}>Switch Active Language Model</h3>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '32px'
      }}>
        {models.length > 0 ? (
          models.map((model) => {
            const isActive = activeModel === model;
            const isOllama = statusData?.provider === 'ollama';
            
            return (
              <div 
                key={model} 
                onClick={() => !switching && handleSelectModel(model)}
                style={{
                  padding: '16px',
                  borderRadius: '12px',
                  backgroundColor: isActive ? 'rgba(37, 99, 235, 0.1)' : theme.cardBg,
                  border: isActive ? '2px solid #2563eb' : theme.cardBorder,
                  cursor: switching ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease',
                  position: 'relative',
                  transform: isActive ? 'scale(1.02)' : 'none',
                  boxShadow: isActive ? '0 4px 12px rgba(37, 99, 235, 0.15)' : 'none'
                }}
                className="model-card"
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    {model}
                  </span>
                  <span style={{
                    fontSize: '0.75rem',
                    padding: '2px 6px',
                    borderRadius: '8px',
                    backgroundColor: isOllama ? '#7c3aed' : '#f59e0b',
                    color: '#ffffff',
                    fontWeight: 600,
                    textTransform: 'uppercase'
                  }}>
                    {isOllama ? 'Local' : 'Offline'}
                  </span>
                </div>
                <p style={{ fontSize: '0.85rem', color: theme.subText, marginTop: '8px', marginBottom: 0 }}>
                  {isActive ? '👉 CURRENT ACTIVE MODEL' : 'Click to activate this model'}
                </p>
                {isActive && (
                  <span style={{
                    position: 'absolute',
                    top: '-10px',
                    right: '10px',
                    backgroundColor: '#2563eb',
                    color: '#ffffff',
                    borderRadius: '50%',
                    width: '20px',
                    height: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.7rem'
                  }}>✓</span>
                )}
              </div>
            );
          })
        ) : (
          <div style={{
            gridColumn: '1 / -1',
            padding: '30px',
            textAlign: 'center',
            backgroundColor: theme.cardBg,
            borderRadius: '12px',
            border: theme.cardBorder
          }}>
            <p style={{ margin: 0, color: theme.subText }}>No models detected. Please verify Ollama service connectivity.</p>
          </div>
        )}
      </div>

      {/* Playground / Interactive Prompt Testing */}
      <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', fontWeight: 600 }}>Interactive LLM Playground</h3>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '24px',
        flexWrap: 'wrap',
        alignItems: 'start'
      }}>
        {/* Left Column: Prompt Form */}
        <div style={{
          padding: '20px',
          borderRadius: '12px',
          backgroundColor: theme.cardBg,
          border: theme.cardBorder
        }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '1rem', fontWeight: 600 }}>Send Prompt Request</h4>
          <textarea
            placeholder="Type a testing prompt here... e.g. Write a SQL query to fetch all users."
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            style={{
              width: '100%',
              minHeight: '120px',
              padding: '12px',
              borderRadius: '8px',
              border: theme.border,
              backgroundColor: darkMode ? '#0f172a' : '#ffffff',
              color: theme.color,
              fontFamily: 'inherit',
              fontSize: '0.95rem',
              resize: 'vertical',
              marginBottom: '16px',
              outline: 'none',
              transition: 'border 0.2s ease'
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.9rem' }}>
              <input 
                type="checkbox" 
                checked={useStreaming}
                onChange={(e) => setUseStreaming(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              Enable Real-time Token Streaming
            </label>
            <button
              onClick={handleTestPrompt}
              disabled={testLoading || !promptInput.trim()}
              style={{
                padding: '10px 24px',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '600',
                backgroundColor: '#2563eb',
                color: '#ffffff',
                opacity: (testLoading || !promptInput.trim()) ? 0.6 : 1,
              }}
            >
              {testLoading ? 'Processing...' : 'Run Query 🚀'}
            </button>
          </div>
        </div>

        {/* Right Column: Streaming Output Preview */}
        <div style={{
          padding: '20px',
          borderRadius: '12px',
          backgroundColor: theme.cardBg,
          border: theme.cardBorder,
          minHeight: '215px',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Streaming Response Preview</h4>
            {latency && <span style={{ fontSize: '0.8rem', color: theme.subText }}>Inference latency: {latency}ms</span>}
          </div>
          
          <div style={{
            flexGrow: 1,
            backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
            borderRadius: '8px',
            padding: '16px',
            fontFamily: "'Courier New', Courier, monospace",
            fontSize: '0.9rem',
            overflowY: 'auto',
            maxHeight: '300px',
            whiteSpace: 'pre-wrap',
            color: darkMode ? '#38bdf8' : '#0f172a',
            border: theme.border
          }}>
            {useStreaming ? (
              streamText || <span style={{ color: theme.subText }}>Response tokens will stream here in real-time...</span>
            ) : (
              testResult || <span style={{ color: theme.subText }}>Completions text will display here...</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelManagement;
