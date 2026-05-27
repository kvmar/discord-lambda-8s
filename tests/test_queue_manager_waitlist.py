"""Tests for pre-queue functionality in QueueManager."""

import pytest
from unittest.mock import MagicMock, patch
from core.QueueManager import (
    add_waitlist_player,
    remove_waitlist_player,
    promote_waitlist,
    MAX_QUEUE_SIZE,
)


class TestAddPreQueuePlayer:
    """Tests for add_waitlist_player business logic."""

    def test_add_player_to_waitlist_success(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Player successfully joins pre-queue when game is Match Ready."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = add_waitlist_player(mock_interaction, "main")

        assert result is not None
        assert mock_interaction.user_id in queue_record_match_ready.waitlist
        assert len(queue_record_match_ready.waitlist) == 1
        mock_queue_dao.put_queue.assert_called_once()

    def test_reject_waitlist_join_when_game_not_in_progress(
        self, queue_record_waiting, mock_interaction, mock_queue_dao
    ):
        """Player cannot join pre-queue when game is in Waiting state."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_waiting)

        result = add_waitlist_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_waiting.waitlist) == 0

    def test_reject_waitlist_join_during_picking_phase(
        self, queue_record_picking, mock_interaction, mock_queue_dao
    ):
        """Player cannot join pre-queue during Picking phase (only Match Ready)."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_picking)

        result = add_waitlist_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_picking.waitlist) == 0

    def test_reject_duplicate_waitlist_entry(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao
    ):
        """Player cannot join pre-queue twice."""
        queue_record_match_ready.waitlist = [mock_interaction.user_id]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)

        result = add_waitlist_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_match_ready.waitlist) == 1

    def test_enforce_waitlist_capacity(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao
    ):
        """Pre-queue respects MAX_QUEUE_SIZE capacity (8 players)."""
        # Fill pre-queue to capacity
        queue_record_match_ready.waitlist = [f"user_{i}" for i in range(MAX_QUEUE_SIZE)]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)

        result = add_waitlist_player(mock_interaction, "main")

        assert result is None
        assert len(queue_record_match_ready.waitlist) == MAX_QUEUE_SIZE

    def test_register_new_player_on_waitlist_join(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Player is successfully added to pre-queue (fixture handles registration)."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = add_waitlist_player(mock_interaction, "main")

        assert result is not None
        assert mock_interaction.user_id in queue_record_match_ready.waitlist
        assert len(queue_record_match_ready.waitlist) == 1

    def test_do_not_reregister_existing_player(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Existing player is not re-registered on pre-queue join."""
        existing_player = MagicMock()
        existing_player.player_id = mock_interaction.user_id
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)
        mock_player_dao.get_player = MagicMock(return_value=existing_player)

        add_waitlist_player(mock_interaction, "main")

        mock_player_dao.put_player.assert_not_called()

    def test_put_queue_called_on_success(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """put_queue is called to persist pre-queue changes."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        add_waitlist_player(mock_interaction, "main")

        mock_queue_dao.put_queue.assert_called_once()
        assert mock_interaction.user_id in queue_record_match_ready.waitlist

    def test_return_none_on_concurrent_write_failure(
        self, queue_record_match_ready, mock_interaction, mock_player_dao, mock_queue_dao
    ):
        """Return None if put_queue fails (concurrent edit)."""
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=None)  # Simulates concurrent failure

        result = add_waitlist_player(mock_interaction, "main")

        assert result is None


class TestRemovePreQueuePlayer:
    """Tests for remove_waitlist_player business logic."""

    def test_remove_player_from_waitlist(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao, mock_player_dao
    ):
        """Player successfully leaves pre-queue."""
        queue_record_match_ready.waitlist = [mock_interaction.user_id, "other_user"]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = remove_waitlist_player(mock_interaction, "main")

        assert result is not None
        assert mock_interaction.user_id not in queue_record_match_ready.waitlist
        assert "other_user" in queue_record_match_ready.waitlist
        mock_queue_dao.put_queue.assert_called_once()

    def test_remove_player_not_in_waitlist_is_noop(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao, mock_player_dao
    ):
        """Removing a player not in pre-queue is a no-op (doesn't error)."""
        queue_record_match_ready.waitlist = ["other_user"]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=True)

        result = remove_waitlist_player(mock_interaction, "main")

        assert result is not None
        assert len(queue_record_match_ready.waitlist) == 1
        mock_queue_dao.put_queue.assert_called_once()

    def test_return_none_on_remove_concurrent_failure(
        self, queue_record_match_ready, mock_interaction, mock_queue_dao
    ):
        """Return None if put_queue fails during remove."""
        queue_record_match_ready.waitlist = [mock_interaction.user_id]
        mock_queue_dao.get_queue = MagicMock(return_value=queue_record_match_ready)
        mock_queue_dao.put_queue = MagicMock(return_value=None)

        result = remove_waitlist_player(mock_interaction, "main")

        assert result is None


class TestPromotePreQueue:
    """Tests for promote_waitlist promotion logic (critical path)."""

    def test_promote_empty_waitlist(self, queue_record_match_ready):
        """Promoting empty pre-queue results in empty active queue."""
        queue_record_match_ready.waitlist = []

        promote_waitlist(queue_record_match_ready)

        assert queue_record_match_ready.queue == []
        assert queue_record_match_ready.waitlist == []

    def test_promote_waitlist_to_active_queue(self, queue_record_match_ready):
        """Pre-queue members become active queue members."""
        waitlist_members = ["user_pre_1", "user_pre_2", "user_pre_3"]
        queue_record_match_ready.waitlist = waitlist_members.copy()

        promote_waitlist(queue_record_match_ready)

        assert queue_record_match_ready.queue == waitlist_members
        assert queue_record_match_ready.waitlist == []

    def test_promote_respects_capacity_limit(self, queue_record_match_ready):
        """Promotion caps queue at MAX_QUEUE_SIZE."""
        # Pre-queue larger than capacity
        waitlist_members = [f"user_{i}" for i in range(MAX_QUEUE_SIZE + 2)]
        queue_record_match_ready.waitlist = waitlist_members.copy()

        promote_waitlist(queue_record_match_ready)

        assert len(queue_record_match_ready.queue) == MAX_QUEUE_SIZE
        # First 8 members promoted, rest discarded
        assert queue_record_match_ready.queue == waitlist_members[:MAX_QUEUE_SIZE]
        assert queue_record_match_ready.waitlist == []

    def test_promote_clears_waitlist(self, queue_record_match_ready):
        """Pre-queue is cleared after promotion."""
        queue_record_match_ready.waitlist = ["user1", "user2"]

        promote_waitlist(queue_record_match_ready)

        assert queue_record_match_ready.waitlist == []

    def test_promote_maintains_order(self, queue_record_match_ready):
        """Promotion maintains join order from pre-queue."""
        waitlist_members = ["first_join", "second_join", "third_join"]
        queue_record_match_ready.waitlist = waitlist_members.copy()

        promote_waitlist(queue_record_match_ready)

        assert queue_record_match_ready.queue == waitlist_members
        assert queue_record_match_ready.queue[0] == "first_join"
        assert queue_record_match_ready.queue[1] == "second_join"

    def test_promote_does_not_affect_other_fields(self, queue_record_match_ready):
        """Promotion only modifies queue and waitlist fields."""
        original_team_1 = queue_record_match_ready.team_1.copy()
        original_team_2 = queue_record_match_ready.team_2.copy()
        original_maps = queue_record_match_ready.maps.copy()

        queue_record_match_ready.waitlist = ["user1", "user2"]
        promote_waitlist(queue_record_match_ready)

        assert queue_record_match_ready.team_1 == original_team_1
        assert queue_record_match_ready.team_2 == original_team_2
        assert queue_record_match_ready.maps == original_maps

    def test_promote_full_waitlist(self, queue_record_match_ready):
        """Promote at capacity (8 players)."""
        waitlist_members = [f"user_{i}" for i in range(MAX_QUEUE_SIZE)]
        queue_record_match_ready.waitlist = waitlist_members.copy()

        promote_waitlist(queue_record_match_ready)

        assert len(queue_record_match_ready.queue) == MAX_QUEUE_SIZE
        assert queue_record_match_ready.queue == waitlist_members


class TestPreQueueIntegration:
    """Integration tests for pre-queue lifecycle."""

    def test_multiple_players_join_waitlist_sequentially(
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

            add_waitlist_player(inter, "main")

        assert len(queue_record_match_ready.waitlist) == 3

    def test_waitlist_survives_clear_queue(self, queue_record_match_ready):
        """Pre-queue is NOT cleared by clear_queue (intentional design)."""
        queue_record_match_ready.waitlist = ["user1", "user2"]
        original_waitlist = queue_record_match_ready.waitlist.copy()

        queue_record_match_ready.clear_queue(reset_expiry=False)

        assert queue_record_match_ready.waitlist == original_waitlist
        assert queue_record_match_ready.team_1 == []
        assert queue_record_match_ready.team_2 == []

    def test_game_end_to_promotion_flow(self, queue_record_match_ready, mock_queue_dao):
        """End-to-end: game finishes and pre-queue is promoted to active queue."""
        # Setup: game in progress with pre-queue waiting
        waitlist_members = ["waiting_1", "waiting_2", "waiting_3"]
        queue_record_match_ready.waitlist = waitlist_members.copy()
        queue_record_match_ready.team_1 = ["cap1", "p1", "p2", "p3"]
        queue_record_match_ready.team_2 = ["cap2", "p4", "p5", "p6"]

        # Simulate game end: clear then promote
        queue_record_match_ready.clear_queue(reset_expiry=False)
        assert queue_record_match_ready.queue == []
        assert queue_record_match_ready.waitlist == waitlist_members

        promote_waitlist(queue_record_match_ready)

        # After promotion: pre-queue members form new active queue
        assert queue_record_match_ready.queue == waitlist_members
        assert queue_record_match_ready.waitlist == []
        assert queue_record_match_ready.team_1 == []
        assert queue_record_match_ready.team_2 == []
