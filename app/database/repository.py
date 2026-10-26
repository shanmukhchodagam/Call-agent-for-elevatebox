import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import zoneinfo

from app.config import DATABASE_PATH, TIMEZONE
from app.database.models import LeadRecord, CallbackRecord, FollowupRecord

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """
    Lightweight SQLite persistence repository for leads, callbacks, and follow-ups.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_PATH or "elevate_sales.db"
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Creates tables if they do not exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 1. Leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id INTEGER UNIQUE,
                    phone_number TEXT,
                    business_type TEXT,
                    product_count_min INTEGER,
                    product_count_max INTEGER,
                    payment_gateway BOOLEAN,
                    customer_accounts BOOLEAN,
                    guest_checkout BOOLEAN,
                    timeline_months INTEGER,
                    budget_min INTEGER,
                    budget_max INTEGER,
                    additional_requirements TEXT,
                    inferred_business_type TEXT,
                    classification TEXT,
                    score INTEGER,
                    reasons TEXT,
                    transcript TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # 2. Callbacks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS callbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id INTEGER,
                    phone_number TEXT,
                    raw_request TEXT,
                    scheduled_time TEXT,
                    timezone TEXT,
                    status TEXT,
                    created_at TEXT
                )
            """)

            # 3. Followups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id INTEGER,
                    phone_number TEXT,
                    message TEXT,
                    channel TEXT,
                    status TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save_lead(self, lead: LeadRecord) -> int:
        """
        Saves or updates a lead record (upsert on call_id).
        """
        tz = zoneinfo.ZoneInfo(TIMEZONE or "Asia/Kolkata")
        now_str = datetime.now(tz).isoformat()
        reasons_json = json.dumps(lead.reasons or [])

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO leads (
                    call_id, phone_number, business_type, product_count_min, product_count_max,
                    payment_gateway, customer_accounts, guest_checkout, timeline_months,
                    budget_min, budget_max, additional_requirements, inferred_business_type,
                    classification, score, reasons, transcript, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(call_id) DO UPDATE SET
                    phone_number=excluded.phone_number,
                    business_type=excluded.business_type,
                    product_count_min=excluded.product_count_min,
                    product_count_max=excluded.product_count_max,
                    payment_gateway=excluded.payment_gateway,
                    customer_accounts=excluded.customer_accounts,
                    guest_checkout=excluded.guest_checkout,
                    timeline_months=excluded.timeline_months,
                    budget_min=excluded.budget_min,
                    budget_max=excluded.budget_max,
                    additional_requirements=excluded.additional_requirements,
                    inferred_business_type=excluded.inferred_business_type,
                    classification=excluded.classification,
                    score=excluded.score,
                    reasons=excluded.reasons,
                    transcript=excluded.transcript,
                    updated_at=excluded.updated_at
            """, (
                lead.call_id,
                lead.phone_number,
                lead.business_type,
                lead.product_count_min,
                lead.product_count_max,
                lead.payment_gateway,
                lead.customer_accounts,
                lead.guest_checkout,
                lead.timeline_months,
                lead.budget_min,
                lead.budget_max,
                lead.additional_requirements,
                lead.inferred_business_type,
                lead.classification,
                lead.score,
                reasons_json,
                lead.transcript,
                now_str,
                now_str,
            ))
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def get_lead_by_call_id(self, call_id: int) -> Optional[LeadRecord]:
        """Retrieves a single lead by OmniDimension call ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE call_id = ?", (call_id,))
            row = cursor.fetchone()
            if not row:
                return None

            reasons_list = json.loads(row["reasons"]) if row["reasons"] else []
            return LeadRecord(
                id=row["id"],
                call_id=row["call_id"],
                phone_number=row["phone_number"],
                business_type=row["business_type"],
                product_count_min=row["product_count_min"],
                product_count_max=row["product_count_max"],
                payment_gateway=bool(row["payment_gateway"]) if row["payment_gateway"] is not None else None,
                customer_accounts=bool(row["customer_accounts"]) if row["customer_accounts"] is not None else None,
                guest_checkout=bool(row["guest_checkout"]) if row["guest_checkout"] is not None else None,
                timeline_months=row["timeline_months"],
                budget_min=row["budget_min"],
                budget_max=row["budget_max"],
                additional_requirements=row["additional_requirements"],
                inferred_business_type=row["inferred_business_type"],
                classification=row["classification"],
                score=row["score"],
                reasons=reasons_list,
                transcript=row["transcript"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        finally:
            conn.close()

    def list_leads(self, limit: int = 50) -> List[LeadRecord]:
        """Lists recent leads up to the given limit."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            leads = []
            for row in rows:
                reasons_list = json.loads(row["reasons"]) if row["reasons"] else []
                leads.append(LeadRecord(
                    id=row["id"],
                    call_id=row["call_id"],
                    phone_number=row["phone_number"],
                    business_type=row["business_type"],
                    product_count_min=row["product_count_min"],
                    product_count_max=row["product_count_max"],
                    payment_gateway=bool(row["payment_gateway"]) if row["payment_gateway"] is not None else None,
                    customer_accounts=bool(row["customer_accounts"]) if row["customer_accounts"] is not None else None,
                    guest_checkout=bool(row["guest_checkout"]) if row["guest_checkout"] is not None else None,
                    timeline_months=row["timeline_months"],
                    budget_min=row["budget_min"],
                    budget_max=row["budget_max"],
                    additional_requirements=row["additional_requirements"],
                    inferred_business_type=row["inferred_business_type"],
                    classification=row["classification"],
                    score=row["score"],
                    reasons=reasons_list,
                    transcript=row["transcript"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                ))
            return leads
        finally:
            conn.close()

    def save_callback(self, cb: CallbackRecord) -> int:
        """Saves a scheduled callback."""
        tz = zoneinfo.ZoneInfo(TIMEZONE or "Asia/Kolkata")
        now_str = datetime.now(tz).isoformat()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO callbacks (
                    call_id, phone_number, raw_request, scheduled_time, timezone, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cb.call_id,
                cb.phone_number,
                cb.raw_request,
                cb.scheduled_time,
                cb.timezone,
                cb.status,
                now_str,
            ))
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def get_callbacks_by_call_id(self, call_id: int) -> List[CallbackRecord]:
        """Retrieves callbacks for a call ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM callbacks WHERE call_id = ?", (call_id,))
            rows = cursor.fetchall()
            return [
                CallbackRecord(
                    id=r["id"],
                    call_id=r["call_id"],
                    phone_number=r["phone_number"],
                    raw_request=r["raw_request"],
                    scheduled_time=r["scheduled_time"],
                    timezone=r["timezone"],
                    status=r["status"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def save_followup(self, fu: FollowupRecord) -> int:
        """Saves a follow-up record."""
        tz = zoneinfo.ZoneInfo(TIMEZONE or "Asia/Kolkata")
        now_str = datetime.now(tz).isoformat()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO followups (
                    call_id, phone_number, message, channel, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                fu.call_id,
                fu.phone_number,
                fu.message,
                fu.channel,
                fu.status,
                now_str,
            ))
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def get_followups_by_call_id(self, call_id: int) -> List[FollowupRecord]:
        """Retrieves follow-ups for a call ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM followups WHERE call_id = ?", (call_id,))
            rows = cursor.fetchall()
            return [
                FollowupRecord(
                    id=r["id"],
                    call_id=r["call_id"],
                    phone_number=r["phone_number"],
                    message=r["message"],
                    channel=r["channel"],
                    status=r["status"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()
