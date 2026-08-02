from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class JobPosting:
    job_id: str
    title: str
    company: str
    location: str
    posted_date: str  # ISO-8601 string (e.g. YYYY-MM-DDTHH:MM:SSZ)
    description: str
    apply_url: str
    source: str = "adzuna"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class BaseJobSource(ABC):
    @abstractmethod
    def fetch_jobs(self, keywords: List[str], country: str = "in", results_per_keyword: int = 20) -> List[JobPosting]:
        pass
