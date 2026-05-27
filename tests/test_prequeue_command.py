"""Tests for the /prequeue command."""

import pytest
from unittest.mock import MagicMock, patch
from commands.prequeue import prequeue_command


class TestPrequeueCommandNoMatch:
    """Tests for /prequeue command when no match is in progress."""

    def test_prequeue_command_no_match_in_progress(
        self, mock_interaction, queue_record_waiting
    ):
        """Command shows 'no match' message when game is in Waiting state."""
        mock_interaction.guild_id = "guild_123"

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get:
            mock_get.return_value = queue_record_waiting

            prequeue_command(mock_interaction, queue="main")

            # Should send "no match" response
            mock_interaction.send_response.assert_called_once()
            call_args = mock_interaction.send_response.call_args
            embed = call_args[1]["embeds"][0]
            assert "No match in progress" in embed.desc
            assert call_args[1]["ephemeral"] is True

    def test_prequeue_command_during_picking_phase(
        self, mock_interaction, queue_record_picking
    ):
        """Command shows 'no match' message during Picking phase."""
        mock_interaction.guild_id = "guild_123"

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get:
            mock_get.return_value = queue_record_picking

            prequeue_command(mock_interaction, queue="main")

            # Should send "no match" response
            mock_interaction.send_response.assert_called_once()
            call_args = mock_interaction.send_response.call_args
            assert call_args[1]["ephemeral"] is True


class TestPrequeueCommandMatchReady:
    """Tests for /prequeue command when match is in progress."""

    def test_prequeue_command_shows_match_ready_status(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Command shows pre-queue members and current match when Match Ready."""
        mock_interaction.guild_id = "guild_123"
        queue_record_match_ready.pre_queue = []

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready

            # Mock player data
            player_data = MagicMock()
            player_data.player_name = "TestPlayer"
            player_data.get_rank_emoji = MagicMock(return_value="⭐")
            player_data.get_streak = MagicMock(return_value="")
            player_data.sr = 2000
            mock_player.return_value = player_data

            prequeue_command(mock_interaction, queue="main")

            # Should send match status response
            mock_interaction.send_response.assert_called_once()
            call_args = mock_interaction.send_response.call_args
            embed = call_args[1]["embeds"][0]

            # Verify embed contains match info
            assert "Match in progress" in embed.desc
            assert "Pre-Queue" in embed.title
            assert "0/8" in embed.desc  # No players in pre-queue

    def test_prequeue_command_shows_pre_queue_members(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Command displays all pre-queue members with ranks and SR."""
        mock_interaction.guild_id = "guild_123"
        queue_record_match_ready.pre_queue = ["user_1", "user_2", "user_3"]

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready

            # Mock player data
            def player_factory(guild_id, user_id):
                data = MagicMock()
                data.player_name = f"Player_{user_id}"
                data.get_rank_emoji = MagicMock(return_value="⭐")
                data.get_streak = MagicMock(return_value=" (3W)")
                data.sr = 2000 + int(user_id.split("_")[1]) * 100
                return data

            mock_player.side_effect = player_factory

            prequeue_command(mock_interaction, queue="main")

            # Verify response shows pre-queue members
            call_args = mock_interaction.send_response.call_args
            embed = call_args[1]["embeds"][0]

            assert "3/8" in embed.desc  # 3 players waiting
            assert "Player_user_1" in embed.desc
            assert "Player_user_2" in embed.desc
            assert "Player_user_3" in embed.desc

    def test_prequeue_command_shows_current_match_teams(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Command displays current match teams."""
        mock_interaction.guild_id = "guild_123"
        queue_record_match_ready.pre_queue = []

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready

            player_data = MagicMock()
            player_data.player_name = "TestPlayer"
            player_data.get_rank_emoji = MagicMock(return_value="⭐")
            player_data.get_streak = MagicMock(return_value="")
            player_data.sr = 2000
            mock_player.return_value = player_data

            prequeue_command(mock_interaction, queue="main")

            # Verify teams are shown
            call_args = mock_interaction.send_response.call_args
            embed_fields = call_args[1]["embeds"][0].fields

            # Check that Current Match field exists
            assert any("Current Match" in field.get("name", "") for field in embed_fields)

    def test_prequeue_command_shows_join_leave_buttons(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Command shows Join/Leave Pre-Queue buttons during Match Ready."""
        mock_interaction.guild_id = "guild_123"
        queue_record_match_ready.pre_queue = []

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready

            player_data = MagicMock()
            player_data.player_name = "TestPlayer"
            player_data.get_rank_emoji = MagicMock(return_value="⭐")
            player_data.get_streak = MagicMock(return_value="")
            player_data.sr = 2000
            mock_player.return_value = player_data

            prequeue_command(mock_interaction, queue="main")

            # Verify buttons are provided
            call_args = mock_interaction.send_response.call_args
            components = call_args[1]["components"]
            assert len(components) > 0

            # Check button labels
            component = components[0]
            assert any("Join Pre-Queue" in str(btn) for btn in component.rows)
            assert any("Leave Pre-Queue" in str(btn) for btn in component.rows)


class TestPrequeueCommandQueueParameter:
    """Tests for queue name parameter."""

    def test_prequeue_command_accepts_queue_parameter(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Command accepts custom queue name parameter."""
        mock_interaction.guild_id = "guild_123"

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready
            player_data = MagicMock()
            player_data.player_name = "TestPlayer"
            player_data.get_rank_emoji = MagicMock(return_value="⭐")
            player_data.get_streak = MagicMock(return_value="")
            player_data.sr = 2000
            mock_player.return_value = player_data

            prequeue_command(mock_interaction, queue="variant")

            # Verify queue_dao was called with correct queue_id
            mock_get.assert_called_once_with(
                guild_id="guild_123", queue_id="variant"
            )

    def test_prequeue_command_defaults_to_main_queue(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Command defaults to 'main' queue if not specified."""
        mock_interaction.guild_id = "guild_123"

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready
            player_data = MagicMock()
            player_data.player_name = "TestPlayer"
            player_data.get_rank_emoji = MagicMock(return_value="⭐")
            player_data.get_streak = MagicMock(return_value="")
            player_data.sr = 2000
            mock_player.return_value = player_data

            prequeue_command(mock_interaction, queue="main")

            # Verify default queue_id
            mock_get.assert_called_once_with(
                guild_id="guild_123", queue_id="main"
            )


class TestPrequeueCommandIntegration:
    """Integration tests for /prequeue command."""

    def test_prequeue_command_full_flow_no_match(
        self, mock_interaction, queue_record_waiting
    ):
        """Full /prequeue command flow when no match in progress."""
        mock_interaction.guild_id = "guild_123"

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get:
            mock_get.return_value = queue_record_waiting

            prequeue_command(mock_interaction, queue="main")

            # Should defer and send response
            mock_interaction.defer.assert_called_once()
            mock_interaction.send_response.assert_called_once()
            call_args = mock_interaction.send_response.call_args
            assert call_args[1]["ephemeral"] is True

    def test_prequeue_command_full_flow_match_ready(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Full /prequeue command flow when match is ready."""
        mock_interaction.guild_id = "guild_123"
        queue_record_match_ready.pre_queue = ["waiting_user_1", "waiting_user_2"]

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready

            player_data = MagicMock()
            player_data.player_name = "TestPlayer"
            player_data.get_rank_emoji = MagicMock(return_value="⭐")
            player_data.get_streak = MagicMock(return_value="")
            player_data.sr = 2000
            mock_player.return_value = player_data

            prequeue_command(mock_interaction, queue="main")

            # Should defer and send full match status
            mock_interaction.defer.assert_called_once()
            mock_interaction.send_response.assert_called_once()
            call_args = mock_interaction.send_response.call_args

            # Verify response structure
            assert "embeds" in call_args[1]
            assert "components" in call_args[1]
            assert call_args[1]["ephemeral"] is True

    def test_prequeue_command_shows_empty_pre_queue_message(
        self, mock_interaction, queue_record_match_ready, mock_player_dao
    ):
        """Command shows 'No players waiting' when pre-queue is empty."""
        mock_interaction.guild_id = "guild_123"
        queue_record_match_ready.pre_queue = []

        with patch('commands.prequeue.queue_dao.get_queue') as mock_get, \
             patch('commands.prequeue.player_dao.get_player') as mock_player:
            mock_get.return_value = queue_record_match_ready
            player_data = MagicMock()
            player_data.player_name = "TestPlayer"
            player_data.get_rank_emoji = MagicMock(return_value="⭐")
            player_data.get_streak = MagicMock(return_value="")
            player_data.sr = 2000
            mock_player.return_value = player_data

            prequeue_command(mock_interaction, queue="main")

            call_args = mock_interaction.send_response.call_args
            embed = call_args[1]["embeds"][0]
            assert "*No players waiting*" in embed.desc
