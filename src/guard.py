import re
import logging
from typing import Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)

class FabricationGuard:
    """
    Ensures LLM output does NOT invent new claims, non-existent skills, fake metrics, or fake companies.
    """

    def validate(self, source_resume: Dict[str, Any], tailored_resume: Dict[str, Any]) -> Tuple[bool, str]:
        # Rule 1: Key structure matching
        required_keys = ["profile_summary", "education", "projects", "skills"]
        for key in required_keys:
            if key not in tailored_resume:
                return False, f"Missing required top-level key '{key}' in tailored resume JSON."

        # Rule 2: Institution / Company identity matching (No fabricated employers/schools)
        source_insts = {e.get("institution", "").strip().lower() for e in source_resume.get("education", [])}
        tailored_insts = {e.get("institution", "").strip().lower() for e in tailored_resume.get("education", [])}
        if not tailored_insts.issubset(source_insts):
            return False, f"Fabricated education institution detected: {tailored_insts - source_insts}"

        source_companies = {e.get("company", "").strip().lower() for e in source_resume.get("experience", [])}
        tailored_companies = {e.get("company", "").strip().lower() for e in tailored_resume.get("experience", [])}
        if not tailored_companies.issubset(source_companies):
            return False, f"Fabricated company detected: {tailored_companies - source_companies}"

        source_projects = {p.get("name", "").strip().lower() for p in source_resume.get("projects", [])}
        tailored_projects = {p.get("name", "").strip().lower() for p in tailored_resume.get("projects", [])}
        if not tailored_projects.issubset(source_projects):
            return False, f"Fabricated project detected: {tailored_projects - source_projects}"

        # Rule 3: Skill set validation (No invented skill categories or new ungrounded languages)
        source_skills = self._extract_all_skills(source_resume.get("skills", {}))
        tailored_skills = self._extract_all_skills(tailored_resume.get("skills", {}))
        new_skills = tailored_skills - source_skills
        if new_skills:
            return False, f"Fabricated skill(s) detected not present in source resume: {new_skills}"

        # Rule 4: Numerical metric groundings (Prevent inflated numbers like 50k -> 500k)
        source_numbers = self._extract_numbers(self._flatten_text(source_resume))
        tailored_numbers = self._extract_numbers(self._flatten_text(tailored_resume))
        new_numbers = tailored_numbers - source_numbers
        if new_numbers:
            # Allow common small numbers or date formats if benign, but flag unexpected large numbers
            inflated = [n for n in new_numbers if len(n) > 2 or int(n) > 50]
            if inflated:
                return False, f"Fabricated numerical metric(s) detected: {inflated}"

        return True, "Validation successful: Zero fabrication detected."

    def _extract_all_skills(self, skills_dict: Dict[str, Any]) -> Set[str]:
        skills = set()
        if isinstance(skills_dict, dict):
            for k, v in skills_dict.items():
                if isinstance(v, list):
                    for item in v:
                        skills.add(str(item).strip().lower())
        return skills

    def _extract_numbers(self, text: str) -> Set[str]:
        # Extract digits and numbers like 50k, 99.9%, 35%
        raw_nums = re.findall(r'\b\d+(?:\.\d+)?%?k?\b', text.lower())
        return set(raw_nums)

    def _flatten_text(self, resume_data: Dict[str, Any]) -> str:
        parts = []
        if "profile_summary" in resume_data:
            parts.append(str(resume_data["profile_summary"]))

        for exp in resume_data.get("experience", []):
            parts.extend(exp.get("bullets", []))

        for proj in resume_data.get("projects", []):
            parts.extend(proj.get("bullets", []))

        return " ".join(parts)
