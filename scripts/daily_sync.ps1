# NYC DOT Socrata Toolkit - Daily Sync Script
# Scheduled to run every day at 11:59 PM

$repoPath = "C:\Users\ryudk\nyc_data"
$logPath = "$repoPath\data\logs\daily_sync.log"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Ensure log directory exists
if (-not (Test-Path "$repoPath\data\logs")) {
    New-Item -ItemType Directory -Path "$repoPath\data\logs" -Force | Out-Null
}

Add-Content -Path $logPath -Value "`n--- Sync Started at $date ---"

Set-Location -Path $repoPath

# 1. Fetch updates
Add-Content -Path $logPath -Value "[INFO] Fetching origin..."
git fetch origin main >> $logPath 2>&1

# 2. Check current branch
$branch = git rev-parse --abbrev-ref HEAD
Add-Content -Path $logPath -Value "[INFO] Current branch: $branch"

# 3. Pull with rebase and autostash to handle uncommitted changes safely
Add-Content -Path $logPath -Value "[INFO] Pulling main with --rebase --autostash..."
git pull origin main --rebase --autostash >> $logPath 2>&1

$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Add-Content -Path $logPath -Value "[ERROR] Pull failed with exit code $exitCode."
    
    # Check if we are in the middle of a rebase
    if ((Test-Path "$repoPath\.git\rebase-merge") -or (Test-Path "$repoPath\.git\rebase-apply")) {
        Add-Content -Path $logPath -Value "[CRITICAL] Rebase conflicts detected. Aborting rebase to keep repo clean."
        git rebase --abort >> $logPath 2>&1
    } else {
        Add-Content -Path $logPath -Value "[ERROR] Sync failed for unknown reasons. Current status:"
        git status >> $logPath 2>&1
    }
} else {
    Add-Content -Path $logPath -Value "[SUCCESS] Repository is up to date."
}

Add-Content -Path $logPath -Value "--- Sync Finished at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ---"
