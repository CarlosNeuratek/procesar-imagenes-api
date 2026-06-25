"""Recovery CLI: reset the admin password from --password, env, or stdin.

ponytail: stdlib argparse + getpass, no click/typer. One command, no plugin
surface. Promote to click if we add more commands.

Usage:
    python -m app.auth.cli reset-admin [--password PASSWORD]
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from .models import User
from .security import hash_password


def _read_password(args_password: str | None) -> str:
    if args_password:
        return args_password
    env_pw = os.environ.get("ADMIN_PASSWORD") or settings.admin_password
    if env_pw:
        return env_pw
    return getpass.getpass("New admin password: ")


def _reset_admin(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Reset the admin password.")
    parser.add_argument(
        "--password",
        help="New password (falls back to ADMIN_PASSWORD env, then stdin prompt)",
    )
    args = parser.parse_args(argv)

    new_password = _read_password(args.password)
    if len(new_password) < 8:
        print("password must be at least 8 characters", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        admin = db.execute(
            select(User).where(User.email == settings.admin_email)
        ).scalar_one_or_none()
        if admin is None:
            print(f"no admin user with email {settings.admin_email}", file=sys.stderr)
            return 1
        admin.password_hash = hash_password(new_password)
        admin.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    print(f"admin password updated for {settings.admin_email}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch on first positional: `reset-admin [--password PASSWORD]`."""
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "reset-admin":
        print("usage: python -m app.auth.cli reset-admin [--password PASSWORD]", file=sys.stderr)
        return 2
    return _reset_admin(argv[1:])


if __name__ == "__main__":
    sys.exit(main())