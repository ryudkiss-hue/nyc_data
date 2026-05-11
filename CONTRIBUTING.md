# Contributing to NYC Sidewalk Data Toolkit

Thank you for your interest in contributing to the NYC Sidewalk Data Toolkit! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please read and adhere to our Code of Conduct:

- Be respectful and inclusive
- Welcome all skill levels
- Focus on constructive feedback
- Report violations to the maintainers

## Getting Started

### Prerequisites

- **Python 3.9+** - Backend development
- **Node.js 18+** - Frontend development
- **Git** - Version control
- **Docker** - For containerized testing
- **PostgreSQL 12+** - Database (optional, for local testing)

### Fork and Clone

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/nyc_data.git
cd nyc_data

# 3. Add upstream remote
git remote add upstream https://github.com/ryudkiss-hue/nyc_data.git

# 4. Create a feature branch
git checkout -b feature/your-feature-name
```

## Development Setup

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks (optional but recommended)
pre-commit install

# Run tests
pytest tests/
```

### Frontend Setup

```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint
```

### Database Setup (Optional)

```bash
# Start PostgreSQL in Docker
docker run --name nyc-data-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=nyc_data \
  -p 5432:5432 \
  postgres:15

# Set environment variable
export DATABASE_URL="postgresql://postgres:password@localhost:5432/nyc_data"
```

## Making Changes

### Branching Strategy

Use descriptive branch names:
- `feature/add-chatbot-ui` - New features
- `fix/query-validation-bug` - Bug fixes
- `docs/update-api-guide` - Documentation
- `refactor/optimize-sql-engine` - Refactoring
- `test/add-integration-tests` - Tests

```bash
git checkout -b feature/your-descriptive-name
```

### Commit Messages

Follow conventional commits format:

```
type(scope): brief description

Longer explanation of changes if needed.
Mention any related issues: Fixes #123
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (formatting, missing semicolons)
- `refactor:` - Code refactoring without feature changes
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `chore:` - Dependency updates, configuration changes

Examples:
```bash
git commit -m "feat(llm): Add support for Claude model in chatbot"
git commit -m "fix(query): Validate SQL before execution"
git commit -m "docs: Add deployment guide for Kubernetes"
```

## Submitting Changes

### Before Submission

#### Backend
```bash
# Run tests
pytest tests/ -v

# Check code style
ruff check socrata_toolkit/
black socrata_toolkit/ --check
isort socrata_toolkit/ --check

# Type checking
mypy socrata_toolkit/

# Fix issues
black socrata_toolkit/
isort socrata_toolkit/
ruff check socrata_toolkit/ --fix
```

#### Frontend
```bash
# Run tests
npm run test

# Type checking
npm run type-check

# Linting
npm run lint

# Build
npm run build
```

### Pull Request Process

1. **Update your branch**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your changes**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**
   - Go to GitHub and create a PR
   - Fill in the PR template completely
   - Link any related issues: `Fixes #123`
   - Add description of changes
   - Request reviewers

4. **PR Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Unit tests added/updated
   - [ ] Integration tests passed
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] No new warnings generated
   - [ ] Tests pass locally
   
   ## Related Issues
   Fixes #123
   ```

5. **Review Process**
   - At least one maintainer approval required
   - All CI checks must pass
   - Address reviewer feedback
   - Squash commits if requested

## Coding Standards

### Python

- **Style**: PEP 8
- **Formatter**: `black` (line length: 100)
- **Linter**: `ruff`
- **Type hints**: Required for new code
- **Docstrings**: Google style for public functions

```python
def fetch_dataset(domain: str, fourfour: str, limit: int = 1000) -> pd.DataFrame:
    """Fetch data from Socrata API.
    
    Args:
        domain: Socrata domain (e.g., 'data.cityofnewyork.us')
        fourfour: Dataset ID (e.g., '4d3e-4d3e-4d3e-4d3e')
        limit: Maximum rows to fetch
        
    Returns:
        DataFrame with dataset contents
        
    Raises:
        ValueError: If domain or fourfour invalid
    """
    # Implementation
    pass
```

### TypeScript/React

- **Style**: ESLint configuration
- **Formatter**: Prettier (via ESLint)
- **Type hints**: Required, no `any` types
- **Components**: Functional components with hooks
- **Naming**: PascalCase for components, camelCase for functions

```typescript
interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ role, content, timestamp }) => {
  // Component implementation
  return (...)
}
```

### SQL

- **Style**: Uppercase keywords, lowercase table/column names
- **Comments**: Explain complex queries
- **Performance**: Use indexes, avoid N+1 queries

```sql
-- Fetch sidewalk inspections by borough
SELECT 
  borough,
  COUNT(*) as inspection_count,
  AVG(CAST(repair_cost AS FLOAT)) as avg_cost
FROM sidewalk_inspections
WHERE inspection_date >= NOW() - INTERVAL '1 year'
GROUP BY borough
ORDER BY inspection_count DESC;
```

## Testing

### Backend Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=socrata_toolkit

# Run specific test file
pytest tests/test_llm_chatbot.py

# Run specific test
pytest tests/test_llm_chatbot.py::TestChatbot::test_multi_turn_conversation

# Run with verbose output
pytest tests/ -v

# Run with markers
pytest tests/ -m "unit"
pytest tests/ -m "integration"
```

### Frontend Testing

```bash
# Run unit tests
npm run test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test -- --watch

# Specific test
npm run test -- ChatInterface
```

### Test Requirements

- **Unit tests**: For all public functions/components
- **Integration tests**: For API endpoints and workflows
- **Coverage**: Maintain >80% code coverage
- **E2E tests**: For critical user workflows

### Test Structure

```python
# Backend test example
def test_chatbot_multi_turn_conversation():
    """Test multi-turn conversation maintains context."""
    chatbot = SocrataLLMChatbot(llm_provider="ollama", model_name="mistral")
    
    # First turn
    response1 = chatbot.chat("What are common sidewalk defects?")
    assert len(response1) > 0
    assert len(chatbot.get_conversation_history()) == 2  # user + assistant
    
    # Second turn (should have context from first)
    response2 = chatbot.chat("Which borough has the most?")
    assert len(response2) > 0
    assert len(chatbot.get_conversation_history()) == 4
```

## Documentation

### Adding Documentation

1. **Code comments**: Explain WHY, not WHAT
2. **Docstrings**: For all public functions
3. **README updates**: For new features
4. **docs/ files**: For detailed guides
5. **Changelog**: Update CHANGELOG.md

### Documentation Standards

- **Clarity**: Write for beginners
- **Examples**: Include code samples
- **Links**: Cross-reference related docs
- **Updates**: Keep docs in sync with code
- **Formatting**: Use consistent markdown

### Adding a New Guide

1. Create `docs/FEATURE_NAME.md`
2. Include:
   - Overview section
   - Getting started
   - Examples
   - API reference (if applicable)
   - Troubleshooting
   - Related documentation links

## Reviewer Expectations

Reviewers will check:

- **Code quality**: Following standards
- **Tests**: Adequate coverage
- **Documentation**: Clear and complete
- **Performance**: No regressions
- **Security**: No vulnerabilities
- **Compatibility**: No breaking changes

## Getting Help

- **Questions**: Open a discussion or issue
- **Bugs**: Report with reproduction steps
- **Ideas**: Discuss in issues first
- **Chat**: Join our community chat (if available)

## Recognition

Contributors are recognized in:
- CHANGELOG.md
- GitHub contributors page
- Project README (for major contributions)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

---

**Thank you for contributing to the NYC Sidewalk Data Toolkit!** 🎉

Your efforts help make data exploration and analysis more accessible for NYC's sidewalk management. If you have any questions, don't hesitate to reach out to the maintainers.
