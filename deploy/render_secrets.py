"""Render RADIUS/Chilli config templates, substituting secrets from .env.

The raddb/ and chilli/ files use __PLACEHOLDER__ tokens so real secrets are
never committed. Run this during deployment to write actual config to the
system locations:

    python deploy/render_secrets.py \
        --radusers /etc/freeradius/3.0/mods-enabled/sql \
        --radclients /etc/freeradius/3.0/clients.conf \
        --chilli /etc/chilli/config

Purely mechanical string substitution; no evaluation.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings


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
    parser.add_argument("--chilli", help="write rendered chilli config to this path")
    args = parser.parse_args()

    s = get_settings()
    root = Path(__file__).resolve().parent.parent

    targets = {
        str(root / "raddb/mods-enabled/sql"): args.radusers,
        str(root / "raddb/clients.conf"): args.radclients,
        str(root / "chilli/chilli.conf"): args.chilli,
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
