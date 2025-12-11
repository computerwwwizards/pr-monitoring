"""
Analysis engine for classifying PR activity and generating reports
"""
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Tuple
import pytz

logger = logging.getLogger(__name__)

class ActivityState:
    """PR Activity state constants"""
    NOT_SENT = "Not Sent"
    SENT_IN_TIME = "Sent In Time" 
    SENT_OUTSIDE_TIME = "Sent Outside Time"

class PRAnalyzer:
    """Analyze PR activity and classify by working hours"""
    
    def __init__(self, timezone: pytz.timezone, work_start_hour: int, work_end_hour: int):
        self.timezone = timezone
        self.work_start_hour = work_start_hour
        self.work_end_hour = work_end_hour
        
    def convert_to_local_timezone(self, utc_datetime: datetime) -> datetime:
        """Convert UTC datetime to configured timezone"""
        if utc_datetime.tzinfo is None:
            utc_datetime = pytz.utc.localize(utc_datetime)
        
        return utc_datetime.astimezone(self.timezone)
    
    def is_within_working_hours(self, local_datetime: datetime) -> bool:
        """Check if datetime falls within working hours"""
        hour = local_datetime.hour
        return self.work_start_hour <= hour < self.work_end_hour
    
    def classify_daily_activity(self, prs_for_date: List[Dict]) -> Tuple[str, int, int]:
        """
        Classify PR activity for a single date
        Returns: (state, count_in_time, count_outside_time)
        """
        if not prs_for_date:
            return ActivityState.NOT_SENT, 0, 0
        
        count_in_time = 0
        count_outside_time = 0
        
        for pr in prs_for_date:
            # Convert timestamp to local timezone
            if isinstance(pr['timestamp_local'], str):
                local_dt = datetime.fromisoformat(pr['timestamp_local'])
            else:
                local_dt = pr['timestamp_local']
            
            if self.is_within_working_hours(local_dt):
                count_in_time += 1
            else:
                count_outside_time += 1
        
        # Determine state based on counts
        if count_in_time > 0:
            return ActivityState.SENT_IN_TIME, count_in_time, count_outside_time
        else:
            return ActivityState.SENT_OUTSIDE_TIME, count_in_time, count_outside_time
    
    def analyze_user_activity(self, user_prs: List[Dict], start_date: date, end_date: date) -> List[Dict]:
        """
        Analyze PR activity for a user across a date range
        Returns list of daily activity records
        """
        # Group PRs by date
        prs_by_date = {}
        for pr in user_prs:
            pr_date = datetime.fromisoformat(pr['date_local']).date()
            if pr_date not in prs_by_date:
                prs_by_date[pr_date] = []
            
            # Enrich PR data with formatted times and classification
            local_dt = datetime.fromisoformat(pr['timestamp_local'])
            utc_dt = datetime.fromisoformat(pr['timestamp_utc'])
            is_in_working_hours = self.is_within_working_hours(local_dt)
            
            enriched_pr = {
                **pr,
                'created_at_lima': local_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'created_at_utc': utc_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'is_in_working_hours': is_in_working_hours
            }
            
            prs_by_date[pr_date].append(enriched_pr)
        
        # Analyze each date in range
        daily_activities = []
        current_date = start_date
        
        while current_date <= end_date:
            prs_for_date = prs_by_date.get(current_date, [])
            state, count_in_time, count_outside_time = self.classify_daily_activity(prs_for_date)
            
            daily_activities.append({
                'date': current_date,
                'state': state,
                'count_in_time': count_in_time,
                'count_outside_time': count_outside_time,
                'prs': prs_for_date
            })
            
            current_date += timedelta(days=1)
        
        return daily_activities
    
    def generate_user_summary(self, daily_activities: List[Dict]) -> Dict:
        """Generate summary statistics for a user"""
        total_days_in_time = 0
        total_days_outside_time = 0
        total_days_not_sent = 0
        total_prs_in_time = 0
        total_prs_outside_time = 0
        
        for activity in daily_activities:
            state = activity['state']
            
            if state == ActivityState.SENT_IN_TIME:
                total_days_in_time += 1
            elif state == ActivityState.SENT_OUTSIDE_TIME:
                total_days_outside_time += 1
            elif state == ActivityState.NOT_SENT:
                total_days_not_sent += 1
            
            total_prs_in_time += activity['count_in_time']
            total_prs_outside_time += activity['count_outside_time']
        
        return {
            'total_days_in_time': total_days_in_time,
            'total_days_outside_time': total_days_outside_time, 
            'total_days_not_sent': total_days_not_sent,
            'total_prs_in_time': total_prs_in_time,
            'total_prs_outside_time': total_prs_outside_time,
            'total_days': len(daily_activities),
            'total_prs': total_prs_in_time + total_prs_outside_time
        }

class UserFilter:
    """Filter users based on exclusion lists and email patterns"""
    
    def __init__(self, exclusion_list: List[str], email_prefix_filter: str = ""):
        self.exclusion_list = set(exclusion_list)
        self.email_prefix_filter = email_prefix_filter.strip()
    
    def should_include_user(self, user: Dict) -> bool:
        """Determine if user should be included in analysis"""
        login = user.get('login', '')
        email = user.get('email', '') or ''
        
        # Check exclusion list
        if login in self.exclusion_list:
            return False
        
        # Check email prefix filter (if configured)
        if self.email_prefix_filter and email:
            if not email.endswith(self.email_prefix_filter):
                return False
        
        return True