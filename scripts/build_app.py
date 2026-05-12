"""Run this script to regenerate app.py with all modules."""
from pathlib import Path

APP = Path("app.py")
APP.write_text(open("socrata_toolkit/viz/dashboard.py", encoding="utf-8").read().replace(
    "if __name__ == \"__main__\":\n    main()",
    "main()"
).replace(
    'from ..analysis.program import',
    'from socrata_toolkit.analysis.program import'
).replace(
    'from ..engineering.borough_analysis import',
    'from socrata_toolkit.engineering.borough_analysis import'
).replace(
    'from ..tools.tasks import',
    'from socrata_toolkit.tools.tasks import'
).replace(
    'from ..engineering.construction_list import',
    'from socrata_toolkit.engineering.construction_list import'
).replace(
    'from ..engineering.contract_analytics import',
    'from socrata_toolkit.engineering.contract_analytics import'
).replace(
    'from ..core.client import',
    'from socrata_toolkit.core.client import'
).replace(
    'from ..analysis.core import',
    'from socrata_toolkit.analysis.core import'
).replace(
    'from ..governance.core import',
    'from socrata_toolkit.governance.core import'
).replace(
    'from ..reports.reporting import',
    'from socrata_toolkit.reports.reporting import'
).replace(
    'from ..analysis.program import compute_program_dashboard\n            from ..reports.reporting import',
    'from socrata_toolkit.analysis.program import compute_program_dashboard\n            from socrata_toolkit.reports.reporting import'
), encoding="utf-8")

print("app.py written from dashboard.py")
print(f"Lines: {len(APP.read_text().splitlines())}")
