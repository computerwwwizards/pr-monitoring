"""
Main application for PR Monitoring System
"""
import logging
import argparse
from datetime import datetime, date, timedelta
from typing import List, Dict

from pr_monitoring.config import Config
from pr_monitoring.database import Database
from pr_monitoring.github_api import GitHubAPIClient
from pr_monitoring.analysis import PRAnalyzer, UserFilter, ActivityState
from pr_monitoring.reports import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PRMonitoringSystem:
    """Main PR Monitoring System"""
    
    def __init__(self):
        # Validate configuration
        errors = Config.validate()
        if errors:
            for error in errors:
                logger.error(error)
            raise ValueError("Configuration validation failed")
        
        self.config = Config
        self.database = Database(Config.DATABASE_PATH)
        self.github_client = GitHubAPIClient(Config.GITHUB_TOKEN)
        self.analyzer = PRAnalyzer(
            Config.get_timezone(), 
            Config.WORK_START_HOUR, 
            Config.WORK_END_HOUR
        )
        self.user_filter = UserFilter(Config.EXCLUSION_LIST, Config.EMAIL_PREFIX_FILTER)
        self.report_generator = ReportGenerator()
        
    def fetch_and_store_users(self) -> Dict:
        """Fetch users from GitHub and store in database"""
        logger.info("Fetching team members from GitHub...")
        
        # Fetch users from GitHub
        raw_users = self.github_client.get_team_members(
            self.config.GITHUB_ORGANIZATION,
            self.config.GITHUB_TEAM
        )
        
        included_count = 0
        excluded_count = 0
        
        # Filter and store users
        for user in raw_users:
            included = self.user_filter.should_include_user(user)
            
            self.database.upsert_user(
                login=user['login'],
                email=user['email'],
                name=user['name'],
                included=included
            )
            
            if included:
                included_count += 1
            else:
                excluded_count += 1
        
        logger.info(f"Processed {len(raw_users)} users: {included_count} included, {excluded_count} excluded")
        
        return {
            'total_fetched': len(raw_users),
            'included': included_count,
            'excluded': excluded_count,
            'exclusion_list': self.config.EXCLUSION_LIST,
            'email_prefix_filter': self.config.EMAIL_PREFIX_FILTER
        }
    
    def fetch_and_cache_pull_requests(self, start_date: date, end_date: date):
        """Fetch pull requests with intelligent caching"""
        users = self.database.get_users(included_only=True)
        today = datetime.now(self.config.get_timezone()).date()
        
        logger.info(f"Fetching PRs for {len(users)} users from {start_date} to {end_date}")
        
        for user in users:
            logger.debug(f"Processing user: {user['login']}")
            
            # Get cached dates for this user
            cached_dates = set(self.database.get_cached_dates_for_user(user['id']))
            
            # Determine which dates need fetching
            dates_to_fetch = []
            current_date = start_date
            
            while current_date <= end_date:
                # Always fetch today's data, only fetch historical if not cached
                if current_date == today or current_date not in cached_dates:
                    dates_to_fetch.append(current_date)
                current_date += timedelta(days=1)
            
            if not dates_to_fetch:
                logger.debug(f"All data cached for {user['login']}")
                continue
            
            # Fetch PRs for needed dates
            fetch_start = min(dates_to_fetch)
            fetch_end = max(dates_to_fetch)
            
            logger.debug(f"Fetching PRs for {user['login']} from {fetch_start} to {fetch_end}")
            
            try:
                raw_prs = self.github_client.get_user_pull_requests(
                    user['login'], fetch_start, fetch_end
                )
                
                # Convert and store PRs
                processed_prs = []
                for pr in raw_prs:
                    # Convert to local timezone
                    local_dt = self.analyzer.convert_to_local_timezone(pr['created_at_utc'])
                    local_date = local_dt.date()
                    
                    processed_prs.append({
                        'pr_id': pr['id'],
                        'user_id': user['id'],
                        'repository': pr['repository'],
                        'title': pr['title'],
                        'timestamp_utc': pr['created_at_utc'].isoformat(),
                        'timestamp_local': local_dt.isoformat(),
                        'date_local': local_date
                    })
                
                if processed_prs:
                    self.database.insert_pull_requests(processed_prs)
                
                logger.debug(f"Cached {len(processed_prs)} PRs for {user['login']}")
                
            except Exception as e:
                logger.error(f"Failed to fetch PRs for {user['login']}: {e}")
                continue
    
    def analyze_and_store_daily_activity(self, start_date: date, end_date: date):
        """Analyze daily activity and store results"""
        users = self.database.get_users(included_only=True)
        
        logger.info(f"Analyzing daily activity for {len(users)} users")
        
        for user in users:
            # Get PRs for user in date range
            user_prs = self.database.get_pull_requests_for_date_range(
                user['id'], start_date, end_date
            )
            
            # Analyze daily activity
            daily_activities = self.analyzer.analyze_user_activity(
                user_prs, start_date, end_date
            )
            
            # Store daily activity results
            for activity in daily_activities:
                self.database.upsert_daily_activity(
                    user['id'],
                    activity['date'],
                    activity['state'],
                    activity['count_in_time'],
                    activity['count_outside_time']
                )
            
            # Generate and store summary
            summary = self.analyzer.generate_user_summary(daily_activities)
            self.database.upsert_summary(user['id'], start_date, end_date, summary)
        
        logger.info("Daily activity analysis completed")
    
    def generate_reports(self, start_date: date, end_date: date, output_prefix: str = "pr_report"):
        """Generate all reports"""
        logger.info("Generating reports...")
        
        # Get data from database
        daily_activities = self.database.get_daily_activity(start_date, end_date)
        summaries = self.database.get_summaries(start_date, end_date)
        users = self.database.get_users(included_only=False)
        
        # Get detailed activity data with PR information
        users_included = self.database.get_users(included_only=True)
        detailed_activities = []
        
        for user in users_included:
            user_prs = self.database.get_pull_requests_for_date_range(
                user['id'], start_date, end_date
            )
            user_daily_activities = self.analyzer.analyze_user_activity(
                user_prs, start_date, end_date
            )
            
            # Add user info to activities
            for activity in user_daily_activities:
                activity.update({
                    'login': user['login'],
                    'name': user['name'],
                    'email': user['email']
                })
                detailed_activities.append(activity)
        
        # Generate reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Daily activity report
        daily_csv = self.report_generator.generate_daily_activity_csv(daily_activities)
        self.report_generator.save_report_to_file(
            daily_csv, f"{output_prefix}_daily_{timestamp}.csv"
        )
        
        # Detailed PRs report with timestamps
        detailed_csv = self.report_generator.generate_detailed_prs_csv(detailed_activities)
        self.report_generator.save_report_to_file(
            detailed_csv, f"{output_prefix}_detailed_{timestamp}.csv"
        )
        
        # Summary report
        summary_csv = self.report_generator.generate_summary_csv(summaries)
        self.report_generator.save_report_to_file(
            summary_csv, f"{output_prefix}_summary_{timestamp}.csv"
        )
        
        # User metadata report
        filter_info = {
            'exclusion_list': self.config.EXCLUSION_LIST,
            'email_prefix_filter': self.config.EMAIL_PREFIX_FILTER
        }
        included_users = [u for u in users if u.get('included', True)]
        excluded_users = [u for u in users if not u.get('included', True)]
        
        metadata_csv = self.report_generator.generate_user_metadata_csv(
            users, len(included_users), len(excluded_users), filter_info
        )
        self.report_generator.save_report_to_file(
            metadata_csv, f"{output_prefix}_users_{timestamp}.csv"
        )
        
        # JSON report with all data
        json_data = {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'config': {
                'timezone': self.config.PROJECT_TIMEZONE,
                'working_hours': f"{self.config.WORK_START_HOUR}:00-{self.config.WORK_END_HOUR}:00"
            },
            'daily_activities': daily_activities,
            'summaries': summaries,
            'users': users,
            'generated_at': datetime.now().isoformat()
        }
        
        json_report = self.report_generator.generate_json_report(json_data)
        self.report_generator.save_report_to_file(
            json_report, f"{output_prefix}_full_{timestamp}.json"
        )
        
        # Print summary to console
        self.report_generator.print_summary_to_console(summaries, start_date, end_date)
        
        logger.info("All reports generated successfully")
    
    def run_full_analysis(self, start_date: date, end_date: date, output_prefix: str = "pr_report"):
        """Run complete analysis pipeline"""
        logger.info(f"Starting PR monitoring analysis for {start_date} to {end_date}")
        
        # Step 1: Fetch and store users
        user_stats = self.fetch_and_store_users()
        
        # Step 2: Fetch and cache pull requests
        self.fetch_and_cache_pull_requests(start_date, end_date)
        
        # Step 3: Analyze daily activity
        self.analyze_and_store_daily_activity(start_date, end_date)
        
        # Step 4: Generate reports
        self.generate_reports(start_date, end_date, output_prefix)
        
        logger.info("PR monitoring analysis completed successfully")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="PR Monitoring System")
    parser.add_argument(
        "--start-date", 
        type=str, 
        default=(date.today() - timedelta(days=7)).isoformat(),
        help="Start date (YYYY-MM-DD), default: 7 days ago"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=date.today().isoformat(), 
        help="End date (YYYY-MM-DD), default: today"
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="pr_report",
        help="Output file prefix, default: pr_report"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse dates
    try:
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return 1
    
    if start_date > end_date:
        logger.error("Start date must be before or equal to end date")
        return 1
    
    try:
        # Initialize and run system
        system = PRMonitoringSystem()
        system.run_full_analysis(start_date, end_date, args.output_prefix)
        return 0
        
    except Exception as e:
        logger.error(f"System error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())