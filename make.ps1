param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    [string]$File = ""
)

# Colors for output
function Write-Success { param($Text) Write-Host $Text -ForegroundColor Green }
function Write-Error { param($Text) Write-Host $Text -ForegroundColor Red }
function Write-Info { param($Text) Write-Host $Text -ForegroundColor Cyan }
function Write-Warning { param($Text) Write-Host $Text -ForegroundColor Yellow }

# Check if virtual environment is activated
function Test-VirtualEnv {
    if (-not $env:VIRTUAL_ENV) {
        Write-Error "Virtual environment not activated!"
        Write-Info "Please run: venv\Scripts\activate"
        exit 1
    }
}

# Function definitions
function Show-Help {
    Write-Host "Vending Hive Development Commands" -ForegroundColor Magenta
    Write-Host "=================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "Setup Commands:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 setup-venv       Create virtual environment"
    Write-Host "  .\make.ps1 install          Install production dependencies"
    Write-Host "  .\make.ps1 install-dev      Install development dependencies"
    Write-Host "  .\make.ps1 setup-env        Copy .env.example to .env"
    Write-Host ""
    Write-Host "Development Commands:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 runserver        Run development server"
    Write-Host "  .\make.ps1 shell            Open Django shell"
    Write-Host "  .\make.ps1 dbshell          Open database shell"
    Write-Host ""
    Write-Host "Database Commands:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 makemigrations   Create database migrations"
    Write-Host "  .\make.ps1 migrate          Apply database migrations"
    Write-Host "  .\make.ps1 reset-db         Reset database (WARNING: destroys data)"
    Write-Host "  .\make.ps1 backup-db        Backup database to JSON file"
    Write-Host "  .\make.ps1 restore-db       Restore database from backup file"
    Write-Host ""
    Write-Host "Testing Commands:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 test             Run all tests"
    Write-Host "  .\make.ps1 test-app         Run tests for specific app"
    Write-Host "  .\make.ps1 coverage         Run tests with coverage report"
    Write-Host ""
    Write-Host "Code Quality Commands:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 format           Format code with black and isort"
    Write-Host "  .\make.ps1 lint             Lint code with flake8"
    Write-Host "  .\make.ps1 check            Run format, lint, and tests"
    Write-Host ""
    Write-Host "Admin Commands:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 superuser        Create superuser"
    Write-Host "  .\make.ps1 collectstatic    Collect static files"
    Write-Host "  .\make.ps1 clean            Clean pyc files and cache"
    Write-Host ""
    Write-Host "Docker Commands:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 docker-build     Build Docker image"
    Write-Host "  .\make.ps1 docker-up        Start Docker containers"
    Write-Host "  .\make.ps1 docker-down      Stop Docker containers"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\make.ps1 test-app accounts"
    Write-Host "  .\make.ps1 restore-db -File backup_20250603.json"
}

function Setup-VirtualEnv {
    Write-Info "Creating virtual environment..."
    if (Test-Path "venv") {
        Write-Warning "Virtual environment already exists!"
        return
    }
    python -m venv venv
    Write-Success "Virtual environment created!"
    Write-Info "Activate it with: venv\Scripts\activate"
}

function Install-Deps {
    Test-VirtualEnv
    Write-Info "Installing production dependencies..."
    pip install -r requirements/base.txt
    Write-Success "Production dependencies installed!"
}

function Install-DevDeps {
    Test-VirtualEnv
    Write-Info "Installing development dependencies..."
    pip install -r requirements/development.txt
    Write-Success "Development dependencies installed!"
}

function Setup-Environment {
    if (Test-Path ".env") {
        Write-Warning ".env file already exists!"
        $overwrite = Read-Host "Overwrite? (y/N)"
        if ($overwrite -ne "y" -and $overwrite -ne "Y") {
            return
        }
    }
    Copy-Item ".env.example" ".env"
    Write-Success ".env file created!"
    Write-Info "Please edit .env file with your configuration"
}

function Run-Server {
    Test-VirtualEnv
    Write-Info "Starting Django development server..."
    python manage.py runserver
}

function Open-Shell {
    Test-VirtualEnv
    Write-Info "Opening Django shell..."
    python manage.py shell
}

function Open-DbShell {
    Test-VirtualEnv
    Write-Info "Opening database shell..."
    python manage.py dbshell
}

function Make-Migrations {
    Test-VirtualEnv
    Write-Info "Creating database migrations..."
    python manage.py makemigrations
    Write-Success "Migrations created!"
}

function Apply-Migrations {
    Test-VirtualEnv
    Write-Info "Applying database migrations..."
    python manage.py migrate
    Write-Success "Migrations applied!"
}

function Reset-Database {
    Test-VirtualEnv
    Write-Warning "This will destroy all data in the database!"
    $confirm = Read-Host "Are you sure? Type 'yes' to continue"
    if ($confirm -ne "yes") {
        Write-Info "Operation cancelled."
        return
    }
    
    Write-Info "Resetting database..."
    # Remove migration files except __init__.py
    Get-ChildItem -Path "apps\*\migrations\*.py" -Exclude "__init__.py" | Remove-Item -Force
    
    # Reset migrations
    python manage.py makemigrations
    python manage.py migrate
    Write-Success "Database reset complete!"
}

function Backup-Database {
    Test-VirtualEnv
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "backup_$timestamp.json"
    Write-Info "Backing up database to $filename..."
    python manage.py dumpdata > $filename
    Write-Success "Database backed up to $filename"
}

function Restore-Database {
    param([string]$BackupFile)
    Test-VirtualEnv
    
    if (-not $BackupFile) {
        $BackupFile = $File
    }
    
    if (-not $BackupFile) {
        Write-Error "Please specify backup file: .\make.ps1 restore-db -File backup.json"
        return
    }
    
    if (-not (Test-Path $BackupFile)) {
        Write-Error "Backup file '$BackupFile' not found!"
        return
    }
    
    Write-Info "Restoring database from $BackupFile..."
    python manage.py loaddata $BackupFile
    Write-Success "Database restored from $BackupFile"
}

function Run-Tests {
    Test-VirtualEnv
    Write-Info "Running tests..."
    python -m pytest -v
}

function Run-AppTests {
    param([string]$AppName)
    Test-VirtualEnv
    
    if (-not $AppName) {
        Write-Error "Please specify app name: .\make.ps1 test-app accounts"
        return
    }
    
    Write-Info "Running tests for app: $AppName..."
    python -m pytest apps/$AppName/tests.py -v
}

function Run-Coverage {
    Test-VirtualEnv
    Write-Info "Running tests with coverage..."
    python -m pytest --cov=apps --cov-report=html --cov-report=term
    Write-Success "Coverage report generated in htmlcov/"
}

function Format-Code {
    Test-VirtualEnv
    Write-Info "Formatting code with black and isort..."
    python -m black .
    python -m isort .
    Write-Success "Code formatted!"
}

function Lint-Code {
    Test-VirtualEnv
    Write-Info "Linting code with flake8..."
    python -m flake8 .
}

function Run-AllChecks {
    Write-Info "Running all checks..."
    Format-Code
    Lint-Code
    Run-Tests
    Write-Success "All checks completed!"
}

function Create-Superuser {
    Test-VirtualEnv
    Write-Info "Creating superuser..."
    python manage.py createsuperuser
}

function Collect-Static {
    Test-VirtualEnv
    Write-Info "Collecting static files..."
    python manage.py collectstatic --noinput
    Write-Success "Static files collected!"
}

function Clean-Project {
    Write-Info "Cleaning project files..."
    
    # Remove __pycache__ directories
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object {
        Remove-Item -Path $_ -Recurse -Force
        Write-Host "Removed: $_"
    }
    
    # Remove .pyc files
    Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force
    
    # Remove pytest cache
    if (Test-Path ".pytest_cache") {
        Remove-Item -Path ".pytest_cache" -Recurse -Force
    }
    
    # Remove coverage files
    if (Test-Path "htmlcov") {
        Remove-Item -Path "htmlcov" -Recurse -Force
    }
    if (Test-Path ".coverage") {
        Remove-Item -Path ".coverage" -Force
    }
    
    Write-Success "Project cleaned!"
}

function Docker-Build {
    Write-Info "Building Docker image..."
    docker build -t vending-hive .
    Write-Success "Docker image built!"
}

function Docker-Up {
    Write-Info "Starting Docker containers..."
    docker-compose up -d
    Write-Success "Docker containers started!"
}

function Docker-Down {
    Write-Info "Stopping Docker containers..."
    docker-compose down
    Write-Success "Docker containers stopped!"
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "setup-venv" { Setup-VirtualEnv }
    "install" { Install-Deps }
    "install-dev" { Install-DevDeps }
    "setup-env" { Setup-Environment }
    "runserver" { Run-Server }
    "shell" { Open-Shell }
    "dbshell" { Open-DbShell }
    "makemigrations" { Make-Migrations }
    "migrate" { Apply-Migrations }
    "reset-db" { Reset-Database }
    "backup-db" { Backup-Database }
    "restore-db" { Restore-Database -BackupFile $File }
    "test" { Run-Tests }
    "test-app" { Run-AppTests -AppName $File }
    "coverage" { Run-Coverage }
    "format" { Format-Code }
    "lint" { Lint-Code }
    "check" { Run-AllChecks }
    "superuser" { Create-Superuser }
    "collectstatic" { Collect-Static }
    "clean" { Clean-Project }
    "docker-build" { Docker-Build }
    "docker-up" { Docker-Up }
    "docker-down" { Docker-Down }
    default {
        Write-Error "Unknown command: $Command"
        Write-Info "Run '.\make.ps1 help' to see available commands"
    }
}