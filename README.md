# WSO2 Log Analyzer

A professional desktop-grade web application for analyzing WSO2 product logs (API Manager, Identity Server, Micro Integrator, Enterprise Integrator).

## Features (Sprint 1)

- Project management: create, open, and track recent projects
- Log file ingestion: upload, reference by path, or scan entire folders
- File type auto-detection: wso2carbon, audit, http_access, correlation
- Metadata extraction: line count, timestamp range
- Dark-mode professional UI

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the server
python run.py
```

The app opens automatically at http://localhost:8765.

## Project Structure

```
wso2-log-analyzer/
├── server/          # FastAPI backend
│   ├── api/         # REST endpoints
│   ├── core/        # Business logic
│   └── models/      # Pydantic models
├── frontend/        # Vanilla JS/HTML/CSS SPA
└── tests/           # pytest test suite
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check .
```
