#!/usr/bin/env python
"""
NYC DOT Sidewalk Data Governance Toolkit - Universal Launcher
================================================

This script provides a unified entry point for:
- CLI commands: Socrata data ingestion, transformations, governance
- Web UI: Dash analyst dashboard (dash_app/app.py)
- Docker: Container orchestration (PostgreSQL, API, monitoring)
- Setup: Database initialization and configuration

Usage:
    python launcher.py cli <command> [options]     # Run CLI commands
    python launcher.py web [options]               # Launch Streamlit dashboard
    python launcher.py docker [action] [options]   # Manage Docker containers
    python launcher.py setup [component]           # Initialize system
    python launcher.py doctor                      # Health check
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

__version__ = "0.3.0"
PROJECT_ROOT = Path(__file__).parent.absolute()
SOCRATA_TOOLKIT = PROJECT_ROOT / "socrata_toolkit"


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}╔{'═' * 60}╗{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}║{text:^60}║{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚{'═' * 60}╝{Colors.ENDC}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}[OK] {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}[ERR] {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.CYAN}[INFO] {text}{Colors.ENDC}")


def check_requirements() -> bool:
    """Check if required dependencies are installed."""
    print_header("Checking Requirements")

    requirements = {
        "python": "Python",
        "docker": "Docker",
        "docker-compose": "Docker Compose",
        "git": "Git",
    }

    missing = []
    for cmd, name in requirements.items():
        if shutil.which(cmd):
            print_success(f"{name} is installed")
        else:
            print_warning(f"{name} is not installed (optional for some features)")
            if cmd not in ["docker", "docker-compose"]:
                missing.append(name)

    # Check Python packages
    try:
        import click

        print_success("click package is installed")
    except ImportError:
        print_warning("click package not found - install with: pip install click")
        missing.append("click")

    if missing:
        print_error(f"\nMissing required packages: {', '.join(missing)}")
        return False

    return True


def run_cli(args: list) -> int:
    """Run CLI command."""
    print_header("NYC DOT Toolkit - CLI Mode")

    try:
        from socrata_toolkit.core.cli import main as cli_main

        # Set up sys.argv for Click
        sys.argv = ["socrata"] + args
        cli_main()
        return 0
    except Exception as e:
        print_error(f"CLI error: {e}")
        return 1


def run_web(host: str = "127.0.0.1", port: int = 8050, dev: bool = False) -> int:
    """Launch primary Dash analyst dashboard."""
    print_header("NYC DOT Toolkit - Dash Dashboard")
    print_info(f"Starting Dash on http://{host}:{port}/")

    dash_script = PROJECT_ROOT / "dash_app" / "app.py"
    if not dash_script.exists():
        print_error(f"Dash app not found: {dash_script}")
        return 1

    env = os.environ.copy()
    if dev:
        env["NYC_DOT_DEBUG"] = "1"
    env["NYC_DOT_DASH_HOST"] = host
    env["NYC_DOT_DASH_PORT"] = str(port)

    cmd = [sys.executable, str(dash_script)]

    try:
        subprocess.run(cmd, env=env, check=True)
        return 0
    except KeyboardInterrupt:
        print_info("Dash dashboard stopped")
        return 0
    except Exception as e:
        print_error(f"Failed to start Dash: {e}")
        return 1


def run_docker(action: str, service: str | None = None, **kwargs) -> int:
    """Manage Docker containers."""
    print_header(f"NYC DOT Toolkit - Docker {action.upper()}")

    # Check Docker availability
    if not shutil.which("docker-compose") and not shutil.which("docker"):
        print_error(
            "Docker/Docker Compose not found. Install Docker Desktop from https://www.docker.com"
        )
        return 1

    # Determine docker-compose command
    docker_cmd = "docker-compose"
    if not shutil.which("docker-compose"):
        docker_cmd = "docker compose"

    compose_file = PROJECT_ROOT / "docker-compose.yml"

    if action == "up":
        print_info("Validating environment variables...")
        try:
            subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_env.py")], check=True
            )
        except subprocess.CalledProcessError:
            print_error("Environment validation failed. Please check your .env file.")
            return 1

        print_info("Starting all services...")
        service_part = service if service else ""
        cmd = [docker_cmd, "-f", str(compose_file), "up", "-d", service_part]
        try:
            subprocess.run(cmd, check=True)
            print_success("Services started successfully")
            print_info("Access services at:")
            print(f"  PostgreSQL: localhost:5432")
            print(f"  Prometheus: http://localhost:9090")
            print(f"  Grafana: http://localhost:3000 (admin/admin)")
            print(f"  Jaeger: http://localhost:16686")
            print(f"  API: http://localhost:8000/docs")
            return 0
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to start services: {e}")
            return 1

    elif action == "down":
        print_info("Stopping all services...")
        cmd = [docker_cmd, "-f", str(compose_file), "down"]
        if kwargs.get("remove_volumes"):
            cmd.append("-v")
        try:
            subprocess.run(cmd, check=True)
            print_success("Services stopped successfully")
            return 0
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to stop services: {e}")
            return 1

    elif action == "logs":
        service_part = service if service else ""
        cmd = [docker_cmd, "-f", str(compose_file), "logs", "-f", service_part]
        try:
            subprocess.run(cmd)
            return 0
        except KeyboardInterrupt:
            return 0

    elif action == "status":
        cmd = [docker_cmd, "-f", str(compose_file), "ps"]
        try:
            subprocess.run(cmd, check=True)
            return 0
        except subprocess.CalledProcessError:
            return 1

    else:
        print_error(f"Unknown docker action: {action}")
        return 1


def run_setup_wizard() -> int:
    """Run interactive install wizard."""
    print_header("NYC DOT Toolkit - Install Wizard")
    try:
        from socrata_toolkit.install_wizard import _print_summary, run_wizard

        summary = run_wizard()
        _print_summary(summary)
        print_success("Configuration written. Next: socrata analyst run --profile config/analyst_profile.yaml")
        return 0
    except SystemExit as exc:
        return int(exc.code) if exc.code else 1
    except Exception as e:
        print_error(f"Wizard failed: {e}")
        return 1


def run_setup_docker() -> int:
    """Prepare .env and start Docker analyst stack."""
    print_header("NYC DOT Toolkit - Docker Setup")
    root_env = PROJECT_ROOT / ".env"
    example = PROJECT_ROOT / "config" / ".env.example"
    if not root_env.exists():
        if example.exists():
            shutil.copy(example, root_env)
            print_success(f"Created {root_env} from config/.env.example")
        elif (PROJECT_ROOT / ".env.example").exists():
            shutil.copy(PROJECT_ROOT / ".env.example", root_env)
            print_success("Created .env from .env.example")
        else:
            print_warning(".env missing — run: python launcher.py setup wizard")
    else:
        print_success(".env already exists")

    docker_cmd = "docker-compose" if shutil.which("docker-compose") else "docker compose"
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    cmd = [
        *docker_cmd.split(),
        "-f",
        str(compose_file),
        "--profile",
        "analyst",
        "up",
        "-d",
        "postgres",
    ]
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
        print_success("Postgres started (profile: analyst)")
        print_info("Run wizard in container: docker compose --profile analyst run --rm setup")
        print_info("Start analyst runner: docker compose --profile analyst up -d analyst-runner")
        return 0
    except subprocess.CalledProcessError as e:
        print_error(f"Docker setup failed: {e}")
        return 1


def run_setup(component: str | None = None) -> int:
    """Initialize system components."""
    print_header("NYC DOT Toolkit - Setup & Initialization")

    components = ["database", "schema", "config", "wizard", "docker", "all"]

    if component and component not in components:
        print_error(f"Unknown component: {component}")
        print_info(f"Available: {', '.join(components)}")
        return 1

    if component == "wizard":
        return run_setup_wizard()
    if component == "docker":
        return run_setup_docker()

    if not component or component == "all":
        wizard_rc = run_setup_wizard()
        legacy_rc = run_setup_all()
        return 0 if wizard_rc == 0 and legacy_rc == 0 else 1
    elif component == "database":
        return setup_database()
    elif component == "schema":
        return setup_schema()
    elif component == "config":
        return setup_config()

    return 0


def setup_database() -> int:
    """Initialize PostgreSQL database."""
    print_info("Setting up PostgreSQL database...")

    try:
        import psycopg

        print_success("psycopg2 available")
    except ImportError:
        print_warning("psycopg2 not installed - skipping database setup")
        print_info("Install with: pip install psycopg[binary]")
        return 0

    print_info("Run 'python launcher.py docker up postgres' first")
    print_success("Database initialization configured")
    return 0


def setup_schema() -> int:
    """Initialize database schema."""
    print_info("Setting up database schema...")

    sql_dir = PROJECT_ROOT / "sql"
    if not sql_dir.exists():
        print_error(f"SQL directory not found: {sql_dir}")
        return 1

    print_success("Schema files found:")
    for sql_file in sorted(sql_dir.glob("*.sql")):
        print(f"  - {sql_file.name}")

    print_info("Schemas will be initialized when PostgreSQL starts in Docker")
    return 0


def setup_config() -> int:
    """Generate configuration files."""
    print_info("Setting up configuration files...")

    # Check .env file
    env_file = PROJECT_ROOT / ".env.socrata"
    if not env_file.exists():
        print_warning(".env.socrata not found")
        print_info("Create it with:")
        print("  SOCRATA_DOMAIN=data.cityofnewyork.us")
        print("  POSTGRES_USER=dot_user")
        print("  POSTGRES_PASSWORD=secure_password")
        return 1

    print_success(".env.socrata found")

    # Check config file
    config_file = PROJECT_ROOT / "socrata_toolkit.config.json"
    if config_file.exists():
        print_success("socrata_toolkit.config.json found")

    return 0


def run_setup_all() -> int:
    """Run all setup steps."""
    print_info("Running complete setup...")

    steps = [
        ("Configuration", setup_config),
        ("Database", setup_database),
        ("Schema", setup_schema),
    ]

    failed = []
    for step_name, step_func in steps:
        print_info(f"\nStep: {step_name}")
        try:
            if step_func() != 0:
                failed.append(step_name)
        except Exception as e:
            print_error(f"Step failed: {e}")
            failed.append(step_name)

    if failed:
        print_error(f"\nSetup incomplete. Failed steps: {', '.join(failed)}")
        return 1

    print_success("Setup complete!")
    return 0


def check_analyst_profile() -> bool:
    """Verify analyst profile paths and DuckDB writability."""
    ok = True
    profile = PROJECT_ROOT / "config" / "analyst_profile.yaml"
    example = PROJECT_ROOT / "config" / "analyst_profile.example.yaml"
    if profile.exists():
        print_success(f"Analyst profile: {profile}")
    elif example.exists():
        print_warning("config/analyst_profile.yaml missing — run: socrata analyst init-config")
        ok = False
    else:
        print_warning("No analyst profile found")
        ok = False

    outputs = PROJECT_ROOT / "outputs" / "analyst_pack"
    try:
        outputs.mkdir(parents=True, exist_ok=True)
        test_file = outputs / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        print_success(f"Analyst outputs writable: {outputs}")
    except OSError as exc:
        print_warning(f"Cannot write analyst outputs: {exc}")
        ok = False

    duckdb_path = PROJECT_ROOT / "nyc_mission_control.duckdb"
    try:
        from socrata_toolkit.core import DuckDBManager

        mgr = DuckDBManager(str(duckdb_path))
        mgr.query("SELECT 1")
        mgr.close()
        print_success(f"DuckDB writable: {duckdb_path.name}")
    except Exception as exc:
        print_warning(f"DuckDB check failed: {exc}")

    pg_dsn = os.getenv("PG_DSN")
    if pg_dsn:
        try:
            import psycopg

            with psycopg.connect(pg_dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            print_success("PG_DSN connection OK")
        except Exception as exc:
            print_warning(f"PG_DSN configured but unreachable: {exc}")
    else:
        print_info("PG_DSN not set (optional for PostGIS conflicts)")

    return ok


def run_doctor() -> int:
    """Health check and diagnostics."""
    print_header("NYC DOT Toolkit - Health Check")

    checks = {
        "Python": check_python,
        "Dependencies": check_dependencies,
        "Docker": check_docker,
        "Database": check_database,
        "Configuration": check_config,
        "Analyst Autopilot": check_analyst_profile,
    }

    results = {}
    for check_name, check_func in checks.items():
        print_info(f"Checking {check_name}...")
        try:
            results[check_name] = check_func()
            if results[check_name]:
                print_success(f"{check_name} OK")
            else:
                print_warning(f"{check_name} has issues")
        except Exception as e:
            print_error(f"{check_name} check failed: {e}")
            results[check_name] = False

    print_header("Health Check Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    return 0 if passed == total else 1


def check_python() -> bool:
    """Check Python version."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print_success(f"Python {version.major}.{version.minor} (>= 3.9)")
        return True
    print_error(f"Python {version.major}.{version.minor} (needs >= 3.9)")
    return False


def check_dependencies() -> bool:
    """Check Python packages."""
    packages = ["click", "pandas", "requests", "pyyaml"]
    all_ok = True

    for pkg in packages:
        try:
            __import__(pkg)
            print_success(f"  {pkg} installed")
        except ImportError:
            print_warning(f"  {pkg} not found")
            all_ok = False

    return all_ok


def check_docker() -> bool:
    """Check Docker availability."""
    if shutil.which("docker") or shutil.which("docker-compose"):
        print_success("Docker available")
        return True
    print_warning("Docker not found (optional)")
    return False


def check_database() -> bool:
    """Check database connectivity."""
    try:
        import psycopg

        print_success("psycopg available")
        # Try to connect to localhost PostgreSQL
        try:
            conn = psycopg.connect(
                "host=localhost user=dot_user password=dot_pass dbname=sidewalk_db",
                connect_timeout=2,
            )
            conn.close()
            print_success("PostgreSQL connection OK")
            return True
        except Exception:
            print_warning("PostgreSQL not running or connection failed")
            return False
    except ImportError:
        print_warning("psycopg not installed")
        return False


def check_config() -> bool:
    """Check configuration files."""
    ok = True
    config_file = PROJECT_ROOT / "socrata_toolkit.config.json"
    env_file = PROJECT_ROOT / ".env"
    legacy_env = PROJECT_ROOT / ".env.socrata"

    if config_file.exists():
        print_success("socrata_toolkit.config.json found")
    else:
        print_info("socrata_toolkit.config.json optional (not required)")

    if env_file.exists():
        print_success(".env found")
    elif legacy_env.exists():
        print_success(".env.socrata found (legacy)")
    else:
        print_warning(".env missing — run: python launcher.py setup wizard")
        ok = False

    profile = PROJECT_ROOT / "config" / "analyst_profile.yaml"
    if profile.exists():
        print_success(f"Analyst profile: {profile.name}")
    else:
        print_warning("config/analyst_profile.yaml missing")
        ok = False

    return ok


def main():
    """Main entry point."""
    try:
        from dotenv import load_dotenv

        # Prioritize the shared network drive path if the batch file provided it
        shared_env = os.getenv("SHARED_ENV_PATH")
        if shared_env and os.path.exists(shared_env):
            load_dotenv(shared_env)
        else:
            # Fallback to local .env
            env_path = PROJECT_ROOT / ".env"
            if os.path.exists(env_path):
                load_dotenv(env_path)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, prog="launcher"
    )

    parser.add_argument("--version", action="version", version=f"NYC DOT Toolkit v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # CLI subcommand
    cli_parser = subparsers.add_parser("cli", help="Run CLI commands")
    cli_parser.add_argument("cli_args", nargs=argparse.REMAINDER, help="CLI arguments")

    # Web subcommand
    web_parser = subparsers.add_parser("web", help="Launch web dashboard")
    web_parser.add_argument("--host", default="localhost", help="Host to bind to")
    web_parser.add_argument("--port", type=int, default=8501, help="Port to bind to")
    web_parser.add_argument("--dev", action="store_true", help="Development mode")

    # Docker subcommand
    docker_parser = subparsers.add_parser("docker", help="Manage Docker containers")
    docker_parser.add_argument(
        "action", choices=["up", "down", "logs", "status", "restart"], help="Docker action"
    )
    docker_parser.add_argument("--service", help="Specific service to manage")
    docker_parser.add_argument(
        "--remove-volumes", action="store_true", help="Remove volumes on down"
    )

    # Setup subcommand
    setup_parser = subparsers.add_parser("setup", help="Initialize system")
    setup_parser.add_argument(
        "component",
        nargs="?",
        choices=["database", "schema", "config", "wizard", "docker", "all"],
        default="all",
        help="Component to set up",
    )

    # Doctor subcommand
    subparsers.add_parser("doctor", help="Health check and diagnostics")

    # Info subcommand
    subparsers.add_parser("info", help="Show system information")

    args = parser.parse_args()

    # Check requirements
    if not check_requirements():
        print_warning("Some requirements are missing. Continue? (y/n)")
        if input().lower() != "y":
            return 1

    # Route commands
    if args.command == "cli":
        return run_cli(args.cli_args)
    elif args.command == "web":
        return run_web(args.host, args.port, args.dev)
    elif args.command == "docker":
        return run_docker(args.action, service=args.service, remove_volumes=args.remove_volumes)
    elif args.command == "setup":
        return run_setup(args.component)
    elif args.command == "doctor":
        return run_doctor()
    elif args.command == "info":
        print_header("NYC DOT Toolkit - System Information")
        print(f"Version: {__version__}")
        print(f"Python: {sys.version}")
        print(f"Project Root: {PROJECT_ROOT}")
        print(f"Toolkit: {SOCRATA_TOOLKIT}")
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
