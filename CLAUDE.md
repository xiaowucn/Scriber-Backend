# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Scriber(Remarkable) is a financial and legal document annotation and analysis platform that processes complex documents (PDFs, contracts, prospectuses) using AI-powered extraction and rule-based compliance checking. The system serves multiple financial institutions with client-specific implementations.

## Common Development Commands

### Database Operations
```bash
# Initialize database
bin/db_init

# Run database migrations
inv db.upgrade

# Create new migration
inv db.revision "migration message"

# Start/stop local test database
bin/db_util.sh test
bin/db_util.sh test down
```

### Development Server
```bash
# Start development server (with hot reload)
bin/run

# Start Celery worker
inv worker.start
```

### Testing & Quality
```bash
# Run unit tests
inv test.unittest

# Run linting (pre-commit checks on recent changes)
inv lint.code-check

# Manual pre-commit on all files
pre-commit run --all-files
```

### Model Training & Deployment
```bash
# Train document extraction models
inv predictor.prepare-dataset <schema_id> --start=<file_id> --end=<file_id>
inv predictor.train <schema_id>
inv predictor.archive-model-for <schema_id> --name=<model_name>

# Deploy trained models
inv op.deploy-model <schema_id> --name=<model_name>

# Train location prompter models
inv prompter.build-model <schema_id> --start=<start> --end=<end> --clear --update
```

## Architecture Overview

### Hybrid Framework Architecture
- **FastAPI**: Modern async API framework handling v2 routes (`/api/v2/*`)
- **Tornado**: Legacy web server handling v1 routes (`/api/v1/*`)
- **Mount Strategy**: FastAPI app mounts Tornado middleware for backward compatibility

### Dual ORM Pattern
The codebase uses two ORMs simultaneously:
- **SQLAlchemy/Gino**: Legacy ORM in `remarkable/models/` for older features. 计划废弃
- **Peewee**: Modern ORM in `remarkable/pw_models/` for newer features (law module, file management). async 异步方式.

**Development Preference**: Use **FastAPI + Peewee async** for all new development.

### Key Directories
- `remarkable/routers/`: FastAPI route handlers (v2 API)
- `remarkable/service/`: Business logic layer
- `remarkable/models/` & `remarkable/pw_models/`: Database models (dual ORM)
- `remarkable/predictor/`: AI/ML model pipeline for document extraction
- `remarkable/plugins/`: Client-specific implementations
- `remarkable/worker/`: Celery background task processing
- `config/`: Environment-specific configuration files

### Database Support
- **Primary**: PostgreSQL (preferred, latest versions)
- **Compatibility**: MySQL and GaussDB (PostgreSQL 9.x) support required
- **Caching**: Redis for sessions, file progress, and API responses

### Client Plugin System
Each financial institution has dedicated plugins with custom:
- Document processors
- Data format converters
- Compliance rule engines
- Output templates

### Document Processing Pipeline
1. **File Upload** → **PDF Parsing** → **Text Extraction** → **Entity Recognition** → **Rule Application**
2. **Key Components**:
   - `pdfinsight/`: PDF processing and table extraction
   - `predictor/`: AI model pipeline for information extraction
   - `converter/`: Client-specific data format converters

### Legal Compliance System
- **Law Management**: Upload and parse legal documents
- **Rule Engine**: Extract compliance rules from legal texts
- **Contract Analysis**: AI-powered contract compliance checking
- **Checkpoint System**: Granular rule validation points

## Configuration

### Environment Setup
1. Copy `config/config-dev.yml` → `config-usr.yml` and modify for local setup
2. Set environment variables as needed (see `remarkable/config.py`)
3. Configure database connection in config file

### Dependencies
- Python 3.12 required
- Install with: `uv sync --group=dev` (正在用uv替换pip)
- Pre-commit hooks: `for t in pre-commit commit-msg pre-push; do pre-commit install --hook-type $t; done`

### Virtual Environment (.venv)
The project uses a `.venv` virtual environment to manage Python dependencies:

```bash
uv venv --python 3.12

source .venv/bin/activate 

uv sync --group=dev
```

**Development Workflow with .venv:**
- Always activate `.venv` before running development commands
- Use `uv sync` instead of `pip install` for dependency management
- The `.venv` directory is git-ignored and contains all project dependencies
- All `inv` commands and `bin/` scripts should be run within the activated environment

## Development Patterns

### Adding New Client Support
1. Create plugin in `remarkable/plugins/<client_name>/`
2. Implement client-specific converters and processors
3. Add configuration in `config/config-docker-<client>.yml`
4. Update deployment scripts in `ci/`

### Database Changes
- Use Alembic migrations (template: `misc/alembic/script.py.mako`)
- Create new migrations with `inv db.revision "message"`
- Use Peewee models in `remarkable/pw_models/` for new development
- Test migrations on both PostgreSQL and MySQL if needed

### API Development
- **v2 APIs**: Use FastAPI routers in `remarkable/routers/`
- **v1 APIs**: Use Tornado handlers (legacy, avoid for new features)
- Follow async/await patterns throughout
- Use service layer for business logic

### Model Training Workflow
1. Prepare training dataset with `inv predictor.prepare-dataset`
2. Train model with `inv predictor.train`
3. Archive trained model with `inv predictor.archive-model-for`
4. Deploy to production with `inv op.deploy-model`

## Testing

- Test files in `tests/` directory
- Test structure should mirror code structure (e.g., `tests/test_service/` for `remarkable/service/`)
- Use pytest with async support
- Database tests use temporary test database
- Client-specific test data in `data/` directory

**Note**: Focus on efficiency by default - only run tests when explicitly requested or when making significant changes.

## Development Guidelines

### Code Style & Practices
- **Think in English, respond in Chinese** when working with Chinese developers
- **Be concise and precise** - avoid speculation or verbose explanations
- **Avoid meaningless exception handling** - no empty try-except blocks or unnecessary try-raise patterns
- **Follow comment-driven development** - implement code directly at comment locations when completing functionality

### Technology Preferences
- **New Development**: Use FastAPI + Peewee async pattern
- **Database Priority**: PostgreSQL first, ensure MySQL/GaussDB compatibility
- **API Design**: Prefer v2 FastAPI routes over v1 Tornado handlers