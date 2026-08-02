import os
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path

# Load .env manually or via python-dotenv if present
def load_dotenv(dotenv_path: str = ".env"):
    p = Path(dotenv_path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_dotenv()

@dataclass
class SearchConfig:
    country: str = "in"
    keywords: List[str] = field(default_factory=lambda: ["Software Engineer", "SDE", "Backend Engineer"])
    location: str = "India"
    max_freshness_days: int = 21
    results_per_keyword: int = 20

@dataclass
class RankingConfig:
    min_relevance_score: float = 0.50
    embedding_model: str = "all-MiniLM-L6-v2"
    max_jobs_to_tailor: int = 10
    top_company_boost: float = 0.10
    top_companies: List[str] = field(default_factory=lambda: ["Amazon", "Google", "Microsoft", "Goldman Sachs", "Bosch", "Hevo Data"])

@dataclass
class LLMConfig:
    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.2
    fallback_to_keyword_reorder: bool = True

@dataclass
class DeliveryConfig:
    enable_email: bool = False
    email_recipient: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    enable_telegram: bool = False
    dashboard_dir: str = "output"

@dataclass
class PathsConfig:
    resume_json: str = "data/resume_source.json"
    seen_jobs_db: str = "data/seen_jobs.db"
    latex_template: str = "templates/resume_template.tex"
    compiler: str = "pdflatex"

@dataclass
class AppConfig:
    search: SearchConfig = field(default_factory=SearchConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    # API Keys & Tokens from env
    adzuna_app_id: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_ID", ""))
    adzuna_app_key: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    smtp_sender_email: str = field(default_factory=lambda: os.getenv("SMTP_SENDER_EMAIL", ""))
    smtp_app_password: str = field(default_factory=lambda: os.getenv("SMTP_APP_PASSWORD", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

def load_config(config_path: str = "config.yaml") -> AppConfig:
    p = Path(config_path)
    if not p.exists():
        return AppConfig()
    
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    search_cfg = SearchConfig(**data.get("search", {}))
    ranking_cfg = RankingConfig(**data.get("ranking", {}))
    llm_cfg = LLMConfig(**data.get("llm", {}))
    delivery_cfg = DeliveryConfig(**data.get("delivery", {}))
    paths_cfg = PathsConfig(**data.get("paths", {}))

    return AppConfig(
        search=search_cfg,
        ranking=ranking_cfg,
        llm=llm_cfg,
        delivery=delivery_cfg,
        paths=paths_cfg
    )
