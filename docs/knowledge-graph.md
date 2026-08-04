# Enterprise Knowledge Graph (KG) Architecture

The platform includes a 100% offline Enterprise Knowledge Graph that automatically extracts, discovers, and traverses associations across database schemas, uploaded files, RAG documents, reports, and background workflows.

## Entity Model
The graph is built on a structured node-relationship model mapped directly to SQLite database tables:
- **Dataset**: Physical flat data files (CSV, Excel, JSON).
- **Table**: Mapped relational database tables (local database context or remote connections).
- **Column**: Individual table columns metadata.
- **KPI / Metric**: Business calculation metrics formulas.
- **Business Term**: Glossary definitions and synonyms.
- **Document**: RAG-indexed document files.
- **Workflow**: Automated pipeline definitions.
- **Report**: Compiled summaries and PDF/Word/PPT templates.

## Relationship Discovery Heuristics
1. **Lineage (`lineage`)**: Extracted from column-to-table mappings and table-to-dataset uploads.
2. **Foreign Keys (`foreign_key`)**: Inferred using structural metadata matching columns across tables (e.g. `order_id` in `sales` referencing `id` in `orders`), scored at confidence level `0.85`.
3. **Glossary Mapping (`glossary_mapping`)**: Links business terms and synonyms from the semantic layer catalog to active columns matching those term aliases.
4. **Workflow Dependency (`workflow_dependency`)**: Connects workflows to the tables and datasets they query or write.
5. **Report Dependency (`report_dependency`)**: Maps reports to their parent workflow steps or source tables.

## Traversal & Analysis
- **Lineage Analysis**: Upstream recursive queries trace a column back to its source table, connection, or dataset file.
- **Impact Analysis**: Downstream recursive queries trace what metrics, workflows, and business reports depend on a database column, enabling automated change-impact assessments.
