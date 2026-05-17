import pytest
from dao.QueueDao import QueueRecord


class TestQueueRecordPreQueue:
    """Test pre_queue field in QueueRecord"""

    def test_queue_record_initializes_with_empty_pre_queue(self):
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
        assert record.pre_queue == []

    def test_queue_record_initializes_with_provided_pre_queue(self):
        """Pre-queue is set when provided"""
        pre_queue_members = ["user1", "user2"]
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
            pre_queue=pre_queue_members,
        )
        assert record.pre_queue == pre_queue_members

    def test_clear_queue_does_not_wipe_pre_queue(self):
        """clear_queue() must NOT clear pre_queue"""
        pre_queue_members = ["user1", "user2"]
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
            pre_queue=pre_queue_members,
        )

        record.clear_queue(reset_expiry=False)

        # Teams and queue cleared
        assert record.team_1 == []
        assert record.team_2 == []
        assert record.queue == []

        # Pre-queue MUST survive
        assert record.pre_queue == pre_queue_members

    def test_queue_record_dict_includes_pre_queue(self):
        """QueueRecord.__dict__ includes pre_queue for serialization"""
        pre_queue_members = ["user1"]
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
            pre_queue=pre_queue_members,
        )

        record_dict = record.__dict__
        assert "pre_queue" in record_dict
        assert record_dict["pre_queue"] == pre_queue_members
