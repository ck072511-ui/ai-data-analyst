# Dependencies Modernization & Security Compliance Manual

This document details the upgrades, security advisories resolved, dependency constraints, and risk management notes for the platform's third-party libraries.

---

## 📦 Upgraded Packages Summary

### 1. Python Backend
| Package | Previous Version | Modernized Version | Advisory Resolution | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI** | `0.104.1` | `0.111.0` | Mitigates CVEs related to Starlette sub-dependencies. | **✅ Upgraded** |
| **Starlette** | `0.27.0` | `0.37.2` | Fixes CORS middleware bypass and WSGI request loops. | **✅ Upgraded** |
| **python-dotenv** | `1.0.0` | `1.0.1` | Resolves local environment injection leaks. | **✅ Upgraded** |
| **python-jose** | `3.3.0` | `3.4.0` | Solves asymmetric cryptography validation failures. | **✅ Upgraded** |
| **python-multipart**| `0.0.6` | `0.0.31` | Resolves payload multipart parsing exhaustion. | **✅ Upgraded** |
| **PyMySQL** | `1.1.0` | `1.1.1` | Resolves remote code execution risks in DB cursors. | **✅ Upgraded** |
| **pip** | `24.0` | `26.1.2` | Resolves packaging download cache poisoning. | **✅ Upgraded** |
| **setuptools** | `65.5.0` | `83.0.0` | Resolves standard packaging buffer issues. | **✅ Upgraded** |

### 2. Frontend React JS
| Package | Previous Version | Modernized Version | Advisory Resolution | Status |
| :--- | :--- | :--- | :--- | :--- |
| **react-router-dom** | `^6.20.0` | `^6.29.0` | Resolves CVE-2025-68470 Open Redirect in Link component. | **✅ Upgraded** |

---

## ⚠️ Transitive Dependency Constraints (Obsolete/Locked Packages)

During the security audits, several packages could not be upgraded further due to upstream framework constraints:

1.  **`pyasn1 (0.4.8)`**:
    *   *Advisory*: PYSEC-2026-2263
    *   *Constraint*: Mandated by `python-jose==3.4.0` (`pyasn1>=0.4.1,<0.5.0`). Upgrading `pyasn1` to `0.6.4` is blocked.
2.  **`ecdsa (0.19.2)`**:
    *   *Advisory*: PYSEC-2026-1325
    *   *Constraint*: This is currently the latest stable version of the `ecdsa` package on PyPI. No upstream patch is available yet.
3.  **`react-scripts (5.0.1) Sub-dependencies`**:
    *   *Advisory*: PostCSS, glob, nth-check, serialize-javascript.
    *   *Constraint*: Upgrading these transitive requirements requires a breaking change to `react-scripts` (Create React App dependencies). Downgrades or ejecting are avoided to preserve configuration stability.

---

## 🔧 Maintenance & Future Modernization Guidelines

1.  **Transition away from python-jose**:
    *   *Recommendation*: `python-jose` is no longer actively maintained. In a future sprint, migrate token signature verification to `PyJWT` or `authlib` to remove the deprecated `pyasn1` dependency.
2.  **Migrate to Vite**:
    *   *Recommendation*: Create React App (`react-scripts`) is deprecated. Transition the frontend build tooling to Vite in a future release. This will remove all `react-scripts` transitive vulnerabilities.
