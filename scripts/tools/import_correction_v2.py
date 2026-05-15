import re
from pathlib import Path

# We want to fix cases where a package name was replaced because it matched a module name that was moved.
# Example: socrata_toolkit.cdc.engine -> socrata_toolkit.pipeline.cdc.engine (WRONG)
# Because 'cdc' (module) was moved to 'pipeline.cdc', but 'cdc' (package) should stay 'cdc'.

REVERSIONS = [
    (r"socrata_toolkit\.pipeline\.cdc\.", r"socrata_toolkit.cdc."),
    (r"socrata_toolkit\.core\.api\.", r"socrata_toolkit.api."),
    (
        r"socrata_toolkit\.governance\.governance\.",
        r"socrata_toolkit.governance.",
    ),  # wait, governance module moved to governance/core.py
    (r"socrata_toolkit\.analysis\.analysis\.", r"socrata_toolkit.analysis."),
    (r"socrata_toolkit\.spatial\.spatial\.", r"socrata_toolkit.spatial."),
    (r"socrata_toolkit\.ops\.ops\.", r"socrata_toolkit.ops."),
    (r"socrata_toolkit\.viz\.visualization\.", r"socrata_toolkit.viz."),
    (r"socrata_toolkit\.lineage\.lineage\.", r"socrata_toolkit.lineage."),
    (r"socrata_toolkit\.observability\.observability\.", r"socrata_toolkit.observability."),
]

# Also fix the 'core' module names if they were doubled
# socrata_toolkit.governance.core.compliance -> socrata_toolkit.governance.compliance
DOUBLED_MAINS = {
    "governance": "core",
    "analysis": "core",
    "spatial": "core",
    "ops": "core",
    "viz": "core",
    "lineage": "manager",
    "observability": "manager",
}


def fix_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    for pattern, replacement in REVERSIONS:
        content = re.sub(pattern, replacement, content)
        # Relative versions
        rel_pattern = pattern.replace(r"socrata_toolkit\.", r"\.\.")
        rel_replacement = replacement.replace("socrata_toolkit.", "..")
        content = re.sub(rel_pattern, rel_replacement, content)

    for sub, main in DOUBLED_MAINS.items():
        # socrata_toolkit.sub.main.something -> socrata_toolkit.sub.something
        # UNLESS something is 'main' itself (which shouldn't happen with this regex)
        pattern = rf"socrata_toolkit\.{sub}\.{main}\.([a-zA-Z0-9_]+)"
        replacement = rf"socrata_toolkit.{sub}.\1"
        content = re.sub(pattern, replacement, content)

        rel_pattern = rf"\.\.{sub}\.{main}\.([a-zA-Z0-9_]+)"
        rel_replacement = rf"..{sub}.\1"
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
