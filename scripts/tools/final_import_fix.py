import re
from pathlib import Path

# Subpackages and their 'main' module names (that caused double replacements)
MAINS = {
    "quality": [
        "core",
        "validation",
        "freshness",
        "sla_tracking",
    ],  # wait, quality.core was analysis.core
    "observability": ["manager"],
    "lineage": ["manager"],
    "spatial": ["core"],
    "governance": ["core"],
    "ops": ["core"],
    "analysis": ["core"],
    "viz": ["core"],
    "core": [
        "api",
        "app",
        "cli",
        "client",
        "config",
        "db_helpers",
        "logging_utils",
        "models",
        "persistence",
        "pipeline",
        "state",
        "utils",
        "master_data",
        "exporters",
    ],
    "api": ["core"],  # formerly socrata_toolkit.api (module) -> socrata_toolkit.core.api
}

# Specific doubled patterns to fix
DOUBLES = [
    (r"socrata_toolkit\.governance\.core\.compliance", r"socrata_toolkit.governance.compliance"),
    (r"socrata_toolkit\.governance\.core\.audit", r"socrata_toolkit.governance.audit"),
    (r"socrata_toolkit\.governance\.core\.processor", r"socrata_toolkit.governance.processor"),
    (r"socrata_toolkit\.analysis\.core\.text", r"socrata_toolkit.analysis.text"),
    (r"socrata_toolkit\.analysis\.core\.advanced", r"socrata_toolkit.analysis.advanced"),
    (r"socrata_toolkit\.analysis\.core\.insights", r"socrata_toolkit.analysis.insights"),
    (r"socrata_toolkit\.analysis\.core\.metrics", r"socrata_toolkit.analysis.metrics"),
    (r"socrata_toolkit\.analysis\.core\.program", r"socrata_toolkit.analysis.program"),
    (r"socrata_toolkit\.analysis\.core\.relevance", r"socrata_toolkit.analysis.relevance"),
    (r"socrata_toolkit\.core\.api\.auth", r"socrata_toolkit.api.auth"),
    (r"socrata_toolkit\.core\.api\.authorization", r"socrata_toolkit.api.authorization"),
    (r"socrata_toolkit\.core\.api\.cache", r"socrata_toolkit.api.cache"),
    (r"socrata_toolkit\.core\.api\.config", r"socrata_toolkit.api.config"),
    (r"socrata_toolkit\.core\.api\.exceptions", r"socrata_toolkit.api.exceptions"),
    (r"socrata_toolkit\.core\.api\.governance", r"socrata_toolkit.api.governance"),
    (r"socrata_toolkit\.core\.api\.llm_routes", r"socrata_toolkit.api.llm_routes"),
    (r"socrata_toolkit\.core\.api\.main", r"socrata_toolkit.api.main"),
    (
        r"socrata_toolkit\.core\.api\.models",
        r"socrata_toolkit.core.api.models",
    ),  # wait, models.py is in api/
    (r"socrata_toolkit\.core\.api\.rate_limiting", r"socrata_toolkit.api.rate_limiting"),
    (r"socrata_toolkit\.core\.api\.request_pipeline", r"socrata_toolkit.api.request_pipeline"),
    (r"socrata_toolkit\.core\.api\.routes", r"socrata_toolkit.api.routes"),
    (r"socrata_toolkit\.core\.api\.schemas", r"socrata_toolkit.api.schemas"),
    (r"socrata_toolkit\.core\.api\.versioning", r"socrata_toolkit.api.versioning"),
    (r"socrata_toolkit\.spatial\.core\.analytics", r"socrata_toolkit.spatial.analytics"),
    (r"socrata_toolkit\.spatial\.core\.database", r"socrata_toolkit.spatial.database"),
    (r"socrata_toolkit\.spatial\.core\.metrics", r"socrata_toolkit.spatial.metrics"),
    (r"socrata_toolkit\.spatial\.core\.queries", r"socrata_toolkit.spatial.queries"),
    (r"socrata_toolkit\.spatial\.core\.visualization", r"socrata_toolkit.spatial.visualization"),
    (r"socrata_toolkit\.ops\.core\.workflow", r"socrata_toolkit.ops.workflow"),
]


def fix_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    for pattern, replacement in DOUBLES:
        content = re.sub(pattern, replacement, content)

    # Also handle relative imports if needed, but absolute are more common in tests
    # from ..governance.core.compliance -> from ..governance.compliance
    for pattern, replacement in DOUBLES:
        # replace socrata_toolkit. with .. or . if they are relative
        rel_pattern = pattern.replace(r"socrata_toolkit\.", r"\.\.")
        rel_replacement = replacement.replace("socrata_toolkit.", "..")
        content = re.sub(rel_pattern, rel_replacement, content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    root = Path(".")
    count = 0
    for py_file in root.glob("socrata_toolkit/**/*.py"):
        if fix_file(py_file):
            count += 1
            print(f"Fixed: {py_file}")
    for py_file in root.glob("tests/**/*.py"):
        if fix_file(py_file):
            count += 1
            print(f"Fixed: {py_file}")
    print(f"Total files fixed: {count}")


if __name__ == "__main__":
    main()
