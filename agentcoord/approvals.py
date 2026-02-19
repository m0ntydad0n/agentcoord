"""
Approval workflow system for blocking operations.
"""

import json
import uuid
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class Approval:
    """Represents an approval request."""
    id: str
    requested_by: str
    action_type: str  # "commit", "deploy", "architectural_change"
    description: str
    status: ApprovalStatus
    requested_at: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class ApprovalWorkflow:
    """Manages approval requests and responses."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def request_approval(
        self,
        agent_id: str,
        action_type: str,
        description: str,
        timeout: int = 300  # 5 minutes default
    ) -> Approval:
        """
        Request approval and block until approved/rejected/timeout.

        Publishes to channel:approval:requests for other agents to see.
        Polls every second for approval status.
        """
        approval = Approval(
            id=str(uuid.uuid4()),
            requested_by=agent_id,
            action_type=action_type,
            description=description,
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(timezone.utc).isoformat()
        )

        # Store approval request
        approval_key = f"approval:{approval.id}"
        self.redis.hset(approval_key, mapping={
            "id": approval.id,
            "requested_by": approval.requested_by,
            "action_type": approval.action_type,
            "description": approval.description,
            "status": approval.status.value,
            "requested_at": approval.requested_at,
            "approved_by": "",
            "approved_at": ""
        })
        self.redis.expire(approval_key, timeout + 60)  # Cleanup after timeout

        # Publish notification
        self.redis.publish("channel:approval:requests", json.dumps({
            "approval_id": approval.id,
            "requested_by": agent_id,
            "action_type": action_type,
            "description": description
        }))

        logger.info(f"Approval requested: {approval.id} by {agent_id} for {action_type}")

        # Block and poll for approval
        start_time = time.time()
        while True:
            # Check current status
            data = self.redis.hgetall(approval_key)
            if data:
                status = ApprovalStatus(data["status"])
                if status == ApprovalStatus.APPROVED:
                    approval.status = status
                    approval.approved_by = data.get("approved_by")
                    approval.approved_at = data.get("approved_at")
                    logger.info(f"Approval {approval.id} approved by {approval.approved_by}")
                    return approval
                elif status == ApprovalStatus.REJECTED:
                    approval.status = status
                    logger.info(f"Approval {approval.id} rejected")
                    return approval

            # Check timeout
            if time.time() - start_time > timeout:
                self.redis.hset(approval_key, "status", ApprovalStatus.TIMEOUT.value)
                approval.status = ApprovalStatus.TIMEOUT
                logger.warning(f"Approval {approval.id} timed out after {timeout}s")
                return approval

            # Wait before next poll
            time.sleep(1)

    def approve(self, approval_id: str, approver_id: str):
        """Approve a pending request."""
        approval_key = f"approval:{approval_id}"
        data = self.redis.hgetall(approval_key)
        if not data:
            raise ValueError(f"Approval {approval_id} not found")

        self.redis.hset(approval_key, mapping={
            "status": ApprovalStatus.APPROVED.value,
            "approved_by": approver_id,
            "approved_at": datetime.now(timezone.utc).isoformat()
        })

        logger.info(f"Approval {approval_id} approved by {approver_id}")

    def reject(self, approval_id: str, approver_id: str):
        """Reject a pending request."""
        approval_key = f"approval:{approval_id}"
        data = self.redis.hgetall(approval_key)
        if not data:
            raise ValueError(f"Approval {approval_id} not found")

        self.redis.hset(approval_key, mapping={
            "status": ApprovalStatus.REJECTED.value,
            "approved_by": approver_id,
            "approved_at": datetime.now(timezone.utc).isoformat()
        })

        logger.info(f"Approval {approval_id} rejected by {approver_id}")

    def list_pending_approvals(self):
        """List all pending approvals."""
        approvals = []
        for key in self.redis.keys("approval:*"):
            data = self.redis.hgetall(key)
            if data and data.get("status") == ApprovalStatus.PENDING.value:
                approvals.append(Approval(
                    id=data["id"],
                    requested_by=data["requested_by"],
                    action_type=data["action_type"],
                    description=data["description"],
                    status=ApprovalStatus(data["status"]),
                    requested_at=data["requested_at"],
                    approved_by=data.get("approved_by") or None,
                    approved_at=data.get("approved_at") or None
                ))
        return approvals
