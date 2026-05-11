# Changelog

All notable changes to the NYC Sidewalk Data Toolkit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-05-11

### Added

#### LangChain AI Integration
- **LLM Chatbot** - Multi-turn conversational AI with dataset context awareness
  - Support for Ollama, OpenAI, and Hugging Face LLM backends
  - Conversation history management with configurable window size
  - Dataset-aware responses using metadata
  - Specialized Data Quality Assistant for issue assessment
  - Specialized Analytics Advisor for metric suggestions and pattern identification
  
- **SQL Query Engine** - Wolfram-like natural language to SQL translation
  - Automatic database schema introspection
  - Query safety validation (blocks DELETE, DROP, ALTER operations)
  - Automatic result interpretation via LLM
  - Interactive query sessions with context-aware follow-ups
  - Query execution history and audit trail
  - Query optimizer with optimization suggestions
  
- **FastAPI Routes** - Complete REST API for LLM features
  - Chat endpoints: `/chat`, `/chat/history`, `/chat/clear`, `/chat/suggest-analyses`
  - Query endpoints: `/query`, `/query/session/{id}`, `/query/schema`
  - Quality assessment: `/quality/assess`
  - Analytics: `/analytics/suggest-metrics`
  - Health checks: `/health`

#### React/TypeScript Frontend
- **Modern Web UI** built with Vite + React 18 + TypeScript
- **ChatInterface Component** - Multi-turn conversational messaging
  - Real-time message streaming
  - Auto-scroll to latest messages
  - Clear conversation history
  - Provider and model selection
  - Loading and error states
  
- **QueryBuilder Component** - SQL query execution interface
  - Natural language query input
  - Generated SQL display with copy functionality
  - Results visualization with statistics
  - Results table with pagination
  - Query interpretation display
  
- **App Layout & Navigation**
  - Collapsible sidebar with settings
  - Multi-tab interface (Chat/Query/Quality)
  - Dark mode toggle with persistent preference
  - System status indicator
  - Professional NYC blue theme
  
- **State Management** - Zustand store
  - Chat message history
  - UI state (tabs, dark mode, sidebar)
  - Settings (provider, model, theme)
  - Error and loading states
  
- **Styling & Responsive Design**
  - TailwindCSS with NYC blue color palette
  - Dark mode support
  - Mobile-responsive layout
  - Professional component design

#### Documentation
- **LANGCHAIN_INTEGRATION_GUIDE.md** - Complete LLM integration guide
  - Setup for all LLM providers (Ollama, OpenAI, Hugging Face)
  - Quick start examples with code
  - Advanced usage patterns
  - CLI integration guide
  - FastAPI integration examples
  - Streamlit web UI integration
  - Performance tuning and optimization
  - Best practices and troubleshooting

- **Documentation Index** - Central hub for all 49+ guides
  - Role-based navigation (analyst, admin, developer, DevOps)
  - Task-based navigation (install, query, integrate, monitor)
  - Quick reference links
  - Support and feedback channels

#### Configuration
- **.env.example** - Comprehensive environment configuration template
  - Database configuration (PostgreSQL, MongoDB)
  - API configuration
  - Frontend configuration
  - LLM configuration for all providers
  - Socrata API configuration
  - Security and authentication
  - Logging and debugging
  - Production configuration
  - Email alerts
  - Cloud provider setup (AWS, Azure, GCP)
  - Docker configuration
  - Feature flags

#### Developer Experience
- **CONTRIBUTING.md** - Complete contribution guidelines
  - Code of conduct
  - Development setup instructions
  - Branching strategy and commit message conventions
  - Coding standards (Python, TypeScript, SQL)
  - Testing requirements and examples
  - Documentation standards
  - Pull request process
  
- **Frontend documentation**
  - frontend/README.md - Architecture and features
  - frontend/SETUP.md - Detailed setup instructions with troubleshooting
  - API client types and methods
  - Component documentation
  - Styling guide

### Changed

#### Dependencies
- Updated `pyproject.toml` with LangChain ecosystem packages
  - `langchain`, `langchain-community`
  - `ollama`, `openai`, `huggingface-hub`
  - `pydantic` for data validation
  - `sqlalchemy` for database abstraction

### Technical Improvements

- **Type Safety** - Full TypeScript in frontend, type hints in Python backend
- **Error Handling** - Comprehensive error handling with meaningful messages
- **API Design** - RESTful design with Pydantic models and async support
- **Code Organization** - Clean separation of concerns across backend and frontend
- **Documentation** - 49+ guides covering all aspects of the toolkit

## [2.0.0] - 2026-04-15

### Added
- Executable package with CLI and Web UI
- Docker containerization for deployment
- Comprehensive deployment guides
- Makefile with 40+ build commands
- Complete CLI command reference
- QUICKSTART and EXECUTABLE_PACKAGE documentation

### Changed
- Reorganized project structure for modularity
- Enhanced API architecture
- Improved deployment configurations

## [1.0.0] - 2026-03-01

### Added
- Initial NYC Sidewalk Data Toolkit release
- Core CLI functionality
- Data pipeline support
- Material standards and compliance checking
- Sidewalk inspection management
- Entity resolution capabilities
- Spatial analysis features
- Master data management
- Data quality framework
- Basic API endpoints
- Documentation foundation

---

## Unreleased

### In Development
- GraphQL API endpoints
- Advanced vector search capabilities
- ML-based anomaly detection
- Real-time streaming analytics
- Mobile app for field inspections
- ArcGIS Pro integration
- Kubernetes multi-cluster support

### Planned
- Predictive maintenance models
- Advanced geospatial analysis
- Business intelligence dashboards
- Workflow automation engine
- Advanced caching strategies
- Multi-language support

---

## Version Naming

Versions follow Semantic Versioning:
- **MAJOR** (3.0.0) - Breaking changes
- **MINOR** (3.1.0) - Backward-compatible new features
- **PATCH** (3.0.1) - Bug fixes and minor improvements

---

## How to Report Issues

Found a bug or have a feature request?

1. Check existing [GitHub Issues](https://github.com/ryudkiss-hue/nyc_data/issues)
2. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Screenshots or logs if relevant

---

## How to Get Involved

Interested in contributing?

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Check [GitHub Issues](https://github.com/ryudkiss-hue/nyc_data/issues) for open tasks
3. Fork the repository and create a feature branch
4. Submit a pull request with your improvements

---

## Acknowledgments

This toolkit was built to support NYC's sidewalk management and maintenance operations. Thanks to all contributors and users who help improve it.

## License

MIT License - See [LICENSE](LICENSE) file for details

---

## Release History

| Version | Date | Notes |
|---------|------|-------|
| 3.0.0 | 2026-05-11 | LangChain AI integration, React frontend, comprehensive documentation |
| 2.0.0 | 2026-04-15 | Executable package, Docker, deployment guides |
| 1.0.0 | 2026-03-01 | Initial release |

For detailed migration guides, see [docs/releases.md](docs/releases.md)
