from pathlib import Path


def cleanup_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Fix double replacements like observability.manager.logging -> observability.logging
    # This happened because 'observability' was a prefix of 'observability_logging'
    # and both were in the mapping, and 'observability' matched after 'observability_logging'
    # was replaced by 'observability.logging' because of the dot boundary.

    # We want socrata_toolkit.SUBPACKAGE.manager.SOMETHING -> socrata_toolkit.SUBPACKAGE.SOMETHING
    # UNLESS SOMETHING is not in the subpackage.

    # Actually, it's easier to just fix the specific ones that were doubled.
    doubles = [
        "quality",
        "observability",
        "lineage",
        "entity",
        "material",
        "spatial",
        "cdc",
        "dataverse",
        "llm",
        "nlp",
        "qgis",
        "quantum",
        "reports",
        "geo",
        "engineering",
        "core",
        "alerts",
        "analysis",
        "governance",
        "integrations",
        "tools",
        "viz",
        "pipeline",
        "discovery",
        "ops",
        "standards",
        "sql",
    ]

    for sub in doubles:
        # pattern matches socrata_toolkit.sub.manager.anything where anything is another module in the same sub
        # Wait, the script replaced 'observability_logging' with 'observability.logging'
        # Then it replaced 'observability' with 'observability.manager'
        # So 'socrata_toolkit.observability.logging' became 'socrata_toolkit.observability.manager.logging'
        content = content.replace(f"socrata_toolkit.{sub}.manager.", f"socrata_toolkit.{sub}.")

        # Also relative imports: from ..sub.manager.module
        content = content.replace(f"from ..{sub}.manager.", f"from ..{sub}.")

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False

def main():
    root = Path(".")
    count = 0
    for py_file in root.glob("socrata_toolkit/**/*.py"):
        if cleanup_file(py_file):
            count += 1
            print(f"Cleaned: {py_file}")
    for py_file in root.glob("tests/**/*.py"):
        if cleanup_file(py_file):
            count += 1
            print(f"Cleaned: {py_file}")
    print(f"Total files cleaned: {count}")

if __name__ == "__main__":
    main()
