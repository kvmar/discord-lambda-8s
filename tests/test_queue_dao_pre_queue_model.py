"""Tests for pre-queue data model in QueueDao."""

import pytest
from dao.QueueDao import QueueRecord


class TestQueueRecordPreQueueField:
    """Tests for pre_queue field in QueueRecord."""

    def test_queue_record_initializes_with_empty_pre_queue(self):
        """Pre-queue defaults to empty list when not provided."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
        )
        assert hasattr(record, "pre_queue")
        assert record.pre_queue == []
        assert isinstance(record.pre_queue, list)

    def test_queue_record_initializes_with_provided_pre_queue(self):
        """Pre-queue is set when explicitly provided."""
        pre_queue_members = ["user1", "user2"]
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=pre_queue_members,
        )
        assert record.pre_queue == pre_queue_members

    def test_queue_record_dict_includes_pre_queue(self):
        """QueueRecord.__dict__ includes pre_queue for serialization."""
        pre_queue_members = ["user1"]
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=pre_queue_members,
        )

        record_dict = record.__dict__
        assert "pre_queue" in record_dict
        assert record_dict["pre_queue"] == pre_queue_members


class TestClearQueuePreservesPreQueue:
    """Tests that clear_queue() does NOT wipe pre_queue."""

    def test_clear_queue_does_not_wipe_pre_queue(self):
        """clear_queue() must NOT clear pre_queue."""
        pre_queue_members = ["user1", "user2"]
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["cap1"],
            team_2=["cap2"],
            queue=["user3"],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=pre_queue_members.copy(),
        )

        record.clear_queue(reset_expiry=False)

        # Teams and queue cleared
        assert record.team_1 == []
        assert record.team_2 == []
        assert record.queue == []
        assert record.cancel_votes == []
        assert record.team1_votes == []
        assert record.team2_votes == []
        assert record.maps == []

        # Pre-queue MUST survive
        assert record.pre_queue == pre_queue_members

    def test_clear_queue_with_expiry_reset(self):
        """clear_queue with reset_expiry=True still preserves pre_queue."""
        pre_queue_members = ["user1"]
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["cap1"],
            team_2=["cap2"],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=pre_queue_members.copy(),
        )

        original_expiry = record.expiry
        record.clear_queue(reset_expiry=True)

        # Pre-queue survives
        assert record.pre_queue == pre_queue_members
        # Expiry updated
        assert record.expiry > original_expiry

    def test_clear_empty_pre_queue(self):
        """clear_queue on empty pre_queue leaves it empty."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["cap1"],
            team_2=["cap2"],
            queue=["user3"],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=[],
        )

        record.clear_queue(reset_expiry=False)

        assert record.pre_queue == []


class TestQueueRecordImmutability:
    """Tests that pre_queue operations follow immutability patterns."""

    def test_pre_queue_append_creates_new_list(self):
        """When adding to pre_queue, create new list (immutability pattern)."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=["user1"],
        )

        original_list = record.pre_queue
        record.pre_queue = record.pre_queue + ["user2"]

        # New list created (different object)
        assert record.pre_queue is not original_list
        assert record.pre_queue == ["user1", "user2"]

    def test_pre_queue_remove_creates_new_list(self):
        """When removing from pre_queue, create new list (immutability pattern)."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=["user1", "user2"],
        )

        original_list = record.pre_queue
        new_pre_queue = [u for u in record.pre_queue if u != "user1"]
        record.pre_queue = new_pre_queue

        # New list created
        assert record.pre_queue is not original_list
        assert record.pre_queue == ["user2"]


class TestQueueRecordPreQueueEdgeCases:
    """Tests for edge cases with pre_queue field."""

    def test_pre_queue_with_none_defaults_to_empty(self):
        """Passing None for pre_queue defaults to empty list."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=None,
        )
        assert record.pre_queue == []

    def test_pre_queue_large_list(self):
        """Pre-queue can hold large lists (capacity not enforced at model layer)."""
        large_pre_queue = [f"user_{i}" for i in range(1000)]
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=large_pre_queue,
        )
        assert len(record.pre_queue) == 1000

    def test_pre_queue_with_duplicate_users(self):
        """Pre-queue can technically contain duplicates (deduplication at business logic layer)."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=[],
            team_2=[],
            queue=[],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=[],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=["user1", "user1", "user2"],
        )
        assert record.pre_queue == ["user1", "user1", "user2"]

    def test_pre_queue_isolated_from_other_queues(self):
        """Pre-queue changes don't affect other queue fields."""
        record = QueueRecord(
            guild_id="guild_123",
            queue_id="main",
            team_1=["cap1"],
            team_2=["cap2"],
            queue=["user3"],
            cancel_votes=[],
            team1_votes=[],
            team2_votes=[],
            maps=["Map1"],
            map_set=[],
            version=1,
            expiry=1000,
            result_channel_id="ch1",
            team_1_channel_id="ch2",
            team_2_channel_id="ch3",
            money_queue=False,
            pre_queue=["pre1"],
        )

        # Modify pre_queue
        record.pre_queue = record.pre_queue + ["pre2"]

        # Other fields unchanged
        assert record.team_1 == ["cap1"]
        assert record.team_2 == ["cap2"]
        assert record.queue == ["user3"]
