from __future__ import annotations

from datetime import datetime
import re

from dao.QueueDao import QueueDao, QueueRecord

queue_dao = QueueDao()

TERMINAL_BRACKET_STATUSES = {"complete", "cancelled"}
META_SUFFIX = "META"
_MESSAGE_URL_RE = re.compile(r"channels/([^/]+)/messages/([^/?\s]+)", re.IGNORECASE)


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


def _result_channel_key(record: QueueRecord) -> str | None:
    result_channel_id = getattr(record, "result_channel_id", None)
    if result_channel_id is None:
        return None
    return str(result_channel_id)


def _sanitize_result_channel_in_memory(record: QueueRecord) -> str | None:
    """Remove the results channel from a live queue board's channel_config.

    Match-completion messages belong in result_channel_id, but the live queue
    board does not. Older queue records can contain the results channel in
    channel_config, which makes every join/leave update mirror the live board
    into both channels.

    Returns the stale queue-board message ID that was removed, if any.
    """
    result_key = _result_channel_key(record)
    if result_key is None:
        return None

    if record.channel_config is None:
        record.channel_config = {}

    stale_message_id = record.channel_config.pop(result_key, None)
    if stale_message_id is None:
        return None

    if str(getattr(record, "channel_id", "")) == result_key:
        fallback = next(iter(record.channel_config.items()), (None, None))
        record.channel_id = fallback[0]
        record.message_id = fallback[1]

    return stale_message_id


def remove_result_channel_queue_board(
    record: QueueRecord,
    inter=None,
    max_retries: int = 4,
) -> tuple[QueueRecord, bool]:
    """Persistently remove a live queue board from the configured results channel.

    If a stale queue board exists there, we also try to delete that Discord
    message. Deletion failures are non-fatal because the important part is
    removing the channel from channel_config so it is never updated/recreated.
    """
    initial_result_key = _result_channel_key(record)
    if initial_result_key is None or initial_result_key not in (record.channel_config or {}):
        return record, False

    stale_message_id = (record.channel_config or {}).get(initial_result_key)
    if inter is not None and stale_message_id:
        try:
            inter.delete_message(
                channel_id=initial_result_key,
                message_id=stale_message_id,
            )
        except Exception as exc:
            print(
                f"[Queue repair] Could not delete stale results-channel queue "
                f"message {stale_message_id}: {exc}"
            )

    latest = record
    for _ in range(max_retries):
        current = queue_dao.get_queue_or_none(record.guild_id, record.queue_id)
        if current is None:
            _sanitize_result_channel_in_memory(latest)
            return latest, True

        latest = current
        result_key = _result_channel_key(current)
        if result_key is None or result_key not in (current.channel_config or {}):
            return current, True

        _sanitize_result_channel_in_memory(current)
        if queue_dao.put_queue(current) is not None:
            refreshed = queue_dao.get_queue_or_none(record.guild_id, record.queue_id)
            return (refreshed if refreshed is not None else current), True

    # Keep the caller's in-memory view clean even if OCC repeatedly collided.
    _sanitize_result_channel_in_memory(latest)
    print(
        f"[Queue repair] WARNING: could not persist results-channel cleanup "
        f"for queue {record.queue_id}."
    )
    return latest, False


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

        result_key = _result_channel_key(current)
        if result_key is not None and str(new_channel_id) == result_key:
            # Never turn the results channel into a live queue-board destination.
            _sanitize_result_channel_in_memory(current)
            queue_dao.put_queue(current)
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


def recover_missing_queue_message(
    record: QueueRecord,
    embeds,
    components,
    inter,
    exc: Exception,
) -> None:
    """Recover only the queue board that caused a Discord 404 edit failure.

    The normal queue update path remains in QueueManager. ButtonManager calls this
    helper only after that path raises. The channel/message pair is extracted from
    Discord's failed request URL when available, preventing duplicate replacement
    boards in other channels.
    """
    if not _is_missing_discord_message(exc):
        raise exc

    result_key = _result_channel_key(record)
    match = _MESSAGE_URL_RE.search(str(exc))
    if match:
        targets = [(match.group(1), match.group(2))]
    else:
        targets = list((record.channel_config or {}).items())

    if result_key is not None:
        targets = [
            (channel_id, message_id)
            for channel_id, message_id in targets
            if str(channel_id) != result_key
        ]

    if not targets:
        # A missing queue board in the results channel is intentionally not
        # recreated. Clean the stale destination instead.
        remove_result_channel_queue_board(record, inter=inter)
        return

    for channel_id, message_id in targets:
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


def update_queue_view_with_recovery(
    record: QueueRecord,
    embeds,
    components,
    inter,
) -> None:
    """Standalone updater used by regression tests and maintenance code.

    Production button handlers keep QueueManager's established update behavior and
    call ``recover_missing_queue_message`` only if Discord reports a missing
    message. This helper remains useful when a caller wants the same behavior in
    one operation.
    """
    record, _ = remove_result_channel_queue_board(record, inter=inter)

    expired = int(datetime.utcnow().timestamp()) > record.expiry
    if expired:
        record.update_expiry_date()
        queue_dao.put_queue(record)

    for channel_id, message_id in list((record.channel_config or {}).items()):
        try:
            if expired:
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
        except Exception as update_exc:
            recover_missing_queue_message(
                record, embeds, components, inter, update_exc
            )
            continue

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
