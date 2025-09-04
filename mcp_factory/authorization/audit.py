"""
Permission audit logging system

Records all permission-related operations to meet security compliance requirements and troubleshooting needs
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .config import get_default_audit_db_path, get_default_audit_log_path

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types"""

    PERMISSION_CHECK = "permission_check"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    TEMPORARY_PERMISSION_GRANTED = "temp_permission_granted"
    TEMPORARY_PERMISSION_EXPIRED = "temp_permission_expired"
    LOGIN_ATTEMPT = "login_attempt"
    ACCESS_DENIED = "access_denied"
    SYSTEM_CONFIG_CHANGED = "system_config_changed"


class AuditResult(Enum):
    """Audit results"""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"


@dataclass
class AuditEvent:
    """Audit event"""

    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: str
    result: AuditResult
    resource: str | None = None
    action: str | None = None
    scope: str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    session_id: str | None = None
    duration_ms: int | None = None
    error_message: str | None = None


class AuditLogger:
    """Permission audit logger"""

    def __init__(self, db_path: str | None = None, enable_file_log: bool = True, log_file_path: str | None = None):
        """
        Initialize audit logger

        Args:
            db_path: Audit database path
            enable_file_log: Whether to enable file logging
            log_file_path: Log file path
        """
        self.db_path = db_path or get_default_audit_db_path()
        self.enable_file_log = enable_file_log
        self.log_file_path = log_file_path or get_default_audit_log_path()

        # Initialize database
        self._init_database()

        # Initialize file logging
        if self.enable_file_log:
            self._init_file_logger()

    def _init_database(self) -> None:
        """Initialize audit database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create audit events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    result TEXT NOT NULL,
                    resource TEXT,
                    action TEXT,
                    scope TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    session_id TEXT,
                    duration_ms INTEGER,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_events(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_events(result)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource)")

            conn.commit()
            conn.close()

            logger.info(f"Audit database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")
            raise

    def _init_file_logger(self) -> None:
        """Initialize file logger"""
        try:
            # Create dedicated audit logger
            self.file_logger = logging.getLogger("mcp_audit")
            self.file_logger.setLevel(logging.INFO)

            # Avoid duplicate handlers
            if not self.file_logger.handlers:
                # Create file handler
                file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
                file_handler.setLevel(logging.INFO)

                # Set format
                formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
                file_handler.setFormatter(formatter)

                self.file_logger.addHandler(file_handler)
                # Prevent log propagation to root logger
                self.file_logger.propagate = False

            logger.info(f"Audit file logger initialized: {self.log_file_path}")
        except Exception as e:
            logger.error(f"Failed to initialize audit file logger: {e}")

    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = int(time.time() * 1000000)  # Microsecond timestamp
        return f"audit_{timestamp}"

    def log_permission_check(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str,
        result: bool,
        duration_ms: int | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Record permission check event"""
        audit_result = AuditResult.SUCCESS if result else AuditResult.DENIED

        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.PERMISSION_CHECK,
            timestamp=datetime.now(),
            user_id=user_id,
            result=audit_result,
            resource=resource,
            action=action,
            scope=scope,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
            duration_ms=duration_ms,
        )

        self._write_audit_event(event)

    def log_role_change(
        self,
        user_id: str,
        role: str,
        action: str,  # "assigned" or "removed"
        operator_id: str,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Record role change event"""
        event_type = AuditEventType.ROLE_ASSIGNED if action == "assigned" else AuditEventType.ROLE_REMOVED

        details = {"role": role, "operator_id": operator_id}
        if reason:
            details["reason"] = reason

        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            result=AuditResult.SUCCESS,
            resource="role",
            action=action,
            scope=role,
            details=details,
            ip_address=ip_address,
        )

        self._write_audit_event(event)

    def log_access_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str,
        reason: str,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Record access denied event"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.ACCESS_DENIED,
            timestamp=datetime.now(),
            user_id=user_id,
            result=AuditResult.DENIED,
            resource=resource,
            action=action,
            scope=scope,
            details={"reason": reason},
            ip_address=ip_address,
            session_id=session_id,
        )

        self._write_audit_event(event)

    def log_temporary_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str,
        operation: str,  # "granted" or "expired"
        expires_at: datetime | None = None,
        granted_by: str | None = None,
    ) -> None:
        """Record temporary permission event"""
        event_type = (
            AuditEventType.TEMPORARY_PERMISSION_GRANTED
            if operation == "granted"
            else AuditEventType.TEMPORARY_PERMISSION_EXPIRED
        )

        details = {"operation": operation}
        if expires_at:
            details["expires_at"] = expires_at.isoformat()
        if granted_by:
            details["granted_by"] = granted_by

        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            result=AuditResult.SUCCESS,
            resource=resource,
            action=action,
            scope=scope,
            details=details,
        )

        self._write_audit_event(event)

    def log_system_event(
        self,
        user_id: str,
        event_type: AuditEventType,
        details: dict[str, Any],
        result: AuditResult = AuditResult.SUCCESS,
        ip_address: str | None = None,
    ) -> None:
        """Record system event"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            result=result,
            details=details,
            ip_address=ip_address,
        )

        self._write_audit_event(event)

    def _write_audit_event(self, event: AuditEvent) -> None:
        """Write audit event"""
        try:
            # Write to database
            self._write_to_database(event)

            # Write to file log
            if self.enable_file_log:
                self._write_to_file(event)

        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")

    def _write_to_database(self, event: AuditEvent) -> None:
        """Write to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO audit_events
                (event_id, event_type, timestamp, user_id, result, resource, action, scope,
                 details, ip_address, user_agent, session_id, duration_ms, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.user_id,
                    event.result.value,
                    event.resource,
                    event.action,
                    event.scope,
                    json.dumps(event.details) if event.details else None,
                    event.ip_address,
                    event.user_agent,
                    event.session_id,
                    event.duration_ms,
                    event.error_message,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to write audit event to database: {e}")

    def _write_to_file(self, event: AuditEvent) -> None:
        """Write to file log"""
        try:
            # Build log message
            log_parts = [
                f"EVENT_ID={event.event_id}",
                f"TYPE={event.event_type.value}",
                f"USER={event.user_id}",
                f"RESULT={event.result.value}",
            ]

            if event.resource:
                log_parts.append(f"RESOURCE={event.resource}")
            if event.action:
                log_parts.append(f"ACTION={event.action}")
            if event.scope:
                log_parts.append(f"SCOPE={event.scope}")
            if event.ip_address:
                log_parts.append(f"IP={event.ip_address}")
            if event.duration_ms:
                log_parts.append(f"DURATION={event.duration_ms}ms")
            if event.details:
                log_parts.append(f"DETAILS={json.dumps(event.details)}")

            log_message = " | ".join(log_parts)
            self.file_logger.info(log_message)

        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")

    def query_events(
        self,
        user_id: str | None = None,
        event_type: AuditEventType | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        result: AuditResult | None = None,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """Query audit events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM audit_events WHERE 1=1"
            params: list[Any] = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            if result:
                query += " AND result = ?"
                params.append(result.value)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Convert to AuditEvent objects
            events = []
            for row in rows:
                event = AuditEvent(
                    event_id=row[0],
                    event_type=AuditEventType(row[1]),
                    timestamp=datetime.fromisoformat(row[2]),
                    user_id=row[3],
                    result=AuditResult(row[4]),
                    resource=row[5],
                    action=row[6],
                    scope=row[7],
                    details=json.loads(row[8]) if row[8] else None,
                    ip_address=row[9],
                    user_agent=row[10],
                    session_id=row[11],
                    duration_ms=row[12],
                    error_message=row[13],
                )
                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return []

    def get_audit_stats(self, days: int = 7) -> dict[str, Any]:
        """Get audit statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Time range
            end_time = datetime.now()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = start_time.replace(day=start_time.day - days + 1)

            stats = {}

            # Total events
            cursor.execute("SELECT COUNT(*) FROM audit_events WHERE timestamp >= ?", (start_time.isoformat(),))
            stats["total_events"] = cursor.fetchone()[0]

            # Statistics by event type
            cursor.execute(
                "SELECT event_type, COUNT(*) FROM audit_events WHERE timestamp >= ? GROUP BY event_type",
                (start_time.isoformat(),),
            )
            stats["events_by_type"] = dict(cursor.fetchall())

            # Statistics by result
            cursor.execute(
                "SELECT result, COUNT(*) FROM audit_events WHERE timestamp >= ? GROUP BY result",
                (start_time.isoformat(),),
            )
            stats["events_by_result"] = dict(cursor.fetchall())

            # Statistics by user (top 10)
            cursor.execute(
                "SELECT user_id, COUNT(*) FROM audit_events WHERE timestamp >= ? GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 10",
                (start_time.isoformat(),),
            )
            stats["top_users"] = dict(cursor.fetchall())

            # Failed events
            cursor.execute(
                "SELECT COUNT(*) FROM audit_events WHERE timestamp >= ? AND result IN ('failure', 'denied', 'error')",
                (start_time.isoformat(),),
            )
            stats["failed_events"] = cursor.fetchone()[0]

            conn.close()
            return stats

        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            return {}

    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """Clean up old audit events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate cutoff time
            cutoff_time = datetime.now().replace(day=datetime.now().day - days_to_keep)

            cursor.execute("DELETE FROM audit_events WHERE timestamp < ?", (cutoff_time.isoformat(),))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old audit events (older than {days_to_keep} days)")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old audit events: {e}")
            return 0


# Global audit logger instance
_global_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _global_audit_logger

    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()

    return _global_audit_logger


def configure_audit_logger(
    db_path: str | None = None, enable_file_log: bool = True, log_file_path: str | None = None
) -> None:
    """Configure global audit logger"""
    global _global_audit_logger
    _global_audit_logger = AuditLogger(db_path=db_path, enable_file_log=enable_file_log, log_file_path=log_file_path)
    logger.info(f"Global audit logger configured: db={db_path}, file_log={enable_file_log}")
