"""Tests for cancel_match permission and threshold logic."""

import pytest
from unittest.mock import MagicMock, patch
from dao.QueueDao import QueueRecord
from core.QueueManager import cancel_match


def _make_record(team_1=None, team_2=None, queue=None, cancel_votes=None):
    return QueueRecord(
        guild_id="guild_123",
        queue_id="main",
        team_1=team_1 or [],
        team_2=team_2 or [],
        queue=queue or [],
        cancel_votes=cancel_votes or [],
        team1_votes=[],
        team2_votes=[],
        maps=["Map1", "Map2", "Map3"],
        map_set=["Map1", "Map2", "Map3"],
        version=1,
        expiry=9999999999,
        result_channel_id="result_ch",
        team_1_channel_id="team1_ch",
        team_2_channel_id="team2_ch",
        money_queue=False,
    )


def _make_inter(user_id="voter1"):
    inter = MagicMock()
    inter.guild_id = "guild_123"
    inter.user_id = user_id
    inter.custom_id = "cancel_match#main"
    return inter


class TestCancelMatchPermissions:

    def test_pick_phase_player_in_queue_can_cancel(self, mock_queue_dao, mock_player_dao):
        """A player in the queue can vote to cancel during pick phase."""
        record = _make_record(
            team_1=["cap1"], team_2=["cap2"],
            queue=["cap1", "cap2", "p3", "p4", "p5", "p6", "p7", "p8"],
        )
        mock_queue_dao.get_queue.return_value = record
        mock_queue_dao.put_queue.return_value = True

        inter = _make_inter(user_id="p3")
        result = cancel_match(inter, "main")

        assert result is not None
        assert "p3" in record.cancel_votes

    def test_pick_phase_outsider_cannot_cancel(self, mock_queue_dao, mock_player_dao):
        """A player NOT in the queue cannot cancel during pick phase."""
        record = _make_record(
            team_1=["cap1"], team_2=["cap2"],
            queue=["cap1", "cap2", "p3", "p4", "p5", "p6", "p7", "p8"],
        )
        mock_queue_dao.get_queue.return_value = record

        inter = _make_inter(user_id="outsider")
        result = cancel_match(inter, "main")

        assert result is None
        assert "outsider" not in record.cancel_votes

    def test_match_ready_team_member_can_cancel(self, mock_queue_dao, mock_player_dao):
        """A player on a team can vote to cancel after teams are full."""
        record = _make_record(
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
        )
        mock_queue_dao.get_queue.return_value = record
        mock_queue_dao.put_queue.return_value = True

        inter = _make_inter(user_id="p1")
        result = cancel_match(inter, "main")

        assert result is not None
        assert "p1" in record.cancel_votes

    def test_match_ready_outsider_cannot_cancel(self, mock_queue_dao, mock_player_dao):
        """A player not on either team cannot cancel after teams are full."""
        record = _make_record(
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
        )
        mock_queue_dao.get_queue.return_value = record

        inter = _make_inter(user_id="outsider")
        result = cancel_match(inter, "main")

        assert result is None
        assert "outsider" not in record.cancel_votes


class TestCancelMatchThresholds:

    def test_pick_phase_cancels_at_half_queue_size(self, mock_queue_dao, mock_player_dao):
        """Pick phase cancels when votes reach half the queue size (8 players → 4 votes)."""
        all_players = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]
        record = _make_record(
            team_1=["p1"], team_2=["p2"],
            queue=all_players,
            cancel_votes=["p1", "p2", "p3"],  # 3 votes already
        )
        cleared_record = _make_record()  # empty after clear
        mock_queue_dao.get_queue.side_effect = [record, cleared_record]
        mock_queue_dao.put_queue.return_value = True

        inter = _make_inter(user_id="p4")  # 4th vote
        cancel_match(inter, "main")

        # clear_queue should have been called — put_queue called twice
        assert mock_queue_dao.put_queue.call_count == 2

    def test_pick_phase_does_not_cancel_at_3_votes(self, mock_queue_dao, mock_player_dao):
        """Pick phase does NOT cancel at 3 votes."""
        all_players = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]
        record = _make_record(
            team_1=["p1"], team_2=["p2"],
            queue=all_players,
            cancel_votes=["p1", "p2"],  # 2 votes already
        )
        mock_queue_dao.get_queue.return_value = record
        mock_queue_dao.put_queue.return_value = True

        inter = _make_inter(user_id="p3")  # 3rd vote — not enough
        cancel_match(inter, "main")

        # put_queue called only once (no second call for clear_queue)
        assert mock_queue_dao.put_queue.call_count == 1

    def test_match_ready_cancels_at_5_votes(self, mock_queue_dao, mock_player_dao):
        """Match ready phase cancels when 5th vote is cast (half + 1)."""
        record = _make_record(
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            cancel_votes=["p1", "p2", "p3", "p4"],  # 4 votes already
        )
        cleared_record = _make_record()
        mock_queue_dao.get_queue.side_effect = [record, cleared_record]
        mock_queue_dao.put_queue.return_value = True

        inter = _make_inter(user_id="p5")  # 5th vote
        cancel_match(inter, "main")

        assert mock_queue_dao.put_queue.call_count == 2

    def test_match_ready_does_not_cancel_at_4_votes(self, mock_queue_dao, mock_player_dao):
        """Match ready phase does NOT cancel at 4 votes."""
        record = _make_record(
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            cancel_votes=["p1", "p2", "p3"],  # 3 votes already
        )
        mock_queue_dao.get_queue.return_value = record
        mock_queue_dao.put_queue.return_value = True

        inter = _make_inter(user_id="p4")  # 4th vote — not enough
        cancel_match(inter, "main")

        assert mock_queue_dao.put_queue.call_count == 1

    def test_duplicate_vote_ignored(self, mock_queue_dao, mock_player_dao):
        """A player who already voted cannot vote again."""
        record = _make_record(
            team_1=["p1", "p2", "p3", "p4"],
            team_2=["p5", "p6", "p7", "p8"],
            cancel_votes=["p1"],
        )
        mock_queue_dao.get_queue.return_value = record
        mock_queue_dao.put_queue.return_value = True

        inter = _make_inter(user_id="p1")
        cancel_match(inter, "main")

        assert record.cancel_votes.count("p1") == 1
