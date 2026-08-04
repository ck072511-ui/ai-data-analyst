# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.9] - 2026-07-25

### Added
- Created [dependency-upgrade.md](file:///c:/Users/DELL/OneDrive/ai-data-analyst/docs/dependency-upgrade.md) detailing security mitigations and upgrade instructions.
- Configured Ruff lint rules under the modernized `[tool.ruff.lint]` table format.

### Changed
- Upgraded **FastAPI** (`0.104.1` -> `0.111.0`) and **Starlette** (`0.27.0` -> `0.37.2`) to mitigate core ASGI vulnerabilities.
- Upgraded **python-jose** (`3.3.0` -> `3.4.0`), **python-dotenv** (`1.0.0` -> `1.0.1`), **python-multipart** (`0.0.6` -> `0.0.31`), and **PyMySQL** (`1.1.0` -> `1.1.1`) to resolve backend dependency advisories.
- Upgraded **react-router-dom** (`6.20.0` -> `6.29.0`) to resolve CVE-2025-68470.
- Upgraded virtualenv environment packaging tools **pip** (`24.0` -> `26.1.2`) and **setuptools** (`65.5.0` -> `83.0.0`).
- Refactored `pd.to_datetime` calls in `cleaning_service.py`, `dashboard_service.py`, and `profiling_service.py` with `format="mixed"` parameter, resolving pandas user warnings.
- Patched request client handling in `auth.py` registration, login, and refresh endpoints to return a fallback host (`"testclient"`) when client address headers are missing.

### Fixed
- Fixed deprecation and user warnings in test suites runs, reducing active warnings by 72% (from 11 down to 3).
