"""Regression tests for stale bracket flags and deleted Discord queue boards."""

from unittest.mock import MagicMock

import pytest

from dao.QueueDao import QueueRecord
import core.StateRepair as StateRepair


def _record(
    queue_id="kali",
    *,
    version=1,
    is_bracket=False,
    tournament_id=None,
    bracket=None,
    channel_config=None,
):
    return QueueRecord(
        guild_id="guild_123",
        money_queue=False,
        queue_id=queue_id,
        team_1=[],
        team_2=[],
        queue=[],
        cancel_votes=[],
        team1_votes=[],
        team2_votes=[],
        maps=[],
        map_set=["Map1"],
        version=version,
        expiry=9999999999,
        result_channel_id="result_ch",
        team_1_channel_id="team1_ch",
        team_2_channel_id="team2_ch",
        message_id=None,
        channel_id=None,
        channel_config={} if channel_config is None else channel_config,
        waitlist=[],
        is_bracket=is_bracket,
        tournament_id=tournament_id,
        bracket_match_id=None,
        bracket=bracket,
    )


def test_completed_bracket_flag_is_cleared(mocker):
    origin = _record(is_bracket=True, tournament_id="abc123")
    meta = _record(
        "BRACKET#abc123#META",
        is_bracket=True,
        tournament_id="abc123",
        bracket={"status": "complete"},
    )
    refreshed = _record(is_bracket=False, tournament_id=None, version=2)

    dao = MagicMock()
    dao.get_queue_or_none.side_effect = [origin, meta, refreshed]
    dao.put_queue.return_value = {"ok": True}
    mocker.patch.object(StateRepair, "queue_dao", dao)

    record, repaired, status = StateRepair.repair_stale_bracket_flag(
        "guild_123", "kali"
    )

    assert repaired is True
    assert status == "complete"
    assert record.is_bracket is False
    assert record.tournament_id is None
    written = dao.put_queue.call_args.args[0]
    assert written.is_bracket is False
    assert written.tournament_id is None


def test_bracket_repair_retries_occ_collision(mocker):
    first_origin = _record(version=4, is_bracket=True, tournament_id="abc123")
    second_origin = _record(version=5, is_bracket=True, tournament_id="abc123")
    meta = _record(
        "BRACKET#abc123#META",
        is_bracket=True,
        tournament_id="abc123",
        bracket={"status": "complete"},
    )
    refreshed = _record(version=6, is_bracket=False, tournament_id=None)

    dao = MagicMock()
    dao.get_queue_or_none.side_effect = [
        first_origin,
        meta,
        second_origin,
        meta,
        refreshed,
    ]
    dao.put_queue.side_effect = [None, {"ok": True}]
    mocker.patch.object(StateRepair, "queue_dao", dao)

    record, repaired, status = StateRepair.repair_stale_bracket_flag(
        "guild_123", "kali"
    )

    assert repaired is True
    assert status == "complete"
    assert record.version == 6
    assert dao.put_queue.call_count == 2


def test_active_bracket_is_never_cleared(mocker):
    origin = _record(is_bracket=True, tournament_id="abc123")
    meta = _record(
        "BRACKET#abc123#META",
        is_bracket=True,
        tournament_id="abc123",
        bracket={"status": "active"},
    )

    dao = MagicMock()
    dao.get_queue_or_none.side_effect = [origin, meta]
    mocker.patch.object(StateRepair, "queue_dao", dao)

    record, repaired, status = StateRepair.repair_stale_bracket_flag(
        "guild_123", "kali"
    )

    assert repaired is False
    assert status == "active"
    assert record.is_bracket is True
    dao.put_queue.assert_not_called()


def test_missing_meta_is_not_cleared_during_possible_startup_race(mocker):
    origin = _record(is_bracket=True, tournament_id="abc123")

    dao = MagicMock()
    dao.get_queue_or_none.side_effect = [origin, None]
    mocker.patch.object(StateRepair, "queue_dao", dao)

    record, repaired, status = StateRepair.repair_stale_bracket_flag(
        "guild_123", "kali"
    )

    assert repaired is False
    assert status is None
    assert record.is_bracket is True
    dao.put_queue.assert_not_called()


def test_deleted_discord_queue_message_is_recreated_and_saved(mocker):
    live = _record(channel_config={"channel_1": "dead_message"})
    stored = _record(channel_config={"channel_1": "dead_message"})

    dao = MagicMock()
    dao.get_queue_or_none.return_value = stored
    dao.put_queue.return_value = {"ok": True}
    mocker.patch.object(StateRepair, "queue_dao", dao)

    inter = MagicMock()
    inter.edit_message.side_effect = Exception(
        "Unable to edit message: 404 Client Error: Not Found for url: "
        "https://discord.com/api/v10/channels/channel_1/messages/dead_message"
    )
    inter.send_message.return_value = ("new_message", "channel_1")

    StateRepair.update_queue_view_with_recovery(
        live, embeds=[MagicMock()], components=[MagicMock()], inter=inter
    )

    inter.send_message.assert_called_once()
    assert stored.channel_config == {"channel_1": "new_message"}
    assert stored.message_id == "new_message"
    assert stored.channel_id == "channel_1"
    dao.put_queue.assert_called_once_with(stored)


def test_non_404_edit_failure_is_not_hidden(mocker):
    live = _record(channel_config={"channel_1": "message_1"})
    dao = MagicMock()
    mocker.patch.object(StateRepair, "queue_dao", dao)

    inter = MagicMock()
    inter.edit_message.side_effect = Exception("500 Internal Server Error")

    with pytest.raises(Exception, match="500 Internal Server Error"):
        StateRepair.update_queue_view_with_recovery(
            live, embeds=[], components=[], inter=inter
        )

    inter.send_message.assert_not_called()
