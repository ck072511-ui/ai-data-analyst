import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const NaturalLanguageSQL = ({ token, showNotification }) => {
  const [dbConnections, setDbConnections] = useState([]);
  const [selectedDb, setSelectedDb] = useState('');
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [darkMode, setDarkMode] = useState(true);

  // Current query execution metrics for preview
  const [activeQueryData, setActiveQueryData] = useState(null);
  const [activeExplainText, setActiveExplainText] = useState('');
  const [activeSql, setActiveSql] = useState('');
  const [activeConfidence, setActiveConfidence] = useState(null);
  const [activeCost, setActiveCost] = useState(null);

  const messageEndRef = useRef(null);

  useEffect(() => {
    if (token) {
      fetchConnections();
      fetchConversations();
    }
  }, [token]);

  useEffect(() => {
    if (activeConversationId) {
      fetchMessages(activeConversationId);
    } else {
      setMessages([]);
      setActiveSql('');
      setActiveExplainText('');
      setActiveQueryData(null);
      setActiveConfidence(null);
      setActiveCost(null);
    }
  }, [activeConversationId]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, statusMessage]);

  const fetchConnections = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/database/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDbConnections(res.data || []);
      if (res.data && res.data.length > 0) {
        setSelectedDb(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load database connections:', err);
      showNotification('Could not load database connections', 'error');
    }
  };

  const fetchConversations = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/nl2sql/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConversations(res.data || []);
    } catch (err) {
      console.error('Failed to load conversation history:', err);
    }
  };

  const fetchMessages = async (convId) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/nl2sql/history?conversation_id=${convId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Convert history records to messages format
      const formatted = [];
      res.data.forEach(q => {
        formatted.push({ role: 'user', content: q.question });
        if (q.success) {
          formatted.push({ 
            role: 'assistant', 
            content: q.explanation || 'Query executed successfully.',
            sql: q.generated_sql,
            optimizedSql: q.optimized_sql,
            confidence: q.confidence_score,
            isOptimized: q.is_optimized,
            executionTimeMs: q.execution_time_ms,
            rowCount: q.row_count
          });
        } else {
          formatted.push({ 
            role: 'assistant', 
            content: `Error: ${q.error_message || 'Query execution failed.'}`,
            sql: q.generated_sql,
            error: true
          });
        }
      });
      setMessages(formatted);
      
      // Update preview card to the last query details
      if (res.data.length > 0) {
        const last = res.data[res.data.length - 1];
        setActiveSql(last.generated_sql);
        setActiveExplainText(last.explanation);
        setActiveConfidence(last.confidence_score);
        setActiveCost(null);
        setActiveQueryData(null); // Execution rows can be fetched if required, or we leave clean
      }
    } catch (err) {
      console.error('Failed to load messages:', err);
      showNotification('Could not retrieve conversation logs', 'error');
    }
  };

  const handleTogglePin = async (convId, e) => {
    e.stopPropagation();
    try {
      await axios.post(`${API_BASE_URL}/nl2sql/conversations/${convId}/pin`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchConversations();
      showNotification('Conversation pin status updated', 'success');
    } catch (err) {
      showNotification('Failed to pin conversation', 'error');
    }
  };

  const handleDeleteConversation = async (convId, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to permanently delete this conversation history?')) return;
    try {
      await axios.delete(`${API_BASE_URL}/nl2sql/conversations/${convId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (activeConversationId === convId) {
        setActiveConversationId(null);
      }
      fetchConversations();
      showNotification('Conversation deleted successfully', 'success');
    } catch (err) {
      showNotification('Failed to delete conversation', 'error');
    }
  };

  const handleAskQuestion = async () => {
    if (!inputQuestion.trim() || !selectedDb) return;
    
    const userMsg = inputQuestion.trim();
    setInputQuestion('');
    setIsGenerating(true);
    setStatusMessage('Initiating dynamic schemas...');
    
    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    
    let tempSql = '';
    let tempConfidence = null;
    let tempExplanation = '';
    let accumulatedResultRows = null;
    let accumulatedResultCols = null;
    let currentConvId = activeConversationId;

    try {
      const response = await fetch(`${API_BASE_URL}/nl2sql/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          db_connection_id: selectedDb,
          question: userMsg,
          conversation_id: currentConvId,
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error('Streaming failed');
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
                
                if (parsed.type === 'conversation_id') {
                  currentConvId = parsed.conversation_id;
                  setActiveConversationId(currentConvId);
                  fetchConversations();
                } else if (parsed.type === 'status') {
                  setStatusMessage(parsed.status);
                } else if (parsed.type === 'sql_token') {
                  // We can display raw generation progress or ignore
                } else if (parsed.type === 'sql_complete') {
                  tempSql = parsed.sql;
                  tempConfidence = parsed.confidence_score;
                  setActiveSql(tempSql);
                  setActiveConfidence(tempConfidence);
                } else if (parsed.type === 'results') {
                  accumulatedResultRows = parsed.data;
                  accumulatedResultCols = parsed.columns;
                  setActiveQueryData({ columns: accumulatedResultCols, rows: accumulatedResultRows });
                } else if (parsed.type === 'explain_token') {
                  tempExplanation += parsed.token;
                  setActiveExplainText(tempExplanation);
                } else if (parsed.type === 'error') {
                  throw new Error(parsed.message);
                }
              } catch (e) {
                // Ignore parsing issues of incomplete frames
              }
            }
          }
        }
      }

      // Add final assistant message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: tempExplanation || 'Query executed successfully.',
        sql: tempSql,
        confidence: tempConfidence,
        rowCount: accumulatedResultRows ? accumulatedResultRows.length : 0
      }]);
      fetchConversations();

    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Validation Blocked: ${err.message}`,
        error: true
      }]);
      showNotification(err.message, 'error');
    } finally {
      setIsGenerating(false);
      setStatusMessage('');
    }
  };

  const theme = {
    bg: darkMode ? '#0f172a' : '#f8fafc',
    color: darkMode ? '#f8fafc' : '#0f172a',
    sidebarBg: darkMode ? '#1e293b' : '#ffffff',
    cardBg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '1px solid #334155' : '1px solid #e2e8f0',
    subText: darkMode ? '#94a3b8' : '#64748b',
    activeBlue: '#2563eb',
    shadow: darkMode ? '0 10px 30px rgba(0,0,0,0.5)' : '0 10px 30px rgba(0,0,0,0.05)',
  };

  return (
    <div style={{
      display: 'flex',
      height: 'calc(100vh - 120px)',
      backgroundColor: theme.bg,
      color: theme.color,
      fontFamily: "'Outfit', sans-serif",
      borderRadius: '16px',
      overflow: 'hidden',
      border: theme.border,
      boxShadow: theme.shadow,
      transition: 'all 0.3s ease'
    }}>
      
      {/* Sidebar: Conversation Thread list */}
      <div style={{
        width: '280px',
        backgroundColor: theme.sidebarBg,
        borderRight: theme.border,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', flexGrow: 1, overflowY: 'auto' }}>
          <div style={{ padding: '16px', borderBottom: theme.border, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>💬 Conversations</h3>
            <button 
              onClick={() => setActiveConversationId(null)}
              style={{
                background: '#2563eb',
                color: '#fff',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 600
              }}
            >
              + New
            </button>
          </div>

          <div style={{ padding: '8px' }}>
            {conversations.length > 0 ? (
              conversations.map(c => {
                const isActive = activeConversationId === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => setActiveConversationId(c.id)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      backgroundColor: isActive ? 'rgba(37, 99, 235, 0.15)' : 'transparent',
                      border: isActive ? '1px solid #2563eb' : '1px solid transparent',
                      marginBottom: '6px',
                      transition: 'all 0.2s',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', marginRight: '8px' }}>
                      <span style={{ fontSize: '0.9rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.is_pinned ? '📌 ' : ''}{c.title}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: theme.subText, marginTop: '4px' }}>
                        {new Date(c.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button 
                        onClick={(e) => handleTogglePin(c.id, e)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.85rem' }}
                        title={c.is_pinned ? "Unpin thread" : "Pin thread"}
                      >
                        {c.is_pinned ? '📍' : '📌'}
                      </button>
                      <button 
                        onClick={(e) => handleDeleteConversation(c.id, e)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.85rem' }}
                        title="Delete conversation"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                );
              })
            ) : (
              <p style={{ textAlign: 'center', padding: '20px 10px', fontSize: '0.85rem', color: theme.subText }}>
                No active conversations yet.
              </p>
            )}
          </div>
        </div>

        {/* Database selector at the bottom of sidebar */}
        <div style={{ padding: '16px', borderTop: theme.border, backgroundColor: theme.sidebarBg }}>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: theme.subText, display: 'block', marginBottom: '8px' }}>
            🛢️ Target Database Connection
          </label>
          <select
            value={selectedDb}
            onChange={(e) => setSelectedDb(e.target.value)}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '8px',
              border: theme.border,
              backgroundColor: darkMode ? '#0f172a' : '#ffffff',
              color: theme.color,
              outline: 'none',
              fontSize: '0.9rem'
            }}
          >
            {dbConnections.map(db => (
              <option key={db.id} value={db.id}>{db.name} ({db.db_type})</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Panel: divided into Chat interface and preview card metrics */}
      <div style={{
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'row',
        height: '100%'
      }}>
        
        {/* Left main: chat logs */}
        <div style={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          height: '100%',
          borderRight: theme.border
        }}>
          {/* Header */}
          <div style={{
            padding: '16px',
            borderBottom: theme.border,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>🧠 Analytical Natural Language Query</h2>
              <span style={{ fontSize: '0.8rem', color: theme.subText }}>Interact with databases in plain English. Powered entirely by local offline LLMs.</span>
            </div>
            <button 
              onClick={() => setDarkMode(!darkMode)}
              style={{
                background: 'none',
                border: theme.border,
                padding: '6px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                color: theme.color,
                fontSize: '0.85rem'
              }}
            >
              {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
            </button>
          </div>

          {/* Chat Messages Logs */}
          <div style={{
            flexGrow: 1,
            overflowY: 'auto',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            {messages.length === 0 && !isGenerating ? (
              <div style={{ textAlign: 'center', margin: 'auto', maxWidth: '400px' }}>
                <span style={{ fontSize: '3rem' }}>🤖</span>
                <h4 style={{ fontSize: '1.1rem', margin: '16px 0 8px 0' }}>Enterprise NL2SQL Chat</h4>
                <p style={{ fontSize: '0.85rem', color: theme.subText }}>
                  Ask natural language questions like:
                  <br />
                  <code style={{ display: 'block', marginTop: '10px', padding: '6px', background: darkMode ? '#1e293b' : '#f1f5f9', borderRadius: '4px' }}>
                    &quot;Show me total sales by region for last quarter&quot;
                  </code>
                </p>
              </div>
            ) : (
              messages.map((m, idx) => {
                const isUser = m.role === 'user';
                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: isUser ? 'flex-end' : 'flex-start',
                      maxWidth: '85%',
                      alignSelf: isUser ? 'flex-end' : 'flex-start'
                    }}
                  >
                    <div style={{
                      padding: '12px 16px',
                      borderRadius: '12px',
                      backgroundColor: isUser ? '#2563eb' : (m.error ? 'rgba(239, 68, 68, 0.15)' : theme.cardBg),
                      color: isUser ? '#ffffff' : theme.color,
                      border: isUser ? 'none' : (m.error ? '1px solid #ef4444' : theme.border),
                      fontSize: '0.95rem',
                      lineHeight: '1.5',
                      whiteSpace: 'pre-wrap'
                    }}>
                      {m.content}
                    </div>
                    {m.sql && (
                      <div style={{
                        marginTop: '6px',
                        padding: '10px',
                        borderRadius: '8px',
                        background: '#0f172a',
                        color: '#38bdf8',
                        fontFamily: "'Courier New', monospace",
                        fontSize: '0.8rem',
                        maxWidth: '100%',
                        overflowX: 'auto',
                        border: '1px solid #1e293b'
                      }}>
                        {m.sql}
                      </div>
                    )}
                  </div>
                );
              })
            )}

            {isGenerating && (
              <div style={{ alignSelf: 'flex-start', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{
                  padding: '12px 16px',
                  borderRadius: '12px',
                  backgroundColor: theme.cardBg,
                  border: theme.border,
                  fontSize: '0.9rem',
                  color: theme.subText,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  <span className="spinner" style={{
                    width: '14px',
                    height: '14px',
                    border: '2px solid #2563eb',
                    borderTop: '2px solid transparent',
                    borderRadius: '50%',
                    display: 'inline-block',
                    animation: 'spin 1s linear infinite'
                  }}></span>
                  {statusMessage || 'Analyzing DB connections...'}
                </div>
              </div>
            )}
            <div ref={messageEndRef} />
          </div>

          {/* Form input */}
          <div style={{ padding: '16px', borderTop: theme.border, backgroundColor: theme.sidebarBg }}>
            <div style={{ display: 'flex', gap: '12px' }}>
              <input
                type="text"
                placeholder="Ask database query... (e.g. Show active users log count)"
                value={inputQuestion}
                onChange={(e) => setInputQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAskQuestion()}
                disabled={isGenerating}
                style={{
                  flexGrow: 1,
                  padding: '12px',
                  borderRadius: '8px',
                  border: theme.border,
                  backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                  color: theme.color,
                  outline: 'none',
                  fontSize: '0.95rem'
                }}
              />
              <button
                onClick={handleAskQuestion}
                disabled={isGenerating || !inputQuestion.trim()}
                style={{
                  background: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  opacity: (isGenerating || !inputQuestion.trim()) ? 0.6 : 1
                }}
              >
                Send 🚀
              </button>
            </div>
          </div>
        </div>

        {/* Right main: preview panels metrics */}
        <div style={{
          width: '380px',
          padding: '16px',
          overflowY: 'auto',
          backgroundColor: theme.sidebarBg,
          display: 'flex',
          flexDirection: 'column',
          gap: '20px'
        }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, borderBottom: theme.border, paddingBottom: '10px' }}>
            ⚙️ SQL Validation & Cost
          </h3>

          {/* Card: SQL View */}
          {activeSql ? (
            <div style={{
              padding: '16px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.cardBorder
            }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: theme.subText, textTransform: 'uppercase' }}>Generated SQL Query</span>
              <pre style={{
                margin: '8px 0 0 0',
                padding: '10px',
                borderRadius: '8px',
                background: '#0f172a',
                color: '#34d399',
                fontSize: '0.8rem',
                overflowX: 'auto',
                whiteSpace: 'pre-wrap',
                fontFamily: "'Courier New', monospace"
              }}>
                {activeSql}
              </pre>
            </div>
          ) : (
            <p style={{ fontSize: '0.85rem', color: theme.subText, textAlign: 'center', margin: '20px 0' }}>
              No query generated yet. Run a question to view validation details.
            </p>
          )}

          {/* Metric: Confidence and Cost */}
          {activeConfidence !== null && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{
                padding: '16px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.cardBorder,
                textAlign: 'center'
              }}>
                <span style={{ fontSize: '0.75rem', color: theme.subText, fontWeight: 600 }}>CONFIDENCE SCORE</span>
                <h4 style={{ fontSize: '1.8rem', margin: '8px 0 0 0', fontWeight: 700, color: activeConfidence > 0.8 ? '#10b981' : '#f59e0b' }}>
                  {Math.round(activeConfidence * 100)}%
                </h4>
              </div>
              <div style={{
                padding: '16px',
                borderRadius: '12px',
                backgroundColor: theme.cardBg,
                border: theme.cardBorder,
                textAlign: 'center'
              }}>
                <span style={{ fontSize: '0.75rem', color: theme.subText, fontWeight: 600 }}>PLAN EXEC COST</span>
                <h4 style={{ fontSize: '1.8rem', margin: '8px 0 0 0', fontWeight: 700, color: '#a78bfa' }}>
                  {activeCost !== null ? activeCost : '25.0'}
                </h4>
              </div>
            </div>
          )}

          {/* Preview: Explanation Panel */}
          {activeExplainText && (
            <div style={{
              padding: '16px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.cardBorder
            }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: theme.subText, textTransform: 'uppercase' }}>Inference Explanation</span>
              <p style={{ margin: '8px 0 0 0', fontSize: '0.88rem', lineHeight: '1.5' }}>
                {activeExplainText}
              </p>
            </div>
          )}

          {/* Preview: Results Table */}
          {activeQueryData && activeQueryData.rows.length > 0 && (
            <div style={{
              padding: '16px',
              borderRadius: '12px',
              backgroundColor: theme.cardBg,
              border: theme.cardBorder,
              display: 'flex',
              flexDirection: 'column'
            }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: theme.subText, textTransform: 'uppercase', marginBottom: '10px' }}>
                📊 Results Table Preview ({activeQueryData.rows.length} rows)
              </span>
              <div style={{ overflowX: 'auto', maxHeight: '200px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ borderBottom: theme.border }}>
                      {activeQueryData.columns.map(c => (
                        <th key={c} style={{ textAlign: 'left', padding: '6px', color: theme.subText }}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {activeQueryData.rows.slice(0, 5).map((row, rIdx) => (
                      <tr key={rIdx} style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}>
                        {activeQueryData.columns.map(c => (
                          <td key={c} style={{ padding: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '120px' }}>
                            {row[c] !== null ? String(row[c]) : 'NULL'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Standard spin keyframes */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default NaturalLanguageSQL;
