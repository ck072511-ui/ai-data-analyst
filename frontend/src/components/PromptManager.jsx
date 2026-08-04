import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const PromptManager = ({ token, showNotification }) => {
  const [prompts, setPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [editorContent, setEditorContent] = useState('');
  const [changeLog, setChangeLog] = useState('');
  const [versions, setVersions] = useState([]);
  const [compareVerA, setCompareVerA] = useState('');
  const [compareVerB, setCompareVerB] = useState('');
  const [compareResult, setCompareResult] = useState(null);
  const [showCompare, setShowCompare] = useState(false);
  const [name, setName] = useState('');
  const [category, setCategory] = useState('sql');
  const [newContent, setNewContent] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/prompts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPrompts(res.data || []);
      if (res.data.length > 0 && !selectedPrompt) {
        handleSelectPrompt(res.data[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectPrompt = async (p) => {
    setSelectedPrompt(p);
    setEditorContent(p.content);
    setChangeLog('');
    setCompareResult(null);
    setShowCompare(false);
    fetchVersions(p.id);
  };

  const fetchVersions = async (id) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/prompts/${id}/versions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setVersions(res.data || []);
      if (res.data.length > 0) {
        setCompareVerA(res.data[0].version);
        if (res.data.length > 1) {
          setCompareVerB(res.data[1].version);
        } else {
          setCompareVerB(res.data[0].version);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveUpdate = async () => {
    if (!editorContent.trim() || !changeLog.trim()) {
      showNotification('Content and Change Log must not be empty.', 'error');
      return;
    }
    try {
      await axios.put(`${API_BASE_URL}/prompts/${selectedPrompt.id}`, {
        content: editorContent,
        change_log: changeLog
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Prompt template updated to new version!', 'success');
      setChangeLog('');
      fetchPrompts();
      fetchVersions(selectedPrompt.id);
    } catch (err) {
      showNotification('Failed to save prompt update', 'error');
    }
  };

  const handleCreatePrompt = async () => {
    if (!name.trim() || !newContent.trim()) {
      showNotification('Name and content must not be empty.', 'error');
      return;
    }
    try {
      const res = await axios.post(`${API_BASE_URL}/prompts`, {
        name,
        category,
        content: newContent
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Prompt template registered!', 'success');
      setName('');
      setNewContent('');
      setShowCreate(false);
      fetchPrompts();
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to create prompt', 'error');
    }
  };

  const handleRollback = async (ver) => {
    try {
      await axios.post(`${API_BASE_URL}/prompts/${selectedPrompt.id}/rollback`, {
        target_version: ver
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification(`Rolled back prompt template successfully!`, 'success');
      fetchPrompts();
      fetchVersions(selectedPrompt.id);
    } catch (err) {
      showNotification('Rollback execution failed', 'error');
    }
  };

  const handleCompare = () => {
    const valA = versions.find(v => v.version === parseInt(compareVerA))?.content || '';
    const valB = versions.find(v => v.version === parseInt(compareVerB))?.content || '';
    setCompareResult({
      ver_a: compareVerA,
      content_a: valA,
      ver_b: compareVerB,
      content_b: valB
    });
    setShowCompare(true);
  };

  const theme = {
    bg: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    cardBg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    sidebarBg: darkMode ? '#020617' : '#cbd5e1',
    subText: darkMode ? '#94a3b8' : '#64748b',
    activeBlue: '#2563eb',
    shadow: '0 4px 20px rgba(0,0,0,0.1)',
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '260px 1fr',
      height: '100%',
      backgroundColor: theme.bg,
      color: theme.color,
      fontFamily: "'Outfit', sans-serif",
      borderRadius: '16px',
      overflow: 'hidden',
      border: theme.border,
      transition: 'all 0.3s ease'
    }}>
      
      {/* Sidebar: Prompt selector */}
      <div style={{
        backgroundColor: theme.sidebarBg,
        borderRight: theme.border,
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700 }}>📖 Prompt Library</h3>
          <button
            onClick={() => setShowCreate(!showCreate)}
            style={{
              padding: '4px 8px',
              borderRadius: '4px',
              backgroundColor: '#2563eb',
              color: '#fff',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: 700
            }}
          >
            + New
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1, overflowY: 'auto' }}>
          {prompts.map(p => (
            <div
              key={p.id}
              onClick={() => handleSelectPrompt(p)}
              style={{
                padding: '10px 12px',
                borderRadius: '6px',
                backgroundColor: selectedPrompt?.id === p.id ? '#2563eb' : theme.cardBg,
                color: selectedPrompt?.id === p.id ? '#ffffff' : theme.color,
                cursor: 'pointer',
                fontSize: '0.8rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                boxShadow: theme.shadow
              }}
            >
              <span style={{ fontWeight: 600 }}>{p.name}</span>
              <span style={{ fontSize: '0.68rem', color: selectedPrompt?.id === p.id ? '#ffffff' : theme.subText }}>
                {p.category.toUpperCase()} • V{p.version}
              </span>
            </div>
          ))}
        </div>

        <button
          onClick={() => setDarkMode(!darkMode)}
          style={{
            marginTop: '20px',
            background: 'none',
            border: theme.border,
            color: theme.color,
            padding: '8px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.8rem'
          }}
        >
          {darkMode ? '☀️ Light' : '🌙 Dark'}
        </button>
      </div>

      {/* Main Workspace */}
      <div style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: '24px', gap: '20px' }}>
        
        {/* Header */}
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>📖 Prompt Template Manager</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: theme.subText }}>Create, update, version control, and rollback prompt templates.</p>
        </div>

        {/* Modal: Create prompt */}
        {showCreate && (
          <div style={{
            padding: '20px',
            borderRadius: '12px',
            backgroundColor: theme.cardBg,
            border: theme.border,
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            boxShadow: theme.shadow
          }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>✨ Create Prompt Template</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
              <input
                type="text"
                placeholder="Template Name (e.g. custom_nl2sql)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  border: theme.border,
                  backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                  color: theme.color,
                  fontSize: '0.8rem'
                }}
              />
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  border: theme.border,
                  backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                  color: theme.color,
                  fontSize: '0.8rem'
                }}
              >
                <option value="sql">SQL Generation</option>
                <option value="rag">RAG Grounding</option>
                <option value="multi_agent">Multi-Agent</option>
                <option value="insights">Business Insights</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            <textarea
              placeholder="Prompt template text content... Use {table_name} or {variables} placeholders if needed."
              rows={4}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              style={{
                padding: '12px',
                borderRadius: '6px',
                border: theme.border,
                backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                color: theme.color,
                fontFamily: 'monospace',
                fontSize: '0.8rem'
              }}
            />

            <div style={{ display: 'flex', gap: '10px', alignSelf: 'flex-end' }}>
              <button
                onClick={() => setShowCreate(false)}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: theme.border,
                  background: 'none',
                  color: theme.color,
                  cursor: 'pointer',
                  fontSize: '0.8rem'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreatePrompt}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  fontWeight: 600
                }}
              >
                Save Template
              </button>
            </div>
          </div>
        )}

        {selectedPrompt && !showCreate && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1fr', gap: '24px' }}>
            
            {/* Editor panel */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                boxShadow: theme.shadow,
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
              }}>
                <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 700 }}>
                  📝 Edit: {selectedPrompt.name} (V{selectedPrompt.version})
                </h3>
                
                <textarea
                  value={editorContent}
                  onChange={(e) => setEditorContent(e.target.value)}
                  rows={8}
                  style={{
                    padding: '12px',
                    borderRadius: '6px',
                    border: theme.border,
                    backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                    color: theme.color,
                    fontFamily: 'monospace',
                    fontSize: '0.82rem',
                    lineHeight: '1.5'
                  }}
                />

                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <input
                    type="text"
                    placeholder="Change Log (e.g., Optimized sql joins prompt structure)"
                    value={changeLog}
                    onChange={(e) => setChangeLog(e.target.value)}
                    style={{
                      flexGrow: 1,
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: theme.border,
                      backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                      color: theme.color,
                      fontSize: '0.8rem'
                    }}
                  />
                  <button
                    onClick={handleSaveUpdate}
                    style={{
                      backgroundColor: '#2563eb',
                      color: '#ffffff',
                      border: 'none',
                      padding: '8px 18px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: 700,
                      fontSize: '0.8rem'
                    }}
                  >
                    Save Changes V{selectedPrompt.version + 1}
                  </button>
                </div>
              </div>

              {/* Compare Panel */}
              {showCompare && compareResult && (
                <div style={{
                  padding: '20px',
                  borderRadius: '12px',
                  backgroundColor: theme.cardBg,
                  border: theme.border,
                  boxShadow: theme.shadow
                }}>
                  <h4 style={{ margin: '0 0 14px 0', fontSize: '0.9rem' }}>
                    ⚖️ Comparing Version {compareResult.ver_a} vs Version {compareResult.ver_b}
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: theme.subText, marginBottom: '4px' }}>Version {compareResult.ver_a}</div>
                      <pre style={{
                        padding: '10px',
                        borderRadius: '4px',
                        backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
                        fontSize: '0.75rem',
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap'
                      }}>{compareResult.content_a}</pre>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: theme.subText, marginBottom: '4px' }}>Version {compareResult.ver_b}</div>
                      <pre style={{
                        padding: '10px',
                        borderRadius: '4px',
                        backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
                        fontSize: '0.75rem',
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap'
                      }}>{compareResult.content_b}</pre>
                    </div>
                  </div>
                </div>
              )}

            </div>

            {/* Version History & Metadata logs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Compare triggers */}
              <div style={{
                padding: '16px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                boxShadow: theme.shadow,
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                <h4 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700 }}>⚖️ Diff Tool</h4>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <select
                    value={compareVerA}
                    onChange={(e) => setCompareVerA(e.target.value)}
                    style={{
                      flexGrow: 1,
                      padding: '6px',
                      borderRadius: '4px',
                      border: theme.border,
                      backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                      color: theme.color,
                      fontSize: '0.75rem'
                    }}
                  >
                    {versions.map(v => <option key={v.id} value={v.version}>V{v.version}</option>)}
                  </select>
                  <span style={{ fontSize: '0.75rem' }}>vs</span>
                  <select
                    value={compareVerB}
                    onChange={(e) => setCompareVerB(e.target.value)}
                    style={{
                      flexGrow: 1,
                      padding: '6px',
                      borderRadius: '4px',
                      border: theme.border,
                      backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                      color: theme.color,
                      fontSize: '0.75rem'
                    }}
                  >
                    {versions.map(v => <option key={v.id} value={v.version}>V{v.version}</option>)}
                  </select>
                  <button
                    onClick={handleCompare}
                    style={{
                      backgroundColor: '#2563eb',
                      color: '#fff',
                      border: 'none',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: 600
                    }}
                  >
                    Compare
                  </button>
                </div>
              </div>

              {/* History list */}
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.border,
                boxShadow: theme.shadow,
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
              }}>
                <h4 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700 }}>📜 Version Logs</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
                  {versions.map(v => (
                    <div
                      key={v.id}
                      style={{
                        padding: '10px',
                        borderRadius: '6px',
                        border: theme.border,
                        fontSize: '0.75rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                        <span style={{ color: '#2563eb' }}>Version {v.version}</span>
                        <span>{v.author}</span>
                      </div>
                      <div style={{ color: theme.subText }}>{v.change_log || 'No change description.'}</div>
                      {v.version !== selectedPrompt.version && (
                        <button
                          onClick={() => handleRollback(v.version)}
                          style={{
                            alignSelf: 'flex-end',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            backgroundColor: '#ea580c',
                            color: '#fff',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '0.68rem',
                            fontWeight: 600
                          }}
                        >
                          Rollback to this version ↩️
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

            </div>

          </div>
        )}

      </div>

    </div>
  );
};

export default PromptManager;
