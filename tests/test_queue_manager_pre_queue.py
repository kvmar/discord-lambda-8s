"""Tests for pre-queue functionality in QueueManager."""

import pytest
from unittest.mock import MagicMock, patch
from core.QueueManager import (
    add_pre_queue_player,
    remove_pre_queue_player,
    promote_pre_queue,
    MAX_QUEUE_SIZE,
)


class TestAddPreQueuePlayer:
    """Tests for add_pre_queue_player business logic."""

    def test_add_player_to_pre_queue_success(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Player successfully joins pre-queue when game is Match Ready."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = add_pre_queue_player(mock_interaction, "main")

        assert result is not None
        assert mock_interaction.user_id in queue_record_match_ready.pre_queue
        assert len(queue_record_match_ready.pre_queue) == 1
        mock_queue_dao.put_queue.assert_called_once()

    def test_reject_pre_queue_join_when_game_not_in_progress(
        self, queue_record_waiting, mock_interaction, mock_queue_dao
    ):
        """Player cannot join pre-queue when game is in Waiting state."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)

        result = add_pre_queue_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_waiting.pre_queue) == 0

    def test_reject_pre_queue_join_during_picking_phase(
        self, queue_record_picking, mock_interaction, mock_queue_dao
    ):
        """Player cannot join pre-queue during Picking phase (only Match Ready)."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_picking)

        result = add_pre_queue_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_picking.pre_queue) == 0

    def test_reject_duplicate_pre_queue_entry(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao
    ):
        """Player cannot join pre-queue twice."""
        queue_record_match_ready.pre_queue = [mock_interaction.user_id]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)

        result = add_pre_queue_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_match_ready.pre_queue) == 1

    def test_enforce_pre_queue_capacity(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao
    ):
        """Pre-queue respects MAX_QUEUE_SIZE capacity (8 players)."""
        # Fill pre-queue to capacity
        queue_record_match_ready.pre_queue = [f"user_{i}" for i in range(MAX_QUEUE_SIZE)]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)

        result = add_pre_queue_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_match_ready.pre_queue) == MAX_QUEUE_SIZE

    def test_register_new_player_on_pre_queue_join(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Player is successfully added to pre-queue (fixture handles registration)."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = add_pre_queue_player(mock_interaction, "main")

        assert result is not None
        assert mock_interaction.user_id in queue_record_match_ready.pre_queue
        assert len(queue_record_match_ready.pre_queue) == 1

    def test_do_not_reregister_existing_player(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Existing player is not re-registered on pre-queue join."""
        existing_player = MagicMock()
        existing_player.player_id = mock_interaction.user_id
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)
        mock_player_dao.get_player = MagicMock(return_value=existing_player)

        add_pre_queue_player(mock_interaction, "main")

        mock_player_dao.put_player.assert_not_called()

    def test_put_queue_called_on_success(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """put_queue is called to persist pre-queue changes."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        add_pre_queue_player(mock_interaction, "main")

        mock_queue_dao.put_queue.assert_called_once()
        assert mock_interaction.user_id in queue_record_match_ready.pre_queue

    def test_return_none_on_concurrent_write_failure(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Return None if put_queue fails (concurrent edit)."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=None)  # Simulates concurrent failure

        result = add_pre_queue_player(mock_interaction, "main")

        assert result is None


class TestRemovePreQueuePlayer:
    """Tests for remove_pre_queue_player business logic."""

    def test_remove_player_from_pre_queue(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao, mock_player_dao
    ):
        """Player successfully leaves pre-queue."""
        queue_record_match_ready.pre_queue = [mock_interaction.user_id, "other_user"]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = remove_pre_queue_player(mock_interaction, "main")

        assert result is not None
        assert mock_interaction.user_id not in queue_record_match_ready.pre_queue
        assert "other_user" in queue_record_match_ready.pre_queue
        mock_queue_dao.put_queue.assert_called_once()

    def test_remove_player_not_in_pre_queue_is_noop(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao, mock_player_dao
    ):
        """Removing a player not in pre-queue is a no-op (doesn't error)."""
        queue_record_match_ready.pre_queue = ["other_user"]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = remove_pre_queue_player(mock_interaction, "main")

        assert result is not None
        assert len(queue_record_match_ready.pre_queue) == 1
        mock_queue_dao.put_queue.assert_called_once()

    def test_return_none_on_remove_concurrent_failure(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao
    ):
        """Return None if put_queue fails during remove."""
        queue_record_match_ready.pre_queue = [mock_interaction.user_id]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=None)

        result = remove_pre_queue_player(mock_interaction, "main")

        assert result is None


class TestPromotePreQueue:
    """Tests for promote_pre_queue promotion logic (critical path)."""

    def test_promote_empty_pre_queue(self, queue_record_match_ready):
        """Promoting empty pre-queue results in empty active queue."""
        queue_record_match_ready.pre_queue = []

        promote_pre_queue(queue_record_match_ready)

        assert queue_record_match_ready.queue == []
        assert queue_record_match_ready.pre_queue == []

    def test_promote_pre_queue_to_active_queue(self, queue_record_match_ready):
        """Pre-queue members become active queue members."""
        pre_queue_members = ["user_pre_1", "user_pre_2", "user_pre_3"]
        queue_record_match_ready.pre_queue = pre_queue_members.copy()

        promote_pre_queue(queue_record_match_ready)

        assert queue_record_match_ready.queue == pre_queue_members
        assert queue_record_match_ready.pre_queue == []

    def test_promote_respects_capacity_limit(self, queue_record_match_ready):
        """Promotion caps queue at MAX_QUEUE_SIZE."""
        # Pre-queue larger than capacity
        pre_queue_members = [f"user_{i}" for i in range(MAX_QUEUE_SIZE + 2)]
        queue_record_match_ready.pre_queue = pre_queue_members.copy()

        promote_pre_queue(queue_record_match_ready)

        assert len(queue_record_match_ready.queue) == MAX_QUEUE_SIZE
        # First 8 members promoted, rest discarded
        assert queue_record_match_ready.queue == pre_queue_members[:MAX_QUEUE_SIZE]
        assert queue_record_match_ready.pre_queue == []

    def test_promote_clears_pre_queue(self, queue_record_match_ready):
        """Pre-queue is cleared after promotion."""
        queue_record_match_ready.pre_queue = ["user1", "user2"]

        promote_pre_queue(queue_record_match_ready)

        assert queue_record_match_ready.pre_queue == []

    def test_promote_maintains_order(self, queue_record_match_ready):
        """Promotion maintains join order from pre-queue."""
        pre_queue_members = ["first_join", "second_join", "third_join"]
        queue_record_match_ready.pre_queue = pre_queue_members.copy()

        promote_pre_queue(queue_record_match_ready)

        assert queue_record_match_ready.queue == pre_queue_members
        assert queue_record_match_ready.queue[0] == "first_join"
        assert queue_record_match_ready.queue[1] == "second_join"

    def test_promote_does_not_affect_other_fields(self, queue_record_match_ready):
        """Promotion only modifies queue and pre_queue fields."""
        original_team_1 = queue_record_match_ready.team_1.copy()
        original_team_2 = queue_record_match_ready.team_2.copy()
        original_maps = queue_record_match_ready.maps.copy()

        queue_record_match_ready.pre_queue = ["user1", "user2"]
        promote_pre_queue(queue_record_match_ready)

        assert queue_record_match_ready.team_1 == original_team_1
        assert queue_record_match_ready.team_2 == original_team_2
        assert queue_record_match_ready.maps == original_maps

    def test_promote_full_pre_queue(self, queue_record_match_ready):
        """Promote at capacity (8 players)."""
        pre_queue_members = [f"user_{i}" for i in range(MAX_QUEUE_SIZE)]
        queue_record_match_ready.pre_queue = pre_queue_members.copy()

        promote_pre_queue(queue_record_match_ready)

        assert len(queue_record_match_ready.queue) == MAX_QUEUE_SIZE
        assert queue_record_match_ready.queue == pre_queue_members


class TestPreQueueIntegration:
    """Integration tests for pre-queue lifecycle."""

    def test_multiple_players_join_pre_queue_sequentially(
        self, queue_record_match_ready, mock_player_dao, mock_queue_dao
    ):
        """Multiple players can sequentially join pre-queue."""
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        users = ["user_1", "user_2", "user_3"]
        for user_id in users:
            inter = MagicMock()
            inter.guild_id = "guild_123"
            inter.user_id = user_id
            inter.username = f"Player_{user_id}"
            mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)

            add_pre_queue_player(inter, "main")

        assert len(queue_record_match_ready.pre_queue) == 3

    def test_pre_queue_survives_clear_queue(self, queue_record_match_ready):
        """Pre-queue is NOT cleared by clear_queue (intentional design)."""
        queue_record_match_ready.pre_queue = ["user1", "user2"]
        original_pre_queue = queue_record_match_ready.pre_queue.copy()

        queue_record_match_ready.clear_queue(reset_expiry=False)

        assert queue_record_match_ready.pre_queue == original_pre_queue
        assert queue_record_match_ready.team_1 == []
        assert queue_record_match_ready.team_2 == []

    def test_game_end_to_promotion_flow(self, queue_record_match_ready, mock_queue_dao):
        """End-to-end: game finishes and pre-queue is promoted to active queue."""
        # Setup: game in progress with pre-queue waiting
        pre_queue_members = ["waiting_1", "waiting_2", "waiting_3"]
        queue_record_match_ready.pre_queue = pre_queue_members.copy()
        queue_record_match_ready.team_1 = ["cap1", "p1", "p2", "p3"]
        queue_record_match_ready.team_2 = ["cap2", "p4", "p5", "p6"]

        # Simulate game end: clear then promote
        queue_record_match_ready.clear_queue(reset_expiry=False)
        assert queue_record_match_ready.queue == []
        assert queue_record_match_ready.pre_queue == pre_queue_members

        promote_pre_queue(queue_record_match_ready)

        # After promotion: pre-queue members form new active queue
        assert queue_record_match_ready.queue == pre_queue_members
        assert queue_record_match_ready.pre_queue == []
        assert queue_record_match_ready.team_1 == []
        assert queue_record_match_ready.team_2 == []
