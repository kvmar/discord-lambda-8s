from __future__ import annotations

from datetime import datetime

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
    has ``is_bracket=True`` and an old ``tournament_id``. This helper safely
    repairs that split-brain state with bounded optimistic-concurrency retries.

    Returns ``(queue_record, repaired, bracket_status)``.

    A missing META record is intentionally *not* cleared here. During bracket
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


def _is_missing_discord_message(exc: Exception) -> bool:
    """Return True only for the Discord missing-message failure we can repair."""
    text = str(exc).lower()
    return "404" in text and ("not found" in text or "/messages/" in text)


def _save_message_location(
    guild_id: str,
    queue_id: str,
    old_channel_id: str,
    new_channel_id: str,
    new_message_id: str,
    max_retries: int = 4,
) -> bool:
    """Persist a replacement queue-board message without clobbering queue state."""
    for _ in range(max_retries):
        current = queue_dao.get_queue_or_none(guild_id, queue_id)
        if current is None:
            return False

        if current.channel_config is None:
            current.channel_config = {}
        if old_channel_id != new_channel_id:
            current.channel_config.pop(old_channel_id, None)
        current.channel_config[new_channel_id] = new_message_id
        current.channel_id = new_channel_id
        current.message_id = new_message_id

        if queue_dao.put_queue(current) is not None:
            return True

    return False


def update_queue_view_with_recovery(
    record: QueueRecord,
    embeds,
    components,
    inter,
) -> None:
    """Update every live queue board and recreate any board Discord deleted.

    ``QueueManager.update_queue_view`` previously allowed a stale message ID in
    DynamoDB to make every button click fail with Discord 404. This version
    keeps the existing expiry behavior, but if a normal message edit reports
    404 it posts a replacement board and atomically stores the new message ID.
    Other Discord/API failures still raise normally instead of being hidden.
    """
    expired = int(datetime.utcnow().timestamp()) > record.expiry
    if expired:
        record.update_expiry_date()
        # Expiry is advisory. A collision here should not stop the actual UI
        # update; the message-location write below re-reads the newest record.
        queue_dao.put_queue(record)

    for channel_id, message_id in list((record.channel_config or {}).items()):
        try:
            if expired:
                # Existing behavior: old interaction-backed boards are replaced.
                resp = inter.edit_response(
                    channel_id=channel_id,
                    message_id=message_id,
                    embeds=embeds,
                    components=components,
                )
            else:
                resp = inter.edit_message(
                    channel_id=channel_id,
                    message_id=message_id,
                    embeds=embeds,
                    components=components,
                )
        except Exception as exc:
            if not _is_missing_discord_message(exc):
                raise

            print(
                f"[Queue repair] Discord message {message_id} in channel "
                f"{channel_id} is gone; creating a replacement."
            )
            resp = inter.send_message(
                channel_id=channel_id,
                embeds=embeds,
                components=components,
            )

        if not resp:
            continue

        new_message_id, new_channel_id = resp[0], resp[1]
        saved = _save_message_location(
            record.guild_id,
            record.queue_id,
            channel_id,
            new_channel_id,
            new_message_id,
        )
        if not saved:
            print(
                f"[Queue repair] WARNING: could not persist message "
                f"{new_message_id} for queue {record.queue_id}."
            )
