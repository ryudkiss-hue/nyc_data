#!/usr/bin/env python3
"""
Analyze missing exports in stub modules and identify missing symbols.
This script parses imports from the entire codebase and identifies what's missing.
"""

import json
import os
import re
from collections import defaultdict


def extract_imports_from_file(filepath: str) -> list[tuple[str, str, list[str]]]:
    """
    Extract import statements from a file.
    Returns list of (module_path, line, [symbols]) tuples.
    """
    imports = []
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            # Match: from module import symbols
            match = re.match(r"from\s+([\w.]+)\s+import\s+(.+?)(?:#|$)", line)
            if match:
                module = match.group(1).strip()
                symbols_str = match.group(2).strip()
                # Parse symbols (handle parentheses, commas, etc.)
                symbols_str = re.sub(r"[()\\]", "", symbols_str)
                symbols = [
                    s.strip().split(" as ")[0].strip() for s in symbols_str.split(",") if s.strip()
                ]
                imports.append((module, line_num, symbols))
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

    return imports

def get_module_exports(filepath: str) -> set[str]:
    """
    Extract all public exports from a module.
    Returns set of exported symbols (classes, functions, etc.).
    """
    exports = set()
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Check for __all__
        all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if all_match:
            all_str = all_match.group(1)
            symbols = re.findall(r'["\'](\w+)["\']', all_str)
            exports.update(symbols)

        # Find class definitions
        classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
        exports.update(classes)

        # Find function definitions
        functions = re.findall(r"^def\s+(\w+)", content, re.MULTILINE)
        exports.update(functions)

    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")

    return exports

def resolve_module_path(import_module: str, from_file: str) -> str:
    """
    Resolve a module import string to a file path.
    """
    # Convert module path to file path
    parts = import_module.split(".")

    # Try as package (directory with __init__.py)
    pkg_path = os.path.join("/ryudkiss-hue/nyc_data", *parts, "__init__.py")
    if os.path.exists(pkg_path):
        return pkg_path

    # Try as module (.py file)
    mod_path = os.path.join("/ryudkiss-hue/nyc_data", *parts) + ".py"
    if os.path.exists(mod_path):
        return mod_path

    return None

def main():
    base_dir = "/ryudkiss-hue/nyc_data"

    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(base_dir):
        # Skip venv, __pycache__, .git, etc.
        dirs[:] = [
            d
            for d in dirs
            if d
            not in [".git", ".venv", "__pycache__", ".pytest_cache", "venv", "node_modules", ".roo"]
        ]

        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    print(f"Found {len(python_files)} Python files")

    # Stub modules we care about
    stub_modules = {
        "socrata_toolkit.quality_expectations",
        "socrata_toolkit.quality_profiler",
        "socrata_toolkit.quality_validator",
        "socrata_toolkit.scd_type2",
        "socrata_toolkit.temporal_queries",
        "socrata_toolkit.soft_delete",
        "socrata_toolkit.work_management",
        "socrata_toolkit.microsoft_graph",
        "socrata_toolkit.entity_matching",
        "socrata_toolkit.master_data",
        "socrata_toolkit.entity_reconciliation",
        "socrata_toolkit.qgis_compatibility",
        "socrata_toolkit.observability_logging",
    }

    # Track missing exports
    missing_by_module = defaultdict(list)  # module -> [(symbol, importing_file, line)]
    import_map = defaultdict(list)  # (source_module, symbol) -> [importing_files]

    # Process all files to find imports
    for python_file in python_files:
        imports = extract_imports_from_file(python_file)

        for source_module, line_num, symbols in imports:
            # Only care about socrata_toolkit imports
            if not source_module.startswith("socrata_toolkit"):
                continue

            module_path = resolve_module_path(source_module, python_file)

            if module_path is None:
                # Module doesn't exist at all
                for symbol in symbols:
                    missing_by_module[source_module].append(
                        {
                            "symbol": symbol,
                            "importing_file": python_file.replace(base_dir, ""),
                            "line": line_num,
                            "reason": "MODULE_NOT_FOUND",
                        }
                    )
            else:
                # Module exists, check exports
                exports = get_module_exports(module_path)

                for symbol in symbols:
                    if symbol not in exports:
                        missing_by_module[source_module].append(
                            {
                                "symbol": symbol,
                                "importing_file": python_file.replace(base_dir, ""),
                                "line": line_num,
                                "reason": "SYMBOL_NOT_EXPORTED",
                            }
                        )
                        import_map[(source_module, symbol)].append(
                            python_file.replace(base_dir, "")
                        )

    # Filter for stub modules and report
    stub_missing = {k: v for k, v in missing_by_module.items() if k in stub_modules}
    all_missing = {k: v for k, v in missing_by_module.items()}

    print("\n" + "=" * 80)
    print("MISSING EXPORTS ANALYSIS")
    print("=" * 80)

    print(f"\nTotal missing symbols: {sum(len(v) for v in all_missing.values())}")
    print(f"From stub modules: {sum(len(v) for v in stub_missing.values())}")

    print("\n" + "=" * 80)
    print("STUB MODULES WITH MISSING EXPORTS")
    print("=" * 80)

    for module in sorted(stub_modules):
        if module in missing_by_module:
            items = missing_by_module[module]
            unique_symbols = list(set(item["symbol"] for item in items))
            print(f"\n{module}")
            print(f"  Missing symbols: {len(unique_symbols)}")
            for symbol in sorted(unique_symbols):
                count = sum(1 for item in items if item["symbol"] == symbol)
                files = set(item["importing_file"] for item in items if item["symbol"] == symbol)
                print(f"    - {symbol} (imported {count}x from {len(files)} file(s))")

    print("\n" + "=" * 80)
    print("ALL MISSING SYMBOLS (by frequency)")
    print("=" * 80)

    # Count frequency of each missing symbol
    symbol_frequency = defaultdict(int)
    symbol_locations = defaultdict(set)

    for module, items in all_missing.items():
        for item in items:
            key = (module, item["symbol"])
            symbol_frequency[key] += 1
            symbol_locations[key].add(item["importing_file"])

    sorted_symbols = sorted(symbol_frequency.items(), key=lambda x: x[1], reverse=True)

    for (module, symbol), count in sorted_symbols[:50]:  # Top 50
        locations = symbol_locations[(module, symbol)]
        print(f"\n{symbol:<30} [{count:3d}x] from {module}")
        for loc in sorted(list(locations))[:3]:
            print(f"  - {loc}")
        if len(locations) > 3:
            print(f"  ... and {len(locations) - 3} more")

    # Save detailed report to JSON
    report = {
        "summary": {
            "total_missing": sum(len(v) for v in all_missing.values()),
            "stub_modules_affected": len(stub_missing),
            "unique_missing_symbols": len(
                set((m, item["symbol"]) for m, items in all_missing.items() for item in items)
            ),
        },
        "stub_modules": {
            module: {
                "missing_count": len(set(item["symbol"] for item in items)),
                "symbols": list(set(item["symbol"] for item in items)),
                "imports": [
                    {
                        "symbol": item["symbol"],
                        "from_file": item["importing_file"],
                        "line": item["line"],
                    }
                    for item in items
                ],
            }
            for module, items in sorted(stub_missing.items())
        },
        "all_missing_by_frequency": [
            {
                "symbol": symbol,
                "module": module,
                "count": count,
                "locations": list(symbol_locations[(module, symbol)])[:10],
            }
            for (module, symbol), count in sorted_symbols[:100]
        ],
    }

    with open("/ryudkiss-hue/nyc_data/missing_exports_analysis.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("Detailed report saved to: missing_exports_analysis.json")
    print("=" * 80)

if __name__ == "__main__":
    main()
