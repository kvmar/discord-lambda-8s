"""Regression tests for queue rendering and stale results-channel boards."""

from unittest.mock import MagicMock

from dao.PlayerDao import PlayerRecord
from dao.QueueDao import QueueRecord
import core.StateRepair as StateRepair


def _queue_record(channel_config=None, channel_id="queue_ch", message_id="queue_msg"):
    return QueueRecord(
        guild_id="guild_123",
        money_queue=False,
        queue_id="kali",
        team_1=[],
        team_2=[],
        queue=[],
        cancel_votes=[],
        team1_votes=[],
        team2_votes=[],
        maps=[],
        map_set=["Map1", "Map2", "Map3"],
        version=1,
        expiry=9999999999,
        result_channel_id="result_ch",
        team_1_channel_id="team1_ch",
        team_2_channel_id="team2_ch",
        message_id=message_id,
        channel_id=channel_id,
        channel_config=(
            {"queue_ch": "queue_msg"}
            if channel_config is None
            else channel_config
        ),
        waitlist=[],
    )


def test_legacy_string_player_fields_render_safely():
    """Old Dynamo rows with string numerics must not crash queue rendering."""
    player = PlayerRecord(
        guild_id="guild_123",
        player_id="player_1",
        player_name="LegacyPlayer",
        mw="4",
        ml="5",
        sr="123.5",
        rank="1",
        elo="25.0",
        sigma="8.33",
        streak="0",
        version="3",
        last_played="0",
        last_loss_forgiven="0",
        championships="0",
    )

    assert player.mw == 4
    assert player.ml == 5
    assert player.sr == 123.5
    assert player.rank == 1
    assert player.get_rank_emoji() == "<:recruit:1367977165618024491>"
    assert isinstance(player.get_rating(), float)


def test_results_channel_is_removed_from_live_queue_destinations(mocker):
    stored = _queue_record(
        channel_config={
            "queue_ch": "queue_msg",
            "result_ch": "stale_result_queue_msg",
        },
        channel_id="result_ch",
        message_id="stale_result_queue_msg",
    )

    dao = MagicMock()
    dao.get_queue_or_none.return_value = stored
    dao.put_queue.return_value = {"ok": True}
    mocker.patch.object(StateRepair, "queue_dao", dao)

    inter = MagicMock()

    cleaned, repaired = StateRepair.remove_result_channel_queue_board(
        stored, inter=inter
    )

    assert repaired is True
    assert cleaned.channel_config == {"queue_ch": "queue_msg"}
    assert cleaned.channel_id == "queue_ch"
    assert cleaned.message_id == "queue_msg"
    inter.delete_message.assert_called_once_with(
        channel_id="result_ch",
        message_id="stale_result_queue_msg",
    )
    dao.put_queue.assert_called_once()


def test_missing_results_message_is_not_recreated(mocker):
    stored = _queue_record(
        channel_config={
            "queue_ch": "queue_msg",
            "result_ch": "dead_result_msg",
        }
    )

    dao = MagicMock()
    dao.get_queue_or_none.return_value = stored
    dao.put_queue.return_value = {"ok": True}
    mocker.patch.object(StateRepair, "queue_dao", dao)

    inter = MagicMock()
    exc = Exception(
        "Unable to edit message: 404 Client Error: Not Found for url: "
        "https://discord.com/api/v10/channels/result_ch/messages/dead_result_msg"
    )

    StateRepair.recover_missing_queue_message(
        stored,
        embeds=[MagicMock()],
        components=[MagicMock()],
        inter=inter,
        exc=exc,
    )

    inter.send_message.assert_not_called()
    assert "result_ch" not in stored.channel_config
    assert stored.channel_config == {"queue_ch": "queue_msg"}
