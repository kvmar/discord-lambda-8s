import pytest
from dao.QueueDao import QueueRecord


class TestQueueRecordPreQueue:
    """Test waitlist field in QueueRecord"""

    def test_queue_record_initializes_with_empty_waitlist(self):
        """Pre-queue defaults to empty list when not provided"""
        record = QueueRecord(
            guild_id="123",
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
        assert record.waitlist == []

    def test_queue_record_initializes_with_provided_waitlist(self):
        """Pre-queue is set when provided"""
        waitlist_members = ["user1", "user2"]
        record = QueueRecord(
            guild_id="123",
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

    def test_clear_queue_does_not_wipe_waitlist(self):
        """clear_queue() must NOT clear waitlist"""
        waitlist_members = ["user1", "user2"]
        record = QueueRecord(
            guild_id="123",
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
            waitlist=waitlist_members,
        )

        record.clear_queue(reset_expiry=False)

        # Teams and queue cleared
        assert record.team_1 == []
        assert record.team_2 == []
        assert record.queue == []

        # Pre-queue MUST survive
        assert record.waitlist == waitlist_members

    def test_queue_record_dict_includes_waitlist(self):
        """QueueRecord.__dict__ includes waitlist for serialization"""
        waitlist_members = ["user1"]
        record = QueueRecord(
            guild_id="123",
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
