from setuptools import setup, find_packages

setup(
    name="socrata-toolkit",
    version="0.4.0",
    description="NYC DOT Sidewalk Inspection & Management Toolkit",
    author="NYC DOT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "duckdb>=0.8.0",
        "pandas>=1.5.0",
        "requests>=2.28.0",
        "plotly>=5.0.0",
        "dash>=2.0.0",
        "dash-mantine-components>=0.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "ruff>=0.1.0",
            "black>=23.0.0",
        ],
        "mission": [
            "fastapi>=0.95.0",
            "uvicorn>=0.20.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "socrata-nlquery=socrata_toolkit.core.cli:main",
            "socrata=socrata_toolkit.core.cli:main",
        ],
    },
)
