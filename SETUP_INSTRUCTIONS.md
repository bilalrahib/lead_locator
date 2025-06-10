# Vending Hive - Project Setup Instructions

## Prerequisites

1. **Python 3.11+** - Download from [python.org](https://python.org)
2. **PostgreSQL 15+** - Download from [postgresql.org](https://postgresql.org)
3. **Git** - Download from [git-scm.com](https://git-scm.com)

## Initial Setup

### 1. Create and Activate Virtual Environment

```powershell
# Navigate to project directory
cd vending_hive

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install development dependencies
.\make.ps1 install-dev

# Or manually:
pip install -r requirements/development.txt

# Copy environment template
.\make.ps1 setup-env

# Edit .env file with your configuration
# At minimum, configure:
# - SECRET_KEY (generate a random string)
# - Database settings
# - Any API keys you have