import os
import sys
import subprocess
from pathlib import Path

def build_executable():
    """Compiles the NYC DOT Toolkit into a single standalone executable."""
    print("--- 🏗️ Building NYC DOT Toolkit Standalone Executable ---")
    
    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
        print("✅ PyInstaller is ready.")
    except ImportError:
        print("⚠️ PyInstaller not found. Installing now...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        
    project_root = Path(__file__).parent.parent.absolute()
    launcher_script = project_root / "launcher.py"
    
    if not launcher_script.exists():
        print(f"❌ Error: Could not find entry point at {launcher_script}")
        sys.exit(1)
        
    # 2. Configure the PyInstaller Build Command
    # Note: os.pathsep automatically uses ';' for Windows and ':' for Mac/Linux
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "nyc_toolkit",   # Name of the output .exe
        "--onefile",               # Bundle everything into a single file
        "--clean",                 # Clean PyInstaller cache before building
        "--noconfirm",             # Overwrite existing build without asking
        
        # Include the core toolkit package files
        "--add-data", f"socrata_toolkit{os.pathsep}socrata_toolkit",
        
        # Explicitly declare libraries that might be dynamically loaded (Hidden Imports)
        "--hidden-import", "pandas",
        "--hidden-import", "click",
        "--hidden-import", "requests",
        "--hidden-import", "duckdb",
        "--hidden-import", "tqdm",
        "--hidden-import", "dotenv",
        
        str(launcher_script)
    ]
    
    print("\n🚀 Compiling... (This may take 2-5 minutes depending on dependencies)")
    subprocess.run(cmd, cwd=project_root, check=True)
    print(f"\n✅ Build complete! Your standalone executable is located in: {project_root / 'dist'}")

if __name__ == "__main__":
    build_executable()