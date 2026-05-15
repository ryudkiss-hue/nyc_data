import sys
from pathlib import Path


def validate_env():
    """Validates that all variables defined in .env.example are present in .env"""
    project_root = Path(__file__).parent.parent
    example_env_path = project_root / ".env.example"
    active_env_path = project_root / ".env"

    if not example_env_path.exists():
        print(f"❌ Error: {example_env_path.name} not found in the project root.")
        sys.exit(1)

    def extract_keys(file_path: Path) -> set:
        keys = set()
        if not file_path.exists():
            return keys
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Ignore comments and empty lines
                if line and not line.startswith("#") and "=" in line:
                    keys.add(line.split("=", 1)[0].strip())
        return keys

    example_keys = extract_keys(example_env_path)
    active_keys = extract_keys(active_env_path)
    missing_keys = example_keys - active_keys

    print("--- Environment Variable Validation ---")
    if not active_env_path.exists():
        print("⚠️ Warning: .env file does not exist. Please copy .env.example to .env")
    elif not missing_keys:
        print("✅ Success: All expected variables from .env.example are present in .env!")
    else:
        print(f"❌ Error: Missing {len(missing_keys)} required variables in .env:")
        for key in sorted(missing_keys):
            print(f"  - {key}")
        sys.exit(1)


if __name__ == "__main__":
    validate_env()
