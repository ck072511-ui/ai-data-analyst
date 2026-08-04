import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("app.notifications")


class NotificationService:
    def __init__(self):
        # Maps user_id -> list of unread notification dicts
        self._unread_notifications: Dict[str, List[Dict[str, Any]]] = {}

    def send_notification(self, user_id: str, title: str, message: str, severity: str = "info"):
        """Log structured notification and queue for user polling"""
        log_data = {"extra_info": {"user_id": user_id, "title": title, "message": message, "severity": severity}}
        logger.info(f"Notification: {title} - {message}", extra=log_data)

        if user_id not in self._unread_notifications:
            self._unread_notifications[user_id] = []

        self._unread_notifications[user_id].append(
            {"title": title, "message": message, "severity": severity, "timestamp": datetime.utcnow().isoformat() + "Z"}
        )

    def get_unread(self, user_id: str) -> List[Dict[str, Any]]:
        notifications = self._unread_notifications.pop(user_id, [])
        return notifications


notification_service = NotificationService()
