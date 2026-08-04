# Enterprise Platform Administration Guide

This guide covers system upgrades, roles management, and disaster recovery procedures.

---

## 👥 Access Control & Auditing

Administrators can configure role permissions via user database settings:
- **Admin**: Grants full access to backing databases, prompts creation, model changes, and system status tools.
- **Analyst**: Grants dataset analysis, cleanups, RAG chats, and report exports.
- **Viewer**: Read-only restrictions on system states.

---

## 💾 Disaster Recovery Procedures

In the event of database corruption or data loss:
1. Locate the latest snapshot in `./database_backups`.
2. Extract the SQLite `database.db` and json configurations files.
3. Validate metadata hashes and schemas match current build versions.
4. Replace active sqlite file and restart the system.
5. Trigger `/ready` health check endpoint to confirm operational status.
