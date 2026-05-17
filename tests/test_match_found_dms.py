"""Tests for match-found DM feature."""

import pytest
from unittest.mock import MagicMock, patch, call
from dao.QueueDao import QueueRecord
from core.QueueManager import send_match_found_dms


def _make_record(queue, maps=None, team_1=None, team_2=None):
    return QueueRecord(
        guild_id="guild_123",
        queue_id="main",
        team_1=team_1 or [],
        team_2=team_2 or [],
        queue=queue,
        cancel_votes=[],
        team1_votes=[],
        team2_votes=[],
        maps=maps if maps is not None else ["Map1", "Map2", "Map3"],
        map_set=["Map1", "Map2", "Map3"],
        version=1,
        expiry=9999999999,
        result_channel_id="result_ch",
        team_1_channel_id="team1_ch",
        team_2_channel_id="team2_ch",
        money_queue=False,
        pre_queue=[],
    )


class TestSendMatchFoundDms:

    def test_dms_all_players_in_queue(self):
        """DM is sent to every player_id in record.queue."""
        inter = MagicMock()
        record = _make_record(queue=["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"])

        send_match_found_dms(inter, record)

        assert inter.send_dm.call_count == 8
        called_ids = [c.kwargs["user_id"] for c in inter.send_dm.call_args_list]
        assert called_ids == ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]

    def test_embed_contains_maps(self):
        """The DM embed includes the selected maps."""
        inter = MagicMock()
        record = _make_record(queue=["p1"], maps=["Skidrow", "Terminal", "Highrise"])

        send_match_found_dms(inter, record)

        embed = inter.send_dm.call_args.kwargs["embeds"][0]
        assert "Skidrow" in embed.fields[0]["value"]
        assert "Terminal" in embed.fields[0]["value"]
        assert "Highrise" in embed.fields[0]["value"]

    def test_no_double_send_for_captains_manual_pick(self):
        """Captains in team_1/team_2 are not DM'd twice (queue is the source of truth)."""
        inter = MagicMock()
        # Manual pick: captains appear in teams but queue still holds all 8
        all_players = ["cap1", "cap2", "p3", "p4", "p5", "p6", "p7", "p8"]
        record = _make_record(
            queue=all_players,
            team_1=["cap1"],
            team_2=["cap2"],
        )

        send_match_found_dms(inter, record)

        assert inter.send_dm.call_count == 8

    def test_empty_queue_sends_no_dms(self):
        """No DMs sent when queue is empty."""
        inter = MagicMock()
        record = _make_record(queue=[])

        send_match_found_dms(inter, record)

        inter.send_dm.assert_not_called()

    def test_maps_fallback_when_empty(self):
        """Embed shows 'TBD' when maps list is empty."""
        inter = MagicMock()
        record = _make_record(queue=["p1"], maps=[])

        send_match_found_dms(inter, record)

        embed = inter.send_dm.call_args.kwargs["embeds"][0]
        # Embedding objects store fields as a list of dicts
        maps_field = [f for f in embed.fields if f["name"] == "Maps"][0]
        assert maps_field["value"] == "TBD"


class TestSendDm:

    def test_send_dm_creates_channel_then_sends_message(self):
        """send_dm first opens a DM channel, then sends to that channel."""
        import os
        from discord_lambda.Interaction import Interaction

        interaction_data = {
            "type": 2,
            "token": "tok",
            "id": "iid",
            "member": {"user": {"id": "u1", "global_name": "Alice", "username": "alice"}},
            "data": {"custom_id": None, "name": "cmd", "options": []},
            "guild": {"id": "g1"},
        }

        with patch.dict(os.environ, {"BOT_TOKEN": "testtoken"}), \
             patch("requests.post") as mock_post:

            dm_channel_response = MagicMock()
            dm_channel_response.json.return_value = {"id": "dm_ch_999"}
            dm_channel_response.raise_for_status = MagicMock()

            send_message_response = MagicMock()
            send_message_response.json.return_value = {"id": "msg1", "channel_id": "dm_ch_999"}
            send_message_response.raise_for_status = MagicMock()

            mock_post.side_effect = [dm_channel_response, send_message_response]

            inter = Interaction(interaction_data, app_id="app1")
            inter.send_dm(user_id="u999", content="Hello!")

            # First call: create DM channel
            first_call = mock_post.call_args_list[0]
            assert "users/@me/channels" in first_call.args[0]
            assert first_call.kwargs["json"] == {"recipient_id": "u999"}

            # Second call: send message to DM channel
            second_call = mock_post.call_args_list[1]
            assert "dm_ch_999" in second_call.args[0]

    def test_send_dm_swallows_error(self):
        """A failed DM does not raise — the error is only printed."""
        import os
        from discord_lambda.Interaction import Interaction

        interaction_data = {
            "type": 2,
            "token": "tok",
            "id": "iid",
            "member": {"user": {"id": "u1", "global_name": "Alice", "username": "alice"}},
            "data": {"custom_id": None, "name": "cmd", "options": []},
            "guild": {"id": "g1"},
        }

        with patch.dict(os.environ, {"BOT_TOKEN": "testtoken"}), \
             patch("requests.post") as mock_post:

            mock_post.side_effect = Exception("network failure")

            inter = Interaction(interaction_data, app_id="app1")
            # Should not raise
            inter.send_dm(user_id="u999", content="Hello!")


class TestStartQueueButtonSendsDms:

    def test_start_queue_button_calls_send_match_found_dms(self, mock_interaction):
        """start_queue_button calls send_match_found_dms after updating the queue view."""
        mock_interaction.custom_id = "start_queue_custom_id#main"

        embed = MagicMock()
        component = MagicMock()

        record = _make_record(
            queue=["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"],
            maps=["Map1", "Map2", "Map3"],
        )

        with patch("core.ButtonManager.QueueManager.start_match") as mock_start, \
             patch("core.ButtonManager.queue_dao") as mock_dao, \
             patch("core.ButtonManager.QueueManager.update_queue_view") as mock_update, \
             patch("core.ButtonManager.QueueManager.send_match_found_dms") as mock_dms:

            mock_start.return_value = (embed, component)
            mock_dao.get_queue.return_value = record

            from core.ButtonManager import start_queue_button
            start_queue_button(guild_id="guild_123", inter=mock_interaction, autopick=False)

            mock_dms.assert_called_once_with(mock_interaction, record)
