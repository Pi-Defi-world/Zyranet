"""Application settings loaded from environment (.env)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "zyranet"
    db_user: str = "zyranet"
    db_password: str = "change-me"
    db_url: str | None = None

    radius_secret: str = "change-me-to-a-long-random-secret"
    radius_sql_user: str = "raduser"
    radius_sql_password: str = "change-me"

    telegram_bot_token: str = ""
    flutterwave_public_key: str = ""
    flutterwave_secret_key: str = ""
    flutterwave_encryption_key: str = ""
    flutterwave_env: str = "test"
    paystack_public_key: str = ""
    paystack_secret_key: str = ""
    paystack_env: str = "test"
    termii_api_key: str = ""
    termii_sender_id: str = ""

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    admin_jwt_secret: str = "change-me-to-a-long-random-secret"
    admin_user: str = "admin"
    admin_password: str = "change-me"
    currency: str = "NGN"
    public_base_url: str = "http://localhost:8000"

    # --- Network discovery ---
    # Comma-separated CIDRs to scan for device tracking.
    scan_cidrs: str = "172.16.30.0/24,10.10.20.0/24"
    scan_interval_seconds: int = 300
    scan_enabled: bool = True

    # --- SNMP / LLDP (managed switches) ---
    snmp_enabled: bool = False
    snmp_community: str = "public"
    # JSON list: [{"host":"10.10.20.5","community":"public","node_id":"sw-core"}] or comma hosts
    snmp_targets: str = ""
    topology_auto_export: bool = True

    @property
    def scan_cidr_list(self) -> list[str]:
        return [c.strip() for c in self.scan_cidrs.split(",") if c.strip()]

    @property
    def has_payment_keys(self) -> bool:
        """True if a payment provider is configured (dev mode otherwise)."""
        return bool(self.flutterwave_secret_key or self.paystack_secret_key)

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.db_url:
            return self.db_url
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
