"""
Anti-Regression Test Suite for Static Typing and API Exports.
Ensures that all objects declared in the public API (__all__) are completely valid
and resolvable at runtime, preventing "UnsupportedDunderAll" Pyright errors.
"""

import pytest

import socrata_toolkit


def test_all_exports_resolvable():
    """
    Iterates through the lazy-loaded __all__ registry and explicitly attempts
    to access each attribute. If an import path is broken or a function was
    deleted/renamed, this will fail and alert the developer immediately.
    """
    assert hasattr(
        socrata_toolkit, "__all__"
    ), "socrata_toolkit is missing the __all__ declaration."

    failed_imports = []
    missing_deps = set()

    for symbol_name in socrata_toolkit.__all__:
        try:
            # Trigger the __getattr__ lazy loader
            obj = getattr(socrata_toolkit, symbol_name)
            assert obj is not None
        except ImportError as e:
            error_msg = str(e)
            if "No module named 'duckdb'" in error_msg:
                missing_deps.add("duckdb")
            elif "No module named 'fastapi'" in error_msg:
                missing_deps.add("fastapi")
            else:
                failed_imports.append(f"{symbol_name} ({error_msg})")
        except AttributeError as e:
            failed_imports.append(f"{symbol_name} ({str(e)})")

    if missing_deps:
        pytest.fail(
            f"🚨 ENVIRONMENT ERROR: Missing required packages!\nPlease run: pip install {' '.join(missing_deps)}"
        )

    if failed_imports:
        pytest.fail(
            f"CRITICAL: The following {len(failed_imports)} symbols are declared in __all__ but failed to load:\n"
            + "\n".join(failed_imports)
        )
