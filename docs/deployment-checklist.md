# Enterprise Pre-Deployment Checklist

Follow this checklist prior to rolling out the application package:

- [ ] **Secret Encryption**: Ensure `SECRET_KEY` env is set to a cryptographically strong 32-character key.
- [ ] **Request Caps**: Verify maximum request payload sizes cap (100MB) is active.
- [ ] **Write Permissions**: Ensure local directories `/vector_store` and `/generated_documents` have write permissions enabled for the execution process user.
- [ ] **Local LLM Models**: Verify Ollama is running and Llama 3 / Qwen models are loaded locally.
- [ ] **HTTPS Certificate**: In production, ensure SSL certificates are bound and HSTS headers are forced.
