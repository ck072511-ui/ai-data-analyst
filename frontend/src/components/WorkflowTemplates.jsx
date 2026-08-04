import React from 'react';

const PREBUILT_TEMPLATES = [
  {
    id: 'sales_analytics',
    name: 'Sales Analytics Pipeline',
    description: 'Automated loading of sales records, data profiling anomaly checks, dynamic SQL calculations, and compiling high quality PDF summary reports.',
    nodes: [
      { id: 'upload_sales', type: 'dataset_upload', label: 'Load Sales Records', config: { dataset_id: '' } },
      { id: 'profile_sales', type: 'data_profiling', label: 'Inspect Quality', config: { dataset_id: 'upload_sales' }, incoming: ['upload_sales'] },
      { id: 'sql_sales', type: 'sql_query', label: 'Aggregate Revenue', config: { query_sql: 'SELECT strftime("%Y-%m", date) as month, SUM(revenue) FROM sales GROUP BY month' }, incoming: ['profile_sales'] },
      { id: 'pdf_report', type: 'report_generation', label: 'Generate PDF Ledger', config: { report_type: 'sales_analytics', file_format: 'pdf' }, incoming: ['sql_sales'] }
    ]
  },
  {
    id: 'customer_churn',
    name: 'Customer Churn Tracker',
    description: 'Profiles historical customer service logs, normalizes mixed cells and whitespace issues, runs planning critic multi-agent analysis, and triggers task alerts.',
    nodes: [
      { id: 'upload_churn', type: 'dataset_upload', label: 'Load Customer History', config: { dataset_id: '' } },
      { id: 'clean_churn', type: 'data_cleaning', label: 'Clean Empty Cells', config: { dataset_id: 'upload_churn', cleaning_config: { remove_duplicates: true } }, incoming: ['upload_churn'] },
      { id: 'agent_churn', type: 'multi_agent_analysis', label: 'Analyze Churn Correlations', config: { query: 'Detail the main 3 features correlating with churn.' }, incoming: ['clean_churn'] },
      { id: 'notify_churn', type: 'notification', label: 'Trigger Churn Alert', config: { title: 'Churn Analysis Completed', severity: 'warning' }, incoming: ['agent_churn'] }
    ]
  },
  {
    id: 'financial_analysis',
    name: 'Financial Audit insights',
    description: 'Executes ledger balance queries against remote SQL connections, generates explainability audit details, and constructs editable Microsoft Word documents.',
    nodes: [
      { id: 'sql_ledger', type: 'sql_query', label: 'Query Ledger Balance', config: { query_sql: 'SELECT account, balance FROM ledger WHERE balance > 50000' } },
      { id: 'explain_ledger', type: 'explainability', label: 'Audit SQL Statements', config: { sql: 'sql_ledger', query: 'List anomalous balance changes' }, incoming: ['sql_ledger'] },
      { id: 'docx_report', type: 'report_generation', label: 'Generate Word Summary', config: { report_type: 'financial_analysis', file_format: 'docx' }, incoming: ['explain_ledger'] }
    ]
  },
  {
    id: 'data_quality_audit',
    name: 'Data Quality Audit',
    description: 'Verifies phone validation structures, dates format matching indices, and generates health indicators.',
    nodes: [
      { id: 'upload_audit', type: 'dataset_upload', label: 'Upload Dataset For Inspection', config: { dataset_id: '' } },
      { id: 'profile_audit', type: 'data_profiling', label: 'Perform Outliers Scans', config: { dataset_id: 'upload_audit' }, incoming: ['upload_audit'] },
      { id: 'notify_audit', type: 'notification', label: 'Quality Audit Report Alert', config: { title: 'Quality Audit Triggered', message: 'Data quality checks ran.', severity: 'info' }, incoming: ['profile_audit'] }
    ]
  },
  {
    id: 'executive_reporting',
    name: 'Executive Reporting',
    description: 'Runs custom analytical query sweeps and parses PowerPoint presentation slides ready for executive summaries.',
    nodes: [
      { id: 'sql_exec', type: 'sql_query', label: 'Query Executive KPI Balance', config: { query_sql: 'SELECT month, SUM(profit) FROM accounting GROUP BY month' } },
      { id: 'agent_exec', type: 'multi_agent_analysis', label: 'Draft Executive Insights', config: { query: 'Analyze top monthly profit increases.' }, incoming: ['sql_exec'] },
      { id: 'pptx_report', type: 'report_generation', label: 'Generate PPTX Slides', config: { report_type: 'executive_reporting', file_format: 'pptx' }, incoming: ['agent_exec'] }
    ]
  },
  {
    id: 'ai_insights_pipeline',
    name: 'AI Insights Pipeline',
    description: 'Runs auto-cleaning standardizations on raw files and retrieves hybrid RAG queries context to compile actionable business glossaries.',
    nodes: [
      { id: 'upload_ai', type: 'dataset_upload', label: 'Load Raw Database File', config: { dataset_id: '' } },
      { id: 'clean_ai', type: 'data_cleaning', label: 'Standardize Mixed Columns', config: { dataset_id: 'upload_ai', cleaning_config: { remove_duplicates: true } }, incoming: ['upload_ai'] },
      { id: 'rag_ai', type: 'rag_query', label: 'Query Document Repository Context', config: { query: 'Verify glossary dictionary entries matches clean table fields.' }, incoming: ['clean_ai'] }
    ]
  }
];

const WorkflowTemplates = ({ onLoadTemplate }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflowY: 'auto' }}>
      <div>
        <h3 style={{ margin: '0 0 5px 0', fontSize: '18px', color: '#f8fafc' }}>Workflow Templates</h3>
        <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8' }}>
          Select a template to instantly configure and load a visual workflow pipeline in the builder canvas:
        </p>
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', 
        gap: '20px', 
        paddingBottom: '20px' 
      }}>
        {PREBUILT_TEMPLATES.map(tmpl => (
          <div 
            key={tmpl.id}
            className="card hover-trigger"
            style={{ 
              padding: '20px', 
              border: '1px solid #334155', 
              borderRadius: '10px', 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'space-between',
              gap: '15px'
            }}
          >
            <div>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#38bdf8' }}>{tmpl.name}</h4>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8', lineHeight: '1.6' }}>{tmpl.description}</p>
              
              <div style={{ marginTop: '15px' }}>
                <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 'bold' }}>Pipeline Steps:</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '5px' }}>
                  {tmpl.nodes.map((node, i) => (
                    <span 
                      key={i} 
                      style={{ 
                        fontSize: '10px', 
                        padding: '2px 8px', 
                        backgroundColor: '#1e293b', 
                        borderRadius: '4px',
                        border: '1px solid #334155',
                        color: '#cbd5e1'
                      }}
                    >
                      {node.label}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <button 
              className="btn-primary" 
              onClick={() => onLoadTemplate(tmpl)}
              style={{ width: '100%', marginTop: '10px' }}
            >
              Load into Builder
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkflowTemplates;
export { PREBUILT_TEMPLATES };
