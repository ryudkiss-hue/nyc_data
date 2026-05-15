#!/bin/bash

if ! python -m autoflake --version &> /dev/null; then
    echo -e "\e[36mInstalling autoflake...\e[0m"
    python -m pip install autoflake
fi

echo -e "\e[33m🧹 Scrubbing unused imports and variables across the project...\e[0m"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# --in-place modifies files directly, --recursive searches directories
python -m autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive "$PROJECT_ROOT/socrata_toolkit" "$PROJECT_ROOT/tests"

echo -e "\e[32m✅ Cleanup complete! All unused imports have been removed.\e[0m"