import ast
from pathlib import Path

# Read the __init__.py
init_content = Path("socrata_toolkit/__init__.py").read_text()
tree = ast.parse(init_content)

# Extract _lazy_map
_lazy_map = {}
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_lazy_map":
                if isinstance(node.value, ast.Dict):
                    for key, val in zip(node.value.keys, node.value.values):
                        if isinstance(key, ast.Constant) and isinstance(val, ast.Constant):
                            _lazy_map[key.value] = val.value

# Extract __all__
__all__ = []
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant):
                            __all__.append(elt.value)

print("=== CHECKING CONSISTENCY ===")
print(f"_lazy_map entries: {len(_lazy_map)}")
print(f"__all__ entries: {len(__all__)}")

missing_in_map = set(__all__) - set(_lazy_map.keys())
missing_in_all = set(_lazy_map.keys()) - set(__all__)

if missing_in_map:
    print(f"\nIn __all__ but NOT in _lazy_map: {sorted(missing_in_map)}")

if missing_in_all:
    print(f"\nIn _lazy_map but NOT in __all__: {sorted(missing_in_all)}")

if not missing_in_map and not missing_in_all:
    print("✓ __all__ and _lazy_map are perfectly synchronized")

# Extract TYPE_CHECKING imports
type_checking_modules = {}
for node in ast.walk(tree):
    if isinstance(node, ast.If):
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            for item in node.body:
                if isinstance(item, ast.ImportFrom):
                    module = item.module
                    for alias in item.names:
                        name = alias.asname or alias.name
                        if module not in type_checking_modules:
                            type_checking_modules[module] = []
                        type_checking_modules[module].append(name)

print(f"\nTYPE_CHECKING modules: {len(type_checking_modules)}")
all_type_checking_names = set()
for names in type_checking_modules.values():
    all_type_checking_names.update(names)

missing_type_checking = set(_lazy_map.keys()) - all_type_checking_names
if missing_type_checking:
    print(f"In _lazy_map but NOT in TYPE_CHECKING imports: {sorted(missing_type_checking)}")
else:
    print("✓ All _lazy_map entries have corresponding TYPE_CHECKING imports")
