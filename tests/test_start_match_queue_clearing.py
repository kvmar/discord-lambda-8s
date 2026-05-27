"""Tests for queue clearing during start_match (critical for pre-queue functionality)."""

import pytest
from unittest.mock import MagicMock, patch
from core.QueueManager import start_match


class TestStartMatchQueueClearing:
    """Tests for queue clearing in start_match function."""

    def test_start_match_clears_queue_after_team_assignment(
        self, queue_record_waiting, mock_interaction, mock_queue_dao
    ):
        """start_match clears the queue after assigning teams."""
        # Setup: 8 players in queue
        queue_record_waiting.queue = [f"user_{i}" for i in range(8)]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        with patch('core.QueueManager.player_dao.get_player') as mock_player, \
             patch('core.QueueManager.use_average_sr') as mock_teams:
            # Mock player data
            player_data = MagicMock()
            player_data.player_id = "user_0"
            player_data.get_rating = MagicMock(return_value=2000)
            mock_player.return_value = player_data

            # Mock team assignment
            team1_players = [
                MagicMock(player_id="user_0", get_rating=MagicMock(return_value=2000)),
                MagicMock(player_id="user_1", get_rating=MagicMock(return_value=2000)),
                MagicMock(player_id="user_2", get_rating=MagicMock(return_value=2000)),
                MagicMock(player_id="user_3", get_rating=MagicMock(return_value=2000)),
            ]
            team2_players = [
                MagicMock(player_id="user_4", get_rating=MagicMock(return_value=2000)),
                MagicMock(player_id="user_5", get_rating=MagicMock(return_value=2000)),
                MagicMock(player_id="user_6", get_rating=MagicMock(return_value=2000)),
                MagicMock(player_id="user_7", get_rating=MagicMock(return_value=2000)),
            ]
            mock_teams.return_value = (team1_players, team2_players)

            start_match(mock_interaction, "main", autopick=True)

            # After start_match, queue should be empty
            assert len(queue_record_waiting.queue) == 0
            assert len(queue_record_waiting.team_1) == 4
            assert len(queue_record_waiting.team_2) == 4

    def test_start_match_enables_pre_queue_join(
        self, queue_record_waiting, mock_interaction, mock_queue_dao
    ):
        """After start_match, players can join pre-queue (queue == empty AND teams == 4)."""
        queue_record_waiting.queue = [f"user_{i}" for i in range(8)]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        with patch('core.QueueManager.player_dao.get_player') as mock_player, \
             patch('core.QueueManager.use_average_sr') as mock_teams:
            player_data = MagicMock()
            player_data.player_id = "user_0"
            player_data.get_rating = MagicMock(return_value=2000)
            mock_player.return_value = player_data

            team1_players = [
                MagicMock(player_id=f"user_{i}", get_rating=MagicMock(return_value=2000))
                for i in range(4)
            ]
            team2_players = [
                MagicMock(player_id=f"user_{i}", get_rating=MagicMock(return_value=2000))
                for i in range(4, 8)
            ]
            mock_teams.return_value = (team1_players, team2_players)

            start_match(mock_interaction, "main", autopick=True)

            # Verify pre-queue join condition is met
            assert len(queue_record_waiting.team_1) == 4
            assert len(queue_record_waiting.team_2) == 4
            assert len(queue_record_waiting.queue) == 0

    def test_start_match_autopick_clears_queue(
        self, queue_record_waiting, mock_interaction, mock_queue_dao
    ):
        """start_match with autopick=True clears queue."""
        queue_record_waiting.queue = ["user_1", "user_2", "user_3", "user_4", "user_5", "user_6", "user_7", "user_8"]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        with patch('core.QueueManager.player_dao.get_player') as mock_player, \
             patch('core.QueueManager.use_average_sr') as mock_teams, \
             patch('core.QueueManager.get_maps') as mock_maps:
            player_data = MagicMock()
            player_data.player_id = "user_1"
            player_data.get_rating = MagicMock(return_value=2000)
            mock_player.return_value = player_data

            team1_players = [
                MagicMock(player_id=f"user_{i}", get_rating=MagicMock(return_value=2000))
                for i in range(1, 5)
            ]
            team2_players = [
                MagicMock(player_id=f"user_{i}", get_rating=MagicMock(return_value=2000))
                for i in range(5, 9)
            ]
            mock_teams.return_value = (team1_players, team2_players)
            mock_maps.return_value = ["Map1", "Map2", "Map3"]

            start_match(mock_interaction, "main", autopick=True)

            assert queue_record_waiting.queue == []
            assert len(queue_record_waiting.team_1) == 4
            assert len(queue_record_waiting.team_2) == 4

    def test_start_match_manual_pick_clears_queue(
        self, queue_record_waiting, mock_interaction, mock_queue_dao
    ):
        """start_match with autopick=False (manual pick) clears queue."""
        queue_record_waiting.queue = ["user_1", "user_2", "user_3", "user_4", "user_5", "user_6", "user_7", "user_8"]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        with patch('core.QueueManager.player_dao.get_player') as mock_player, \
             patch('core.QueueManager.findMinSRDiff') as mock_caps, \
             patch('core.QueueManager.get_maps') as mock_maps:
            player_data = MagicMock()
            player_data.player_id = "user_1"
            player_data.get_rating = MagicMock(return_value=2000)
            mock_player.return_value = player_data

            mock_caps.return_value = ["user_1", "user_5"]  # Two captains
            mock_maps.return_value = ["Map1", "Map2", "Map3"]

            start_match(mock_interaction, "main", autopick=False)

            assert queue_record_waiting.queue == []
            assert len(queue_record_waiting.team_1) == 1  # Captain 1
            assert len(queue_record_waiting.team_2) == 1  # Captain 2


class TestStartMatchAndPreQueueFlow:
    """End-to-end tests for start_match enabling pre-queue."""

    def test_start_match_then_add_pre_queue_player(
        self, queue_record_waiting, mock_interaction, mock_queue_dao, mock_player_dao
    ):
        """After start_match, player can successfully join pre-queue."""
        from core.QueueManager import add_pre_queue_player

        # Setup initial queue
        queue_record_waiting.queue = [f"user_{i}" for i in range(8)]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        # Step 1: Start match
        with patch('core.QueueManager.player_dao.get_player') as mock_player, \
             patch('core.QueueManager.use_average_sr') as mock_teams, \
             patch('core.QueueManager.get_maps') as mock_maps:
            player_data = MagicMock()
            player_data.player_id = "user_0"
            player_data.get_rating = MagicMock(return_value=2000)
            mock_player.return_value = player_data

            team1_players = [
                MagicMock(player_id=f"user_{i}", get_rating=MagicMock(return_value=2000))
                for i in range(4)
            ]
            team2_players = [
                MagicMock(player_id=f"user_{i}", get_rating=MagicMock(return_value=2000))
                for i in range(4, 8)
            ]
            mock_teams.return_value = (team1_players, team2_players)
            mock_maps.return_value = ["Map1", "Map2", "Map3"]

            start_match(mock_interaction, "main", autopick=True)

        # Step 2: New player tries to join pre-queue
        new_player_inter = MagicMock()
        new_player_inter.guild_id = "guild_123"
        new_player_inter.user_id = "new_user"
        new_player_inter.username = "NewPlayer"

        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)
        mock_queue_dao.put_queue = MagicMock(return_value=True)
        mock_player_dao.get_player = MagicMock(return_value=None)

        result = add_pre_queue_player(new_player_inter, "main")

        # Should succeed because both teams have 4 players and queue is empty
        assert result is not None
        assert "new_user" in queue_record_waiting.pre_queue
