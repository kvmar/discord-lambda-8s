"""Regression tests: a completed/cancelled team match deletes the live Match
Ready (lobby) message and returns None — the result is already posted to the
results channel, so the lobby message just disappears instead of being edited
into a redundant completed view."""

import pytest
from unittest.mock import MagicMock
from dao.QueueDao import QueueRecord
import core.QueueManager as QueueManager
from discord_lambda import Embedding


def _team_match_record(team1_votes=None, team2_votes=None, cancel_votes=None):
    return QueueRecord(
        guild_id="guild_123", money_queue=False, queue_id="TEAM-abc123",
        team_1=["a1", "a2", "a3", "a4"], team_2=["b1", "b2", "b3", "b4"],
        queue=[], cancel_votes=cancel_votes or [],
        team1_votes=team1_votes or [], team2_votes=team2_votes or [],
        maps=["M1", "M2", "M3"], map_set=["M1", "M2", "M3"], version=1,
        expiry=9999999999, result_channel_id="result_ch",
        team_1_channel_id="t1_ch", team_2_channel_id="t2_ch",
        channel_config={"ch": "msg"}, waitlist=[],
        is_team_queue=True, team_1_id="TID1", team_2_id="TID2",
    )


@pytest.fixture
def patched(mocker):
    qd = mocker.patch.object(QueueManager, "queue_dao")
    qd.put_queue.return_value = {"ok": True}
    ts = mocker.patch.object(QueueManager, "ts")
    tm = mocker.patch("core.TeamManager.generate_team_match_done_embed",
                      return_value=Embedding("done", "x", color=0x7c3aed))
    mocker.patch("core.TeamManager.complete_team_match")
    mocker.patch("core.TeamManager.cancel_team_match")
    mocker.patch("core.TeamLeaderboardManager.post_team_leaderboard")
    return qd, ts, tm


def _inter(user_id="a4"):
    inter = MagicMock()
    inter.guild_id = "guild_123"
    inter.user_id = user_id
    inter.send_message = MagicMock()
    return inter


def test_team_win_deletes_lobby_and_returns_none(patched):
    qd, ts, tm = patched
    # 4 votes already; this is the deciding 5th vote.
    record = _team_match_record(team1_votes=["a1", "a2", "a3", "b1"])
    qd.get_queue.return_value = record
    inter = _inter("a4")

    result = QueueManager.team_1_won(inter, "TEAM-abc123")

    assert result is None, "completion deletes the lobby message; nothing left to edit"
    ts.post_team_match.assert_called_once()
    # Result posted to the results channel, lobby message deleted.
    inter.send_message.assert_called_once()
    inter.delete_message.assert_called_once_with(message_id="msg", channel_id="ch")


def test_team_cancel_deletes_lobby_and_returns_none(patched):
    qd, ts, tm = patched
    # Match ready needs 5 cancel votes; supply 4 prior + this one.
    record = _team_match_record(cancel_votes=["a1", "a2", "a3", "b1"])
    qd.get_queue.return_value = record
    inter = _inter("a4")

    result = QueueManager.cancel_match(inter, "TEAM-abc123")

    assert result is None, "cancel deletes the lobby message; nothing left to edit"
    inter.delete_message.assert_called_once_with(message_id="msg", channel_id="ch")


def _mock_team_captains(mocker, t1_captain="a1", t2_captain="b1"):
    MockTeamDao = mocker.patch("dao.TeamDao.TeamDao")
    inst = MockTeamDao.return_value
    t1 = MagicMock(); t1.captain_id = t1_captain
    t2 = MagicMock(); t2.captain_id = t2_captain
    inst.get_team.side_effect = lambda guild_id, team_id: (
        t1 if team_id == "TID1" else t2
    )
    return inst


def test_captain_priority_team1_win_triggers_with_two_votes(patched, mocker):
    qd, ts, tm = patched
    # Only team 1 captain (a1) has voted so far; team 2 captain (b1) votes now.
    record = _team_match_record(team1_votes=["a1"])
    qd.get_queue.return_value = record
    _mock_team_captains(mocker, t1_captain="a1", t2_captain="b1")
    inter = _inter("b1")

    result = QueueManager.team_1_won(inter, "TEAM-abc123")

    assert result is None, "both captains agreed — match should complete immediately"
    ts.post_team_match.assert_called_once()
    inter.delete_message.assert_called_once_with(message_id="msg", channel_id="ch")


def test_captain_priority_team2_win_triggers_with_two_votes(patched, mocker):
    qd, ts, tm = patched
    # Only team 1 captain has voted (for team 2); team 2 captain also votes.
    record = _team_match_record(team2_votes=["a1"])
    qd.get_queue.return_value = record
    _mock_team_captains(mocker, t1_captain="a1", t2_captain="b1")
    inter = _inter("b1")

    result = QueueManager.team_2_won(inter, "TEAM-abc123")

    assert result is None, "both captains agreed — match should complete immediately"
    ts.post_team_match.assert_called_once()
    inter.delete_message.assert_called_once_with(message_id="msg", channel_id="ch")


def test_captain_priority_cancel_triggers_with_two_votes(patched, mocker):
    qd, ts, tm = patched
    # Team 1 captain already voted to cancel; team 2 captain votes now.
    record = _team_match_record(cancel_votes=["a1"])
    qd.get_queue.return_value = record
    _mock_team_captains(mocker, t1_captain="a1", t2_captain="b1")
    inter = _inter("b1")

    result = QueueManager.cancel_match(inter, "TEAM-abc123")

    assert result is None, "both captains agreed to cancel — should complete immediately"
    inter.delete_message.assert_called_once_with(message_id="msg", channel_id="ch")


def test_single_captain_vote_does_not_trigger(patched, mocker):
    qd, ts, tm = patched
    # Only one captain voted; the other has not — should NOT trigger.
    record = _team_match_record(team1_votes=[])
    qd.get_queue.return_value = record
    _mock_team_captains(mocker, t1_captain="a1", t2_captain="b1")
    inter = _inter("a1")  # only team-1 captain votes

    result = QueueManager.team_1_won(inter, "TEAM-abc123")

    assert result is not None, "only one captain voted — should not trigger completion"
    ts.post_team_match.assert_not_called()
