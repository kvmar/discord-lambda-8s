"""Tests for pre-queue data model in QueueDao."""

import pytest
from dao.QueueDao import QueueRecord


class TestQueueRecordPreQueueField:
    """Tests for waitlist field in QueueRecord."""

    def test_queue_record_initializes_with_empty_waitlist(self):
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
        assert hasattr(record, "waitlist")
        assert record.waitlist == []
        assert isinstance(record.waitlist, list)

    def test_queue_record_initializes_with_provided_waitlist(self):
        """Pre-queue is set when explicitly provided."""
        waitlist_members = ["user1", "user2"]
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
            waitlist=waitlist_members,
        )
        assert record.waitlist == waitlist_members

    def test_queue_record_dict_includes_waitlist(self):
        """QueueRecord.__dict__ includes waitlist for serialization."""
        waitlist_members = ["user1"]
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
            waitlist=waitlist_members,
        )

        record_dict = record.__dict__
        assert "waitlist" in record_dict
        assert record_dict["waitlist"] == waitlist_members


class TestClearQueuePreservesPreQueue:
    """Tests that clear_queue() does NOT wipe waitlist."""

    def test_clear_queue_does_not_wipe_waitlist(self):
        """clear_queue() must NOT clear waitlist."""
        waitlist_members = ["user1", "user2"]
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
            waitlist=waitlist_members.copy(),
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
        assert record.waitlist == waitlist_members

    def test_clear_queue_with_expiry_reset(self):
        """clear_queue with reset_expiry=True still preserves waitlist."""
        waitlist_members = ["user1"]
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
            waitlist=waitlist_members.copy(),
        )

        original_expiry = record.expiry
        record.clear_queue(reset_expiry=True)

        # Pre-queue survives
        assert record.waitlist == waitlist_members
        # Expiry updated
        assert record.expiry > original_expiry

    def test_clear_empty_waitlist(self):
        """clear_queue on empty waitlist leaves it empty."""
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
            waitlist=[],
        )

        record.clear_queue(reset_expiry=False)

        assert record.waitlist == []


class TestQueueRecordImmutability:
    """Tests that waitlist operations follow immutability patterns."""

    def test_waitlist_append_creates_new_list(self):
        """When adding to waitlist, create new list (immutability pattern)."""
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
            waitlist=["user1"],
        )

        original_list = record.waitlist
        record.waitlist = record.waitlist + ["user2"]

        # New list created (different object)
        assert record.waitlist is not original_list
        assert record.waitlist == ["user1", "user2"]

    def test_waitlist_remove_creates_new_list(self):
        """When removing from waitlist, create new list (immutability pattern)."""
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
            waitlist=["user1", "user2"],
        )

        original_list = record.waitlist
        new_waitlist = [u for u in record.waitlist if u != "user1"]
        record.waitlist = new_waitlist

        # New list created
        assert record.waitlist is not original_list
        assert record.waitlist == ["user2"]


class TestQueueRecordPreQueueEdgeCases:
    """Tests for edge cases with waitlist field."""

    def test_waitlist_with_none_defaults_to_empty(self):
        """Passing None for waitlist defaults to empty list."""
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
            waitlist=None,
        )
        assert record.waitlist == []

    def test_waitlist_large_list(self):
        """Pre-queue can hold large lists (capacity not enforced at model layer)."""
        large_waitlist = [f"user_{i}" for i in range(1000)]
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
            waitlist=large_waitlist,
        )
        assert len(record.waitlist) == 1000

    def test_waitlist_with_duplicate_users(self):
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
            waitlist=["user1", "user1", "user2"],
        )
        assert record.waitlist == ["user1", "user1", "user2"]

    def test_waitlist_isolated_from_other_queues(self):
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
            waitlist=["pre1"],
        )

        # Modify waitlist
        record.waitlist = record.waitlist + ["pre2"]

        # Other fields unchanged
        assert record.team_1 == ["cap1"]
        assert record.team_2 == ["cap2"]
        assert record.queue == ["user3"]
