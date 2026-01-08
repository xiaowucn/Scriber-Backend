# ast-grep Rules

This directory contains ast-grep rules for code quality and best practices enforcement in the Scriber-Backend project.

## Directory Structure

```
ci/ast-grep/
├── README.md                                    # This file
├── rules/                                       # Rule definitions
│   ├── mysql-string-column.yml
│   ├── mysql-string-assignment.yml
│   ├── mysql-string-add-column.yml
│   ├── mysql-string-array.yml
│   ├── no-match-case.yml
│   ├── no-global-remarkable-import-in-devtools.yml
│   └── no-devtools-import-outside-devtools.yml
└── tests/                                       # Rule tests
    ├── __snapshots__/                           # Auto-generated test snapshots
    ├── mysql-string-column-test.yml
    ├── mysql-string-assignment-test.yml
    ├── mysql-string-add-column-test.yml
    ├── mysql-string-array-test.yml
    ├── no-match-case-test.yml
    ├── no-global-remarkable-import-in-devtools-test.yml
    └── no-devtools-import-outside-devtools-test.yml

sgconfig.yml                                     # ast-grep project configuration (in project root)
```

## Rules

### 1. MySQL String Rules

These rules ensure MySQL compatibility for SQLAlchemy String columns.

#### mysql-string-column

**Purpose**: Enforce length parameter for `sa.String` in `sa.Column()` definitions.

**Reason**: MySQL requires explicit length for VARCHAR columns.

**Example**:
```python
# ❌ Bad - Will trigger error
sa.Column("name", sa.String())
sa.Column("name", sa.String)

# ✅ Good - Specify length
sa.Column("name", sa.String(255))
sa.Column("name", sa.String(100), nullable=False)
```

#### mysql-string-assignment

**Purpose**: Enforce length parameter for `sa.String` in variable assignments.

**Reason**: MySQL requires explicit length for VARCHAR columns.

**Example**:
```python
# ❌ Bad - Will trigger error
name = sa.Column(sa.String())
name = sa.Column(sa.String)

# ✅ Good - Specify length
name = sa.Column(sa.String(255))
name = sa.Column(sa.String(100), nullable=False)
```

#### mysql-string-add-column

**Purpose**: Enforce length parameter for `sa.String` in Alembic `op.add_column()`.

**Reason**: MySQL requires explicit length for VARCHAR columns in migrations.

**Example**:
```python
# ❌ Bad - Will trigger error
op.add_column("users", sa.Column("name", sa.String()))
op.add_column("users", sa.Column("name", sa.String))

# ✅ Good - Specify length
op.add_column("users", sa.Column("name", sa.String(255)))
op.add_column("users", sa.Column("name", sa.String(100), nullable=False))
```

#### mysql-string-array

**Purpose**: Enforce use of `create_array_field()` for ARRAY types.

**Reason**: MySQL doesn't support native ARRAY type. The `create_array_field()` utility from `remarkable.common.migrate_util` automatically converts ARRAY to JSON in MySQL environments.

**Example**:
```python
# ❌ Bad - Will trigger error
sa.Column("tags", sa.ARRAY(sa.String))
sa.ARRAY(sa.String(255))

# ✅ Good - Use create_array_field
from remarkable.common.migrate_util import create_array_field
create_array_field("tags", sa.ARRAY(sa.String), nullable=True)
```

### 2. no-match-case

**Purpose**: Prohibit structural pattern matching (match/case) usage.

**Reason**: Cython does not currently support match/case statements.

**Example**:
```python
# ❌ Bad - Will trigger error
def process_value(value):
    match value:
        case 1:
            return "one"
        case _:
            return "other"

# ✅ Good - Use if-elif-else instead
def process_value(value):
    if value == 1:
        return "one"
    else:
        return "other"
```

### 3. no-global-remarkable-import-in-devtools

**Purpose**: Enforce local imports in devtools modules to maintain independence and improve loading speed.

**Reason**: devtools modules should remain independent from the main project code to avoid:
- Circular dependencies
- Side effects during startup
- Slow CLI loading time
- Tight coupling between development tools and production code

**Example**:
```python
# ❌ Bad - Global import of remarkable modules
from remarkable.config import get_config
from remarkable.service.deploy import deploy_model

def deploy():
    config = get_config()
    return deploy_model(config)

# ✅ Good - Local imports inside functions
def deploy():
    from remarkable.config import get_config
    from remarkable.service.deploy import deploy_model

    config = get_config()
    return deploy_model(config)
```

### 4. no-devtools-import-outside-devtools

**Purpose**: Prevent production code from importing devtools modules to maintain clear architectural boundaries.

**Reason**: devtools contains development and operational tools (database migrations, model training, deployment scripts) that should NOT be imported by production code to prevent:
- Production code depending on development tools
- Accidental deployment of dev-only dependencies
- Circular dependencies between business logic and tooling
- Mixing development utilities with production logic

**Example**:
```python
# ❌ Bad - Production code importing devtools
# In remarkable/service/prompter.py
from remarkable.devtools import copy_model_file

def build_model():
    copy_model_file(src, dst)

# ❌ Bad - Test importing devtools utilities
# In tests/test_pdf_cache.py
from remarkable.devtools.task_sync import _sync_file

def test_sync():
    _sync_file(file_id)

# ✅ Good - Move shared functionality to common/service
# In remarkable/common/file_util.py
def copy_model_file(src, dst):
    """Shared utility for copying model files"""
    shutil.copy2(src, dst)

# In remarkable/service/prompter.py
from remarkable.common.file_util import copy_model_file

def build_model():
    copy_model_file(src, dst)
```

**Note**: This rule excludes:
- Files inside `remarkable/devtools/` (devtools can import from itself)
- Root `tasks.py` (invoke tasks file that legitimately uses devtools)

## Usage

### Running Rules

```bash
# Scan all files
ast-grep scan

# Scan specific file
ast-grep scan misc/alembic/versions/001_initial.py

# Scan with specific rule
ast-grep scan --filter mysql-string-column

# Run through pre-commit
inv lint.code-check
```

### Auto-fixing with Ruff (Type Hints)

For modern type hints (PEP 604/585), use Ruff instead of ast-grep:

```bash
# Check for legacy type hints
ruff check --select UP006,UP007

# Auto-fix legacy type hints
ruff check --select UP006,UP007 --fix

# Fix all enabled rules (includes UP006/UP007 since pyproject.toml config)
ruff check --fix
```

**Note**: Ruff's UP006/UP007 rules are enabled by default in `pyproject.toml` and provide:
- Automatic detection and fixing of legacy type hints
- Better performance than ast-grep for this use case
- Integration with the existing linting workflow

### Testing Rules

```bash
# Run all tests
ast-grep test

# Update test snapshots
ast-grep test --update-all

# Interactive update
ast-grep test --interactive
```

### Adding New Rules

1. Create a new rule file in `rules/`:
   ```bash
   touch rules/my-new-rule.yml
   ```

2. Define the rule following the [ast-grep rule schema](https://raw.githubusercontent.com/ast-grep/ast-grep/main/schemas/rule.json):
   ```yaml
   # yaml-language-server: $schema=https://raw.githubusercontent.com/ast-grep/ast-grep/main/schemas/rule.json

   id: my-new-rule
   message: "Description of what this rule checks"
   severity: error  # or warning, info, hint
   language: Python
   rule:
     pattern: |
       # Your pattern here
   ```

3. Create a test file in `rule-tests/`:
   ```bash
   touch rule-tests/my-new-rule-test.yml
   ```

4. Define test cases:
   ```yaml
   # yaml-language-server: $schema=https://raw.githubusercontent.com/ast-grep/ast-grep/main/schemas/test.json

   id: my-new-rule

   valid:
     - |
       # Code that should NOT trigger the rule

   invalid:
     - |
       # Code that SHOULD trigger the rule
   ```

5. Run tests and update snapshots:
   ```bash
   ast-grep test --update-all
   ```

## Integration

### Pre-commit Hook

The rules are automatically run as part of the pre-commit hooks. See `.pre-commit-config.yaml`:

```yaml
- id: ast-grep-rule-check
  name: ast-grep-rule-check
  entry: ast-grep scan
  language: system
  types: [python]
```

**Benefits**:
- ✅ Only checks files that have been modified (faster)
- ✅ Supports both single file and multiple files
- ✅ Works with `git add` staged files

### CI/CD

The rules can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run ast-grep
  run: |
    ast-grep scan
```

## Resources

- [ast-grep Documentation](https://ast-grep.github.io/)
- [Rule Configuration Guide](https://ast-grep.github.io/guide/rule-config.html)
- [Testing Rules](https://ast-grep.github.io/guide/test-rule.html)
- [Pattern Syntax](https://ast-grep.github.io/guide/pattern-syntax.html)

