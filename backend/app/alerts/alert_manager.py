from typing import Dict, List, Optional
import time
from ..schemas.models import AlertPayload


class AlertManager:
    """
    Alert Manager with alert fatigue control (cooldown / debounce logic)
    and full audit trail payload retention.
    """

    def __init__(self, cooldown_seconds: float = 10.0):
        self.cooldown_ms = int(cooldown_seconds * 1000)
        # Key: f"{alert_type}_{symbol}_{price:.2f}" -> last_trigger_timestamp
        self.last_alerts: Dict[str, int] = {}
        self.audit_log: List[AlertPayload] = []

    def process_alert(self, alert: AlertPayload) -> Optional[AlertPayload]:
        """
        Evaluates alert cooldown. Returns the alert if allowed, or None if debounced.
        """
        key = f"{alert.alert_type}_{alert.symbol}_{alert.price:.2f}"
        last_time = self.last_alerts.get(key, 0)

        if alert.timestamp - last_time < self.cooldown_ms:
            alert.is_debounced = True
            return None

        self.last_alerts[key] = alert.timestamp
        self.audit_log.append(alert)
        return alert

    def get_audit_log(self, limit: int = 100) -> List[AlertPayload]:
        return self.audit_log[-limit:]
