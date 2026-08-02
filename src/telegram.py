import json
import logging
import urllib.request
import urllib.parse
from typing import List, Dict, Any
from src.sources.base import JobPosting

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Sends instant mobile notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_digest(self, job_items: List[Dict[str, Any]]) -> bool:
        if not self.bot_token or not self.chat_id or self.bot_token == "your_telegram_bot_token":
            logger.warning("Telegram bot credentials not configured. Skipping mobile push notification.")
            return False

        try:
            msg_text = f"⚡ *Daily Job Discovery & Resume Digest*\n"
            msg_text += f"Found *{len(job_items)}* top matches for India SDE / Tech roles:\n\n"

            for idx, item in enumerate(job_items[:5], 1):  # Top 5 for mobile screen readability
                job: JobPosting = item["job"]
                score: float = item["score"]
                score_pct = int(score * 100)

                msg_text += f"*{idx}. {job.title}*\n"
                msg_text += f"🏢 {job.company} | 📍 {job.location}\n"
                msg_text += f"🎯 Match Score: *{score_pct}%*\n"
                msg_text += f"🔗 [Direct Apply Link]({job.apply_url})\n\n"

            msg_text += "Check your email / dashboard for full tailored resume PDFs!"

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": msg_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logger.info("Successfully sent instant mobile alert via Telegram Bot!")
                    return True
                else:
                    logger.error(f"Telegram API returned HTTP status {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
