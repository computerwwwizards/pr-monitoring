# PR Monitoring System

A comprehensive Pull Request monitoring and reporting system built with Python that tracks team productivity and work patterns.

## 🚀 Features

- **Real-time PR Tracking**: Monitor GitHub PRs across organization teams
- **Timezone-aware Analysis**: Convert UTC timestamps to local working hours
- **Multiple Report Formats**: CSV, JSON with detailed timestamps and statistics
- **Smart Caching**: SQLite database prevents redundant API calls
- **Flexible Configuration**: Customizable working hours and user filtering
- **Detailed Logging**: Comprehensive monitoring and debugging capabilities

## 📋 Requirements

- Python 3.10+
- GitHub Personal Access Token with repository access
- Organization team membership visibility

## 🛠️ Installation

### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <your-repo-url>
cd pr-monitoring-clean

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install requests python-dotenv pytz

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

## ⚙️ Configuration

Edit the `.env` file with your settings:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_ORGANIZATION=your-org-name
GITHUB_TEAM=your-team-slug

# Time Zone Configuration
PROJECT_TIMEZONE=America/Lima

# Working Schedule (24-hour format)
WORK_START_HOUR=0   # Midnight
WORK_END_HOUR=18    # 6 PM

# User Filtering
EXCLUSION_LIST=bot_user,external_user
```

### GitHub Token Setup

1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens
2. Create a new token with these scopes:
   - `read:org` - Read organization membership
   - `repo` - Repository access (if repos are private)
3. For enterprise organizations, ensure SAML authorization is enabled

## 🏃 Usage

### Basic Usage

```bash
# Run analysis for today
uv run python -c "import sys; sys.path.insert(0, 'src'); from pr_monitoring import main; main()"

# Or with traditional Python
python -c "import sys; sys.path.insert(0, 'src'); from pr_monitoring import main; main()"
```

### Advanced Options

```bash
# Specific date range
--start-date 2025-12-01 --end-date 2025-12-11

# Verbose logging
--verbose

# Custom output directory
--output-prefix /path/to/reports/my_report
```

### Complete Example

```bash
uv run python -c "import sys; sys.path.insert(0, 'src'); from pr_monitoring import main; main()" \
  --start-date 2025-12-01 \
  --end-date 2025-12-11 \
  --output-prefix team_reports \
  --verbose
```

## 📊 Output Reports

The system generates multiple report formats:

### 1. Daily Activity Report (`*_daily_*.csv`)
- User-by-user daily status
- In-time vs outside-time PR counts

### 2. **Detailed PR Report (`*_detailed_*.csv`)** ⭐ New!
- Individual PR timestamps
- Exact creation times (local + UTC)
- Working hours classification

### 3. Summary Report (`*_summary_*.csv`)
- Aggregated statistics per user
- Period totals and averages

### 4. User Metadata (`*_users_*.csv`)
- Team member information
- Filtering results

### 5. Complete JSON (`*_full_*.json`)
- All data in structured format
- API integration ready

## 🕒 Working Hours Logic

The system classifies PRs based on local timezone:

- **In Time**: PRs created between `WORK_START_HOUR` and `WORK_END_HOUR`
- **Outside Time**: PRs created outside working hours
- **Not Sent**: Days with no PR activity

Example with default settings (0-18):
- ✅ **Valid**: 12:00 AM - 6:00 PM (local time)
- ❌ **Outside**: 6:01 PM - 11:59 PM (local time)

## 🗄️ Database Schema

SQLite database with tables:
- `users` - Team member information
- `pull_requests` - PR data with timestamps
- `daily_activity` - Daily analysis results
- `summaries` - Period statistics

## 🔧 Architecture

```
src/pr_monitoring/
├── __init__.py          # Main application logic
├── config.py            # Configuration management
├── database/            # SQLite operations
├── github_api/          # GitHub API client
├── analysis/            # Activity classification
└── reports/             # Report generation
```

## 🐛 Troubleshooting

### Common Issues

**403/401 GitHub API Errors**
- Verify token has correct scopes
- Check organization SAML authorization
- Ensure team membership visibility

**Missing PRs**
- Check date range parameters
- Verify timezone configuration
- Review user exclusion list

**Performance Issues**
- Use date ranges instead of full history
- Check GitHub API rate limits
- Monitor database file size

### Debug Mode

```bash
# Enable verbose logging
--verbose

# Check configuration
python -c "from src.pr_monitoring.config import Config; print(f'Timezone: {Config.PROJECT_TIMEZONE}, Hours: {Config.WORK_START_HOUR}-{Config.WORK_END_HOUR}')"
```

## 📝 Development

### Project Structure

- **Modular Design**: Independent components for easy testing
- **Error Handling**: Comprehensive exception management
- **Logging**: Structured logging with timestamps
- **Caching**: Intelligent database caching for performance

### Adding Features

1. **New Report Format**: Extend `reports/__init__.py`
2. **Custom Analysis**: Modify `analysis/__init__.py`
3. **API Extensions**: Update `github_api/__init__.py`

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review GitHub API documentation
- Create an issue with detailed logs