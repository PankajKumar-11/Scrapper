import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from pathlib import Path
from src.sources.base import JobPosting

logger = logging.getLogger(__name__)

class DeduplicationAndFreshnessFilter:
    def __init__(self, db_path: str = "data/seen_jobs.db", max_freshness_days: int = 21):
        self.db_path = db_path
        self.max_freshness_days = max_freshness_days
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_id TEXT PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    posted_date TEXT,
                    first_seen_at TEXT
                )
            """)
            conn.commit()

    def is_seen(self, job_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,))
            return cursor.fetchone() is not None

    def mark_seen(self, jobs: List[JobPosting]):
        now_str = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for j in jobs:
                cursor.execute("""
                    INSERT OR IGNORE INTO seen_jobs (job_id, title, company, posted_date, first_seen_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (j.job_id, j.title, j.company, j.posted_date, now_str))
            conn.commit()

    def filter_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        fresh_and_unique: List[JobPosting] = []
        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=self.max_freshness_days)

        for job in jobs:
            # Check 1: Deduplication
            if self.is_seen(job.job_id):
                logger.debug(f"Filtering out duplicate job: {job.job_id} ({job.title})")
                continue

            # Check 2: Freshness
            if not self._is_fresh(job.posted_date, cutoff_date):
                logger.debug(f"Filtering out stale job: {job.job_id} posted on {job.posted_date}")
                continue

            fresh_and_unique.append(job)

        logger.info(f"Filtered {len(jobs)} jobs down to {len(fresh_and_unique)} fresh, unique postings.")
        return fresh_and_unique

    def _is_fresh(self, posted_date_str: str, cutoff_date: datetime) -> bool:
        if not posted_date_str:
            return True  # Assume fresh if unknown
        try:
            # Parse ISO string
            dt_str = posted_date_str.replace("Z", "+00:00")
            posted_dt = datetime.fromisoformat(dt_str)
            if posted_dt.tzinfo is None:
                posted_dt = posted_dt.replace(tzinfo=timezone.utc)
            return posted_dt >= cutoff_date
        except Exception:
            return True  # Fallback to keeping it if date parsing fails
