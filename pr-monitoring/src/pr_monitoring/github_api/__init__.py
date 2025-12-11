"""
GitHub API client for fetching users and pull requests
"""
import requests
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
import pytz

logger = logging.getLogger(__name__)

class GitHubAPIClient:
    """GitHub API client with GraphQL support"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'PR-Monitoring-System/1.0.0'
        })
    
    def _make_graphql_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Make GraphQL request to GitHub API"""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        response = self.session.post(f"{self.base_url}/graphql", json=payload)
        
        if response.status_code != 200:
            raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
        
        data = response.json()
        
        if 'errors' in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        return data['data']
    
    def get_team_members(self, organization: str, team: str) -> List[Dict]:
        """Get all members of a GitHub team"""
        query = """
        query($org: String!, $team: String!, $cursor: String) {
            organization(login: $org) {
                team(slug: $team) {
                    members(first: 100, after: $cursor) {
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                        nodes {
                            login
                            name
                            email
                        }
                    }
                }
            }
        }
        """
        
        members = []
        cursor = None
        
        while True:
            variables = {"org": organization, "team": team, "cursor": cursor}
            data = self._make_graphql_request(query, variables)
            
            if not data['organization'] or not data['organization']['team']:
                raise Exception(f"Team '{team}' not found in organization '{organization}'")
            
            team_data = data['organization']['team']['members']
            members.extend(team_data['nodes'])
            
            if not team_data['pageInfo']['hasNextPage']:
                break
                
            cursor = team_data['pageInfo']['endCursor']
        
        logger.info(f"Fetched {len(members)} team members")
        return members
    
    def get_user_pull_requests(self, username: str, start_date: date, end_date: date) -> List[Dict]:
        """Get pull requests for a user within date range"""
        # Convert dates to ISO format for GitHub API
        since = datetime.combine(start_date, datetime.min.time()).isoformat() + "Z"
        until = datetime.combine(end_date, datetime.max.time()).isoformat() + "Z"
        
        query = """
        query($username: String!, $cursor: String) {
            user(login: $username) {
                pullRequests(first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        title
                        createdAt
                        repository {
                            nameWithOwner
                        }
                    }
                }
            }
        }
        """
        
        pull_requests = []
        cursor = None
        
        while True:
            variables = {
                "username": username,
                "cursor": cursor
            }
            
            try:
                data = self._make_graphql_request(query, variables)
            except Exception as e:
                logger.warning(f"Failed to fetch PRs for {username}: {e}")
                break
            
            if not data['user']:
                logger.warning(f"User '{username}' not found")
                break
            
            pr_data = data['user']['pullRequests']
            
            # Filter PRs by date range (API may return slightly outside range)
            for pr in pr_data['nodes']:
                created_at = datetime.fromisoformat(pr['createdAt'].replace('Z', '+00:00'))
                pr_date = created_at.date()
                
                if start_date <= pr_date <= end_date:
                    pull_requests.append({
                        'id': pr['id'],
                        'title': pr['title'],
                        'created_at_utc': created_at.replace(tzinfo=pytz.UTC),
                        'repository': pr['repository']['nameWithOwner']
                    })
            
            if not pr_data['pageInfo']['hasNextPage']:
                break
                
            cursor = pr_data['pageInfo']['endCursor']
        
        logger.debug(f"Fetched {len(pull_requests)} PRs for {username}")
        return pull_requests