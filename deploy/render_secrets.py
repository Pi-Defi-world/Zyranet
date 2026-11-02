"""Render the optional FreeRADIUS templates, substituting secrets from .env.

The raddb files use __PLACEHOLDER__ tokens so real secrets are never
committed. Run this only as part of an approved RADIUS deployment to write
rendered configuration to the system locations:

    python deploy/render_secrets.py \
        --radusers /etc/freeradius/3.0/mods-enabled/sql \
        --radclients /etc/freeradius/3.0/clients.conf \
Purely mechanical string substitution; no evaluation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402


def render(text: str, s) -> str:
    mapping = {
        "__RADIUS_SECRET__": s.radius_secret,
        "__RADIUS_SQL_USER__": s.radius_sql_user,
        "__RADIUS_SQL_PASSWORD__": s.radius_sql_password,
        "__DB_NAME__": s.db_name,
    }
    for key, val in mapping.items():
        text = text.replace(key, val)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-targets", nargs="+", help="src=dst pairs", default=[])
    parser.add_argument("--radusers", help="write rendered sql mod to this path")
    parser.add_argument("--radclients", help="write rendered clients.conf to this path")
    args = parser.parse_args()

    s = get_settings()
    if args.radusers or args.radclients or args.source_targets:
        required = {
            "RADIUS_SECRET": s.radius_secret,
            "RADIUS_SQL_USER": s.radius_sql_user,
            "RADIUS_SQL_PASSWORD": s.radius_sql_password,
        }
        missing = [
            name
            for name, value in required.items()
            if not value or value.upper().startswith("CHANGE_ME")
        ]
        if missing:
            parser.error(f"configure real RADIUS values before rendering: {', '.join(missing)}")
    targets = {
        str(ROOT / "raddb/mods-enabled/sql"): args.radusers,
        str(ROOT / "raddb/clients.conf"): args.radclients,
    }
    for src, dst in targets.items():
        if not dst:
            continue
        text = Path(src).read_text(encoding="utf-8")
        rendered = render(text, s)
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        Path(dst).write_text(rendered, encoding="utf-8")
        print(f"rendered {src} -> {dst}")

    # handle explicit src=dst pairs
    for pair in args.source_targets:
        if "=" not in pair:
            continue
        src, dst = pair.split("=", 1)
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        Path(dst).write_text(render(Path(src).read_text(encoding="utf-8"), s), encoding="utf-8")
        print(f"rendered {src} -> {dst}")


if __name__ == "__main__":
    main()
