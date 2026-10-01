"""
config.py — loads environment variables into a single Settings object.

Every adapter and skill reads its configuration from `settings`, never from
os.environ directly, so the whole app has one place that defines what can be
configured and what the safe defaults are.

Public value:
  - settings: Settings  (singleton instance)
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # LLM
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    # Safety switch — when True (default) any action that would leave the
    # local machine (send email, send WhatsApp, call a CRM/logistics API)
    # is logged and returned instead of transmitted.
    dry_run: bool = field(default_factory=lambda: _bool("DRY_RUN", True))

    # Storage sink selection: excel | sheets | postgres | sqlite
    default_sink: str = field(default_factory=lambda: os.getenv("SINK", "excel"))

    # Local storage paths
    data_dir: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))
    memory_db_path: str = field(default_factory=lambda: os.getenv("MEMORY_DB_PATH", os.path.join("data", "agent.db")))
    excel_path: str = field(default_factory=lambda: os.getenv("EXCEL_PATH", os.path.join("data", "records.xlsx")))
    warehouse_db_path: str = field(default_factory=lambda: os.getenv("WAREHOUSE_DB_PATH", os.path.join("data", "warehouse.db")))

    # Postgres
    postgres_dsn: str = field(default_factory=lambda: os.getenv("POSTGRES_DSN", ""))

    # Google Sheets
    sheets_credentials_path: str = field(default_factory=lambda: os.getenv("SHEETS_CREDENTIALS_PATH", ""))
    sheets_spreadsheet_id: str = field(default_factory=lambda: os.getenv("SHEETS_SPREADSHEET_ID", ""))

    # Email (IMAP read / SMTP send)
    imap_host: str = field(default_factory=lambda: os.getenv("IMAP_HOST", ""))
    imap_user: str = field(default_factory=lambda: os.getenv("IMAP_USER", ""))
    imap_password: str = field(default_factory=lambda: os.getenv("IMAP_PASSWORD", ""))
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    routing_map: str = field(default_factory=lambda: os.getenv(
        "ROUTING_MAP",
        "fatturazione:billing@example.com,assistenza:support@example.com,"
        "logistica:logistics@example.com,appuntamento:frontdesk@example.com",
    ))

    # WhatsApp Cloud API
    whatsapp_token: str = field(default_factory=lambda: os.getenv("WHATSAPP_TOKEN", ""))
    whatsapp_phone_id: str = field(default_factory=lambda: os.getenv("WHATSAPP_PHONE_ID", ""))

    # Generic CRM / logistics REST API
    custom_api_base_url: str = field(default_factory=lambda: os.getenv("CUSTOM_API_BASE_URL", ""))
    custom_api_key: str = field(default_factory=lambda: os.getenv("CUSTOM_API_KEY", ""))

    def routing_table(self) -> dict:
        """Parse ROUTING_MAP ('category:email,category:email,...') into a dict."""
        table = {}
        for pair in self.routing_map.split(","):
            if ":" in pair:
                category, email = pair.split(":", 1)
                table[category.strip().lower()] = email.strip()
        return table

    def require_gemini_key(self) -> str:
        if not self.gemini_api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. Add it to your .env file and restart."
            )
        return self.gemini_api_key


settings = Settings()
os.makedirs(settings.data_dir, exist_ok=True)
