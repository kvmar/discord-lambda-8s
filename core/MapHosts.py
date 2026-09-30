"""Assign map hosts once per match and display the saved assignments."""

import random

from dao.QueueDao import QueueRecord


def assign_map_hosts(record: QueueRecord) -> None:
    # Captains may appear in both the queue and a team during manual picking.
    players = list(dict.fromkeys(record.queue + record.team_1 + record.team_2))
    record.map_hosts = [random.choice(players) for _ in record.maps] if players else []


def format_maps(record: QueueRecord, limit: int = None) -> str:
    lines = []
    for index, map_name in enumerate(record.maps[:limit]):
        host = record.map_hosts[index] if index < len(record.map_hosts) else None
        host_label = f" — Host: <@{host}>" if host else ""
        lines.append(f"• {map_name}{host_label}")
    return "\n".join(lines) or "TBD"
