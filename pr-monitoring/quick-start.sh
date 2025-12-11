#!/bin/bash
# Quick start script for PR Monitoring System

set -e

echo "🚀 PR Monitoring System - Quick Start"
echo "===================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📋 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env with your GitHub credentials before running!"
    echo ""
    echo "Required settings:"
    echo "- GITHUB_TOKEN: Your GitHub personal access token"
    echo "- GITHUB_ORGANIZATION: Your GitHub organization name"
    echo "- GITHUB_TEAM: Your team slug"
    echo ""
    read -p "Press Enter to continue after editing .env..."
fi

# Install dependencies
echo "📦 Installing dependencies..."
if command -v uv >/dev/null 2>&1; then
    uv sync
    echo "✅ Dependencies installed with uv"
else
    echo "⚠️  uv not found, using pip..."
    python -m venv .venv
    source .venv/bin/activate
    pip install requests python-dotenv pytz
    echo "✅ Dependencies installed with pip"
fi

# Test configuration
echo "🔧 Testing configuration..."
if command -v uv >/dev/null 2>&1; then
    uv run python -c "
import sys; sys.path.insert(0, 'src')
from pr_monitoring.config import Config
print(f'✅ Organization: {Config.GITHUB_ORGANIZATION}')
print(f'✅ Team: {Config.GITHUB_TEAM}')
print(f'✅ Timezone: {Config.PROJECT_TIMEZONE}')
print(f'✅ Work hours: {Config.WORK_START_HOUR}:00-{Config.WORK_END_HOUR}:00')
"
else
    python -c "
import sys; sys.path.insert(0, 'src')
from pr_monitoring.config import Config
print(f'✅ Organization: {Config.GITHUB_ORGANIZATION}')
print(f'✅ Team: {Config.GITHUB_TEAM}')
print(f'✅ Timezone: {Config.PROJECT_TIMEZONE}')
print(f'✅ Work hours: {Config.WORK_START_HOUR}:00-{Config.WORK_END_HOUR}:00')
"
fi

echo ""
echo "🎉 Setup complete! Ready to run analysis"
echo ""
echo "💡 Usage examples:"
if command -v uv >/dev/null 2>&1; then
    echo "# Today's analysis:"
    echo "uv run python -c \"import sys; sys.path.insert(0, 'src'); from pr_monitoring import main; main()\""
    echo ""
    echo "# Date range analysis:"
    echo "uv run python -c \"import sys; sys.path.insert(0, 'src'); from pr_monitoring import main; main()\" --start-date 2025-12-01 --end-date 2025-12-11"
else
    echo "# Activate virtual environment first:"
    echo "source .venv/bin/activate"
    echo ""
    echo "# Today's analysis:"
    echo "python -c \"import sys; sys.path.insert(0, 'src'); from pr_monitoring import main; main()\""
fi
echo ""
echo "📖 See README.md for detailed documentation"