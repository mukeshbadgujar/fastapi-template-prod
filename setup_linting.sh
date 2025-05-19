#!/bin/bash
set -e

echo "Setting up linting tools for FastAPI project..."

# Install Python linting tools
echo "Installing Python linting packages..."
pip install flake8 pylint mypy isort black pre-commit

# Create flake8 configuration
echo "Creating flake8 configuration..."
cat > .flake8 << EOF
[flake8]
max-line-length = 100
exclude = .git,__pycache__,alembic,venv,env
ignore = E203, W503
EOF

# Create pylint configuration
echo "Creating pylint configuration..."
cat > .pylintrc << EOF
[MASTER]
ignore=alembic,venv,env
init-hook='import sys; sys.path.append(".")'

[MESSAGES CONTROL]
disable=C0111,R0903,C0103,R0913,R0914,C0302,R0912,R0915,R0902,W0212,C0330

[FORMAT]
max-line-length=100

[DESIGN]
max-args=10
EOF

# Create mypy configuration
echo "Creating mypy configuration..."
cat > mypy.ini << EOF
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
disallow_incomplete_defs = False

[mypy.plugins.sqlalchemy.ext.*]
ignore_missing_imports = True

[mypy.plugins.pydantic.*]
ignore_missing_imports = True
EOF

# Create isort configuration
echo "Creating isort configuration..."
cat > .isort.cfg << EOF
[settings]
line_length = 100
multi_line_output = 3
include_trailing_comma = True
force_grid_wrap = 0
use_parentheses = True
ensure_newline_before_comments = True
skip = alembic,venv,env
EOF

# Create pre-commit configuration
echo "Creating pre-commit configuration..."
cat > .pre-commit-config.yaml << EOF
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort

-   repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
    -   id: black

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8

-   repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
    -   id: mypy
        additional_dependencies: [types-requests]
EOF

# Make the setup script executable
chmod +x setup_linting.sh

echo "Installing pre-commit hooks..."
pre-commit install

echo "Linting setup completed!"
echo "You can now run linters with:"
echo "  - flake8 ."
echo "  - pylint app"
echo "  - mypy app"
echo "  - isort ."
echo "  - black ."
echo "Pre-commit hooks will run automatically on git commit."
