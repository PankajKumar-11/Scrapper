from typing import Dict, Any, List

class ResumeDiffGenerator:
    """Generates concise, human-readable diff summaries between source and tailored resumes."""

    def generate_diff(self, source_resume: Dict[str, Any], tailored_resume: Dict[str, Any]) -> List[str]:
        diff_lines = []

        # Compare profile summary
        src_summary = source_resume.get("profile_summary", "").strip()
        tailored_summary = tailored_resume.get("profile_summary", "").strip()
        if src_summary != tailored_summary:
            diff_lines.append("Profile Summary: Reworded to highlight target job keywords.")

        # Compare experience bullet order/content
        src_exp = source_resume.get("experience", [])
        tailored_exp = tailored_resume.get("experience", [])
        for idx, (s_item, t_item) in enumerate(zip(src_exp, tailored_exp)):
            s_bullets = s_item.get("bullets", [])
            t_bullets = t_item.get("bullets", [])
            comp_name = t_item.get("company", f"Role {idx+1}")
            if s_bullets != t_bullets:
                diff_lines.append(f"Experience ({comp_name}): Bullet points re-ordered/prioritized.")

        # Compare project bullets
        src_proj = source_resume.get("projects", [])
        tailored_proj = tailored_resume.get("projects", [])
        for idx, (s_item, t_item) in enumerate(zip(src_proj, tailored_proj)):
            s_bullets = s_item.get("bullets", [])
            t_bullets = t_item.get("bullets", [])
            proj_name = t_item.get("name", f"Project {idx+1}")
            if s_bullets != t_bullets:
                diff_lines.append(f"Project ({proj_name}): Bullet points prioritized for role alignment.")

        if not diff_lines:
            diff_lines.append("No major content changes; baseline resume matches posting requirements closely.")

        return diff_lines
