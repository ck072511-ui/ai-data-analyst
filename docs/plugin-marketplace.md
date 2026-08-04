# Local Plugin Marketplace Catalog

The AI Data Analyst platform includes a 100% offline Marketplace Catalog populated with 6 baseline functional extension blueprints:

## Pre-Packaged Catalog Blueprints

1. **CSV Import Plus (`csv_import_plus`)**
   - **Capability**: Data Source
   - **Description**: Robust CSV parser supporting custom line skipping, column mappings, and auto date conversion.
2. **Advanced Charts (`advanced_charts`)**
   - **Capability**: Visualization
   - **Description**: Generates configurations for radar charts, boxplots, and bubble distributions.
3. **KPI Library (`kpi_library`)**
   - **Capability**: Analytics
   - **Description**: Calculates margins, ROI, and customer churn metrics.
4. **Custom Report Template (`custom_report_template`)**
   - **Capability**: Report Generation
   - **Description**: Compiles customized print layouts with signatures.
5. **Forecast Helper (`forecast_helper`)**
   - **Capability**: Analytics (Depends on KPI Library)
   - **Description**: Computes forecasts based on previous KPI indexes.
6. **Data Quality Rules (`data_quality`)**
   - **Capability**: Workflow Node
   - **Description**: Inspects column types and null percentages.

---

## Lifecycle REST Endpoints

All endpoints are secured using role-based permissions (`view` for reports, `user_management` for administration changes):

### 1. Retrieve Registry List
* **Route**: `GET /api/v1/plugins`
* **Access**: Viewers, Analysts, Scientists, Admins
* **Returns**: A merged list of marketplace and installed plugins including active statuses, health logs, and version details.

### 2. Install Plugin
* **Route**: `POST /api/v1/plugins/install`
* **Access**: Admin only
* **Body**: `{"plugin_id": "csv_import_plus"}`
* **Action**: Copies the blueprint files from marketplace to installed directories, registers metadata, and runs reflection loads.

### 3. Change Enabled State
* **Route**: `POST /api/v1/plugins/enable` / `POST /api/v1/plugins/disable`
* **Access**: Admin only
* **Body**: `{"plugin_id": "csv_import_plus"}`
* **Action**: Toggles the runtime loading check and forces registry reload.

### 4. Health Diagnostic Check
* **Route**: `GET /api/v1/plugins/health`
* **Access**: Viewers, Analysts, Scientists, Admins
* **Action**: Runs dynamic diagnostics on all loaded modules and gathers diagnostic logs.
