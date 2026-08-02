import json
import copy
import time
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple
from src.guard import FabricationGuard
from src.sources.base import JobPosting

logger = logging.getLogger(__name__)

class KeywordFallbackTailor:
    """
    Zero-LLM, offline fallback tailor.
    Ranks projects and re-orders experience/project bullets based on exact keyword overlap with job description.
    """
    def tailor(self, source_resume: Dict[str, Any], job: JobPosting) -> Dict[str, Any]:
        tailored = copy.deepcopy(source_resume)
        job_words = set(job.description.lower().split() + job.title.lower().split())

        def score_text(text: str) -> int:
            words = text.lower().split()
            return sum(1 for w in words if w in job_words)

        # Smart Project Selection: Select top 2-3 most relevant projects if project pool > 3
        projects = tailored.get("projects", [])
        if len(projects) > 3:
            for proj in projects:
                proj_text = f"{proj.get('name', '')} {proj.get('stack', '')} {' '.join(proj.get('bullets', []))}"
                proj["_score"] = score_text(proj_text)
            
            projects.sort(key=lambda p: p.get("_score", 0), reverse=True)
            for p in projects:
                p.pop("_score", None)
            tailored["projects"] = projects[:3]

        # Re-order experience bullets
        for exp in tailored.get("experience", []):
            bullets = exp.get("bullets", [])
            bullets.sort(key=score_text, reverse=True)
            exp["bullets"] = bullets

        # Re-order project bullets
        for proj in tailored.get("projects", []):
            bullets = proj.get("bullets", [])
            bullets.sort(key=score_text, reverse=True)
            proj["bullets"] = bullets

        return tailored

class LLMTailor:
    """
    Google AI Studio Gemini Flash tailor with zero-hallucination fabrication guard.
    """
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.fallback_tailor = KeywordFallbackTailor()
        self.guard = FabricationGuard()

    def tailor(self, source_resume: Dict[str, Any], job: JobPosting) -> Tuple[Dict[str, Any], str]:
        """
        Returns (tailored_resume_dict, method_used)
        method_used is either 'LLM (Gemini Flash)' or 'Fallback (Keyword Reorder)'
        """
        if not self.api_key or self.api_key == "your_google_ai_studio_key":
            logger.info(f"No valid Gemini API key found. Using offline Keyword Fallback for job '{job.title}'.")
            return self.fallback_tailor.tailor(source_resume, job), "Fallback (Keyword Reorder)"

        prompt = f"""
You are an expert resume editor and technical recruiter.
Your task is to tailor the following candidate resume JSON to highlight relevant experience for the target job posting.

CRITICAL RULES:
1. DO NOT invent new companies, degrees, dates, skills, or projects.
2. DO NOT invent new metrics or change existing numbers (e.g. do not change 50k to 500k).
3. If the input resume contains more than 3 projects, SELECT the 2 to 3 most relevant projects for the target job posting and omit the less relevant ones.
4. Re-order and slightly reword bullet points and summary to emphasize keywords matching the job posting.
5. Output MUST be strictly valid JSON matching the exact schema of the input resume JSON.
6. Do NOT include markdown code block wrappers like ```json. Return raw JSON string only.

TARGET JOB POSTING:
Title: {job.title}
Company: {job.company}
Description: {job.description}

INPUT RESUME JSON (SOURCE OF TRUTH):
{json.dumps(source_resume, indent=2)}
"""

        try:
            time.sleep(1.0)  # Gentle delay to respect Gemini API rate limits
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "response_mime_type": "application/json"
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                }
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    text_response = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Clean up JSON formatting if needed
                    clean_json_str = text_response.strip()
                    if clean_json_str.startswith("```"):
                        clean_json_str = clean_json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

                    tailored_dict = json.loads(clean_json_str)

                    # Pass through Fabrication Guard
                    is_valid, reason = self.guard.validate(source_resume, tailored_dict)
                    if is_valid:
                        logger.info(f"LLM tailoring successful & passed fabrication guard for job '{job.title}'.")
                        return tailored_dict, "LLM (Gemini Flash)"
                    else:
                        logger.warning(f"LLM output failed fabrication guard: {reason}. Falling back to Keyword Reorder.")
                        return self.fallback_tailor.tailor(source_resume, job), "Fallback (Keyword Reorder - Guard Triggered)"

        except urllib.error.HTTPError as e:
            logger.warning(f"Gemini API HTTP Error {e.code}: {e.reason}. Falling back to Keyword Reorder.")
        except Exception as e:
            logger.warning(f"LLM tailoring failed for job '{job.title}': {e}. Falling back to Keyword Reorder.")

        return self.fallback_tailor.tailor(source_resume, job), "Fallback (Keyword Reorder)"
