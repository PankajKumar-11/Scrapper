import os
import smtplib
import logging
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from src.sources.base import JobPosting

logger = logging.getLogger(__name__)

class DigestDelivery:
    """Handles generation of interactive Web Dashboard and ultra-clean Email Digest."""

    def build_dashboard_html(self, job_items: List[Dict[str, Any]], run_date_str: str) -> str:
        """Dark-mode Web Dashboard for browser viewing."""
        items_html = ""

        for item in job_items:
            job: JobPosting = item["job"]
            score: float = item["score"]
            pdf_path: str = item.get("pdf_path", "")
            tex_path: str = item.get("tex_path", "")
            diff_lines: List[str] = item.get("diff_lines", [])
            method: str = item.get("method", "Tailored")

            score_pct = int(score * 100)
            score_color = "#10b981" if score_pct >= 70 else "#f59e0b"
            diff_html = "".join(f"<li>{line}</li>" for line in diff_lines)

            pdf_button = ""
            if pdf_path:
                pdf_button = f'<a href="{pdf_path}" target="_blank" class="btn btn-secondary">📄 View Tailored PDF</a>'
            elif tex_path:
                pdf_button = f'<a href="{tex_path}" target="_blank" class="btn btn-secondary">📝 View LaTeX Source</a>'

            items_html += f"""
            <div class="job-card">
                <div class="job-header">
                    <div>
                        <h2 class="job-title">{job.title}</h2>
                        <div class="company-info">{job.company} &bull; <span class="location">{job.location}</span></div>
                    </div>
                    <div class="badge-group">
                        <span class="badge score-badge" style="background-color: {score_color}20; color: {score_color}; border: 1px solid {score_color}50;">
                            {score_pct}% Match
                        </span>
                        <span class="badge method-badge">{method}</span>
                    </div>
                </div>

                <div class="job-description">
                    {job.description[:280]}...
                </div>

                <div class="diff-section">
                    <div class="diff-title">✨ Resume Tailoring Applied:</div>
                    <ul class="diff-list">
                        {diff_html}
                    </ul>
                </div>

                <div class="action-buttons">
                    <a href="{job.apply_url}" target="_blank" class="btn btn-primary">🚀 Direct Apply</a>
                    {pdf_button}
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Job & Tailored Resume Digest — {run_date_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-primary: #6366f1;
            --accent-hover: #4f46e5;
            --accent-secondary: #3b82f6;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 2rem 1rem;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 2rem; border-bottom: 1px solid var(--border-color); padding-bottom: 1.5rem; }}
        header h1 {{
            font-size: 2rem; font-weight: 700;
            background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
            -webkit-background-clip: text; background-clip: text;
            -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;
        }}
        .summary-bar {{
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 2rem;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .summary-stat span {{ color: var(--accent-primary); font-weight: bold; font-size: 1.2rem; }}
        .job-card {{
            background: var(--card-bg); border: 1px solid var(--border-color);
            border-radius: 16px; padding: 1.75rem; margin-bottom: 1.5rem;
        }}
        .job-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; gap: 1rem; }}
        .job-title {{ font-size: 1.25rem; font-weight: 600; color: #ffffff; }}
        .company-info {{ color: var(--text-muted); font-size: 0.9rem; margin-top: 0.25rem; }}
        .badge-group {{ display: flex; gap: 0.5rem; flex-shrink: 0; }}
        .badge {{ font-size: 0.75rem; font-weight: 600; padding: 0.35rem 0.75rem; border-radius: 20px; }}
        .method-badge {{ background: #334155; color: #cbd5e1; }}
        .job-description {{
            font-size: 0.9rem; color: #cbd5e1; margin-bottom: 1.25rem;
            background: rgba(15, 23, 42, 0.5); padding: 1rem; border-radius: 8px;
            border-left: 3px solid var(--accent-secondary);
        }}
        .diff-section {{
            margin-bottom: 1.5rem; background: rgba(99, 102, 241, 0.08);
            border: 1px dashed rgba(99, 102, 241, 0.3); padding: 0.85rem 1.1rem; border-radius: 10px;
        }}
        .diff-title {{ font-size: 0.85rem; font-weight: 600; color: #a5b4fc; margin-bottom: 0.4rem; }}
        .diff-list {{ list-style: none; font-size: 0.85rem; color: #e2e8f0; }}
        .diff-list li {{ margin-bottom: 0.25rem; position: relative; padding-left: 1.2rem; }}
        .diff-list li::before {{ content: "✓"; position: absolute; left: 0; color: #34d399; font-weight: bold; }}
        .action-buttons {{ display: flex; gap: 0.75rem; }}
        .btn {{ display: inline-flex; align-items: center; padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 0.9rem; font-weight: 600; text-decoration: none; }}
        .btn-primary {{ background-color: var(--accent-primary); color: white; }}
        .btn-secondary {{ background-color: #334155; color: #f1f5f9; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Daily Job & Resume Tailoring Digest</h1>
            <p>India Software Engineering & Tech Roles &bull; {run_date_str}</p>
        </header>
        <div class="summary-bar">
            <div class="summary-stat">Surfaced Matches: <span>{len(job_items)}</span></div>
            <div class="summary-stat">Cost: <span>Rs. 0 (Free Tier)</span></div>
        </div>
        {items_html}
    </div>
</body>
</html>"""

    def build_email_html(self, job_items: List[Dict[str, Any]], run_date_str: str) -> str:
        """
        Ultra-clean, high-contrast, mobile-friendly HTML email template specifically 
        engineered for Gmail Desktop and Mobile App compatibility.
        Uses solid backgrounds, inline CSS, explicit padding, and high contrast.
        """
        items_html = ""

        for idx, item in enumerate(job_items, 1):
            job: JobPosting = item["job"]
            score: float = item["score"]
            diff_lines: List[str] = item.get("diff_lines", [])
            method: str = item.get("method", "Tailored")

            score_pct = int(score * 100)
            score_bg = "#dcfce7" if score_pct >= 70 else "#fef3c7"
            score_color = "#15803d" if score_pct >= 70 else "#b45309"

            diff_bullets_html = ""
            for line in diff_lines:
                diff_bullets_html += f'<li style="margin-bottom: 4px; color: #334155;">✓ {line}</li>'

            items_html += f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <tr>
                    <td style="padding: 24px;">
                        <!-- Job Header -->
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                                <td style="vertical-align: top;">
                                    <h2 style="margin: 0 0 6px 0; font-size: 18px; font-weight: 700; color: #0f172a; line-height: 1.3;">
                                        {idx}. {job.title}
                                    </h2>
                                    <p style="margin: 0; font-size: 14px; font-weight: 600; color: #475569;">
                                        {job.company} &bull; <span style="color: #64748b; font-weight: normal;">{job.location}</span>
                                    </p>
                                </td>
                                <td style="vertical-align: top; text-align: right; width: 140px;">
                                    <span style="display: inline-block; background-color: {score_bg}; color: {score_color}; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 16px; margin-bottom: 4px;">
                                        {score_pct}% Match
                                    </span>
                                    <br>
                                    <span style="display: inline-block; background-color: #f1f5f9; color: #475569; font-size: 11px; font-weight: 500; padding: 3px 8px; border-radius: 4px;">
                                        {method}
                                    </span>
                                </td>
                            </tr>
                        </table>

                        <!-- Job Snippet -->
                        <div style="margin-top: 16px; margin-bottom: 16px; background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 12px 14px; border-radius: 0 6px 6px 0; font-size: 13px; color: #334155; line-height: 1.5;">
                            {job.description[:260]}...
                        </div>

                        <!-- Tailoring Applied Box -->
                        <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 14px; margin-bottom: 20px;">
                            <div style="font-size: 12px; font-weight: 700; color: #1d4ed8; margin-bottom: 6px;">
                                ✨ Resume Tailoring Applied:
                            </div>
                            <ul style="margin: 0; padding-left: 0; list-style-type: none; font-size: 13px; line-height: 1.4;">
                                {diff_bullets_html}
                            </ul>
                        </div>

                        <!-- Direct Apply Button -->
                        <table role="presentation" cellpadding="0" cellspacing="0">
                            <tr>
                                <td>
                                    <a href="{job.apply_url}" target="_blank" style="display: inline-block; background-color: #2563eb; color: #ffffff; font-size: 14px; font-weight: 700; text-decoration: none; padding: 10px 22px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37,99,235,0.2);">
                                        🚀 Direct Apply Now
                                    </a>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f1f5f9; padding: 24px 12px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width: 650px;">
                    <!-- Email Header -->
                    <tr>
                        <td style="background-color: #0f172a; border-radius: 12px 12px 0 0; padding: 28px 24px; text-align: center;">
                            <h1 style="margin: 0 0 6px 0; font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">
                                ⚡ Daily Job & Resume Tailoring Digest
                            </h1>
                            <p style="margin: 0; font-size: 14px; color: #94a3b8;">
                                India SDE & Tech Roles &bull; {run_date_str}
                            </p>
                        </td>
                    </tr>
                    <!-- Summary Ribbon -->
                    <tr>
                        <td style="background-color: #1e293b; padding: 12px 24px; color: #e2e8f0; font-size: 13px; font-weight: 600; text-align: center; border-radius: 0 0 12px 12px; margin-bottom: 24px;">
                            Matches Surfaced Today: <span style="color: #38bdf8; font-size: 15px;">{len(job_items)}</span> &nbsp;|&nbsp; Daily Cost: <span style="color: #4ade80;">Rs. 0 (Free Tier)</span>
                        </td>
                    </tr>
                    <tr><td height="20"></td></tr>
                    <!-- Job Cards List -->
                    <tr>
                        <td>
                            {items_html}
                        </td>
                    </tr>
                    <!-- Email Footer -->
                    <tr>
                        <td style="text-align: center; padding: 20px; font-size: 12px; color: #64748b;">
                            AI-Assisted Job Discovery & Resume Tailoring System &bull; 100% Free Tier Infrastructure
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def save_dashboard(self, job_items: List[Dict[str, Any]], output_dir: Path) -> Path:
        run_date_str = datetime.now().strftime("%B %d, %Y")
        html_content = self.build_dashboard_html(job_items, run_date_str)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        dashboard_path = output_dir / "dashboard.html"
        
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Saved interactive Web Dashboard at: {dashboard_path}")
        return dashboard_path

    def send_email_digest(
        self,
        job_items: List[Dict[str, Any]],
        recipient_email: str,
        sender_email: str,
        app_password: str,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587
    ) -> bool:
        if not recipient_email or not sender_email or not app_password:
            logger.warning("SMTP credentials or recipient email not configured. Skipping email send.")
            return False

        try:
            run_date_str = datetime.now().strftime("%B %d, %Y")
            html_body = self.build_email_html(job_items, run_date_str)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"⚡ [{len(job_items)} Top Matches] Daily Tailored Jobs Digest — {run_date_str}"
            msg["From"] = sender_email
            msg["To"] = recipient_email

            part_html = MIMEText(html_body, "html", "utf-8")
            msg.attach(part_html)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls()
                server.login(sender_email, app_password)
                server.sendmail(sender_email, [recipient_email], msg.as_string())

            logger.info(f"Successfully sent clean daily digest email to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email digest: {e}")
            return False
