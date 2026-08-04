import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const DocumentChat = ({ token, showNotification }) => {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [uploadType, setUploadType] = useState('general'); // "general" or "data_dictionary"
  const [uploading, setUploading] = useState(false);
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [activeCitations, setActiveCitations] = useState([]);
  const [activeConfidence, setActiveConfidence] = useState(0.0);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    fetchConversations();
    fetchDocuments();
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/rag/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConversations(res.data || []);
      if (res.data.length > 0 && !activeConvId) {
        setActiveConvId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/rag/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateConversation = async () => {
    try {
      const res = await axios.post(`${API_BASE_URL}/rag/query`, { question: 'Ping' }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchConversations();
      setActiveConvId(res.data.conversation_id);
      setMessages([]);
      setActiveCitations([]);
      setActiveConfidence(0.0);
    } catch (err) {
      showNotification('Failed to create a new conversation thread', 'error');
    }
  };

  const handlePinToggle = async (convId, currentPinned) => {
    try {
      await axios.post(`${API_BASE_URL}/rag/conversation/pin`, {
        conversation_id: convId,
        is_pinned: !currentPinned
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchConversations();
    } catch (err) {
      showNotification('Failed to pin conversation', 'error');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', uploadType);

    try {
      await axios.post(`${API_BASE_URL}/rag/upload`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      showNotification('Document uploaded and indexed successfully!', 'success');
      fetchDocuments();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to ingest document';
      showNotification(errorMsg, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDoc = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document from RAG index?')) return;
    try {
      await axios.delete(`${API_BASE_URL}/rag/document/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Document removed from vector index', 'success');
      fetchDocuments();
    } catch (err) {
      showNotification('Failed to delete document', 'error');
    }
  };

  const handleSendQuery = async () => {
    if (!inputValue.trim()) return;
    const userPrompt = inputValue;
    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', content: userPrompt }]);
    setLoadingQuery(true);

    try {
      const res = await axios.post(`${API_BASE_URL}/rag/query`, {
        question: userPrompt,
        conversation_id: activeConvId
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setMessages(prev => [...prev, { role: 'assistant', content: res.data.answer }]);
      setActiveCitations(res.data.citations || []);
      setActiveConfidence(res.data.confidence_score);
      
      if (!activeConvId) {
        setActiveConvId(res.data.conversation_id);
      }
      fetchConversations();
    } catch (err) {
      showNotification('Error querying the offline RAG system', 'error');
    } finally {
      setLoadingQuery(false);
    }
  };

  const theme = {
    bg: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    cardBg: darkMode ? '#1e293b' : '#ffffff',
    sidebarBg: darkMode ? '#020617' : '#e2e8f0',
    border: darkMode ? '1px solid #334155' : '1px solid #cbd5e1',
    subText: darkMode ? '#94a3b8' : '#475569',
    userBubble: '#2563eb',
    userBubbleText: '#ffffff',
    assistantBubble: darkMode ? '#334155' : '#f1f5f9',
    shadow: '0 4px 12px rgba(0,0,0,0.1)',
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '260px 1fr 300px',
      height: '100%',
      backgroundColor: theme.bg,
      color: theme.color,
      fontFamily: "'Outfit', sans-serif",
      borderRadius: '16px',
      overflow: 'hidden',
      border: theme.border,
      transition: 'all 0.3s ease'
    }}>
      
      {/* Sidebar: Chat threads */}
      <div style={{
        backgroundColor: theme.sidebarBg,
        borderRight: theme.border,
        display: 'flex',
        flexDirection: 'column',
        padding: '16px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>💬 Chat History</span>
          <button
            onClick={handleCreateConversation}
            style={{
              background: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 600
            }}
          >
            + New
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1, overflowY: 'auto' }}>
          {conversations.map(c => (
            <div
              key={c.id}
              onClick={() => setActiveConvId(c.id)}
              style={{
                padding: '10px 12px',
                borderRadius: '8px',
                backgroundColor: activeConvId === c.id ? '#2563eb' : 'transparent',
                color: activeConvId === c.id ? '#ffffff' : theme.color,
                cursor: 'pointer',
                fontSize: '0.85rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'all 0.2s ease'
              }}
            >
              <span style={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '160px'
              }}>
                {c.title}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handlePinToggle(c.id, c.is_pinned);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: activeConvId === c.id ? '#ffffff' : theme.subText,
                  fontSize: '0.9rem'
                }}
              >
                {c.is_pinned ? '📌' : '📎'}
              </button>
            </div>
          ))}
        </div>
        
        <button
          onClick={() => setDarkMode(!darkMode)}
          style={{
            marginTop: 'auto',
            background: 'none',
            border: theme.border,
            color: theme.color,
            padding: '8px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.8rem'
          }}
        >
          {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
        </button>
      </div>

      {/* Center panel: RAG chat workspace */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        
        {/* Chat Feed */}
        <div style={{
          flexGrow: 1,
          padding: '24px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          {messages.length === 0 ? (
            <div style={{
              textAlign: 'center',
              marginTop: '80px',
              color: theme.subText
            }}>
              <span style={{ fontSize: '3rem' }}>📁</span>
              <h3 style={{ margin: '16px 0 8px 0', fontSize: '1.2rem', color: theme.color }}>Offline Document QA</h3>
              <p style={{ margin: 0, fontSize: '0.88rem', maxWidth: '380px', marginInline: 'auto' }}>
                Ask questions from ingested manuals, glossaries, or database schemas. All responses are fully offline.
              </p>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '75%',
                  padding: '12px 18px',
                  borderRadius: '12px',
                  backgroundColor: m.role === 'user' ? theme.userBubble : theme.assistantBubble,
                  color: m.role === 'user' ? theme.userBubbleText : theme.color,
                  boxShadow: theme.shadow,
                  fontSize: '0.92rem',
                  lineHeight: '1.5',
                  wordBreak: 'break-word'
                }}
              >
                {m.content}
              </div>
            ))
          )}
          {loadingQuery && (
            <div style={{ alignSelf: 'flex-start', color: theme.subText, fontSize: '0.85rem' }}>
              🤖 Synthesizing offline retrieval grounded response...
            </div>
          )}
        </div>

        {/* Input area */}
        <div style={{
          padding: '16px 24px',
          borderTop: theme.border,
          display: 'flex',
          gap: '12px',
          alignItems: 'center'
        }}>
          <input
            type="text"
            placeholder="Type your question..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendQuery()}
            disabled={loadingQuery}
            style={{
              flexGrow: 1,
              padding: '12px 16px',
              borderRadius: '8px',
              border: theme.border,
              backgroundColor: darkMode ? '#1e293b' : '#ffffff',
              color: theme.color,
              outline: 'none',
              fontSize: '0.9rem'
            }}
          />
          <button
            onClick={handleSendQuery}
            disabled={loadingQuery || !inputValue.trim()}
            style={{
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem',
              opacity: (loadingQuery || !inputValue.trim()) ? 0.6 : 1
            }}
          >
            Send
          </button>
        </div>

      </div>

      {/* Right panel: File Ingestion & Citations */}
      <div style={{
        backgroundColor: theme.sidebarBg,
        borderLeft: theme.border,
        display: 'flex',
        flexDirection: 'column',
        padding: '16px',
        overflowY: 'auto'
      }}>
        
        {/* Document Ingest section */}
        <div style={{
          borderBottom: theme.border,
          paddingBottom: '20px',
          marginBottom: '20px'
        }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', fontWeight: 700 }}>📥 Ingest Document</h4>
          
          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
            <button
              onClick={() => setUploadType('general')}
              style={{
                flexGrow: 1,
                padding: '6px',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: uploadType === 'general' ? '#2563eb' : (darkMode ? '#334155' : '#cbd5e1'),
                color: '#ffffff',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Manual / Doc
            </button>
            <button
              onClick={() => setUploadType('data_dictionary')}
              style={{
                flexGrow: 1,
                padding: '6px',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: uploadType === 'data_dictionary' ? '#2563eb' : (darkMode ? '#334155' : '#cbd5e1'),
                color: '#ffffff',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Glossary / Dict
            </button>
          </div>

          <label style={{
            display: 'block',
            padding: '12px',
            borderRadius: '6px',
            border: '2px dashed #2563eb',
            textAlign: 'center',
            cursor: uploading ? 'not-allowed' : 'pointer',
            fontSize: '0.8rem',
            fontWeight: 600
          }}>
            {uploading ? 'Processing vectors...' : '📁 Select Document'}
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
              style={{ display: 'none' }}
              accept=".pdf,.docx,.txt,.md,.markdown,.csv"
            />
          </label>
        </div>

        {/* Confidence Gauge */}
        {activeConfidence > 0 && (
          <div style={{
            padding: '12px',
            borderRadius: '8px',
            backgroundColor: theme.cardBg,
            border: theme.border,
            marginBottom: '20px',
            textAlign: 'center'
          }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: theme.subText }}>Grounded Confidence Score</span>
            <h3 style={{ margin: '6px 0 0 0', color: activeConfidence > 0.7 ? '#10b981' : '#f59e0b' }}>
              {Math.round(activeConfidence * 100)}%
            </h3>
          </div>
        )}

        {/* Citations Preview list */}
        {activeCitations.length > 0 && (
          <div style={{
            borderBottom: theme.border,
            paddingBottom: '20px',
            marginBottom: '20px'
          }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', fontWeight: 700 }}>🔍 Cited Context Chunks</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {activeCitations.map((cit, cIdx) => (
                <div
                  key={cIdx}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    backgroundColor: theme.cardBg,
                    border: theme.border,
                    fontSize: '0.78rem'
                  }}
                >
                  <div style={{ fontWeight: 700, color: '#2563eb', marginBottom: '4px' }}>
                    {cit.filename} (Pg {cit.page_number})
                  </div>
                  <div style={{
                    color: theme.color,
                    maxHeight: '80px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    lineHeight: '1.4'
                  }}>
                    {cit.text_content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Document registry list */}
        <div>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', fontWeight: 700 }}>📂 Active Index files</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {documents.length > 0 ? (
              documents.map(d => (
                <div
                  key={d.id}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    backgroundColor: theme.cardBg,
                    border: theme.border,
                    fontSize: '0.78rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    <span style={{ fontWeight: 600 }}>{d.filename}</span>
                    <span style={{ fontSize: '0.68rem', color: theme.subText, marginTop: '2px' }}>
                      {d.doc_type.replace('_', ' ').toUpperCase()} • {Math.round(d.file_size / 1024)} KB
                    </span>
                  </div>
                  <button
                    onClick={() => handleDeleteDoc(d.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ef4444',
                      cursor: 'pointer',
                      fontSize: '0.85rem'
                    }}
                  >
                    🗑️
                  </button>
                </div>
              ))
            ) : (
              <span style={{ fontSize: '0.78rem', color: theme.subText, textAlign: 'center', display: 'block', padding: '10px' }}>
                No active document files.
              </span>
            )}
          </div>
        </div>

      </div>

    </div>
  );
};

export default DocumentChat;
