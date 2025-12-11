"""
Example configuration for PR Monitoring System
Copy this to config.py and customize for your organization
"""
import os
from typing import List
import pytz
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration - customize for your organization"""
    
    # GitHub Configuration
    GITHUB_TOKEN: str = os.getenv('GITHUB_TOKEN', '')
    GITHUB_ORGANIZATION: str = os.getenv('GITHUB_ORGANIZATION', '')
    GITHUB_TEAM: str = os.getenv('GITHUB_TEAM', '')
    
    # Time Zone Configuration - adjust for your location
    PROJECT_TIMEZONE: str = os.getenv('PROJECT_TIMEZONE', 'UTC')
    
    # Working Schedule - customize your work hours
    WORK_START_HOUR: int = int(os.getenv('WORK_START_HOUR', '9'))
    WORK_END_HOUR: int = int(os.getenv('WORK_END_HOUR', '17'))
    
    # User Filtering - add users to exclude from reports
    EXCLUSION_LIST: List[str] = [
        item.strip() for item in os.getenv('EXCLUSION_LIST', '').split(',')
        if item.strip()
    ]
    
    # Email filtering (optional)
    EMAIL_PREFIX_FILTER: str = os.getenv('EMAIL_PREFIX_FILTER', '')
    
    # Database Configuration
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'pr_monitoring.db')
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        required_fields = [
            ('GITHUB_TOKEN', cls.GITHUB_TOKEN),
            ('GITHUB_ORGANIZATION', cls.GITHUB_ORGANIZATION),
            ('GITHUB_TEAM', cls.GITHUB_TEAM)
        ]
        
        missing_fields = [name for name, value in required_fields if not value]
        
        if missing_fields:
            print(f"❌ Missing required configuration: {', '.join(missing_fields)}")
            print("💡 Please check your .env file")
            return False
        
        # Validate timezone
        try:
            pytz.timezone(cls.PROJECT_TIMEZONE)
        except pytz.exceptions.UnknownTimeZoneError:
            print(f"❌ Unknown timezone: {cls.PROJECT_TIMEZONE}")
            return False
        
        # Validate work hours
        if not (0 <= cls.WORK_START_HOUR <= 23) or not (0 <= cls.WORK_END_HOUR <= 23):
            print("❌ Work hours must be between 0-23")
            return False
        
        print("✅ Configuration validated successfully")
        return True