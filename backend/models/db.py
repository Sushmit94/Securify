"""Scan history storage.

Defaults to a local SQLite file (storage/securify.db) so the API and CLI work
out of the box with zero setup. Set DATABASE_URL (e.g. a postgres:// URL) to
point at PostgreSQL instead, per the README's tech stack -- SQLAlchemy's Core
API works against either without any code changes here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{(STORAGE_DIR / 'securify.db').as_posix()}")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ScanRecord(Base):
    __tablename__ = "scans"

    scan_id = Column(String, primary_key=True)
    target = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    total_findings = Column(Integer, nullable=False, default=0)
    result_json = Column(Text, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


def save_scan(scan_result: dict) -> None:
    from datetime import datetime

    init_db()
    with get_session() as session:
        record = ScanRecord(
            scan_id=scan_result["scan_id"],
            target=scan_result["target"],
            created_at=datetime.fromisoformat(scan_result["created_at"]),
            total_findings=scan_result["summary"]["total_findings"],
            result_json=json.dumps(scan_result),
        )
        session.merge(record)
        session.commit()


def get_scan(scan_id: str) -> dict | None:
    init_db()
    with get_session() as session:
        record = session.get(ScanRecord, scan_id)
        return json.loads(record.result_json) if record else None


def list_scans(limit: int = 50) -> list[dict]:
    init_db()
    with get_session() as session:
        records = (
            session.query(ScanRecord)
            .order_by(ScanRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "scan_id": r.scan_id,
                "target": r.target,
                "created_at": r.created_at.isoformat(),
                "total_findings": r.total_findings,
            }
            for r in records
        ]
