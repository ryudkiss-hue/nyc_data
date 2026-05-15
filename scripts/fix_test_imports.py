import os
import re

TEST_DIR = "tests"

MAPPINGS = {
    # Analysis Pillar
    r"socrata_toolkit\.analysis\.\w+": "socrata_toolkit.analysis",
    r"socrata_toolkit\.quality\.\w+": "socrata_toolkit.analysis",
    r"socrata_toolkit\.viz\.\w+": "socrata_toolkit.analysis",
    r"socrata_toolkit\.metrics\.\w+": "socrata_toolkit.analysis",
    r"socrata_toolkit\.reporting\.\w+": "socrata_toolkit.analysis",
    r"socrata_toolkit\.reports\.\w+": "socrata_toolkit.analysis",
    r"socrata_toolkit\.validation\.\w+": "socrata_toolkit.analysis",
    # Core Pillar
    r"socrata_toolkit\.core\.\w+": "socrata_toolkit.core",
    r"socrata_toolkit\.discovery\.\w+": "socrata_toolkit.core",
    r"socrata_toolkit\.config\.\w+": "socrata_toolkit.core",
    r"socrata_toolkit\.db\.\w+": "socrata_toolkit.core",
    # Spatial Pillar
    r"socrata_toolkit\.spatial\.\w+": "socrata_toolkit.spatial",
    r"socrata_toolkit\.geo\.\w+": "socrata_toolkit.spatial",
    r"socrata_toolkit\.qgis\.\w+": "socrata_toolkit.spatial",
    # Governance Pillar
    r"socrata_toolkit\.governance\.\w+": "socrata_toolkit.governance",
    r"socrata_toolkit\.compliance\.\w+": "socrata_toolkit.governance",
    r"socrata_toolkit\.lineage\.\w+": "socrata_toolkit.governance",
    r"socrata_toolkit\.audit\.\w+": "socrata_toolkit.governance",
    # AI Pillar
    r"socrata_toolkit\.ai\.\w+": "socrata_toolkit.ai",
    r"socrata_toolkit\.triage\.\w+": "socrata_toolkit.ai",
    # Pipeline Pillar
    r"socrata_toolkit\.pipeline\.\w+": "socrata_toolkit.pipeline",
    r"socrata_toolkit\.cdc\.\w+": "socrata_toolkit.pipeline",
    # Engineering Pillar
    r"socrata_toolkit\.engineering\.\w+": "socrata_toolkit.engineering",
    r"socrata_toolkit\.material\.\w+": "socrata_toolkit.engineering",
    r"socrata_toolkit\.sql\.\w+": "socrata_toolkit.core",
}


def fix_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    new_content = content
    for pattern, replacement in MAPPINGS.items():
        new_content = re.sub(pattern, replacement, new_content)

    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")


if __name__ == "__main__":
    for filename in os.listdir(TEST_DIR):
        if filename.startswith("test_") and filename.endswith(".py"):
            fix_file(os.path.join(TEST_DIR, filename))
