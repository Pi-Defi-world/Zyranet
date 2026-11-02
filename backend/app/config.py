"""Application settings loaded from environment (.env)."""
from __future__ import annotations

from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "zyranet"
    db_user: str = "zyranet"
    db_password: str = "change-me"
    db_url: str | None = None

    radius_secret: str = ""
    radius_sql_user: str = ""
    radius_sql_password: str = ""

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    admin_jwt_secret: str = "change-me-to-a-long-random-secret"
    admin_user: str = "admin"
    admin_password: str = "change-me"

    # --- Authentication / sessions ---
    # Role granted to the configured admin account: admin | operator | viewer.
    admin_role: str = "admin"
    jwt_expire_minutes: int = 60 * 12
    jwt_issuer: str = "zyranet"
    jwt_audience: str = "zyranet-admin"
    # Failed logins per (client IP, username) before a temporary lockout.
    login_max_attempts: int = 5
    login_lockout_seconds: int = 300
    # Set true only when running behind a reverse proxy that sets X-Forwarded-For.
    trust_proxy_headers: bool = False

    # --- HTTP hardening ---
    # Comma-separated CORS origins allowed to call the API from a browser.
    # Same-origin requests (the bundled dashboard) never need an entry here.
    cors_allowed_origins: str = "http://localhost:5173"
    # Comma-separated Host headers accepted; "*" accepts any (LAN/IP access).
    allowed_hosts: str = "*"
    log_format: str = "auto"  # auto | json | text

    app_env: str = "development"

    # --- Network discovery ---
    # Comma-separated CIDRs to scan for device tracking.
    # No default scan scope: operators must enter the approved management CIDRs.
    scan_cidrs: str = ""
    scan_interval_seconds: int = 300
    scan_enabled: bool = False
    # Bound automatic discovery even if an overly broad CIDR is configured.
    scan_max_hosts_per_subnet: int = 1024
    scan_max_hosts_total: int = 4096
    # Limit repeat sighting writes for stable devices; last_seen still refreshes per scan.
    scan_sighting_interval_seconds: int = 3600
    device_stale_after_seconds: int = 900

    # --- SNMP / LLDP (managed switches) ---
    snmp_enabled: bool = False
    # No implicit community: operators must configure a management credential.
    snmp_community: str = ""
    # JSON list: [{"host":"10.10.20.5","community":"public","node_id":"sw-core"}] or comma hosts
    snmp_targets: str = ""
    topology_auto_export: bool = False
    # Per-walk SNMP timing and bounded discovery concurrency.
    snmp_timeout: float = 2.0
    snmp_retries: int = 1
    snmp_max_concurrent: int = 8

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.app_env.strip().lower() != "production":
            return self

        problems: list[str] = []

        def is_placeholder(value: str) -> bool:
            normalized = value.strip().lower().replace("_", "-")
            return not normalized or "change-me" in normalized or normalized in {
                "password", "secret", "admin", "zyranet",
            }

        if is_placeholder(self.admin_jwt_secret) or len(self.admin_jwt_secret) < 32:
            problems.append(
                "ADMIN_JWT_SECRET must be a unique random value of at least 32 characters"
            )
        if is_placeholder(self.admin_password) or len(self.admin_password) < 12:
            problems.append(
                "ADMIN_PASSWORD must be a non-placeholder value of at least 12 characters"
            )

        try:
            database_url = (
                make_url(self.db_url)
                if self.db_url
                else URL.create(
                    "postgresql+asyncpg",
                    username=self.db_user,
                    password=self.db_password,
                    host=self.db_host,
                    port=self.db_port,
                    database=self.db_name,
                )
            )
            db_secret = database_url.password or ""
            if is_placeholder(db_secret) or len(db_secret) < 20:
                problems.append(
                    "database password must be a non-placeholder value of at least 20 characters"
                )
        except Exception:
            problems.append("DB_URL must be a valid PostgreSQL async URL")

        if "*" in self.allowed_host_list:
            problems.append(
                "ALLOWED_HOSTS must list the production host names and cannot contain '*'"
            )
        if any(not origin.startswith("https://") for origin in self.cors_origin_list):
            problems.append("CORS_ALLOWED_ORIGINS must contain only HTTPS origins in production")

        if problems:
            raise ValueError("invalid production configuration: " + "; ".join(problems))
        return self

    @property
    def scan_cidr_list(self) -> list[str]:
        return [c.strip() for c in self.scan_cidrs.split(",") if c.strip()]

    @property
    def discovery_ready(self) -> bool:
        return self.scan_enabled and bool(self.scan_cidr_list)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()] or ["*"]

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.db_url:
            return self.db_url
        return URL.create(
            "postgresql+asyncpg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
