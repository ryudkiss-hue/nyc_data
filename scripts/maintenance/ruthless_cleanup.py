import os
import shutil
from pathlib import Path

def ruthless_cleanup():
    root = Path(".").resolve()
    archive = root / "legacy_archive"
    archive.mkdir(exist_ok=True)

    print("🧹 Initiating Ruthless Consolidation...\n")

    # 1. Enforce the `app/` directory structure
    app_dir = root / "app"
    app_dir.mkdir(exist_ok=True)

    # Move Streamlit files from root to app/
    streamlit_files = ["app.py", "analytics.py", "data_loader.py", "__init__.py"]
    for f in streamlit_files:
        file_path = root / f
        if file_path.exists() and file_path.is_file():
            dest = app_dir / f
            if dest.exists():
                dest.unlink() # Overwrite if exists
            shutil.move(str(file_path), str(dest))
            print(f"Moved stray file: {f} -> app/{f}")

    # 2. Archive all non-essential folders
    # This leaves ONLY the gold-standard Python/Streamlit structure
    essential_folders = {
        "app", "src", "tests", "data", "docs", "scripts",
        "legacy_archive", ".git", ".venv", ".github",
        ".vscode", ".roo", ".pytest_cache"
    }

    for item in root.iterdir():
        if item.is_dir() and item.name not in essential_folders:
            dest = archive / item.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(item), str(dest))
            print(f"Archived legacy folder: {item.name}/")

    # 3. Archive loose clutter in root
    essential_files = {
        ".env", ".env.example", ".env.socrata", ".gitignore", ".dockerignore",
        ".gitattributes", ".pre-commit-config.yaml", "pyrightconfig.json",
        "pyproject.toml", "poetry.lock", "requirements.txt", "requirements-dev.txt",
        "README.md", "QUICKSTART.md", "CHANGELOG.md", "CONTRIBUTING.md", "Makefile"
    }

    for item in root.iterdir():
        if item.is_file() and item.name not in essential_files and item.name != "ruthless_cleanup.py":
            dest = archive / item.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(item), str(dest))
            print(f"Archived loose script/file: {item.name}")

    print("\n✅ Repository perfectly consolidated. Your workspace is now clean!")

if __name__ == "__main__":
    ruthless_cleanup()
