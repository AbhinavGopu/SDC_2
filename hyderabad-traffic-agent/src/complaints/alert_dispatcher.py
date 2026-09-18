from datetime import datetime, timezone
from typing import Dict, Any, List

class AlertDispatcher:
    """
    Alert and notification dispatcher for urgent citizen grievances.
    Notifies assigned GHMC and Traffic Police ward planners.
    """

    _ALERT_LOG: List[Dict[str, Any]] = []

    def dispatch_alert(self, complaint_id: int, ward_id: int, title: str, severity: str, authority: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        alert_entry = {
            "alert_id": f"ALT-{ward_id}-{int(now.timestamp())}",
            "complaint_id": complaint_id,
            "ward_id": ward_id,
            "title": title,
            "severity": severity,
            "routed_authority": authority,
            "timestamp": now.isoformat(),
            "status": "DISPATCHED" if severity == "high" else "LOGGED"
        }
        self._ALERT_LOG.append(alert_entry)
        return alert_entry

    def get_recent_alerts(self, ward_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        alerts = self._ALERT_LOG
        if ward_id is not None:
            alerts = [a for a in alerts if a["ward_id"] == ward_id]
        return list(reversed(alerts[-limit:]))
