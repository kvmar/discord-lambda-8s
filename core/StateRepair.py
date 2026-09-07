from __future__ import annotations

from dao.QueueDao import QueueDao, QueueRecord

queue_dao = QueueDao()

TERMINAL_BRACKET_STATUSES = {"complete", "cancelled"}
META_SUFFIX = "META"


def _meta_queue_id(tournament_id: str) -> str:
    return f"BRACKET#{tournament_id}#{META_SUFFIX}"


def repair_stale_bracket_flag(
    guild_id: str,
    queue_id: str,
    max_retries: int = 4,
) -> tuple[QueueRecord | None, bool, str | None]:
    """Clear a queue's bracket flag when the tournament is already finished.

    Bracket completion and queue updates can race in separate Lambda invocations.
    In that case the META record may be terminal while the originating queue still
    has ``is_bracket=True`` and an old ``tournament_id``.  This helper safely
    repairs that split-brain state with bounded optimistic-concurrency retries.

    Returns ``(queue_record, repaired, bracket_status)``.

    A missing META record is intentionally *not* cleared here.  During bracket
    startup the origin queue is stamped before META is created, so automatically
    clearing a temporarily-missing META record could cancel a bracket that is
    still being created.
    """
    last_record = None
    last_status = None

    for _ in range(max_retries):
        origin = queue_dao.get_queue_or_none(guild_id, queue_id)
        last_record = origin
        if origin is None:
            return None, False, None

        tournament_id = getattr(origin, "tournament_id", None)
        if not getattr(origin, "is_bracket", False) or not tournament_id:
            return origin, False, None

        meta = queue_dao.get_queue_or_none(guild_id, _meta_queue_id(tournament_id))
        if meta is None:
            return origin, False, None

        bracket = meta.bracket or {}
        status = bracket.get("status")
        last_status = status
        if status not in TERMINAL_BRACKET_STATUSES:
            return origin, False, status

        # Re-read on every retry so we never overwrite unrelated queue changes.
        origin.is_bracket = False
        origin.tournament_id = None
        result = queue_dao.put_queue(origin)
        if result is not None:
            refreshed = queue_dao.get_queue_or_none(guild_id, queue_id)
            return refreshed if refreshed is not None else origin, True, status

    return last_record, False, last_status
