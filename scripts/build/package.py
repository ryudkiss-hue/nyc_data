import os
import shutil

import PyInstaller.__main__


def build():
    print("Starting build process for MissionControl Toolkit...")

    # Ensure build directories are clean
    for d in ["build", "dist"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    # Run PyInstaller
    PyInstaller.__main__.run(["MissionControl.spec", "--noconfirm", "--clean"])

    print("\nBuild complete! Executable is in the 'dist' folder.")


if __name__ == "__main__":
    build()
