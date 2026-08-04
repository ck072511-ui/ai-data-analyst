# Semantic Layer Specifications

The Semantic Layer provides a friendly abstraction layer mapping business language keywords to raw database schema columns and tables.

## Business Glossary Catalog
Exposes standard enterprise terminology offline, enabling mapping checks:
*   `revenue` synonyms: `turnover`, `earnings`, `sales_revenue`, `amount`
*   `profit` synonyms: `earnings`, `margin`, `net_income`, `profit_margin`
*   `customer` synonyms: `client`, `buyer`, `user`, `purchaser`
*   `churn` synonyms: `retention`, `attrition`, `loss`, `exit`

## KPI & Calculations Catalog
Maintains calculation formulas used to compute business analytics:
*   `monthly_sales_growth`: `((Current Month Sales - Previous Month Sales) / Previous Month Sales) * 100`
*   `customer_churn_rate`: `(Customers Lost in Period / Total Customers at Start of Period) * 100`
*   `average_transaction_value`: `Total Revenue / Total Transaction Count`

## NL-to-SQL Synonym Enabler
When the schema intelligence constructor compiles a prompt's schema context, it maps keywords in the user question to resolved semantic synonyms in the catalog. 

These synonyms are directly appended in column descriptors inside the SQL agent prompt layout (e.g. `amount (Synonyms: turnover, earnings)`), guiding the LLM to choose correct columns even if natural language queries use custom terms.
