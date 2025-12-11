"""
Database schema and operations for PR Monitoring System
"""
import sqlite3
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    """SQLite database operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE NOT NULL,
                    email TEXT,
                    name TEXT,
                    included_flag BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Pull requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pull_requests (
                    pr_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    repository TEXT NOT NULL,
                    title TEXT,
                    timestamp_utc TIMESTAMP NOT NULL,
                    timestamp_local TIMESTAMP NOT NULL,
                    date_local DATE NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Daily activity table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_activity (
                    user_id INTEGER NOT NULL,
                    date_local DATE NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('Not Sent', 'Sent In Time', 'Sent Outside Time')),
                    count_in_time INTEGER NOT NULL DEFAULT 0,
                    count_outside_time INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, date_local),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Summary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    user_id INTEGER NOT NULL,
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    total_days_in_time INTEGER NOT NULL DEFAULT 0,
                    total_days_outside_time INTEGER NOT NULL DEFAULT 0,
                    total_days_not_sent INTEGER NOT NULL DEFAULT 0,
                    total_prs_in_time INTEGER NOT NULL DEFAULT 0,
                    total_prs_outside_time INTEGER NOT NULL DEFAULT 0,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, period_start, period_end),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Cache metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_user_date ON pull_requests (user_id, date_local)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_date_local ON pull_requests (date_local)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_date ON daily_activity (date_local)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def upsert_user(self, login: str, email: Optional[str] = None, 
                   name: Optional[str] = None, included: bool = True) -> int:
        """Insert or update user and return user ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (login, email, name, included_flag)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(login) DO UPDATE SET
                    email = COALESCE(excluded.email, email),
                    name = COALESCE(excluded.name, name),
                    included_flag = excluded.included_flag
            """, (login, email, name, included))
            
            cursor.execute("SELECT id FROM users WHERE login = ?", (login,))
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            return user_id
    
    def get_users(self, included_only: bool = True) -> List[Dict]:
        """Get users from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT id, login, email, name FROM users"
            if included_only:
                query += " WHERE included_flag = 1"
            
            cursor.execute(query)
            
            return [
                {"id": row[0], "login": row[1], "email": row[2], "name": row[3]}
                for row in cursor.fetchall()
            ]
    
    def insert_pull_requests(self, prs: List[Dict]):
        """Bulk insert pull requests"""
        if not prs:
            return
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.executemany("""
                INSERT OR REPLACE INTO pull_requests 
                (pr_id, user_id, repository, title, timestamp_utc, timestamp_local, date_local)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                (pr['pr_id'], pr['user_id'], pr['repository'], pr['title'],
                 pr['timestamp_utc'], pr['timestamp_local'], pr['date_local'])
                for pr in prs
            ])
            
            conn.commit()
            logger.info(f"Inserted {len(prs)} pull requests")
    
    def get_cached_dates_for_user(self, user_id: int) -> List[date]:
        """Get list of dates that are already cached for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT date_local 
                FROM pull_requests 
                WHERE user_id = ?
                ORDER BY date_local
            """, (user_id,))
            
            return [datetime.strptime(row[0], '%Y-%m-%d').date() for row in cursor.fetchall()]
    
    def get_pull_requests_for_date_range(self, user_id: int, start_date: date, end_date: date) -> List[Dict]:
        """Get pull requests for user within date range"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pr_id, repository, title, timestamp_utc, timestamp_local, date_local
                FROM pull_requests 
                WHERE user_id = ? AND date_local BETWEEN ? AND ?
                ORDER BY timestamp_local
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            
            return [
                {
                    "pr_id": row[0],
                    "repository": row[1], 
                    "title": row[2],
                    "timestamp_utc": row[3],
                    "timestamp_local": row[4],
                    "date_local": row[5]
                }
                for row in cursor.fetchall()
            ]
    
    def upsert_daily_activity(self, user_id: int, date_local: date, state: str, 
                            count_in_time: int, count_outside_time: int):
        """Insert or update daily activity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO daily_activity (user_id, date_local, state, count_in_time, count_outside_time)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, date_local) DO UPDATE SET
                    state = excluded.state,
                    count_in_time = excluded.count_in_time,
                    count_outside_time = excluded.count_outside_time
            """, (user_id, date_local.isoformat(), state, count_in_time, count_outside_time))
            
            conn.commit()
    
    def get_daily_activity(self, start_date: date, end_date: date) -> List[Dict]:
        """Get daily activity for date range"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.login, u.email, u.name, da.date_local, da.state, 
                       da.count_in_time, da.count_outside_time
                FROM daily_activity da
                JOIN users u ON da.user_id = u.id
                WHERE da.date_local BETWEEN ? AND ?
                ORDER BY u.login, da.date_local
            """, (start_date.isoformat(), end_date.isoformat()))
            
            return [
                {
                    "login": row[0],
                    "email": row[1],
                    "name": row[2],
                    "date": row[3],
                    "state": row[4],
                    "count_in_time": row[5],
                    "count_outside_time": row[6]
                }
                for row in cursor.fetchall()
            ]
    
    def upsert_summary(self, user_id: int, period_start: date, period_end: date, 
                      summary_data: Dict):
        """Insert or update summary data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO summaries (
                    user_id, period_start, period_end, 
                    total_days_in_time, total_days_outside_time, total_days_not_sent,
                    total_prs_in_time, total_prs_outside_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, period_start, period_end) DO UPDATE SET
                    total_days_in_time = excluded.total_days_in_time,
                    total_days_outside_time = excluded.total_days_outside_time,
                    total_days_not_sent = excluded.total_days_not_sent,
                    total_prs_in_time = excluded.total_prs_in_time,
                    total_prs_outside_time = excluded.total_prs_outside_time,
                    generated_at = CURRENT_TIMESTAMP
            """, (
                user_id, period_start.isoformat(), period_end.isoformat(),
                summary_data['total_days_in_time'], summary_data['total_days_outside_time'],
                summary_data['total_days_not_sent'], summary_data['total_prs_in_time'],
                summary_data['total_prs_outside_time']
            ))
            
            conn.commit()
    
    def get_summaries(self, period_start: date, period_end: date) -> List[Dict]:
        """Get summary data for period"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.login, u.email, u.name,
                       s.total_days_in_time, s.total_days_outside_time, s.total_days_not_sent,
                       s.total_prs_in_time, s.total_prs_outside_time, s.generated_at
                FROM summaries s
                JOIN users u ON s.user_id = u.id
                WHERE s.period_start = ? AND s.period_end = ?
                ORDER BY u.login
            """, (period_start.isoformat(), period_end.isoformat()))
            
            return [
                {
                    "login": row[0],
                    "email": row[1],
                    "name": row[2],
                    "total_days_in_time": row[3],
                    "total_days_outside_time": row[4],
                    "total_days_not_sent": row[5],
                    "total_prs_in_time": row[6],
                    "total_prs_outside_time": row[7],
                    "generated_at": row[8]
                }
                for row in cursor.fetchall()
            ]