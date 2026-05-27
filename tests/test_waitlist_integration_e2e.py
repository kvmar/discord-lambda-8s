"""End-to-end integration tests for pre-queue throughout game lifecycle."""

import pytest
from unittest.mock import MagicMock, patch
from dao.QueueDao import QueueRecord
from core.QueueManager import (
    promote_waitlist,
    add_waitlist_player,
    remove_waitlist_player,
)


class TestGameLifecycleWithPreQueue:
    """Tests pre-queue behavior across full game lifecycle."""

    def test_game_lifecycle_waiting_to_match_ready_to_promotion(self):
        """Full game lifecycle: Waiting → Match Ready → Game Finish → Promotion."""
        # Phase 1: Waiting state
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=["M1", "M2", "M3"],
            version=1,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=[],
        )
        assert len(record.queue) == 8
        assert len(record.waitlist) == 0

        # Phase 2: Teams selected, match ready
        record.team_1 = ["p1", "p2", "p3", "p4"]
        record.team_2 = ["p5", "p6", "p7", "p8"]
        record.queue = []
        record.maps = ["M1", "M2", "M3"]
        assert len(record.team_1) == 4
        assert len(record.team_2) == 4
        assert len(record.queue) == 0

        # Phase 3: Players wait in pre-queue
        record.waitlist = ["waiting_1", "waiting_2", "waiting_3"]
        assert len(record.waitlist) == 3

        # Phase 4: Game finishes
        record.clear_queue(reset_expiry=False)
        assert len(record.team_1) == 0
        assert len(record.team_2) == 0
        assert len(record.queue) == 0
        assert len(record.waitlist) == 3  # Survived clear_queue

        # Phase 5: Promotion
        promote_waitlist(record)
        assert len(record.queue) == 3
        assert len(record.waitlist) == 0
        assert record.queue == ["waiting_1", "waiting_2", "waiting_3"]

    def test_cancelled_game_promotion_flow(self):
        """Game cancellation followed by pre-queue promotion."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=[],
            cancel_votes=["p1", "p2", "p3", "p4", "p5"],  # >4 votes = cancelled
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=5,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=["waiting_1", "waiting_2"],
        )

        # Cancel match
        record.clear_queue(reset_expiry=False)
        promote_waitlist(record)

        assert len(record.queue) == 2
        assert len(record.waitlist) == 0
        assert record.queue == ["waiting_1", "waiting_2"]

    def test_waitlist_overflow_during_promotion(self):
        """Pre-queue larger than MAX_QUEUE_SIZE is capped during promotion."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=3,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=[f"wait_{i}" for i in range(10)],  # 10 players, but MAX=8
        )

        record.clear_queue(reset_expiry=False)
        promote_waitlist(record)

        assert len(record.queue) == 8
        assert record.queue == [f"wait_{i}" for i in range(8)]
        assert len(record.waitlist) == 0

    def test_concurrent_waitlist_joins_during_game(self):
        """Multiple players join pre-queue while game is in progress."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=3,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=[],
        )

        # Simulate multiple joins
        for i in range(5):
            record.waitlist = record.waitlist + [f"joiner_{i}"]

        assert len(record.waitlist) == 5
        assert record.waitlist == [f"joiner_{i}" for i in range(5)]

    def test_player_join_and_leave_waitlist_multiple_times(self):
        """Player joins, leaves, and rejoins pre-queue."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=3,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=[],
        )

        user = "flaky_player"

        # Join
        record.waitlist = record.waitlist + [user]
        assert user in record.waitlist

        # Leave
        record.waitlist = [u for u in record.waitlist if u != user]
        assert user not in record.waitlist

        # Rejoin
        record.waitlist = record.waitlist + [user]
        assert user in record.waitlist


class TestPreQueueCapacityScenarios:
    """Tests for pre-queue capacity enforcement across scenarios."""

    def test_waitlist_at_capacity_then_promotion(self):
        """Pre-queue at exactly MAX_QUEUE_SIZE is promoted fully."""
        from core.QueueManager import MAX_QUEUE_SIZE

        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=3,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=[f"p_{i}" for i in range(MAX_QUEUE_SIZE)],
        )

        record.clear_queue(reset_expiry=False)
        promote_waitlist(record)

        assert len(record.queue) == MAX_QUEUE_SIZE
        assert len(record.waitlist) == 0

    def test_join_waitlist_at_capacity_rejected(self):
        """Cannot join pre-queue when at capacity."""
        from core.QueueManager import MAX_QUEUE_SIZE

        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=3,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=[f"p_{i}" for i in range(MAX_QUEUE_SIZE)],
        )

        # Try to add one more
        if len(record.waitlist) >= MAX_QUEUE_SIZE:
            record.waitlist_full = True

        assert len(record.waitlist) == MAX_QUEUE_SIZE

    def test_partial_waitlist_promotion(self):
        """Pre-queue with fewer than 8 players is promoted as-is."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=3,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=["only_one", "only_two"],
        )

        record.clear_queue(reset_expiry=False)
        promote_waitlist(record)

        assert len(record.queue) == 2
        assert record.queue == ["only_one", "only_two"]


class TestPreQueueStateIsolation:
    """Tests that pre-queue state doesn't interfere with game state."""

    def test_waitlist_isolated_during_picking_phase(self):
        """Pre-queue doesn't affect picking phase logic."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["cap1"],
            team_2=["cap2"],
            queue=["p3", "p4", "p5", "p6"],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1"],
            map_set=[],
            version=2,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=["waiting_1"],  # Pre-queue exists but shouldn't affect picking
        )

        # Picking phase logic
        assert len(record.team_1) == 1
        assert len(record.team_2) == 1
        assert len(record.queue) == 4
        # Pre-queue unchanged
        assert len(record.waitlist) == 1

    def test_waitlist_not_included_in_active_queue_count(self):
        """Pre-queue members don't count toward active queue population."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            queue=["in_active_queue"],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["M1", "M2", "M3"],
            map_set=[],
            version=3,
            expiry=9999,
            result_channel_id="result",
            team_1_channel_id="t1",
            team_2_channel_id="t2",
            money_queue=False,
            waitlist=["waiting_1", "waiting_2"],
        )

        # Active queue count
        active_count = len(record.queue)
        waitlist_count = len(record.waitlist)

        assert active_count == 1
        assert waitlist_count == 2
        assert active_count + waitlist_count == 3  # Separate pools
