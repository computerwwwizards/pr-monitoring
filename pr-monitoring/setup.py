#!/usr/bin/env python3
"""
PR Monitoring System - Clean Installation Script
"""
import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.10+"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required")
        print(f"📍 Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def check_uv_installed():
    """Check if uv is installed"""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        print(f"✅ uv version: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("❌ uv not found")
        print("💡 Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

def setup_environment():
    """Setup environment and dependencies"""
    if not Path('.env').exists():
        if Path('.env.example').exists():
            print("📋 Creating .env from template...")
            subprocess.run(['cp', '.env.example', '.env'])
            print("⚠️  Please edit .env with your GitHub credentials")
        else:
            print("❌ No .env.example found")
            return False
    
    print("📦 Installing dependencies...")
    try:
        subprocess.run(['uv', 'sync'], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def validate_config():
    """Validate configuration"""
    try:
        # Add src to path temporarily
        sys.path.insert(0, 'src')
        from pr_monitoring.config import Config
        
        return Config.validate_config() if hasattr(Config, 'validate_config') else True
    except Exception as e:
        print(f"⚠️  Configuration validation failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 PR Monitoring System Setup")
    print("=" * 40)
    
    if not check_python_version():
        sys.exit(1)
    
    if not check_uv_installed():
        print("💡 Alternatively, use pip:")
        print("   python -m venv .venv")
        print("   source .venv/bin/activate")
        print("   pip install requests python-dotenv pytz")
        sys.exit(1)
    
    if not setup_environment():
        sys.exit(1)
    
    print("\n✅ Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Edit .env with your GitHub configuration")
    print("2. Test with: uv run python -c \"import sys; sys.path.insert(0, 'src'); from pr_monitoring import main; main()\"")
    print("\n📖 See README.md for detailed usage instructions")

if __name__ == "__main__":
    main()