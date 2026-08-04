import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const NODE_TYPES = [
  { type: 'dataset_upload', name: 'Dataset Upload', description: 'Loads or references user file datasets' },
  { type: 'data_profiling', name: 'Data Profiling', description: 'Generates outline statistics and alerts' },
  { type: 'data_cleaning', name: 'Data Cleaning', description: 'Runs whitespace and Mixed Type standardizations' },
  { type: 'sql_query', name: 'SQL Query', description: 'Runs intent SQL scripts against DB connections' },
  { type: 'rag_query', name: 'RAG Query', description: 'Performs semantic lookup on loaded glossaries' },
  { type: 'multi_agent_analysis', name: 'Multi-Agent Analysis', description: 'Planner-Critic orchestration review' },
  { type: 'explainability', name: 'Explainability', description: 'Constructs audit ratings and safety scans' },
  { type: 'report_generation', name: 'Report Generation', description: 'Compiles layout assets into PDF/DOCX/PPTX' },
  { type: 'notification', name: 'Notification', description: 'Delivers real-time task triggers alerts' },
  { type: 'export', name: 'Export', description: 'Copies dataset tables to CSV or target format' }
];

const TEMPLATES = [
  {
    name: 'Sales Analytics Pipeline',
    description: 'Profiles uploaded sales tables, runs SQL analytics aggregates, and builds a PDF report.',
    nodes: [
      { id: 'upload_1', type: 'dataset_upload', label: 'Load Sales Data', config: { dataset_id: '', timeout: 30 }, incoming: [] },
      { id: 'profile_1', type: 'data_profiling', label: 'Profile Sales Quality', config: { dataset_id: 'upload_1', timeout: 60 }, incoming: ['upload_1'] },
      { id: 'sql_1', type: 'sql_query', label: 'Compute Aggregate Sales', config: { query_sql: 'SELECT date, SUM(amount) FROM sales GROUP BY date', timeout: 30 }, incoming: ['profile_1'] },
      { id: 'report_1', type: 'report_generation', label: 'Compile Sales PDF', config: { report_type: 'sales_analytics', file_format: 'pdf', branding: { color: '#0f172a' } }, incoming: ['sql_1'] }
    ]
  },
  {
    name: 'Customer Churn Analysis',
    description: 'Cleans mixed placeholders, maps customer trends via AI agents, and fires a notification.',
    nodes: [
      { id: 'upload_1', type: 'dataset_upload', label: 'Load Churn Logs', config: { dataset_id: '', timeout: 30 }, incoming: [] },
      { id: 'clean_1', type: 'data_cleaning', label: 'Normalize mixed cells', config: { dataset_id: 'upload_1', cleaning_config: { remove_duplicates: true, mixed_types: 'constant' } }, incoming: ['upload_1'] },
      { id: 'agent_1', type: 'multi_agent_analysis', label: 'Evaluate Churn Risks', config: { query: 'Analyze top 5 variables correlating with churn flags.' }, incoming: ['clean_1'] },
      { id: 'notify_1', type: 'notification', label: 'Trigger Churn Notification', config: { title: 'Churn Analysis Done', message: 'Risk evaluations completed.', severity: 'success' }, incoming: ['agent_1'] }
    ]
  },
  {
    name: 'Financial Audit insights',
    description: 'Inspects SQL queries with security scanners and compiles Word audit documents.',
    nodes: [
      { id: 'sql_1', type: 'sql_query', label: 'Query Ledger Balance', config: { query_sql: 'SELECT account, balance FROM ledger WHERE balance > 100000' }, incoming: [] },
      { id: 'xai_1', type: 'explainability', label: 'Audit SQL Statements', config: { sql: 'sql_1', query: 'List anomalous balance changes' }, incoming: ['sql_1'] },
      { id: 'report_1', type: 'report_generation', label: 'Generate DOCX Report', config: { report_type: 'financial_analysis', file_format: 'docx' }, incoming: ['xai_1'] }
    ]
  }
];

const WorkflowBuilder = ({ token, datasets, showNotification }) => {
  const [nodes, setNodes] = useState([]);
  const [workflowName, setWorkflowName] = useState('New Workflow Pipeline');
  const [workflowDescription, setWorkflowDescription] = useState('Pipeline description...');
  const [selectedNode, setSelectedNode] = useState(null);
  
  // For Database connections selection in SQL query
  const [dbConnections, setDbConnections] = useState([]);
  
  const [nodeTypes, setNodeTypes] = useState(NODE_TYPES);
  
  // Schedules configuration state
  const [scheduleType, setScheduleType] = useState('one_time');
  const [cronExpression, setCronExpression] = useState('*/5 * * * *');
  const [nextRunAt, setNextRunAt] = useState('');

  useEffect(() => {
    fetchDbConnections();

    const fetchPluginNodes = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/plugins`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const list = res.data || [];
        const dynamicNodes = list
          .filter(p => p.installed && p.enabled && p.capability === 'workflow_node')
          .map(p => ({
            type: p.id,
            name: p.name,
            description: p.description,
            isPlugin: true,
            config_schema: p.config_schema
          }));
        setNodeTypes([...NODE_TYPES, ...dynamicNodes]);
      } catch (err) {
        console.error('Failed to load plugin nodes:', err);
      }
    };
    fetchPluginNodes();

    const checkTemplate = () => {
      const stored = sessionStorage.getItem('loaded_workflow_template');
      if (stored) {
        try {
          const template = JSON.parse(stored);
          setWorkflowName(template.name);
          setWorkflowDescription(template.description);
          setNodes(template.nodes);
          setSelectedNode(template.nodes[0] || null);
          sessionStorage.removeItem('loaded_workflow_template');
        } catch (e) {
          console.error(e);
        }
      }
    };
    
    checkTemplate();
    window.addEventListener('storage', checkTemplate);
    return () => window.removeEventListener('storage', checkTemplate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchDbConnections = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/database/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDbConnections(res.data || []);
    } catch (err) {
      console.error('Failed to load database connections', err);
    }
  };

  const addNode = (typeInfo) => {
    const nodeCount = nodes.filter(n => n.type === typeInfo.type).length + 1;
    const newNode = {
      id: `${typeInfo.type}_${Date.now()}`,
      type: typeInfo.type,
      label: `${typeInfo.name} ${nodeCount}`,
      config: {
        timeout: 60,
        retry_policy: { max_retries: 0, delay: 1 }
      },
      incoming: []
    };
    setNodes([...nodes, newNode]);
    setSelectedNode(newNode);
  };

  const deleteNode = (id) => {
    setNodes(nodes.filter(n => n.id !== id));
    if (selectedNode && selectedNode.id === id) {
      setSelectedNode(null);
    }
  };

  const updateNodeConfig = (id, field, value) => {
    const updated = nodes.map(n => {
      if (n.id === id) {
        return {
          ...n,
          config: {
            ...n.config,
            [field]: value
          }
        };
      }
      return n;
    });
    setNodes(updated);
    // Sync active node settings panel
    const current = updated.find(n => n.id === id);
    setSelectedNode(current);
  };

  const updateNodeRetryPolicy = (id, field, value) => {
    const updated = nodes.map(n => {
      if (n.id === id) {
        return {
          ...n,
          config: {
            ...n.config,
            retry_policy: {
              ...n.config.retry_policy,
              [field]: value
            }
          }
        };
      }
      return n;
    });
    setNodes(updated);
    const current = updated.find(n => n.id === id);
    setSelectedNode(current);
  };

  const toggleIncomingConnection = (nodeId, targetId) => {
    const updated = nodes.map(n => {
      if (n.id === nodeId) {
        const isConnected = n.incoming.includes(targetId);
        return {
          ...n,
          incoming: isConnected 
            ? n.incoming.filter(id => id !== targetId)
            : [...n.incoming, targetId]
        };
      }
      return n;
    });
    setNodes(updated);
    const current = updated.find(n => n.id === nodeId);
    setSelectedNode(current);
  };

  const loadTemplate = (template) => {
    setWorkflowName(template.name);
    setWorkflowDescription(template.description);
    setNodes(template.nodes);
    setSelectedNode(template.nodes[0] || null);
    showNotification(`Loaded template: ${template.name}`, 'info');
  };

  const handleSaveWorkflow = async () => {
    if (nodes.length === 0) {
      showNotification('Workflow contains no nodes to save.', 'warning');
      return;
    }

    // Build standard edges from the incoming mappings
    const edges = [];
    nodes.forEach(node => {
      node.incoming.forEach(sourceId => {
        edges.push({
          id: `edge_${sourceId}_${node.id}`,
          source: sourceId,
          target: node.id
        });
      });
    });

    const definition = {
      nodes: nodes.map(n => ({
        id: n.id,
        type: n.type,
        label: n.label,
        config: n.config
      })),
      edges
    };

    try {
      const res = await axios.post(`${API_BASE_URL}/workflows`, {
        name: workflowName,
        description: workflowDescription,
        definition
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const workflowId = res.data.id;
      showNotification('Workflow definition saved successfully!', 'success');

      // Configure schedule if any
      if (scheduleType !== 'manual') {
        await axios.post(`${API_BASE_URL}/workflows/${workflowId}/schedule`, {
          schedule_type: scheduleType,
          cron_expression: scheduleType === 'cron' ? cronExpression : null,
          next_run_at: nextRunAt ? new Date(nextRunAt).toISOString() : null
        }, {
          headers: { Authorization: `Bearer ${token}` }
        });
        showNotification('Recurrence schedule configured successfully.', 'success');
      }

      return workflowId;
    } catch (err) {
      console.error(err);
      showNotification('Failed to save workflow definition.', 'error');
    }
  };

  const handleRunWorkflow = async () => {
    const workflowId = await handleSaveWorkflow();
    if (!workflowId) return;

    try {
      await axios.post(`${API_BASE_URL}/workflows/${workflowId}/run`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification('Workflow execution triggered successfully!', 'success');
    } catch (err) {
      console.error(err);
      showNotification('Failed to run workflow.', 'error');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '15px' }}>
      
      {/* Configuration Header */}
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            style={{ fontSize: '20px', fontWeight: 'bold', background: 'transparent', border: 'none', color: '#f8fafc', width: '300px' }}
          />
          <input
            type="text"
            value={workflowDescription}
            onChange={(e) => setWorkflowDescription(e.target.value)}
            style={{ fontSize: '13px', background: 'transparent', border: 'none', color: '#94a3b8', width: '300px', display: 'block', marginTop: '5px' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn-secondary" onClick={handleSaveWorkflow}>Save Workflow</button>
          <button className="btn-primary" onClick={handleRunWorkflow}>Run Workflow</button>
        </div>
      </div>

      {/* Templates Selector */}
      <div className="card" style={{ padding: '15px' }}>
        <h4 style={{ margin: '0 0 10px 0' }}>Prebuilt Workflow Templates</h4>
        <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '5px' }}>
          {TEMPLATES.map((tmpl, idx) => (
            <div 
              key={idx} 
              className="card" 
              style={{ padding: '10px', minWidth: '220px', maxWidth: '300px', cursor: 'pointer', border: '1px solid #334155' }}
              onClick={() => loadTemplate(tmpl)}
            >
              <h5 style={{ margin: '0 0 5px 0', color: '#38bdf8' }}>{tmpl.name}</h5>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>{tmpl.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, gap: '20px', minHeight: '450px' }}>
        
        {/* Left Side: Nodes Catalog */}
        <div className="card" style={{ width: '250px', padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h3 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>Nodes Library</h3>
          <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 10px 0' }}>Click to append nodes to your pipeline canvas:</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1 }}>
            {nodeTypes.map(n => (
              <div 
                key={n.type} 
                onClick={() => addNode(n)}
                style={{ 
                  padding: '10px', 
                  backgroundColor: '#1e293b', 
                  borderRadius: '6px', 
                  cursor: 'pointer',
                  border: '1px solid #334155',
                  transition: 'transform 0.2s, background-color 0.2s'
                }}
                className="hover-trigger"
              >
                <div style={{ fontWeight: '600', fontSize: '13px', color: '#38bdf8' }}>{n.name}</div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>{n.description}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Center: Canvas Workspace */}
        <div className="card" style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '15px', position: 'relative' }}>
          <h3 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>Canvas Board</h3>
          
          {nodes.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#94a3b8', border: '2px dashed #334155', borderRadius: '8px' }}>
              Select pre-built templates or click Library items to build your execution path
            </div>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '15px', alignContent: 'flex-start', flex: 1, overflowY: 'auto' }}>
              {nodes.map((node, index) => {
                const isSelected = selectedNode && selectedNode.id === node.id;
                return (
                  <div 
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    style={{ 
                      width: '200px',
                      padding: '15px', 
                      backgroundColor: isSelected ? '#334155' : '#1e293b', 
                      borderRadius: '8px',
                      border: isSelected ? '2px solid #38bdf8' : '1px solid #334155',
                      cursor: 'pointer',
                      position: 'relative'
                    }}
                  >
                    <div style={{ position: 'absolute', top: '10px', right: '10px', cursor: 'pointer', color: '#ef4444' }} onClick={(e) => { e.stopPropagation(); deleteNode(node.id); }}>✕</div>
                    <div style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 'bold', textTransform: 'uppercase' }}>{node.type.replace('_', ' ')}</div>
                    <div style={{ fontWeight: '600', fontSize: '14px', marginTop: '5px', wordBreak: 'break-all' }}>{node.label}</div>
                    
                    {node.incoming.length > 0 && (
                      <div style={{ marginTop: '8px', fontSize: '11px', color: '#94a3b8' }}>
                        🔗 Reads: {node.incoming.map(id => nodes.find(n => n.id === id)?.label || id).join(', ')}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Side: Active Node Configuration Editor */}
        {selectedNode && (
          <div className="card" style={{ width: '320px', padding: '15px', display: 'flex', flexDirection: 'column', gap: '15px', overflowY: 'auto' }}>
            <h3 style={{ margin: 0, fontSize: '15px', borderBottom: '1px solid #334155', paddingBottom: '10px' }}>
              Config: {selectedNode.label}
            </h3>

            {/* Label Name field */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <label style={{ fontSize: '12px', color: '#94a3b8' }}>Node Label</label>
              <input
                type="text"
                value={selectedNode.label}
                onChange={(e) => {
                  const updated = nodes.map(n => n.id === selectedNode.id ? { ...n, label: e.target.value } : n);
                  setNodes(updated);
                  setSelectedNode({ ...selectedNode, label: e.target.value });
                }}
                className="form-control"
              />
            </div>

            {/* Node-specific configuration details */}
            {selectedNode.type === 'dataset_upload' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Source Dataset</label>
                <select
                  value={selectedNode.config.dataset_id || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'dataset_id', e.target.value)}
                  className="form-control"
                >
                  <option value="">Select File...</option>
                  {datasets.map(d => (
                    <option key={d.id} value={d.id}>{d.filename}</option>
                  ))}
                </select>
              </div>
            )}

            {selectedNode.type === 'data_cleaning' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Cleaning Checklist Rules</label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px' }}>
                  <input
                    type="checkbox"
                    checked={!!selectedNode.config.cleaning_config?.remove_duplicates}
                    onChange={(e) => updateNodeConfig(selectedNode.id, 'cleaning_config', {
                      ...selectedNode.config.cleaning_config,
                      remove_duplicates: e.target.checked
                    })}
                  />
                  Remove Exact Row Duplicates
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px' }}>
                  <input
                    type="checkbox"
                    checked={!!selectedNode.config.cleaning_config?.trim_whitespace}
                    onChange={(e) => updateNodeConfig(selectedNode.id, 'cleaning_config', {
                      ...selectedNode.config.cleaning_config,
                      trim_whitespace: e.target.checked
                    })}
                  />
                  Trim whitespace
                </label>
              </div>
            )}

            {selectedNode.type === 'sql_query' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Database Engine Target</label>
                <select
                  value={selectedNode.config.db_connection_id || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'db_connection_id', e.target.value)}
                  className="form-control"
                >
                  <option value="">Local SQLite (Default)</option>
                  {dbConnections.map(c => (
                    <option key={c.id} value={c.id}>{c.database_name} ({c.db_type})</option>
                  ))}
                </select>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>SQL Statement Script</label>
                <textarea
                  value={selectedNode.config.query_sql || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'query_sql', e.target.value)}
                  className="form-control"
                  rows={4}
                />
              </div>
            )}

            {selectedNode.type === 'rag_query' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Glossary Query Question</label>
                <input
                  type="text"
                  value={selectedNode.config.query || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'query', e.target.value)}
                  className="form-control"
                />
              </div>
            )}

            {selectedNode.type === 'multi_agent_analysis' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Analyst query intent</label>
                <textarea
                  value={selectedNode.config.query || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'query', e.target.value)}
                  className="form-control"
                  rows={3}
                />
              </div>
            )}

            {selectedNode.type === 'report_generation' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Document Template Style</label>
                <select
                  value={selectedNode.config.report_type || 'sales_analytics'}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'report_type', e.target.value)}
                  className="form-control"
                >
                  <option value="sales_analytics">Sales Analytics</option>
                  <option value="customer_churn">Customer Churn</option>
                  <option value="financial_analysis">Financial Analysis</option>
                </select>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Asset file format</label>
                <select
                  value={selectedNode.config.file_format || 'pdf'}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'file_format', e.target.value)}
                  className="form-control"
                >
                  <option value="pdf">PDF Document Flowable</option>
                  <option value="docx">Word DOCX Presentation</option>
                  <option value="pptx">PowerPoint PPTX slides</option>
                </select>
              </div>
            )}

            {selectedNode.type === 'notification' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Title</label>
                <input
                  type="text"
                  value={selectedNode.config.title || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'title', e.target.value)}
                  className="form-control"
                />
                <label style={{ fontSize: '12px', color: '#94a3b8' }}>Message Payload</label>
                <textarea
                  value={selectedNode.config.message || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, 'message', e.target.value)}
                  className="form-control"
                  rows={2}
                />
              </div>
            )}

            {/* Render Dynamic Config Schema for Custom Plugins */}
            {nodeTypes.find(t => t.type === selectedNode.type)?.isPlugin && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 600 }}>🔌 Dynamic Plugin Fields</span>
                {(() => {
                  const schema = nodeTypes.find(t => t.type === selectedNode.type)?.config_schema || {};
                  const properties = schema.properties || {};
                  return Object.entries(properties).map(([key, val]) => (
                    <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '11px', color: '#cbd5e1' }}>
                        {key.replace('_', ' ').toUpperCase()} {val.description ? `(${val.description})` : ''}
                      </label>
                      {val.type === 'boolean' ? (
                        <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px' }}>
                          <input
                            type="checkbox"
                            checked={!!selectedNode.config[key]}
                            onChange={(e) => updateNodeConfig(selectedNode.id, key, e.target.checked)}
                          />
                          Enable {key}
                        </label>
                      ) : val.enum ? (
                        <select
                          value={selectedNode.config[key] || val.default || ''}
                          onChange={(e) => updateNodeConfig(selectedNode.id, key, e.target.value)}
                          className="form-control"
                        >
                          {val.enum.map(o => (
                            <option key={o} value={o}>{o}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={val.type === 'integer' || val.type === 'number' ? 'number' : 'text'}
                          value={selectedNode.config[key] ?? val.default ?? ''}
                          onChange={(e) => {
                            const valParsed = val.type === 'integer' || val.type === 'number' ? parseFloat(e.target.value) : e.target.value;
                            updateNodeConfig(selectedNode.id, key, valParsed);
                          }}
                          className="form-control"
                        />
                      )}
                    </div>
                  ));
                })()}
              </div>
            )}

            {/* Cluster Execution Policy */}
            <div style={{ borderTop: '1px solid #334155', paddingTop: '10px', marginTop: '10px' }}>
              <h4 style={{ fontSize: '13px', margin: '0 0 10px 0' }}>⛓️ Cluster Execution Settings</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '11px', color: '#94a3b8' }}>Execution Mode</label>
                  <select
                    value={selectedNode.config.execution_mode || 'local'}
                    onChange={(e) => updateNodeConfig(selectedNode.id, 'execution_mode', e.target.value)}
                    className="form-control"
                  >
                    <option value="local">Local Execution (Single Machine)</option>
                    <option value="distributed">Distributed (Cluster Worker)</option>
                  </select>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '11px', color: '#94a3b8' }}>Priority</label>
                    <select
                      value={selectedNode.config.priority || 'medium'}
                      onChange={(e) => updateNodeConfig(selectedNode.id, 'priority', e.target.value)}
                      className="form-control"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '11px', color: '#94a3b8' }}>Required Cap</label>
                    <select
                      value={selectedNode.config.preferred_capability || ''}
                      onChange={(e) => updateNodeConfig(selectedNode.id, 'preferred_capability', e.target.value)}
                      className="form-control"
                    >
                      <option value="">Any node</option>
                      <option value="predictive">Predictive</option>
                      <option value="rag">RAG</option>
                      <option value="report">Report</option>
                      <option value="streaming">Streaming</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* General policies configuration */}
            <div style={{ borderTop: '1px solid #334155', paddingTop: '10px', marginTop: '10px' }}>
              <h4 style={{ fontSize: '13px', margin: '0 0 10px 0' }}>Retry & Timeout Policy</h4>
              <div style={{ display: 'flex', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94a3b8' }}>Max Retries</label>
                  <input
                    type="number"
                    value={selectedNode.config.retry_policy?.max_retries || 0}
                    onChange={(e) => updateNodeRetryPolicy(selectedNode.id, 'max_retries', parseInt(e.target.value) || 0)}
                    className="form-control"
                    style={{ padding: '4px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94a3b8' }}>Delay (sec)</label>
                  <input
                    type="number"
                    value={selectedNode.config.retry_policy?.delay || 1}
                    onChange={(e) => updateNodeRetryPolicy(selectedNode.id, 'delay', parseFloat(e.target.value) || 1)}
                    className="form-control"
                    style={{ padding: '4px' }}
                  />
                </div>
              </div>
            </div>

            {/* Inputs Connection links */}
            <div style={{ borderTop: '1px solid #334155', paddingTop: '10px' }}>
              <h4 style={{ fontSize: '13px', margin: '0 0 5px 0' }}>DAG Connections</h4>
              <p style={{ fontSize: '11px', color: '#94a3b8', margin: '0 0 8px 0' }}>Select nodes to read inputs from:</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                {nodes.filter(n => n.id !== selectedNode.id).map(n => {
                  const isChecked = selectedNode.incoming.includes(n.id);
                  return (
                    <label key={n.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleIncomingConnection(selectedNode.id, n.id)}
                      />
                      {n.label}
                    </label>
                  );
                })}
              </div>
            </div>

          </div>
        )}

      </div>

      {/* Recurrence Scheduler Configuration block */}
      <div className="card" style={{ padding: '15px' }}>
        <h4 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>Automatic Workflow Scheduler</h4>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '5px' }}>Trigger Type</label>
            <select
              value={scheduleType}
              onChange={(e) => setScheduleType(e.target.value)}
              className="form-control"
              style={{ width: '150px' }}
            >
              <option value="one_time">One-time execution</option>
              <option value="daily">Every day recurrence</option>
              <option value="weekly">Every week recurrence</option>
              <option value="cron">Cron expression matches</option>
              <option value="manual">Manual trigger only</option>
            </select>
          </div>
          {scheduleType === 'cron' && (
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '5px' }}>Cron expression (e.g. */5 * * * *)</label>
              <input
                type="text"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                className="form-control"
                style={{ width: '180px' }}
              />
            </div>
          )}
          {scheduleType === 'one_time' && (
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '5px' }}>Execute scheduled time</label>
              <input
                type="datetime-local"
                value={nextRunAt}
                onChange={(e) => setNextRunAt(e.target.value)}
                className="form-control"
                style={{ width: '220px' }}
              />
            </div>
          )}
        </div>
      </div>

    </div>
  );
};

export default WorkflowBuilder;
