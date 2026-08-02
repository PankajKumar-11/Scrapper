import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any
from src.sources.base import BaseJobSource, JobPosting

logger = logging.getLogger(__name__)

class AdzunaJobSource(BaseJobSource):
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id: str, app_key: str):
        self.app_id = app_id
        self.app_key = app_key

    def fetch_jobs(self, keywords: List[str], country: str = "in", results_per_keyword: int = 20) -> List[JobPosting]:
        all_jobs: List[JobPosting] = []

        if not self.app_id or not self.app_key or self.app_id == "your_adzuna_app_id":
            logger.warning("Adzuna API credentials not configured or using placeholders. Returning mock job data for verification.")
            return self._get_mock_jobs()

        for kw in keywords:
            try:
                encoded_kw = urllib.parse.quote(kw)
                url = f"{self.BASE_URL}/{country}/search/1?app_id={self.app_id}&app_key={self.app_key}&results_per_page={results_per_keyword}&what={encoded_kw}&content-type=application/json"
                
                req = urllib.request.Request(url, headers={"User-Agent": "JobScrapper/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        results = data.get("results", [])
                        for item in results:
                            posting = self._normalize_item(item)
                            if posting:
                                all_jobs.append(posting)
                    else:
                        logger.error(f"Adzuna API returned HTTP status {resp.status} for query '{kw}'")
            except Exception as e:
                logger.error(f"Failed to fetch jobs from Adzuna for keyword '{kw}': {e}")
        
        return all_jobs

    def _normalize_item(self, item: Dict[str, Any]) -> JobPosting:
        try:
            job_id = str(item.get("id", ""))
            title = item.get("title", "Software Engineer")
            company = item.get("company", {}).get("display_name", "Unknown Company")
            location_area = item.get("location", {}).get("display_name", "India")
            posted_str = item.get("created", "")
            description = item.get("description", "")
            apply_url = item.get("redirect_url", "")

            # Ensure clean ISO-8601 string
            if not posted_str:
                posted_str = datetime.now(timezone.utc).isoformat()

            return JobPosting(
                job_id=job_id,
                title=title,
                company=company,
                location=location_area,
                posted_date=posted_str,
                description=description,
                apply_url=apply_url,
                source="adzuna"
            )
        except Exception as e:
            logger.error(f"Error normalizing Adzuna job item: {e}")
            return None

    def _get_mock_jobs(self) -> List[JobPosting]:
        now_iso = datetime.now(timezone.utc).isoformat()
        return [
            JobPosting(
                job_id="mock-adzuna-101",
                title="Backend Engineer (Python / FastAPI)",
                company="Nexus Tech India",
                location="Bangalore, Karnataka, India",
                posted_date=now_iso,
                description="We are seeking a Backend Engineer with strong expertise in Python, FastAPI, PostgreSQL, Redis, and microservices architecture. Experience with Docker, CI/CD pipelines, and high-throughput REST APIs is highly desirable.",
                apply_url="https://example.com/apply/nexus-101",
                source="adzuna"
            ),
            JobPosting(
                job_id="mock-adzuna-102",
                title="Software Development Engineer I (SDE-1)",
                company="Innovate Cloud Solutions",
                location="Hyderabad, Telangana, India",
                posted_date=now_iso,
                description="Looking for an SDE-1 to build distributed systems, API endpoints, and cloud infrastructure. Skills needed: Python or C++, SQL, Git, and automated testing frameworks.",
                apply_url="https://example.com/apply/innovate-102",
                source="adzuna"
            ),
            JobPosting(
                job_id="mock-adzuna-103",
                title="Full Stack Software Engineer",
                company="Apex AI Systems",
                location="Gurgaon, Haryana, India",
                posted_date=now_iso,
                description="Seeking a Full Stack Engineer proficient in React, TypeScript, Python FastAPI, and LLM integrations. Experience with SQLite, search, and containerization is a major plus.",
                apply_url="https://example.com/apply/apex-103",
                source="adzuna"
            )
        ]
