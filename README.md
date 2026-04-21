# WSO2 Log Analyzer

A professional desktop-grade web application for analyzing WSO2 product logs (API Manager, Identity Server, Micro Integrator, Enterprise Integrator).

## Features

- **Project management** — create, open, and track recent projects per WSO2 product/version
- **Multi-format log ingestion** — upload (multi-file), reference by path, or scan entire folders
- **log4j2 format type system** — define named format types with log4j2 patterns; assign per-file or set a project default; built-in types for APIM/IS (TID) and MI/EI (bracket)
- **Auto-detection** — TID, bracket `{logger}`, and basic formats auto-detected when no format type assigned
- **Full log parsing** — stack traces attached to entries, multi-line messages, correlation IDs, tenant IDs
- **Virtual-scroll log viewer** — handles 200K+ line files without lag; color-coded by level
- **Filter & search** — level toggles, text/regex search, `has_stack_trace`, time range
- **Grouping** — group by level, component, logger, tenant, correlationId
- **Cross-file search** — search across all loaded log files simultaneously
- **Format manager UI** — Settings tab: create/edit/delete format types with inline pattern tester
- **Dark-mode professional UI**
- **Repository registration & stack trace resolution** *(S3)* — index local Java repos, click stack frames to jump to source with line snippets
- **Package→repo resolver** — longest-prefix match against 750+ WSO2 package mappings ported from `cre-ai-agent`
- **JAR version scanner** — derive `{artifactId: version}` from a WSO2 pack to resolve source at the correct tag
- **Feature keyword catalog** — 500+ feature→repo mappings (`oauth2`, `saml`, `totp`, …) available via `/api/features`

## Quick Start

```bash
cd wso2-log-analyzer
source .venv/bin/activate
python run.py
# → Opens http://localhost:8765 automatically
```

> The virtual environment is already set up at `.venv/`. If starting fresh:
> `pip install fastapi "uvicorn[standard]" "pydantic>=2.10.0" watchdog aiofiles python-multipart sse-starlette`

## Project Structure

```
wso2-log-analyzer/
├── server/
│   ├── api/            # REST endpoints (projects, logs, parsing, formats, repos, stacktrace, files)
│   ├── core/           # Business logic (parser, indexer, format_manager, pattern_compiler,
│   │                   #                  repo_resolver, repo_scanner, stack_trace, git_client, repo_registry)
│   ├── data/           # Seed configs from cre-ai-agent (repos.json, jar-overrides.json, features.json)
│   └── models/         # Pydantic models
├── frontend/           # Vanilla JS/HTML/CSS SPA (no build step)
└── tests/              # pytest test suite (168 tests)
```

## Development

```bash
# Run tests
pytest tests/ -q

# Lint
ruff check .
```

## Sprint Status

| Sprint | Status |
|--------|--------|
| S1 — Foundation | ✅ Complete |
| S2 — Core Log Viewer | ✅ Complete |
| S2.5 — Log Format Types | ✅ Complete |
| S2.6 — Format Library & Project Defaults | ✅ Complete |
| S3 — Codebase Intelligence | ✅ Complete |
| S4 — Analytics & Timing | ⏳ Not started |
| S5 — AI Integration | ⏳ Not started |
| S6 — Large Logs, Polish & Advanced | ⏳ Not started |
