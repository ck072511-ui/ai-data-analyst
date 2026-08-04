import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const AICopilot = ({ token, datasets, selectedDatasetId, selectedDbConnId, showNotification }) => {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [generatingWorkflow, setGeneratingWorkflow] = useState(false);
  const [workflowName, setWorkflowName] = useState('');
  const [showWorkflowModal, setShowWorkflowModal] = useState(false);
  const [expandedPlanIdx, setExpandedPlanIdx] = useState(null);
  const messagesEndRef = useRef(null);

  // Suggested Prompts
  const suggestedPrompts = [
    "Profile dataset, clean issues, run SQL analytics, and explain the outputs",
    "Explain table connections and lineage paths in the database schema",
    "Analyze sales, query top category rows, and generate a PDF report",
    "Search document chat manuals for dictionary references"
  ];

  const getHeaders = () => {
    return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
  };

  const fetchHistory = async (autoSelect = false) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/copilot/history`, getHeaders());
      setConversations(res.data);
      
      if (res.data.length > 0) {
        if (autoSelect && !activeConversationId) {
          setActiveConversationId(res.data[0].id);
          setMessages(res.data[0].messages || []);
        } else if (activeConversationId) {
          const active = res.data.find(c => c.id === activeConversationId);
          if (active) {
            setMessages(active.messages || []);
          }
        }
      }
    } catch (err) {
      console.error("Error fetching copilot history:", err);
    }
  };

  useEffect(() => {
    fetchHistory(true);
  }, [token]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const selectConversation = (id) => {
    setActiveConversationId(id);
    const conv = conversations.find(c => c.id === id);
    if (conv) {
      setMessages(conv.messages || []);
    }
  };

  const startNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setInputMessage('');
  };

  const handleSendMessage = async (msgText) => {
    const textToSend = msgText || inputMessage;
    if (!textToSend.trim() || loading) return;

    setLoading(true);
    setInputMessage('');
    
    // Optimistic user message append
    const userMsg = { role: 'user', content: textToSend, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);

    try {
      const res = await axios.post(`${API_BASE_URL}/copilot/chat`, {
        message: textToSend,
        conversation_id: activeConversationId || undefined,
        dataset_id: selectedDatasetId || undefined,
        db_connection_id: selectedDbConnId || undefined
      }, getHeaders());

      const data = res.data;
      
      if (!activeConversationId) {
        setActiveConversationId(data.conversation_id);
      }
      
      // Refresh histories and active messages list
      await fetchHistory();
    } catch (err) {
      console.error("Error sending message:", err);
      showNotification("Failed to send message to Copilot.", "error");
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "I encountered an error executing your request offline. Please verify that Ollama is running and try again."
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkflow = async () => {
    if (!activeConversationId) return;
    setGeneratingWorkflow(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/copilot/workflow`, {
        conversation_id: activeConversationId,
        name: workflowName || "Copilot Auto Pipeline",
        description: "Generated dynamically from conversational analyst history."
      }, getHeaders());
      
      showNotification(`Workflow pipeline '${res.data.name}' generated successfully!`, "success");
      setShowWorkflowModal(false);
      setWorkflowName('');
    } catch (err) {
      console.error("Error creating workflow:", err);
      showNotification("Failed to convert conversation to visual workflow.", "error");
    } finally {
      setGeneratingWorkflow(false);
    }
  };

  const getConfidenceLevel = (score) => {
    if (score >= 0.8 || score >= 80) return { label: 'High', color: '#10b981' };
    if (score >= 0.5 || score >= 50) return { label: 'Medium', color: '#f59e0b' };
    return { label: 'Low', color: '#ef4444' };
  };

  // Styles definition
  const layoutStyle = {
    display: 'flex',
    height: 'calc(100vh - 120px)',
    fontFamily: "'Inter', sans-serif",
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    borderRadius: '16px',
    overflow: 'hidden',
    border: '1px solid #1e293b'
  };

  const sidebarStyle = {
    width: '260px',
    borderRight: '1px solid #1e293b',
    backgroundColor: '#1e293b',
    display: 'flex',
    flexDirection: 'column',
    padding: '15px'
  };

  const chatContainerStyle = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#0f172a',
    position: 'relative'
  };

  const messagesFeedStyle = {
    flex: 1,
    padding: '20px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px'
  };

  const inputAreaStyle = {
    padding: '20px',
    borderTop: '1px solid #1e293b',
    backgroundColor: '#1e293b',
    display: 'flex',
    gap: '10px',
    alignItems: 'center'
  };

  const bubbleStyle = (role) => ({
    maxWidth: '80%',
    alignSelf: role === 'user' ? 'flex-end' : 'flex-start',
    backgroundColor: role === 'user' ? '#2563eb' : '#1e293b',
    padding: '16px',
    borderRadius: '12px',
    border: role === 'user' ? 'none' : '1px solid #334155',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    transition: 'all 0.3s ease'
  });

  return (
    <div style={layoutStyle}>
      {/* Sidebar Thread List */}
      <div style={sidebarStyle}>
        <button
          onClick={startNewConversation}
          style={{
            width: '100%',
            padding: '10px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: '600',
            marginBottom: '15px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px'
          }}
        >
          ➕ New Chat Thread
        </button>
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <h5 style={{ margin: '0 0 10px 0', textTransform: 'uppercase', fontSize: '11px', color: '#94a3b8', letterSpacing: '0.5px' }}>Past Threads</h5>
          {conversations.map(conv => (
            <div
              key={conv.id}
              onClick={() => selectConversation(conv.id)}
              style={{
                padding: '10px',
                borderRadius: '8px',
                cursor: 'pointer',
                backgroundColor: activeConversationId === conv.id ? '#334155' : 'transparent',
                border: activeConversationId === conv.id ? '1px solid #475569' : '1px solid transparent',
                transition: 'all 0.2s ease',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontSize: '13px'
              }}
            >
              💬 {conv.title || "New Chat"}
            </div>
          ))}
        </div>
      </div>

      {/* Main Workspace Chat Container */}
      <div style={chatContainerStyle}>
        {/* Top Header bar with status and workflow conversions */}
        <div style={{
          padding: '15px 20px',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#1e293b'
        }}>
          <div>
            <h4 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>🤖 Enterprise AI Copilot</h4>
            <span style={{ fontSize: '12px', color: '#10b981' }}>● Offline Local Orchestrator Active</span>
          </div>
          {activeConversationId && (
            <button
              onClick={() => setShowWorkflowModal(true)}
              style={{
                padding: '8px 16px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '13px'
              }}
            >
              ⛓️ Generate Workflow
            </button>
          )}
        </div>

        {/* Message Feeds Area */}
        <div style={messagesFeedStyle}>
          {messages.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              textAlign: 'center',
              color: '#94a3b8',
              padding: '40px'
            }}>
              <span style={{ fontSize: '48px', marginBottom: '15px' }}>🤖</span>
              <h3>Welcome to your Copilot Workspace</h3>
              <p style={{ maxWidth: '480px', fontSize: '14px', marginBottom: '25px' }}>
                Ask complex analytics questions. The Copilot will intelligently route tasks between SQL pipelines, profiling, cleaners, and RAG document search engines offline.
              </p>
              
              {/* Suggested Carousel Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', maxWidth: '600px', width: '100%' }}>
                {suggestedPrompts.map((prompt, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      cursor: 'pointer',
                      fontSize: '12px',
                      textAlign: 'left',
                      transition: 'all 0.2s ease',
                      hover: { backgroundColor: '#334155' }
                    }}
                  >
                    💡 {prompt}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const plan = msg.orchestration_plan;
              const metadata = msg.response_metadata;
              const confidence = metadata?.confidence_score || msg.intent_confidence;
              const confLevel = getConfidenceLevel(confidence);

              return (
                <div key={idx} style={bubbleStyle(msg.role)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '4px', fontSize: '11px', color: '#94a3b8' }}>
                    <strong>{msg.role === 'user' ? 'You' : 'Copilot Assistant'}</strong>
                    <span>{new Date(msg.created_at || Date.now()).toLocaleTimeString()}</span>
                  </div>
                  
                  <div style={{ fontSize: '14px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </div>

                  {/* Render Tool Transparency Stepper Timeline if assistant has execution plan */}
                  {msg.role === 'assistant' && plan && (
                    <div style={{ marginTop: '15px', padding: '12px', backgroundColor: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <span style={{ fontSize: '12px', fontWeight: '600', color: '#38bdf8' }}>⚙️ Execution Timeline</span>
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                          {confidence && (
                            <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', backgroundColor: confLevel.color, color: 'white', fontWeight: 'bold' }}>
                              {confLevel.label} ({Math.round(confidence * 100)}%)
                            </span>
                          )}
                          {metadata?.processing_time_seconds && (
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>⏱️ {metadata.processing_time_seconds}s</span>
                          )}
                        </div>
                      </div>

                      {/* Timeline Nodes */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderLeft: '2px solid #334155', paddingLeft: '12px', margin: '5px 0' }}>
                        {(plan.timeline || []).map((step, sidx) => (
                          <div key={sidx} style={{ fontSize: '12px', display: 'flex', justifyContent: 'space-between' }}>
                            <div>
                              <span style={{ color: step.status === 'success' ? '#10b981' : '#ef4444' }}>
                                {step.status === 'success' ? '✓' : '✗'}
                              </span>{' '}
                              <strong style={{ color: '#f8fafc' }}>{step.module}</strong>:{' '}
                              <span style={{ color: '#94a3b8' }}>{step.summary}</span>
                            </div>
                            <span style={{ color: '#64748b' }}>{step.duration_seconds}s</span>
                          </div>
                        ))}
                      </div>

                      {/* Expandable Reasoning Details Accordion */}
                      <div style={{ marginTop: '10px', borderTop: '1px solid #1e293b', paddingTop: '8px' }}>
                        <button
                          onClick={() => setExpandedPlanIdx(expandedPlanIdx === idx ? null : idx)}
                          style={{
                            backgroundColor: 'transparent',
                            border: 'none',
                            color: '#38bdf8',
                            fontSize: '11px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: 0
                          }}
                        >
                          {expandedPlanIdx === idx ? '▼ Collapse Orchestrator Details' : '▶ Expand Orchestrator Details'}
                        </button>
                        {expandedPlanIdx === idx && (
                          <div style={{ marginTop: '8px', fontSize: '11px', color: '#94a3b8', backgroundColor: '#1e293b', padding: '10px', borderRadius: '6px', overflowX: 'auto' }}>
                            <div style={{ marginBottom: '4px' }}><strong>Orchestration Order:</strong> {plan.execution_order?.join(' → ')}</div>
                            {plan.limitations && plan.limitations.length > 0 && (
                              <div style={{ color: '#ef4444', marginTop: '4px' }}>
                                <strong>Warnings/Limitations:</strong>
                                <ul>
                                  {plan.limitations.map((lim, lidx) => (
                                    <li key={lidx}>{lim}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Text Form Area */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          style={inputAreaStyle}
        >
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={loading}
            placeholder={loading ? "Copilot orchestrator running in background..." : "Type analytical prompts (e.g. Profile this, clean issues and query sales)..."}
            style={{
              flex: 1,
              padding: '12px 16px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: 'white',
              fontSize: '14px',
              outline: 'none'
            }}
          />
          <button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            style={{
              padding: '12px 24px',
              backgroundColor: loading || !inputMessage.trim() ? '#475569' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: loading || !inputMessage.trim() ? 'not-allowed' : 'pointer',
              fontWeight: '600'
            }}
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </form>
      </div>

      {/* Reusable Visual Workflow Creation Modal */}
      {showWorkflowModal && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            width: '400px',
            backgroundColor: '#1e293b',
            borderRadius: '12px',
            padding: '24px',
            border: '1px solid #334155',
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)'
          }}>
            <h3 style={{ margin: '0 0 10px 0' }}>⛓️ Convert to Reusable Workflow</h3>
            <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '20px' }}>
              Create a saved pipeline script from the steps in this conversation thread so you can execute them recursively in the Visual Automation canvas.
            </p>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', fontSize: '12px', marginBottom: '5px', color: '#94a3b8' }}>Workflow Pipeline Name</label>
              <input
                type="text"
                placeholder="Sales Analytics Auto Clean"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  color: 'white',
                  outline: 'none'
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setShowWorkflowModal(false)}
                style={{
                  padding: '8px 16px',
                  backgroundColor: 'transparent',
                  color: '#94a3b8',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateWorkflow}
                disabled={generatingWorkflow || !workflowName.trim()}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                {generatingWorkflow ? "Saving..." : "Save Pipeline"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AICopilot;
