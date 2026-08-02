import sys
import json
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime

from src.config import load_config
from src.sources.adzuna import AdzunaJobSource
from src.filter import DeduplicationAndFreshnessFilter
from src.ranker import RelevanceRanker
from src.tailor import LLMTailor
from src.renderer import LaTeXRenderer
from src.diff import ResumeDiffGenerator
from src.digest import DigestDelivery

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")

def check_environment(cfg):
    print("=" * 60)
    print("      ENVIRONMENT & DEPENDENCY HEALTH CHECK")
    print("=" * 60)
    
    # 1. Config & Paths
    print(f"[OK] Resume Source JSON: {cfg.paths.resume_json} -> {'EXISTS' if Path(cfg.paths.resume_json).exists() else 'MISSING'}")
    print(f"[OK] LaTeX Template:     {cfg.paths.latex_template} -> {'EXISTS' if Path(cfg.paths.latex_template).exists() else 'MISSING'}")

    # 2. LaTeX compiler
    try:
        res = subprocess.run([cfg.paths.compiler, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            version_line = res.stdout.splitlines()[0] if res.stdout else "Available"
            print(f"[OK] LaTeX Compiler ({cfg.paths.compiler}): {version_line}")
        else:
            print(f"[!]  LaTeX Compiler ({cfg.paths.compiler}): Returned exit code {res.returncode}")
    except FileNotFoundError:
        print(f"[!]  LaTeX Compiler ({cfg.paths.compiler}): NOT FOUND in system PATH. Rendered .tex files will be generated for manual compile.")

    # 3. Adzuna API Key
    if cfg.adzuna_app_id and cfg.adzuna_app_id != "your_adzuna_app_id":
        print(f"[OK] Adzuna API Credentials: Configured (App ID: {cfg.adzuna_app_id[:4]}***)")
    else:
        print(f"[!]  Adzuna API Credentials: Not configured. Using offline mock jobs.")

    # 4. Gemini API Key
    if cfg.gemini_api_key and cfg.gemini_api_key != "your_google_ai_studio_key":
        print(f"[OK] Gemini AI API Key: Configured ({cfg.gemini_api_key[:4]}***)")
    else:
        print(f"[!]  Gemini AI API Key: Not configured. Pipeline will use zero-cost Keyword Fallback Tailor.")

    print("=" * 60)

def run_pipeline(dry_run: bool = False):
    logger.info("Initializing Daily Job Discovery & Resume Tailoring Pipeline...")
    cfg = load_config()

    # Load Resume JSON source of truth
    resume_path = Path(cfg.paths.resume_json)
    if not resume_path.exists():
        logger.error(f"Resume source JSON not found at {resume_path}. Please create it first.")
        return

    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)

    # 1. Ingestion Layer
    job_source = AdzunaJobSource(app_id=cfg.adzuna_app_id, app_key=cfg.adzuna_app_key)
    logger.info(f"Fetching jobs for keywords: {cfg.search.keywords} in {cfg.search.location}...")
    raw_jobs = job_source.fetch_jobs(
        keywords=cfg.search.keywords,
        country=cfg.search.country,
        results_per_keyword=cfg.search.results_per_keyword
    )
    logger.info(f"Fetched {len(raw_jobs)} raw job postings.")

    # 2. Dedup & Freshness Filter
    dedup_filter = DeduplicationAndFreshnessFilter(
        db_path=cfg.paths.seen_jobs_db,
        max_freshness_days=cfg.search.max_freshness_days
    )
    fresh_jobs = dedup_filter.filter_jobs(raw_jobs)
    if not fresh_jobs:
        logger.info("No new fresh jobs found today. Pipeline finished.")
        return

    # 3. Relevance Ranking
    ranker = RelevanceRanker(
        model_name=cfg.ranking.embedding_model,
        min_score=cfg.ranking.min_relevance_score,
        top_company_boost=cfg.ranking.top_company_boost,
        top_companies=cfg.ranking.top_companies
    )
    scored_jobs = ranker.score_jobs(fresh_jobs, resume_data)
    if not scored_jobs:
        logger.info("No jobs met the minimum relevance score threshold. Pipeline finished.")
        return

    top_jobs = scored_jobs[:cfg.ranking.max_jobs_to_tailor]
    logger.info(f"Selected top {len(top_jobs)} relevant jobs for processing.")

    if dry_run:
        logger.info("--- DRY RUN RESULTS ---")
        for job, score in top_jobs:
            logger.info(f"Score: {score:.2f} | Title: {job.title} | Company: {job.company} | Apply: {job.apply_url}")
        return

    # 4. Tailoring, Rendering, Diffing & Delivery
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path("output") / date_str

    llm_tailor = LLMTailor(api_key=cfg.gemini_api_key, model_name=cfg.llm.model_name)
    renderer = LaTeXRenderer(template_path=cfg.paths.latex_template, compiler=cfg.paths.compiler)
    diff_gen = ResumeDiffGenerator()
    delivery = DigestDelivery()

    processed_items = []
    seen_to_mark = []

    for job, score in top_jobs:
        logger.info(f"Tailoring resume for: '{job.title}' at {job.company} (Score: {score})...")
        tailored_resume, method = llm_tailor.tailor(resume_data, job)
        
        # File naming prefix
        safe_company = "".join(c for c in job.company if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
        safe_title = "".join(c for c in job.title if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
        prefix = f"{safe_company}_{safe_title}_{job.job_id}"

        # Render & Compile PDF
        pdf_path = renderer.compile_pdf(tailored_resume, output_dir, prefix)
        tex_path = output_dir / f"{prefix}.tex"

        # Generate Diff
        diff_lines = diff_gen.generate_diff(resume_data, tailored_resume)

        processed_items.append({
            "job": job,
            "score": score,
            "pdf_path": str(pdf_path.relative_to("output").as_posix()) if pdf_path else "",
            "tex_path": str(tex_path.relative_to("output").as_posix()) if tex_path.exists() else "",
            "diff_lines": diff_lines,
            "method": method
        })
        seen_to_mark.append(job)

    # Save Interactive Web Dashboard
    dashboard_path = delivery.save_dashboard(processed_items, output_dir)

    # Optional Email Digest
    if cfg.delivery.enable_email:
        delivery.send_email_digest(
            job_items=processed_items,
            recipient_email=cfg.delivery.email_recipient,
            sender_email=cfg.smtp_sender_email,
            app_password=cfg.smtp_app_password,
            smtp_host=cfg.delivery.smtp_host,
            smtp_port=cfg.delivery.smtp_port
        )

    # Optional Mobile Push via Telegram Bot
    if cfg.delivery.enable_telegram or (cfg.telegram_bot_token and cfg.telegram_bot_token != "your_telegram_bot_token"):
        from src.telegram import TelegramNotifier
        tg = TelegramNotifier(bot_token=cfg.telegram_bot_token, chat_id=cfg.telegram_chat_id)
        tg.send_digest(processed_items)

    # Mark jobs as seen in DB
    dedup_filter.mark_seen(seen_to_mark)
    logger.info(f"Pipeline finished successfully! Web Dashboard created at: {dashboard_path.resolve()}")

def main():
    parser = argparse.ArgumentParser(description="AI-Assisted Job Discovery & Resume Tailoring System")
    parser.add_argument("--run", action="store_true", help="Run full pipeline: ingest, tailor, compile PDFs, generate digest.")
    parser.add_argument("--dry-run", action="store_true", help="Run ingestion and ranking only without calling LLM or compiling PDFs.")
    parser.add_argument("--check-env", action="store_true", help="Check system environment, dependencies, and API configuration.")
    args = parser.parse_args()

    cfg = load_config()

    if args.check_env:
        check_environment(cfg)
    elif args.dry_run:
        run_pipeline(dry_run=True)
    elif args.run:
        run_pipeline(dry_run=False)
    else:
        # Default behavior: run pipeline
        run_pipeline(dry_run=False)

if __name__ == "__main__":
    main()
