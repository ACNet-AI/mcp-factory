"""
SaaS Service - SaaS mode permission request and workflow management

This module handles permission requests, approval workflows,
and user self-service functionality for SaaS deployments.
"""

import logging
import sqlite3
import time
from typing import Any

from .audit import get_audit_logger
from .models import DEFAULT_ROLES

logger = logging.getLogger(__name__)


class SaaSService:
    """SaaS permission request and workflow management service"""

    def __init__(self, enforcer: Any, db_path: str, role_service: Any, enable_audit: bool = True) -> None:
        """
        Initialize SaaS service

        Args:
            enforcer: Casbin enforcer instance
            db_path: Database path
            role_service: Role service instance
            enable_audit: Whether to enable audit logging
        """
        self.enforcer = enforcer
        self.db_path = db_path
        self.role_service = role_service
        self.enable_audit = enable_audit

        # Initialize audit logging
        self.audit_logger = get_audit_logger() if enable_audit else None

        # Initialize database tables
        self._init_saas_tables()

    def _init_saas_tables(self) -> None:
        """Initialize SaaS-specific database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create permission request table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS permission_requests (
                    request_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    requested_role TEXT NOT NULL,
                    current_roles TEXT,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    review_comment TEXT
                )
            """)

            conn.commit()
            conn.close()
            logger.debug("SaaS database tables initialized")

        except Exception as e:
            logger.error(f"Error initializing SaaS tables: {e}")
            raise

    def submit_permission_request(self, user_id: str, requested_role: str, reason: str = "") -> str:
        """
        User submits permission request

        Args:
            user_id: Requesting User ID
            requested_role: Requested role
            reason: Request reason

        Returns:
            str: Request ID
        """
        try:
            import uuid

            request_id = f"req_{int(time.time())}_{uuid.uuid4().hex[:8]}"

            # Check if role exists
            if requested_role not in DEFAULT_ROLES:
                raise ValueError(f"Invalid role: {requested_role}")

            # Check user's current roles
            current_roles = self.role_service.get_user_roles(user_id)
            if requested_role in current_roles:
                raise ValueError(f"User already has role: {requested_role}")

            # Save request to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Insert request record
            cursor.execute(
                """
                INSERT INTO permission_requests
                (request_id, user_id, requested_role, current_roles, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, user_id, requested_role, ",".join(current_roles), reason),
            )

            conn.commit()
            conn.close()

            # Record audit log
            if self.audit_logger:
                from .audit import AuditEventType

                self.audit_logger.log_system_event(
                    user_id=user_id,
                    event_type=AuditEventType.PERMISSION_GRANTED,  # Reuse existing type
                    details={
                        "action": "permission_request_submitted",
                        "request_id": request_id,
                        "requested_role": requested_role,
                        "reason": reason,
                    },
                )

            logger.info(f"Permission request submitted: {request_id} by {user_id} for {requested_role}")
            return request_id

        except Exception as e:
            logger.error(f"Error submitting permission request: {e}")
            raise

    def get_permission_requests(self, user_id: str | None = None, status: str | None = None) -> list[dict]:
        """
        Get permission request list

        Args:
            user_id: User ID (empty to get all users' requests)
            status: Request status (pending, approved, rejected)

        Returns:
            list[dict]: Request list
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM permission_requests WHERE 1=1"
            params: list[Any] = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY submitted_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Convert to dictionary format
            columns = [desc[0] for desc in cursor.description]
            requests = []
            for row in rows:
                request_dict = dict(zip(columns, row, strict=False))
                requests.append(request_dict)

            return requests

        except Exception as e:
            logger.error(f"Error getting permission requests: {e}")
            return []

    def review_permission_request(self, request_id: str, reviewer_id: str, action: str, comment: str = "") -> bool:
        """
        Review permission request

        Args:
            request_id: Request ID
            reviewer_id: Reviewer ID
            action: Review action (approve, reject)
            comment: Review comment

        Returns:
            bool: Whether successful
        """
        try:
            if action not in ["approve", "reject"]:
                raise ValueError("Action must be 'approve' or 'reject'")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get request information
            cursor.execute("SELECT * FROM permission_requests WHERE request_id = ?", (request_id,))
            request_row = cursor.fetchone()

            if not request_row:
                conn.close()
                raise ValueError(f"Request not found: {request_id}")

            # Parse request information
            columns = [desc[0] for desc in cursor.description]
            request_data = dict(zip(columns, request_row, strict=False))

            if request_data["status"] != "pending":
                conn.close()
                raise ValueError(f"Request already reviewed: {request_data['status']}")

            # Update request status
            new_status = "approved" if action == "approve" else "rejected"
            cursor.execute(
                """
                UPDATE permission_requests
                SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, review_comment = ?
                WHERE request_id = ?
                """,
                (new_status, reviewer_id, comment, request_id),
            )

            success = False

            # If approved, assign role
            if action == "approve":
                success = self.role_service.assign_role(
                    request_data["user_id"],
                    request_data["requested_role"],
                    reviewer_id,
                    f"Approved request {request_id}: {comment}",
                )
            else:
                success = True  # Rejection operation is always successful

            if success:
                conn.commit()

                # Record audit log
                if self.audit_logger:
                    from .audit import AuditEventType

                    self.audit_logger.log_system_event(
                        user_id=reviewer_id,
                        event_type=AuditEventType.PERMISSION_GRANTED
                        if action == "approve"
                        else AuditEventType.ACCESS_DENIED,
                        details={
                            "action": f"permission_request_{action}d",
                            "request_id": request_id,
                            "target_user": request_data["user_id"],
                            "requested_role": request_data["requested_role"],
                            "comment": comment,
                        },
                    )

                logger.info(f"Permission request {action}d: {request_id} by {reviewer_id}")
            else:
                conn.rollback()
                logger.error(f"Failed to {action} permission request: {request_id}")

            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error reviewing permission request: {e}")
            return False

    def get_user_permission_summary(self, user_id: str) -> dict:
        """
        Get user permission summary (for SaaS users to view their own permission status)

        Args:
            user_id: User ID

        Returns:
            dict: Permission summary
        """
        try:
            # Get user roles
            roles = self.role_service.get_user_roles(user_id)

            # Get permission list
            permissions = []
            limitations = {}

            for role in roles:
                if role in DEFAULT_ROLES:
                    role_info = DEFAULT_ROLES[role]
                    for perm in role_info["permissions"]:  # type: ignore[attr-defined]
                        # Type hint for MyPy - cast to MCPPermission
                        permission = perm
                        perm_str = f"{permission.resource}:{permission.action}:{permission.scope}"
                        if perm_str not in permissions:
                            permissions.append(perm_str)

                    # Merge limitation information
                    role_limitations = role_info.get("limitations", {})
                    for key, value in role_limitations.items():  # type: ignore[attr-defined]
                        if key not in limitations or value == "unlimited":
                            limitations[key] = value

            # Get pending requests
            pending_requests = self.get_permission_requests(user_id=user_id, status="pending")

            # Get recent request history
            recent_requests = self.get_permission_requests(user_id=user_id)[:5]

            return {
                "user_id": user_id,
                "current_roles": roles,
                "permissions": permissions,
                "limitations": limitations,
                "pending_requests": len(pending_requests),
                "recent_requests": recent_requests,
            }

        except Exception as e:
            logger.error(f"Error getting user permission summary: {e}")
            return {"error": str(e)}

    def get_request_statistics(self, days: int = 30) -> dict[str, Any]:
        """
        Get permission request statistics

        Args:
            days: Number of days to analyze

        Returns:
            dict: Statistics data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get total requests in the period
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM permission_requests
                WHERE submitted_at >= datetime('now', '-{days} days')
                """
            )
            total_requests = cursor.fetchone()[0]

            # Get requests by status
            cursor.execute(
                f"""
                SELECT status, COUNT(*) FROM permission_requests
                WHERE submitted_at >= datetime('now', '-{days} days')
                GROUP BY status
                """
            )
            status_stats = dict(cursor.fetchall())

            # Get requests by role
            cursor.execute(
                f"""
                SELECT requested_role, COUNT(*) FROM permission_requests
                WHERE submitted_at >= datetime('now', '-{days} days')
                GROUP BY requested_role
                ORDER BY COUNT(*) DESC
                """
            )
            role_stats = dict(cursor.fetchall())

            # Get average processing time for approved/rejected requests
            cursor.execute(
                f"""
                SELECT AVG(
                    (julianday(reviewed_at) - julianday(submitted_at)) * 24 * 60
                ) as avg_minutes
                FROM permission_requests
                WHERE status IN ('approved', 'rejected')
                AND submitted_at >= datetime('now', '-{days} days')
                """
            )
            avg_processing_time = cursor.fetchone()[0]

            conn.close()

            return {
                "period_days": days,
                "total_requests": total_requests,
                "status_breakdown": status_stats,
                "role_breakdown": role_stats,
                "average_processing_time_minutes": round(avg_processing_time or 0, 2),
                "approval_rate": round((status_stats.get("approved", 0) / max(total_requests, 1)) * 100, 2),
            }

        except Exception as e:
            logger.error(f"Error getting request statistics: {e}")
            return {"error": str(e)}

    def cleanup_old_requests(self, days_to_keep: int = 365) -> int:
        """
        Clean up old permission requests

        Args:
            days_to_keep: Number of days to keep requests

        Returns:
            int: Number of cleaned up requests
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                f"""
                DELETE FROM permission_requests
                WHERE submitted_at < datetime('now', '-{days_to_keep} days')
                """
            )

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old permission requests")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old requests: {e}")
            return 0

    def get_pending_requests_summary(self) -> dict[str, Any]:
        """
        Get summary of pending requests (for administrators)

        Returns:
            dict: Pending requests summary
        """
        try:
            pending_requests = self.get_permission_requests(status="pending")

            # Group by requested role
            role_counts: dict[str, int] = {}
            user_requests: dict[str, list[dict[str, Any]]] = {}

            for request in pending_requests:
                role = request["requested_role"]
                user_id = request["user_id"]

                role_counts[role] = role_counts.get(role, 0) + 1

                if user_id not in user_requests:
                    user_requests[user_id] = []
                user_requests[user_id].append(request)

            # Find users with multiple pending requests
            multiple_requests_users = {
                user_id: requests for user_id, requests in user_requests.items() if len(requests) > 1
            }

            return {
                "total_pending": len(pending_requests),
                "role_breakdown": role_counts,
                "unique_users": len(user_requests),
                "multiple_requests_users": len(multiple_requests_users),
                "oldest_request": min((req["submitted_at"] for req in pending_requests), default=None),
                "recent_requests": pending_requests[:10],  # Most recent 10 requests
            }

        except Exception as e:
            logger.error(f"Error getting pending requests summary: {e}")
            return {"error": str(e)}

    def auto_approve_requests(self, criteria: dict[str, Any]) -> dict[str, Any]:
        """
        Auto-approve requests based on criteria (for automation)

        Args:
            criteria: Approval criteria (e.g., {"role": "free_user", "max_age_hours": 24})

        Returns:
            dict: Auto-approval results
        """
        try:
            results: dict[str, Any] = {
                "processed": 0,
                "approved": 0,
                "failed": 0,
                "errors": [],
            }

            # Get pending requests
            pending_requests = self.get_permission_requests(status="pending")

            for request in pending_requests:
                try:
                    should_approve = True

                    # Check role criteria
                    if "role" in criteria and request["requested_role"] != criteria["role"]:
                        should_approve = False

                    # Check age criteria
                    if "max_age_hours" in criteria:
                        import datetime

                        submitted_time = datetime.datetime.fromisoformat(request["submitted_at"])
                        age_hours = (datetime.datetime.now() - submitted_time).total_seconds() / 3600
                        if age_hours > criteria["max_age_hours"]:
                            should_approve = False

                    # Check user criteria
                    if "allowed_users" in criteria and request["user_id"] not in criteria["allowed_users"]:
                        should_approve = False

                    if should_approve:
                        success = self.review_permission_request(
                            request["request_id"],
                            "system_auto_approval",
                            "approve",
                            f"Auto-approved based on criteria: {criteria}",
                        )

                        if success:
                            results["approved"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append(f"Failed to approve request {request['request_id']}")

                    results["processed"] += 1

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Error processing request {request.get('request_id', 'unknown')}: {e}")

            logger.info(f"Auto-approval completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Error in auto-approval: {e}")
            return {"error": str(e)}
