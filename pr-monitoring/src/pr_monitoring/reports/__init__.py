"""
Report generation for PR monitoring system
"""
import csv
import json
import logging
from datetime import date
from typing import List, Dict
from io import StringIO

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate various types of reports from analyzed data"""
    
    @staticmethod
    def generate_daily_activity_csv(daily_activities: List[Dict]) -> str:
        """Generate CSV report of daily activities"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'login', 'email', 'name', 'date', 'state', 
            'count_in_time', 'count_outside_time'
        ])
        
        # Data rows
        for activity in daily_activities:
            writer.writerow([
                activity['login'],
                activity['email'] or '',
                activity['name'] or '',
                activity['date'],
                activity['state'],
                activity['count_in_time'],
                activity['count_outside_time']
            ])
        
        return output.getvalue()
    
    @staticmethod
    def generate_detailed_prs_csv(daily_activities: List[Dict]) -> str:
        """Generate detailed CSV report with PR times and titles"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'login', 'name', 'date', 'pr_title', 'repository', 
            'created_time_lima', 'created_time_utc', 'is_in_working_hours'
        ])
        
        # Data rows - flatten PRs from all activities
        for activity in daily_activities:
            if 'prs' in activity and activity['prs']:
                for pr in activity['prs']:
                    writer.writerow([
                        activity['login'],
                        activity.get('name', ''),
                        activity['date'],
                        pr.get('title', ''),
                        pr.get('repository', ''),
                        pr.get('created_at_lima', ''),
                        pr.get('created_at_utc', ''),
                        pr.get('is_in_working_hours', False)
                    ])
            else:
                # Include users with no PRs
                writer.writerow([
                    activity['login'],
                    activity.get('name', ''),
                    activity['date'],
                    'No PRs',
                    '',
                    '',
                    '',
                    False
                ])
        
        return output.getvalue()

    @staticmethod
    def generate_summary_csv(summaries: List[Dict]) -> str:
        """Generate CSV report of user summaries"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'login', 'email', 'name',
            'total_days_in_time', 'total_days_outside_time', 'total_days_not_sent',
            'total_prs_in_time', 'total_prs_outside_time', 'generated_at'
        ])
        
        # Data rows
        for summary in summaries:
            writer.writerow([
                summary['login'],
                summary['email'] or '',
                summary['name'] or '',
                summary['total_days_in_time'],
                summary['total_days_outside_time'], 
                summary['total_days_not_sent'],
                summary['total_prs_in_time'],
                summary['total_prs_outside_time'],
                summary.get('generated_at', '')
            ])
        
        return output.getvalue()
    
    @staticmethod
    def generate_user_metadata_csv(users: List[Dict], included_count: int, 
                                  excluded_count: int, filter_info: Dict) -> str:
        """Generate CSV report of user metadata and filtering results"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Summary information
        writer.writerow(['# User Filtering Summary'])
        writer.writerow(['Total users fetched', len(users)])
        writer.writerow(['Included users', included_count])
        writer.writerow(['Excluded users', excluded_count])
        writer.writerow(['Exclusion list', ', '.join(filter_info.get('exclusion_list', []))])
        writer.writerow(['Email filter', filter_info.get('email_prefix_filter', 'None')])
        writer.writerow([])
        
        # User details
        writer.writerow(['login', 'email', 'name', 'included'])
        for user in users:
            writer.writerow([
                user['login'],
                user['email'] or '',
                user['name'] or '',
                'Yes' if user.get('included', True) else 'No'
            ])
        
        return output.getvalue()
    
    @staticmethod
    def generate_json_report(data: Dict) -> str:
        """Generate JSON report with all data"""
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def save_report_to_file(content: str, filename: str):
        """Save report content to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Report saved to {filename}")
    
    @staticmethod
    def print_summary_to_console(summaries: List[Dict], start_date: date, end_date: date):
        """Print summary statistics to console"""
        print(f"\n{'='*60}")
        print(f"PR ACTIVITY SUMMARY ({start_date} to {end_date})")
        print(f"{'='*60}")
        
        if not summaries:
            print("No data available for the specified period.")
            return
        
        print(f"{'User':<25} {'In Time':<8} {'Outside':<8} {'Not Sent':<8} {'Total PRs':<10}")
        print("-" * 60)
        
        total_in_time = 0
        total_outside = 0 
        total_not_sent = 0
        total_prs = 0
        
        for summary in summaries:
            login = summary['login'][:24]  # Truncate long usernames
            days_in_time = summary['total_days_in_time']
            days_outside = summary['total_days_outside_time']
            days_not_sent = summary['total_days_not_sent']
            user_total_prs = summary['total_prs_in_time'] + summary['total_prs_outside_time']
            
            print(f"{login:<25} {days_in_time:<8} {days_outside:<8} {days_not_sent:<8} {user_total_prs:<10}")
            
            total_in_time += days_in_time
            total_outside += days_outside
            total_not_sent += days_not_sent
            total_prs += user_total_prs
        
        print("-" * 60)
        print(f"{'TOTAL':<25} {total_in_time:<8} {total_outside:<8} {total_not_sent:<8} {total_prs:<10}")
        
        # Calculate percentages
        total_user_days = len(summaries) * (end_date - start_date).days if summaries else 1
        in_time_pct = (total_in_time / total_user_days * 100) if total_user_days > 0 else 0
        
        print(f"\nStatistics:")
        print(f"- Users analyzed: {len(summaries)}")
        print(f"- Days with in-time activity: {in_time_pct:.1f}%")
        print(f"- Total PRs created: {total_prs}")
        print(f"- Average PRs per user: {total_prs / len(summaries):.1f}" if summaries else "0")