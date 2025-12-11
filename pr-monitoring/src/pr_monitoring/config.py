"""
Configuration management for PR Monitoring System
"""
import os
from typing import List, Optional
import pytz
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # GitHub Configuration
    GITHUB_TOKEN: str = os.getenv('GITHUB_TOKEN', '')
    GITHUB_ORGANIZATION: str = os.getenv('GITHUB_ORGANIZATION', '')
    GITHUB_TEAM: str = os.getenv('GITHUB_TEAM', '')
    
    # Time Zone Configuration
    PROJECT_TIMEZONE: str = os.getenv('PROJECT_TIMEZONE', 'UTC')
    
    # Working Schedule
    WORK_START_HOUR: int = int(os.getenv('WORK_START_HOUR', '9'))
    WORK_END_HOUR: int = int(os.getenv('WORK_END_HOUR', '18'))
    
    # User Filtering
    EXCLUSION_LIST: List[str] = [
        item.strip() for item in os.getenv('EXCLUSION_LIST', '').split(',')
        if item.strip()
    ]
    EMAIL_PREFIX_FILTER: str = os.getenv('EMAIL_PREFIX_FILTER', '')
    
    # Database
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'pr_monitoring.db')
    
    @classmethod
    def get_timezone(cls) -> pytz.timezone:
        """Get configured timezone object"""
        return pytz.timezone(cls.PROJECT_TIMEZONE)
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not cls.GITHUB_TOKEN:
            errors.append("GITHUB_TOKEN is required")
        
        if not cls.GITHUB_ORGANIZATION:
            errors.append("GITHUB_ORGANIZATION is required")
            
        if not cls.GITHUB_TEAM:
            errors.append("GITHUB_TEAM is required")
        
        try:
            cls.get_timezone()
        except pytz.exceptions.UnknownTimeZoneError:
            errors.append(f"Invalid timezone: {cls.PROJECT_TIMEZONE}")
        
        if cls.WORK_START_HOUR < 0 or cls.WORK_START_HOUR > 23:
            errors.append("WORK_START_HOUR must be between 0 and 23")
            
        if cls.WORK_END_HOUR < 0 or cls.WORK_END_HOUR > 23:
            errors.append("WORK_END_HOUR must be between 0 and 23")
            
        if cls.WORK_START_HOUR >= cls.WORK_END_HOUR:
            errors.append("WORK_START_HOUR must be less than WORK_END_HOUR")
        
        return errors