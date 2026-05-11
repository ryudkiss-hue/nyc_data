# NYC DOT Sidewalk Data Governance Toolkit - Windows Deployment Script
# PowerShell script for Windows 10/11 with Docker Desktop

param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "start", "stop", "status", "logs", "clean", "help")]
    [string]$Action = "help",
    
    [switch]$RemoveVolumes,
    [string]$Service = "",
    [switch]$Dev
)

$ErrorActionPreference = "Stop"

# Color functions for terminal output
function Write-Header {
    param([string]$Text)
    Write-Host "`n" -NoNewline
    Write-Host "================================================" -ForegroundColor Blue -NoNewline
    Write-Host "`n"
    Write-Host $Text.PadRight(50).PadLeft(50 + ([int]($Text.Length - 50) / 2)) -ForegroundColor Cyan -NoNewline
    Write-Host "`n"
    Write-Host "================================================" -ForegroundColor Blue
    Write-Host "`n"
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ " -ForegroundColor Green -NoNewline
    Write-Host $Text
}

function Write-Error {
    param([string]$Text)
    Write-Host "✗ " -ForegroundColor Red -NoNewline
    Write-Host $Text
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $Text
}

function Write-Info {
    param([string]$Text)
    Write-Host "ℹ " -ForegroundColor Cyan -NoNewline
    Write-Host $Text
}

# Check prerequisites
function Test-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    $allOk = $true
    
    # Check Docker
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Success "Docker is installed"
    } else {
        Write-Error "Docker not found. Install from https://www.docker.com/products/docker-desktop"
        $allOk = $false
    }
    
    # Check Docker Compose
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        Write-Success "Docker Compose is installed"
    } else {
        try {
            $null = docker compose version
            Write-Success "Docker Compose is available via 'docker compose'"
        } catch {
            Write-Error "Docker Compose not found"
            $allOk = $false
        }
    }
    
    # Check Python
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonVersion = python --version
        Write-Success "Python is installed: $pythonVersion"
    } else {
        Write-Warning "Python not found (optional)"
    }
    
    # Check Git
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Success "Git is installed"
    } else {
        Write-Warning "Git not found (optional)"
    }
    
    return $allOk
}

# Setup function
function Invoke-Setup {
    Write-Header "NYC DOT Toolkit - Setup"
    
    # Check .env file
    if (Test-Path ".env.socrata") {
        Write-Success ".env.socrata already exists"
    } else {
        Write-Info "Creating .env.socrata template..."
        @"
# Socrata Configuration
SOCRATA_DOMAIN=data.cityofnewyork.us
SOCRATA_APP_TOKEN=your_app_token_here

# PostgreSQL Configuration
POSTGRES_USER=dot_user
POSTGRES_PASSWORD=secure_password_change_this
POSTGRES_DB=sidewalk_db

# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change_this_password

# Application Configuration
LOG_LEVEL=INFO
DEBUG=false
"@ | Out-File -Encoding UTF8 ".env.socrata"
        Write-Success ".env.socrata created - please edit with your credentials"
    }
    
    # Check Docker Compose
    Write-Info "Validating docker-compose.yml..."
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            docker-compose config > $null
        } else {
            docker compose config > $null
        }
        Write-Success "docker-compose.yml is valid"
    } catch {
        Write-Error "docker-compose.yml validation failed: $_"
        return
    }
    
    Write-Success "Setup complete! Run 'deploy.ps1 start' to begin services"
}

# Start services
function Start-Services {
    param([string]$ServiceName = "")
    
    Write-Header "Starting Services"
    
    if (-not (Test-Prerequisites)) {
        Write-Error "Prerequisites not met"
        return
    }
    
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            $composeCmd = "docker-compose"
        } else {
            $composeCmd = "docker"
            $dockerComposeArgs = "compose"
        }
        
        Write-Info "Starting Docker services..."
        if ($composeCmd -eq "docker") {
            docker compose up -d $ServiceName
        } else {
            docker-compose up -d $ServiceName
        }
        
        Write-Success "Services started successfully"
        
        Write-Info "`nAccess services at:"
        Write-Host "  PostgreSQL:  localhost:5432"
        Write-Host "  Prometheus:  http://localhost:9090"
        Write-Host "  Grafana:     http://localhost:3000 (admin/admin)"
        Write-Host "  Jaeger:      http://localhost:16686"
        Write-Host ""
        
        # Wait for services
        Write-Info "Waiting for services to be ready..."
        Start-Sleep -Seconds 5
        
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            docker-compose ps
        } else {
            docker compose ps
        }
    } catch {
        Write-Error "Failed to start services: $_"
    }
}

# Stop services
function Stop-Services {
    param([string]$ServiceName = "")
    
    Write-Header "Stopping Services"
    
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            $cmd = "docker-compose"
            if ($RemoveVolumes) {
                & $cmd down -v $ServiceName
            } else {
                & $cmd down $ServiceName
            }
        } else {
            if ($RemoveVolumes) {
                docker compose down -v $ServiceName
            } else {
                docker compose down $ServiceName
            }
        }
        
        Write-Success "Services stopped"
        if ($RemoveVolumes) {
            Write-Success "Volumes removed"
        }
    } catch {
        Write-Error "Failed to stop services: $_"
    }
}

# Show status
function Show-Status {
    Write-Header "Service Status"
    
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            docker-compose ps
        } else {
            docker compose ps
        }
    } catch {
        Write-Error "Failed to get status: $_"
    }
}

# Show logs
function Show-Logs {
    param([string]$ServiceName = "")
    
    Write-Header "Service Logs"
    
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            docker-compose logs -f $ServiceName
        } else {
            docker compose logs -f $ServiceName
        }
    } catch {
        Write-Error "Failed to show logs: $_"
    }
}

# Clean function
function Clean-Environment {
    Write-Header "Cleaning Environment"
    
    Write-Warning "This will stop all containers and optionally remove volumes"
    
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        docker-compose down -v
    } else {
        docker compose down -v
    }
    
    Write-Success "Environment cleaned"
}

# Show help
function Show-Help {
    Write-Header "NYC DOT Toolkit - Deployment Help"
    
    Write-Host @"
USAGE:
    deploy.ps1 [Action] [Options]

ACTIONS:
    setup       Initialize configuration files and environment
    start       Start Docker services
    stop        Stop Docker services
    status      Show current service status
    logs        Show service logs (Ctrl+C to exit)
    clean       Stop services and remove volumes (destructive)
    help        Show this help message

OPTIONS:
    -Service <name>      Specific service to operate on (postgres, api, etc.)
    -RemoveVolumes       Remove volumes when stopping (use with 'stop')
    -Dev                 Development mode (more verbose logging)

EXAMPLES:
    # Initial setup
    .\\deploy.ps1 setup

    # Start all services
    .\\deploy.ps1 start

    # Start only PostgreSQL
    .\\deploy.ps1 start -Service postgres

    # Stop services and remove volumes
    .\\deploy.ps1 stop -RemoveVolumes

    # View logs
    .\\deploy.ps1 logs

    # Clean everything
    .\\deploy.ps1 clean

FIRST TIME SETUP:
    1. Run: .\\deploy.ps1 setup
    2. Edit .env.socrata with your credentials
    3. Run: .\\deploy.ps1 start
    4. Access services at the URLs printed above

TROUBLESHOOTING:
    - If Docker won't start: Ensure Docker Desktop is running
    - If ports conflict: Edit docker-compose.yml to change port mappings
    - For detailed logs: Run .\\deploy.ps1 logs -Service postgres
"@
}

# Main routing
switch ($Action) {
    "setup" {
        Invoke-Setup
    }
    "start" {
        Start-Services -ServiceName $Service
    }
    "stop" {
        Stop-Services -ServiceName $Service
    }
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs -ServiceName $Service
    }
    "clean" {
        Clean-Environment
    }
    "help" {
        Show-Help
    }
    default {
        Write-Error "Unknown action: $Action"
        Show-Help
    }
}
