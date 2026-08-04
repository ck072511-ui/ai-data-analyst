import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const ENTITY_TYPES = [
  'Dataset', 'Table', 'Column', 'KPI', 'Metric', 
  'Business Term', 'Document', 'Workflow', 'Report'
];

const KnowledgeGraph = ({ token, showNotification }) => {
  const [entities, setEntities] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [selectedEntity, setSelectedEntity] = useState(null);
  
  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [semanticSearch, setSemanticSearch] = useState(false);
  const [typeFilter, setTypeFilter] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [buildProgress, setBuildProgress] = useState(0);

  // Lineage & Impact state
  const [lineagePaths, setLineagePaths] = useState([]);
  const [impactPaths, setImpactPaths] = useState([]);

  useEffect(() => {
    fetchGraphData();
  }, [typeFilter]);

  const fetchGraphData = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch entities list
      const entUrl = semanticSearch 
        ? `${API_BASE_URL}/knowledge/search?query=${searchQuery}`
        : `${API_BASE_URL}/knowledge/entities?search=${searchQuery}&entity_type=${typeFilter}`;
      
      const entRes = await axios.get(entUrl, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEntities(entRes.data || []);

      // 2. Fetch relationships list
      const relRes = await axios.get(`${API_BASE_URL}/knowledge/relationships`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRelationships(relRes.data || []);
    } catch (err) {
      console.error(err);
      showNotification('Failed to fetch Knowledge Graph data.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBuildGraph = async (rebuild = false) => {
    setIsLoading(true);
    setBuildProgress(10);
    const endpoint = rebuild ? 'rebuild' : 'build';
    try {
      const res = await axios.post(`${API_BASE_URL}/knowledge/${endpoint}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBuildProgress(100);
      showNotification(`Knowledge Graph ${rebuild ? 'rebuilt' : 'updated'} successfully in ${res.data.duration_seconds}s!`, 'success');
      fetchGraphData();
    } catch (err) {
      console.error(err);
      showNotification('Failed to process graph discovery build.', 'error');
    } finally {
      setIsLoading(false);
      setTimeout(() => setBuildProgress(0), 2000);
    }
  };

  const handleEntityClick = async (entity) => {
    setSelectedEntity(entity);
    // Fetch Lineage and Impact paths
    try {
      const lineageRes = await axios.get(`${API_BASE_URL}/knowledge/lineage/${entity.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setLineagePaths(lineageRes.data || []);

      const impactRes = await axios.get(`${API_BASE_URL}/knowledge/impact/${entity.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setImpactPaths(impactRes.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const getEntityIcon = (type) => {
    switch (type) {
      case 'Dataset': return '💾';
      case 'Table': return '📊';
      case 'Column': return '📑';
      case 'KPI': return '📈';
      case 'Business Term': return '📖';
      case 'Document': return '📄';
      case 'Workflow': return '⛓️';
      case 'Report': return '📃';
      default: return '📍';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '15px' }}>
      
      {/* Header Controls */}
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0 }}>Enterprise Knowledge Graph</h2>
          <p style={{ margin: '5px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Automatically discover semantic connections across schemas, document catalogs, workflows, and business definitions offline.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn-secondary" onClick={() => handleBuildGraph(false)} disabled={isLoading}>Scan & Update Graph</button>
          <button className="btn-primary" onClick={() => handleBuildGraph(true)} disabled={isLoading}>Rebuild Graph</button>
        </div>
      </div>

      {buildProgress > 0 && (
        <div className="card" style={{ padding: '15px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '12px' }}>
            <span>Running discovery scans...</span>
            <span>{buildProgress}%</span>
          </div>
          <div style={{ background: '#1e293b', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
            <div style={{ background: '#38bdf8', width: `${buildProgress}%`, height: '100%', transition: 'width 0.3s' }}></div>
          </div>
        </div>
      )}

      {/* Explorer Panels */}
      <div style={{ display: 'flex', flex: 1, gap: '20px', minHeight: '500px' }}>
        
        {/* Left Side: Search, Filters & Entities list */}
        <div className="card" style={{ width: '350px', padding: '15px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <h3 style={{ margin: 0, fontSize: '15px' }}>Entities Explorer</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', gap: '5px' }}>
              <input
                type="text"
                placeholder={semanticSearch ? "Ask business synonyms..." : "Search entities..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-control"
                style={{ flex: 1 }}
              />
              <button className="btn-secondary" onClick={fetchGraphData} style={{ padding: '8px 12px' }}>🔍</button>
            </div>
            
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={semanticSearch}
                onChange={(e) => {
                  setSemanticSearch(e.target.checked);
                  // clear queries when swapping modes
                  setSearchQuery('');
                }}
              />
              Enable Semantic synonym lookup mapping
            </label>

            {!semanticSearch && (
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="form-control"
              >
                <option value="">Filter by Type...</option>
                {ENTITY_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            )}
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {entities.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                No entities found. Click &apos;Rebuild Graph&apos; to trigger first run discovery.
              </div>
            ) : (
              entities.map(ent => (
                <div
                  key={ent.id}
                  onClick={() => handleEntityClick(ent)}
                  style={{
                    padding: '10px',
                    borderRadius: '6px',
                    backgroundColor: selectedEntity && selectedEntity.id === ent.id ? '#334155' : '#0f172a',
                    border: selectedEntity && selectedEntity.id === ent.id ? '1px solid #38bdf8' : '1px solid #334155',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    transition: 'background-color 0.2s'
                  }}
                  className="hover-trigger"
                >
                  <span style={{ fontSize: '18px' }}>{getEntityIcon(ent.entity_type)}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ent.name}</div>
                    <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>{ent.entity_type}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Center: Details & Lineage / Impact Viewer */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Entity Details Card */}
          <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', borderBottom: '1px solid #334155', paddingBottom: '10px' }}>
              Entity Metadata Details
            </h3>

            {!selectedEntity ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>
                Select an entity from explorer list to inspect properties, descriptions, and associations.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
                <div>
                  <div style={{ fontSize: '32px', marginBottom: '10px' }}>{getEntityIcon(selectedEntity.entity_type)}</div>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#f8fafc' }}>{selectedEntity.name}</div>
                  <div style={{ fontSize: '11px', color: '#38bdf8', textTransform: 'uppercase', marginTop: '5px' }}>{selectedEntity.entity_type}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {Object.entries(selectedEntity.properties || {}).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px dashed #334155', paddingBottom: '4px' }}>
                      <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>{k.replace('_', ' ')}:</span>
                      <span style={{ fontWeight: 'bold' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Lineage & Impact Traversal paths */}
          {selectedEntity && (
            <div style={{ display: 'flex', gap: '20px', flex: 1 }}>
              
              {/* Upstream Lineage paths */}
              <div className="card" style={{ flex: 1, padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <h4 style={{ margin: 0, fontSize: '14px', color: '#10b981' }}> Upstream Lineage path</h4>
                <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {lineagePaths.length === 0 ? (
                    <div style={{ fontSize: '12px', color: '#94a3b8', padding: '10px' }}>No upstream parent links.</div>
                  ) : (
                    lineagePaths.map((p, idx) => (
                      <div key={idx} style={{ padding: '8px', backgroundColor: '#0f172a', borderRadius: '4px', border: '1px solid #334155', fontSize: '12px' }}>
                        <div><strong>Parent Name:</strong> {p.target_name} ({p.target_type})</div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '3px' }}>
                          Connection: {p.relationship_type} (Confidence: {p.confidence})
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Downstream Impact paths */}
              <div className="card" style={{ flex: 1, padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <h4 style={{ margin: 0, fontSize: '14px', color: '#f59e0b' }}> Downstream Impact path</h4>
                <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {impactPaths.length === 0 ? (
                    <div style={{ fontSize: '12px', color: '#94a3b8', padding: '10px' }}>No downstream dependencies.</div>
                  ) : (
                    impactPaths.map((p, idx) => (
                      <div key={idx} style={{ padding: '8px', backgroundColor: '#0f172a', borderRadius: '4px', border: '1px solid #334155', fontSize: '12px' }}>
                        <div><strong>Dependent Node:</strong> {p.source_name} ({p.source_type})</div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '3px' }}>
                          Connection: {p.relationship_type} (Confidence: {p.confidence})
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>
          )}

        </div>

      </div>

    </div>
  );
};

export default KnowledgeGraph;
export { ENTITY_TYPES };
