import re
import math
import logging
from collections import Counter
from typing import List, Dict, Any, Tuple
from src.sources.base import JobPosting

logger = logging.getLogger(__name__)

# Try importing sentence_transformers
try:
    from sentence_transformers import SentenceTransformer, util  # type: ignore
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

class RelevanceRanker:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", min_score: float = 0.50, top_company_boost: float = 0.10, top_companies: List[str] = None):
        self.min_score = min_score
        self.model_name = model_name
        self.top_company_boost = top_company_boost
        self.top_companies = [c.lower() for c in (top_companies or [])]
        self.model = None
        
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                logger.info(f"Loading local SentenceTransformer model '{model_name}'...")
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer '{model_name}': {e}. Falling back to TF-IDF ranker.")
                self.model = None

    def _apply_company_boost(self, job: JobPosting, raw_score: float) -> float:
        comp_name = (job.company or "").lower()
        for top_comp in self.top_companies:
            if top_comp in comp_name:
                boosted = min(1.0, raw_score + self.top_company_boost)
                logger.info(f"Priority boost (+{self.top_company_boost}) applied for top company '{job.company}': {raw_score:.2f} -> {boosted:.2f}")
                return boosted
        return raw_score

    def flatten_resume(self, resume_data: Dict[str, Any]) -> str:
        parts = []
        if "profile_summary" in resume_data:
            parts.append(str(resume_data["profile_summary"]))
        
        for exp in resume_data.get("experience", []):
            parts.append(f"{exp.get('role', '')} {exp.get('company', '')}")
            parts.extend(exp.get("bullets", []))

        for proj in resume_data.get("projects", []):
            parts.append(f"{proj.get('name', '')} {proj.get('stack', '')}")
            parts.extend(proj.get("bullets", []))

        skills = resume_data.get("skills", {})
        if isinstance(skills, dict):
            for k, v in skills.items():
                if isinstance(v, list):
                    parts.append(" ".join(v))

        return " ".join(parts)

    def score_jobs(self, jobs: List[JobPosting], resume_data: Dict[str, Any]) -> List[Tuple[JobPosting, float]]:
        resume_text = self.flatten_resume(resume_data)
        scored_jobs: List[Tuple[JobPosting, float]] = []

        if self.model:
            try:
                resume_emb = self.model.encode(resume_text, convert_to_tensor=True)
                job_texts = [f"{j.title} {j.description}" for j in jobs]
                job_embs = self.model.encode(job_texts, convert_to_tensor=True)
                
                cos_scores = util.cos_sim(resume_emb, job_embs)[0]
                
                for idx, job in enumerate(jobs):
                    raw_score = float(cos_scores[idx])
                    final_score = self._apply_company_boost(job, raw_score)
                    if final_score >= self.min_score:
                        scored_jobs.append((job, round(final_score, 4)))
            except Exception as e:
                logger.error(f"Error during SentenceTransformer scoring: {e}. Switching to TF-IDF.")
                scored_jobs = self._tfidf_score(jobs, resume_text)
        else:
            scored_jobs = self._tfidf_score(jobs, resume_text)

        # Sort by relevance score descending
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Scored {len(jobs)} jobs. Found {len(scored_jobs)} above minimum relevance threshold ({self.min_score}).")
        return scored_jobs

    def _tfidf_score(self, jobs: List[JobPosting], resume_text: str) -> List[Tuple[JobPosting, float]]:
        def tokenize(text: str) -> List[str]:
            return re.findall(r'\w+', text.lower())

        resume_tokens = tokenize(resume_text)
        resume_counts = Counter(resume_tokens)
        
        scored = []
        for job in jobs:
            job_text = f"{job.title} {job.description}"
            job_tokens = tokenize(job_text)
            job_counts = Counter(job_tokens)

            # Cosine similarity on word frequency
            intersection = set(resume_counts.keys()) & set(job_counts.keys())
            dot_product = sum(resume_counts[x] * job_counts[x] for x in intersection)

            mag1 = math.sqrt(sum(v**2 for v in resume_counts.values()))
            mag2 = math.sqrt(sum(v**2 for v in job_counts.values()))

            if mag1 == 0 or mag2 == 0:
                score = 0.0
            else:
                score = dot_product / (mag1 * mag2)

            # Scale TF-IDF score to match ~0.3-0.8 range for thresholding
            normalized_score = min(1.0, score * 2.5)
            final_score = self._apply_company_boost(job, normalized_score)
            if final_score >= self.min_score:
                scored.append((job, round(final_score, 4)))

        return scored
